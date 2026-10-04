import re

from fastapi import HTTPException
from sqlalchemy import func, select

from .catalog import QUALITY_KEYS
from .db import Photo, Shoot, ShotType, TrainingExample, now
from .schemas import NameInput, PasteInput, TrashInput
from .workflows import change_labels, suggested_sequence, training_example


def register_workflow_routes(app, factory, policy_for, required):
    @app.get("/api/sequence")
    def sequence(dealership_id: str = "", inventory_type: str = "used"):
        with factory() as session:
            policy = policy_for(session, dealership_id or None, inventory_type)
            return suggested_sequence(session, dealership_id or None, inventory_type, policy)

    @app.post("/api/shot-types", status_code=201)
    def add_shot_type(body: NameInput):
        with factory() as session:
            if session.scalar(select(ShotType.key).where(func.lower(ShotType.label) == body.name.lower())):
                raise HTTPException(409, "That shot type already exists.")
            key = re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_")[:70]
            if not key or not key[0].isalpha():
                key = "custom_" + key
            if session.get(ShotType, key):
                raise HTTPException(409, "A shot type with this identifier already exists.")
            item = ShotType(
                key=key,
                label=body.name,
                position=(session.scalar(select(func.max(ShotType.position))) or 0) + 1,
            )
            session.add(item)
            session.commit()
            return {"key": key, "label": body.name}

    @app.post("/api/training/paste")
    def paste(body: PasteInput):
        ids = [target.photo_id for target in body.targets]
        if len(ids) != len(set(ids)):
            raise HTTPException(422, "Select each target once.")
        patch = {key: body.labels.model_dump()[key] for key in QUALITY_KEYS + ["note"]}
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            for target in body.targets:
                photo = required(session, Photo, target.photo_id)
                shoot = required(session, Shoot, photo.shoot_id)
                if shoot.training_deleted_at:
                    raise HTTPException(409, "A target vehicle's training membership is in Trash.")
                current = session.scalar(
                    select(TrainingExample)
                    .where(TrainingExample.photo_id == photo.id)
                    .execution_options(include_deleted=True)
                )
                if (current.revision if current else None) != target.revision:
                    raise HTTPException(409, "A selected photo's labels changed. Reload before pasting.")
                example = training_example(session, photo)
                # Normal and training shot types stay independent of copied quality labels.
                change_labels(session, example, {**example.labels, **patch}, body.actor, eligible=False)
            session.commit()
            return {"updated": len(ids), "approval": "Review pasted labels and approve before training."}

    def ensure_idle(shoot):
        if shoot.status in ("queued", "processing"):
            raise HTTPException(
                409, "Wait for this vehicle's analysis to finish before moving it to or from Trash."
            )

    def revoke(session, photo_ids):
        for example in session.scalars(
            select(TrainingExample).where(TrainingExample.photo_id.in_(photo_ids))
        ):
            # Record changed approval and invalidate stale editor revisions; never change labels.
            change_labels(session, example, dict(example.labels), actor="Trash", eligible=False)

    @app.post("/api/shoots/{shoot_id}/trash")
    def trash_shoot(shoot_id: str, body: TrashInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            shoot = required(session, Shoot, shoot_id)
            ensure_idle(shoot)
            stamp = now()
            if body.scope == "training":
                shoot.training_deleted_at = stamp
            else:
                shoot.deleted_at = stamp
            ids = list(session.scalars(select(Photo.id).where(Photo.shoot_id == shoot.id)))
            revoke(session, ids)
            session.commit()
            return {"status": "trashed", "scope": body.scope}

    @app.post("/api/photos/{photo_id}/trash")
    def trash_photo(photo_id: str, body: TrashInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            photo = required(session, Photo, photo_id)
            shoot = required(session, Shoot, photo.shoot_id)
            ensure_idle(shoot)
            revoke(session, [photo.id])
            if body.scope == "training":
                example = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == photo.id))
                if not example:
                    raise HTTPException(404, "Photo is not in the Training Library.")
                example.deleted_at = now()
            else:
                photo.deleted_at = now()
                shoot.status, shoot.score = "queued", None
            session.commit()
            return {"status": "trashed", "scope": body.scope}

    @app.get("/api/trash")
    def trash_list():
        items = []
        with factory(info={"include_deleted": True}) as session:
            shoots = {s.id: s for s in session.scalars(select(Shoot))}
            for shoot in shoots.values():
                scope = "all" if shoot.deleted_at else "training" if shoot.training_deleted_at else None
                if scope:
                    items.append(
                        {
                            "kind": "shoot",
                            "id": shoot.id,
                            "scope": scope,
                            "title": shoot.stock_number or "Vehicle shoot",
                            "deleted_at": shoot.deleted_at or shoot.training_deleted_at,
                        }
                    )
            for photo in session.scalars(select(Photo)):
                shoot = shoots[photo.shoot_id]
                if shoot.deleted_at:
                    continue
                training = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == photo.id))
                scope = (
                    "all"
                    if photo.deleted_at
                    else "training"
                    if training and training.deleted_at and not shoot.training_deleted_at
                    else None
                )
                if scope:
                    items.append(
                        {
                            "kind": "photo",
                            "id": photo.id,
                            "scope": scope,
                            "title": f"{shoot.stock_number or 'Vehicle'} · {photo.original_filename}",
                            "deleted_at": photo.deleted_at or training.deleted_at,
                        }
                    )
        return sorted(items, key=lambda item: item["deleted_at"], reverse=True)

    @app.post("/api/trash/{kind}/{item_id}/restore")
    def restore(kind: str, item_id: str, body: TrashInput):
        if kind not in ("shoot", "photo"):
            raise HTTPException(422, "Unsupported trash item")
        with factory(info={"include_deleted": True}) as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            obj = session.get(Shoot if kind == "shoot" else Photo, item_id)
            if obj is None:
                raise HTTPException(404)
            shoot = obj if kind == "shoot" else session.get(Shoot, obj.shoot_id)
            ensure_idle(shoot)
            if kind == "photo" and shoot.deleted_at:
                raise HTTPException(409, "Restore the vehicle first.")
            if body.scope == "all":
                obj.deleted_at = None
                if kind == "photo":
                    shoot.status, shoot.score = "queued", None
            elif kind == "shoot":
                if shoot.deleted_at:
                    raise HTTPException(409, "Restore the vehicle from all storage first.")
                shoot.training_deleted_at = None
            else:
                if shoot.training_deleted_at or obj.deleted_at:
                    raise HTTPException(409, "Restore the vehicle/photo first.")
                example = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == obj.id))
                if not example:
                    raise HTTPException(404)
                example.deleted_at = None
            session.commit()
            return {"status": "restored", "approval": "Training eligibility remains off until reviewed."}
