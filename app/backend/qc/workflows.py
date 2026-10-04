import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select

from .catalog import DEFAULT_SEQUENCE, good_labels
from .db import DealerSequence, LabelRevision, Photo, ShotType, TrainingExample, now


def validate_shots(session, values):
    known = set(session.scalars(select(ShotType.key)))
    if set(values) - known:
        raise HTTPException(422, "Unknown shot category. Add it in Dealership Setup first.")


def validate_rules(session, overrides):
    validate_shots(session, overrides.get("required_shots", []) + overrides.get("banner_shot_types", []))


def sequence_signature(policy):
    rules = policy["rules"]
    return hashlib.sha256(
        json.dumps([rules.get("required_shots", []), rules.get("strict_sequence", False)]).encode()
    ).hexdigest()


def suggested_sequence(session, dealer_id, inventory, policy):
    active = set(session.scalars(select(ShotType.key).where(ShotType.archived.is_(False))))

    def clean(sequence):
        return [key if key in active else "unknown" for key in sequence]

    memory = session.get(DealerSequence, (dealer_id, inventory)) if dealer_id else None
    if memory and memory.rules_signature == sequence_signature(policy):
        return {"sequence": clean(memory.sequence), "source": "Last-used dealership sequence"}
    configured = policy["rules"].get("required_shots", [])
    return {
        "sequence": clean(configured or DEFAULT_SEQUENCE),
        "source": "Dealership-required sequence" if configured else "Default exterior sequence",
    }


def remember_sequence(session, shoot, live_policy):
    if not shoot.dealership_id or sequence_signature(shoot.policy) != sequence_signature(live_policy):
        return  # Editing an old shoot must not revive a superseded dealership sequence.
    sequence = list(
        session.scalars(select(Photo.shot_type).where(Photo.shoot_id == shoot.id).order_by(Photo.position))
    )
    key = (shoot.dealership_id, shoot.inventory_type)
    memory = session.get(DealerSequence, key)
    if memory is None:
        memory = DealerSequence(dealership_id=key[0], inventory_type=key[1])
        session.add(memory)
    memory.sequence, memory.rules_signature, memory.updated_at = (
        sequence,
        sequence_signature(live_policy),
        now(),
    )


def change_labels(session, example, labels, actor="Local reviewer", eligible=False):
    example.labels, example.eligible = labels, eligible
    example.revision += 1
    example.updated_at, example.labeled_by = now(), actor
    session.add(
        LabelRevision(
            example_id=example.id, revision=example.revision, labels=labels, eligible=eligible, actor=actor
        )
    )


def training_example(session, photo, origin="operational_photo"):
    example = session.scalar(
        select(TrainingExample)
        .where(TrainingExample.photo_id == photo.id)
        .execution_options(include_deleted=True)
    )
    if example and example.deleted_at:
        raise HTTPException(409, "This training photo is in Trash. Restore it before editing.")
    if not example:
        example = TrainingExample(
            photo_id=photo.id, origin=origin, labels=good_labels(photo.shot_type), eligible=True
        )
        session.add(example)
        session.flush()
    return example
