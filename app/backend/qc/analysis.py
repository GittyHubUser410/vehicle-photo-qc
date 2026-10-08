from __future__ import annotations

import logging
import threading

import cv2
import numpy as np
from PIL import Image, ImageOps
from sqlalchemy import select

from .evidence import EVIDENCE_VERSION, resolve_shot
from .db import Issue, Measurement, ModelVersion, Photo, Review, Run, Shoot, now
from .media import resolved_file
from .banner import banner_region, banner_overlap

PIPELINE_VERSION = "technical-baseline-0.1"
LOG = logging.getLogger(__name__)


def technical_metrics(path, rules):
    with Image.open(path) as im:
        image = ImageOps.exif_transpose(im).convert("RGB")
        image.thumbnail((1024, 1024))
        rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    metrics = {
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 3),
        "brightness": round(float(gray.mean()) / 255, 4),
        "shadow_clipping": round(float(np.mean(gray <= 10)), 4),
        "highlight_clipping": round(float(np.mean(gray >= 245)), 4),
        "saturation": round(float(hsv[:, :, 1].mean()) / 255, 4),
    }
    findings = []
    if metrics["sharpness"] < rules["blur_min"]:
        severe = metrics["sharpness"] < rules["blur_min"] / 3
        findings.append(
            (
                "BLUR",
                "severe" if severe else "moderate",
                "Possible blur or low texture. Inspect the vehicle at full size.",
            )
        )
    if metrics["shadow_clipping"] > rules["dark_max"]:
        findings.append(
            (
                "EXPOSURE",
                "moderate",
                "A large portion of the image is very dark. Check whether vehicle detail is visible.",
            )
        )
    if metrics["highlight_clipping"] > rules["bright_max"]:
        findings.append(
            (
                "EXPOSURE",
                "moderate",
                "A large portion of the image is very bright. Check for lost highlight detail.",
            )
        )
    if metrics["saturation"] > rules["saturation_max"]:
        findings.append(
            (
                "SATURATION",
                "minor",
                "Strong overall saturation. Check whether the vehicle color looks natural.",
            )
        )
    score = max(0, 100 - sum({"severe": 35, "moderate": 20, "minor": 10}[s] for _, s, _ in findings))
    return metrics, float(score), findings


def coverage_findings(shot_types: list[str], rules: dict, general: bool):
    if general:
        return [], "not_applicable"
    findings = []
    if len(shot_types) < rules["min_photos"]:
        findings.append(
            (
                "PHOTO_COUNT",
                "moderate",
                f"{len(shot_types)} photos uploaded; at least {rules['min_photos']} are required.",
            )
        )
    required = rules["required_shots"]
    if not required:
        return findings, "not_configured"
    if "unknown" in shot_types:
        return findings, "needs_shot_labels"
    missing = [shot for shot in required if shot not in shot_types]
    if missing:
        findings.append(
            (
                "MISSING_REQUIRED_SHOT",
                "severe",
                "Missing required shots: " + ", ".join(s.replace("_", " ") for s in missing),
            )
        )
    elif rules["strict_sequence"]:
        # Required shots must appear as an ordered subsequence; optional shots may intervene.
        cursor = 0
        for shot in shot_types:
            if cursor < len(required) and shot == required[cursor]:
                cursor += 1
        if cursor != len(required):
            findings.append(
                ("SEQUENCE", "moderate", "Required shots are present but not in the configured order.")
            )
    return findings, "checked"


def check_record(
    check_id,
    run,
    applicability="applicable",
    execution="completed",
    outcome="pass",
    reason="measured",
    photo_id=None,
    inputs=None,
):
    return {
        "check_id": check_id,
        "applicability": applicability,
        "execution": execution,
        "outcome": outcome,
        "reason_code": reason,
        "scope": "photo" if photo_id else "shoot",
        "photo_id": photo_id,
        "input_provenance": inputs or {},
        "run_id": run.id,
        "rule_version": {
            "dealer": run.policy_snapshot.get("dealer_version"),
            "group": run.policy_snapshot.get("group_version"),
        },
        "model_id": run.model_version_id,
        "pipeline_version": run.pipeline_version,
    }


