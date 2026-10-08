"""Shared field-level evidence policy. Values, verification and approval are independent."""

from copy import deepcopy

from .db import now

EVIDENCE_VERSION = 1


def actor_for(request=None, declared="Local reviewer"):
    if request is not None and request.app.state.security.remote:
        return {
            "actor_id": request.state.user,
            "actor_display": request.state.email,
            "actor_basis": "authenticated",
        }
    return {"actor_id": declared, "actor_display": declared, "actor_basis": "local_declared"}


def system_actor(name="system"):
    return {"actor_id": name, "actor_display": name, "actor_basis": "system"}


def evidence(value, revision, source="default", state="suggested", actor=None, source_ref=None):
    if state == "verified" and (not actor or actor["actor_basis"] == "system"):
        raise ValueError("Human verification requires attributable human identity.")
    return {
        "evidence_schema_version": EVIDENCE_VERSION,
        "state": state,
        "source": source,
        "value": value,
        "value_revision": revision,
        "recorded_at": now(),
        **(actor or system_actor()),
        "source_ref": source_ref,
    }


def suggested_labels(labels, revision=0, source="default"):
    return {key: evidence(value, revision, source) for key, value in labels.items() if key != "note"}


def transition(
    old_labels,
    old_evidence,
    labels,
    revision,
    actor,
    verify_fields=(),
    invalidate=(),
    invalidate_source="paste",
):
    result = deepcopy(old_evidence or {})
    for key, value in labels.items():
        if key == "note":
            continue
        if key in verify_fields:
            result[key] = evidence(value, revision, "explicit_confirmation", "verified", actor)
        elif key in invalidate or value != old_labels.get(key) or key not in result:
            result[key] = evidence(
                value, revision, invalidate_source if key in invalidate else "edit", actor=actor
            )
    return result


def is_verified(item, value):
    return bool(
        item
        and item.get("evidence_schema_version") == EVIDENCE_VERSION
        and item.get("state") == "verified"
        and item.get("value") == value
        and item.get("actor_basis") in ("authenticated", "local_declared")
        and item.get("actor_id")
        and item.get("recorded_at")
        and isinstance(item.get("value_revision"), int)
        and item["value_revision"] >= 0
    )


def exclusion_reasons(example, photo=None, shoot=None, field="shot_type"):
    reasons = []
    if not example.eligible:
        reasons.append("not_approved")
    if (
        example.deleted_at
        or (photo and photo.deleted_at)
        or (shoot and (shoot.deleted_at or shoot.training_deleted_at))
    ):
        reasons.append("inactive_membership")
    value = example.labels.get(field)
    if value in (None, "unknown"):
        reasons.append("unknown_value")
    if not is_verified((example.label_evidence or {}).get(field), value):
        reasons.append("unverified_label")
    return reasons


def training_response(example, photo=None, shoot=None):
    from sqlalchemy import inspect

    reasons = exclusion_reasons(example, photo, shoot)
    return {col.key: getattr(example, col.key) for col in inspect(example).mapper.column_attrs} | {
        "exportable": not reasons,
        "exclusion_reasons": reasons,
    }


def resolve_shot(photo, predicted=None, confidence=None, model_id=None, run_id=None):
    prediction = None
    if predicted is not None:
        prediction = {
            "evidence_schema_version": EVIDENCE_VERSION,
            "state": "predicted",
            "value": predicted,
            "confidence": confidence,
            "model_id": model_id,
            "run_id": run_id,
            "source": "model",
        }
    if (
        photo.shot_type != "unknown"
        and is_verified(photo.shot_evidence, photo.shot_type)
        and photo.shot_evidence["value_revision"] == photo.shot_revision
    ):
        return photo.shot_type, deepcopy(photo.shot_evidence), prediction
    if predicted and predicted != "unknown" and confidence is not None and confidence >= 0.8:
        return predicted, prediction, prediction
    return "unknown", {"state": "unresolved", "reason_code": "needs_verified_label_or_prediction"}, prediction


def coverage_state(checks):
    return (
        "complete"
        if checks
        and all(
            c["applicability"] == "not_applicable"
            or (c["applicability"] == "applicable" and c["execution"] == "completed")
            for c in checks
        )
        else "incomplete"
    )


def run_envelope(session, shoot, photos):
    from sqlalchemy import select
    from .db import Measurement, Run

    run = session.get(Run, shoot.current_run_id) if shoot.current_run_id else None
    if not run or not run.evidence_schema_version:
        return {
            "evidence_schema_version": 0,
            "run_id": shoot.current_run_id,
            "score_scope": "technical_baseline",
            "coverage": "unknown",
            "freshness": "historical_unknown",
            "checks": [],
        }
    snapshots = {
        m.photo_id: m.context.get("evidence", {})
        for m in session.scalars(select(Measurement).where(Measurement.run_id == run.id))
    }
    stale = set(snapshots) != {p.id for p in photos} or any(
        snapshots.get(p.id, {}).get("shot_revision") != p.shot_revision for p in photos
    )
    stale = stale or run.policy_snapshot != shoot.policy or shoot.status != "complete"
    checks = run.check_results or []
    return {
        "evidence_schema_version": run.evidence_schema_version,
        "run_id": run.id,
        "score_scope": "technical_baseline",
        "coverage": coverage_state(checks),
        "freshness": "stale" if stale else "current",
        "checks": deepcopy(checks),
    }
