from __future__ import annotations

import logging
import threading

import cv2
import numpy as np
from PIL import Image, ImageOps
from sqlalchemy import select

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
        )
        session.add(run)
        session.commit()
        run_id = run.id
        try:
            photos = session.scalars(
                select(Photo).where(Photo.shoot_id == shoot.id).order_by(Photo.position)
            ).all()
            scores, shot_types, computed = [], [], []
            for rank, photo in enumerate(photos, 1):
                path = resolved_file(data, photo.original_key)
                metrics, score, findings = technical_metrics(path, shoot.policy["rules"])
                predicted, confidence = None, None
                if active:
                    from .classifier import predict

                    predicted, confidence = predict(
                        resolved_file(data, active.artifact_key), active.classes, path
                    )
                shot_types.append(
                    photo.shot_type
                    if photo.shot_type != "unknown"
                    else (predicted if confidence and confidence >= 0.8 else "unknown")
                )
                region = banner_region(shoot.policy["rules"], rank, shot_types[-1])
                context = {"banner": region, "banner_overlap": banner_overlap(region)}
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