def photo_checks(run, photo, findings, resolved, inputs, region, prediction_error=False):
    records = [
        check_record(
            key,
            run,
            outcome="concern" if any(f[0] == kind for f in findings) else "pass",
            photo_id=photo.id,
            inputs=inputs,
        )
        for key, kind in (("blur", "BLUR"), ("exposure", "EXPOSURE"), ("saturation", "SATURATION"))
    ]
    records.append(
        check_record(
            "shot_classification",
            run,
            execution=(
                "error"
                if prediction_error
                else "completed"
                if resolved != "unknown"
                else "not_run"
                if run.model_version_id
                else "unavailable"
            ),
            outcome="pass" if resolved != "unknown" and not prediction_error else "unknown",
            reason="prediction_error"
            if prediction_error
            else "resolved"
            if resolved != "unknown"
            else "unresolved_shot",
            photo_id=photo.id,
            inputs=inputs,
        )
    )
    for key in ("vehicle_segmentation", "critical_crop", "angle"):
        records.append(
            check_record(
                key,
                run,
                applicability="unknown" if resolved == "unknown" else "applicable",
                execution="unavailable",
                outcome="unknown",
                reason="detector_unavailable",
                photo_id=photo.id,
                inputs=inputs,
            )
        )
    applies = region["applicable"]
    records.append(
        check_record(
            "banner_clearance",
            run,
            applicability="unknown" if applies is None else "applicable" if applies else "not_applicable",
            execution="unavailable" if applies else "not_run",
            outcome="unknown",
            reason="needs_shot_label"
            if applies is None
            else "geometry_unavailable"
            if applies
            else "banner_disabled_or_out_of_scope",
            photo_id=photo.id,
            inputs=inputs,
        )
    )
    return records


def shoot_checks(run, shoot, shots, findings, provenance):
    rules = shoot.policy["rules"]
    general = shoot.mode == "general"
    records = [
        check_record(
            "photo_count",
            run,
            applicability="not_applicable" if general or not rules["min_photos"] else "applicable",
            execution="not_run" if general or not rules["min_photos"] else "completed",
            outcome="unknown"
            if general or not rules["min_photos"]
            else "concern"
            if any(f[0] == "PHOTO_COUNT" for f in findings)
            else "pass",
            reason="general_mode" if general else "not_configured" if not rules["min_photos"] else "counted",
            inputs={"photo_count": len(shots)},
        )
    ]
    for key, kinds in (("required_shots", ["MISSING_REQUIRED_SHOT"]), ("sequence", ["SEQUENCE"])):
        applicable = (
            not general and bool(rules["required_shots"]) and (key != "sequence" or rules["strict_sequence"])
        )
        unresolved = "unknown" in shots
        records.append(
            check_record(
                key,
                run,
                applicability="applicable" if applicable else "not_applicable",
                execution="not_run" if not applicable or unresolved else "completed",
                outcome="unknown"
                if not applicable or unresolved
                else "concern"
                if any(
                    f[0] in kinds + (["MISSING_REQUIRED_SHOT"] if key == "sequence" else []) for f in findings
                )
                else "pass",
                reason="general_mode"
                if general
                else "not_configured"
                if not applicable
                else "unresolved_shot"
                if unresolved
                else "checked",
                inputs={"shots": provenance},
            )
        )
    return records


def analyze_shoot(factory, data, shoot_id: str):
    with factory() as session:
        shoot = session.get(Shoot, shoot_id)
        if not shoot or shoot.status != "queued":
            return
        shoot.status, shoot.error = "processing", None
        active = session.scalar(select(ModelVersion).where(ModelVersion.status == "active"))
        run = Run(
            shoot_id=shoot.id,
            pipeline_version=PIPELINE_VERSION,
            policy_snapshot=shoot.policy,
            model_version_id=active.id if active else None,
            evidence_schema_version=EVIDENCE_VERSION,
        )
        session.add(run)
        session.commit()
        run_id = run.id
        try:
            photos = session.scalars(
                select(Photo).where(Photo.shoot_id == shoot.id).order_by(Photo.position)
            ).all()
            scores, shot_types, computed, all_checks, provenance = [], [], [], [], []
            for rank, photo in enumerate(photos, 1):
                path = resolved_file(data, photo.original_key)
                metrics, score, findings = technical_metrics(path, shoot.policy["rules"])
                predicted, confidence = None, None
                prediction_error = False
                if active:
                    from .classifier import predict

                    try:
                        predicted, confidence = predict(
                            resolved_file(data, active.artifact_key), active.classes, path
                        )
                    except Exception:
                        LOG.exception("Shot prediction failed for %s", photo.id)
                        prediction_error = True
                resolved, used, prediction = resolve_shot(
                    photo, predicted, confidence, run.model_version_id, run.id
                )
                shot_types.append(resolved)
                inputs = {
                    "shot_revision": photo.shot_revision,
                    "shot_evidence": photo.shot_evidence,
                    "resolved_shot": resolved,
                    "used_evidence": used,
                    "prediction": prediction,
                }
                provenance.append(inputs)
                region = banner_region(shoot.policy["rules"], rank, resolved)
                checks = photo_checks(run, photo, findings, resolved, inputs, region, prediction_error)
                all_checks.extend(checks)
                context = {
                    "banner": region,
                    "banner_overlap": banner_overlap(region),
                    "evidence": {"evidence_schema_version": EVIDENCE_VERSION, **inputs, "checks": checks},
                }
                computed.append((photo.id, metrics, score, predicted, confidence, findings, context))
                scores.append(score)
            # Keep expensive image/model work outside the SQLite write transaction so
            # reviewers can keep saving notes while a large shoot is being analyzed.
            for photo_id, metrics, score, predicted, confidence, findings, context in computed:
                session.add(
                    Measurement(
                        run_id=run.id,
                        photo_id=photo_id,
                        score=score,
                        metrics=metrics,
                        context=context,
                        predicted_shot=predicted,
                        confidence=confidence,
                    )
                )
                add_findings(session, shoot, run.id, photo_id, findings)
            findings, coverage = coverage_findings(shot_types, shoot.policy["rules"], shoot.mode == "general")
            add_findings(session, shoot, run.id, None, findings)
            all_checks.extend(shoot_checks(run, shoot, shot_types, findings, provenance))
            run.check_results = all_checks
            shoot.score = round(sum(scores) / len(scores), 1) if scores else None
            shoot.checks = {
                "technical": "baseline",
                "required_shots": coverage,
                "shot_classification": "active_model" if active else "manual_only",
                "vehicle_segmentation": "unavailable",
                "critical_crop": "unavailable",
                "angle": "unavailable",
                "banner_clearance": "preview_only",
            }
            shoot.current_run_id, shoot.status = run.id, "complete"
            run.completed_at, run.status = now(), "complete"
            session.commit()
        except Exception:
            LOG.exception("Analysis failed for shoot %s", shoot_id)
            session.rollback()
            shoot = session.get(Shoot, shoot_id)
            run = session.get(Run, run_id)
            shoot.status = "failed"
            shoot.error = "Analysis could not finish. Check the server log, original files, and active model; then retry."
            run.status, run.completed_at = "failed", now()
            run.check_results = [
                check_record(
                    key,
                    run,
                    execution="error" if key in ("blur", "exposure", "saturation") else "not_run",
                    outcome="unknown",
                    reason="analysis_failed",
                )
                for key in (
                    "blur",
                    "exposure",
                    "saturation",
                    "photo_count",
                    "required_shots",
                    "sequence",
                    "shot_classification",
                    "vehicle_segmentation",
                    "critical_crop",
                    "angle",
                    "banner_clearance",
                )
            ]
            session.commit()


def add_findings(session, shoot, run_id, photo_id, findings):
    for kind, severity, description in findings:
        session.add(
            Issue(
                run_id=run_id,
                shoot_id=shoot.id,
                photo_id=photo_id,
                kind=kind,
                severity=severity,
                description=description,
            )
        )
    if findings and shoot.purpose == "evaluation":
        # Keep an open review across reruns. Never silently resolve a manager's work item.
        existing = session.scalar(
            select(Review).where(
                Review.shoot_id == shoot.id, Review.photo_id == photo_id, Review.resolved_at.is_(None)
            )
        )
        if not existing:
            severity = min(
                (s for _, s, _ in findings), key=lambda x: ["severe", "moderate", "minor"].index(x)
            )
            session.add(
                Review(
                    shoot_id=shoot.id,
                    photo_id=photo_id,
                    run_id=run_id,
                    severity=severity,
                    reason=" ".join(d for _, _, d in findings),
                )
            )


class Worker:
    """Single-process durable queue. SQLite shoot states survive app restarts."""

    def __init__(self, factory, data):
        self.factory, self.data = factory, data
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True, name="qc-worker")

    def start(self):
        with self.factory() as session:
            for shoot in session.scalars(select(Shoot).where(Shoot.status == "processing")):
                shoot.status = "queued"
            for run in session.scalars(select(Run).where(Run.status == "running")):
                run.status, run.completed_at = "interrupted", now()
            session.commit()
        self.thread.start()

    def loop(self):
        while not self.stop_event.is_set():
            try:
                with self.factory() as session:
                    shoot_id = session.scalar(
                        select(Shoot.id).where(Shoot.status == "queued").order_by(Shoot.created_at).limit(1)
                    )
                if shoot_id:
                    analyze_shoot(self.factory, self.data, shoot_id)
                else:
                    self.stop_event.wait(0.5)
            except Exception:
                LOG.exception("Worker loop failed")
                self.stop_event.wait(2)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=30)
