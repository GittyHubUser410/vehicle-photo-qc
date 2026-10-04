"""Small, backward-compatible library editing and collection guidance workflows."""

import re
from collections import defaultdict
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select

from .db import Dealer, Group, Photo, Photographer, Shoot, ShotType, TrainingExample, now
from .schemas import ShotEditInput, ShotOrderInput, TrainingMembershipInput, VehicleEditInput
from .workflows import change_labels, training_example


def display_filename(session, shoot, photo):
    dealer = session.get(Dealer, shoot.dealership_id) if shoot.dealership_id else None
    parts = [shoot.year, shoot.make, shoot.model, dealer.name if dealer else shoot.source, shoot.stock_number]
    name = "_".join(str(p).strip() for p in parts if p) or "Vehicle"
    name = re.sub(r"[^\w-]+", "_", name, flags=re.UNICODE).strip("_")[:160]
    extension = Path(photo.original_key).suffix.lower() or Path(photo.original_filename).suffix.lower()
    return f"{name}_{photo.position:03d}{extension}"


def register_library_routes(app, factory, policy_for, required):
    @app.put("/api/shot-types/order")
    def order_shots(body: ShotOrderInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            items = list(session.scalars(select(ShotType).where(ShotType.archived.is_(False))))
            if len(body.keys) != len(set(body.keys)) or set(body.keys) != {x.key for x in items}:
                raise HTTPException(409, "Shot types changed. Refresh the list before reordering.")
            positions = {key: i for i, key in enumerate(body.keys)}
            for item in items:
                item.position = positions[item.key]
            session.commit()
            return {"updated": len(items)}

    @app.patch("/api/shot-types/{key}")
    def edit_shot(key: str, body: ShotEditInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            item = required(session, ShotType, key)
            if body.name and session.scalar(
                select(ShotType.key).where(
                    func.lower(ShotType.label) == body.name.lower(), ShotType.key != key
                )
            ):
                raise HTTPException(409, "That shot type name already exists.")
            if body.archived and key in ("unknown", "other"):
                raise HTTPException(
                    422, "Other and Unassigned are fallback categories and must remain available."
                )
            if body.archived:
                rules = [g.rules for g in session.scalars(select(Group))]
                for dealer in session.scalars(select(Dealer)):
                    rules.extend([dealer.new_rules, dealer.used_rules])
                if any(
                    key in r.get("required_shots", []) or key in r.get("banner_shot_types", []) for r in rules
                ):
                    raise HTTPException(
                        409,
                        "Remove this category from current dealership/group rules before deleting it. Historical shoots remain unchanged.",
                    )
            if body.name:
                item.label = body.name
            if body.archived is not None:
                item.archived = body.archived
                if not body.archived:
                    item.position = (session.scalar(select(func.max(ShotType.position))) or 0) + 1
            session.commit()
            return {"key": key, "label": item.label, "archived": item.archived}

    @app.put("/api/shoots/{shoot_id}")
    def edit_vehicle(shoot_id: str, body: VehicleEditInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            shoot = required(session, Shoot, shoot_id)
            if shoot.status in ("queued", "processing"):
                raise HTTPException(409, "Wait for analysis to finish before editing this vehicle.")
            if shoot.metadata_revision != body.metadata_revision:
                raise HTTPException(409, "This vehicle was edited elsewhere. Close and reopen the editor.")
            if body.photographer_id:
                required(session, Photographer, body.photographer_id)
            policy = policy_for(session, body.dealership_id, body.inventory_type)
            policy_changed = (shoot.dealership_id, shoot.inventory_type, shoot.mode) != (
                body.dealership_id,
                body.inventory_type,
                body.mode,
            )
            values = body.model_dump(
                mode="json", exclude={"purpose", "shot_types", "metadata_revision", "season"}
            )
            for key, value in values.items():
                setattr(shoot, key, value)
            if body.season:
                shoot.season, shoot.season_source = body.season, "manual"
            else:
                month = body.shoot_date.month
                shoot.season = (
                    "winter"
                    if month in (12, 1, 2)
                    else "spring"
                    if month < 6
                    else "summer"
                    if month < 9
                    else "autumn"
                )
                shoot.season_source = "northern_meteorological"
            shoot.metadata_revision += 1
            if policy_changed:
                # Existing runs retain their policy_snapshot; the new run uses the corrected dealership.
                shoot.policy, shoot.status, shoot.score, shoot.error = policy, "queued", None, None
            session.commit()
            return {"id": shoot.id, "reanalysis": policy_changed}

    @app.put("/api/shoots/{shoot_id}/training-membership")
    def membership(shoot_id: str, body: TrainingMembershipInput):
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            shoot = required(session, Shoot, shoot_id)
            if shoot.training_deleted_at:
                raise HTTPException(409, "Restore this vehicle from Training Trash first.")
            photos = list(session.scalars(select(Photo).where(Photo.shoot_id == shoot_id)))
            if body.photo_ids is not None:
                if set(body.photo_ids) - {p.id for p in photos}:
                    raise HTTPException(422, "Select only active photos from this vehicle.")
                photos = [p for p in photos if p.id in body.photo_ids]
            for photo in photos:
                example = session.scalar(
                    select(TrainingExample)
                    .where(TrainingExample.photo_id == photo.id)
                    .execution_options(include_deleted=True)
                )
                if body.enabled:
                    if example and example.deleted_at:
                        example.deleted_at = None
                        # Restore preserved labels, but never silently reapprove an old example.
                        change_labels(
                            session,
                            example,
                            dict(example.labels),
                            actor="Training membership",
                            eligible=False,
                        )
                    elif not example:
                        training_example(session, photo)
                elif example and not example.deleted_at:
                    change_labels(
                        session, example, dict(example.labels), actor="Training membership", eligible=False
                    )
                    example.deleted_at = now()
            session.commit()
            return {"updated": len(photos), "enabled": body.enabled}

    @app.get("/api/training/readiness")
    def readiness():
        with factory() as session:
            rows = session.execute(
                select(TrainingExample, Photo, Shoot)
                .join(Photo, TrainingExample.photo_id == Photo.id)
                .join(Shoot, Photo.shoot_id == Shoot.id)
                .where(Shoot.training_deleted_at.is_(None))
            ).all()
            catalog = list(
                session.scalars(
                    select(ShotType).where(ShotType.archived.is_(False)).order_by(ShotType.position)
                )
            )
            by_class, by_dealer, by_quality = defaultdict(set), defaultdict(set), defaultdict(set)
            shoots = defaultdict(set)
            approved, ready, unknown = 0, set(), 0
            for example, photo, shoot in rows:
                if not example.eligible:
                    continue
                approved += 1
                shot = example.labels.get("shot_type", "unknown")
                if shot == "unknown":
                    unknown += 1
                    continue
                ready.add(photo.sha256)
                by_class[shot].add(photo.sha256)
                # Count known vehicles together, even across repeat shoots.
                shoots[shot].add(
                    (shoot.dealership_id or shoot.source, shoot.stock_number.casefold() or shoot.id)
                )
                by_dealer[shoot.dealership_id or "general"].add(photo.sha256)
                for quality in ("blur", "exposure", "crop", "saturation", "framing", "angle", "overall"):
                    if example.labels.get(quality) not in (None, "unknown", "good"):
                        by_quality[quality].add(photo.sha256)
            dealers = {d.id: d.name for d in session.scalars(select(Dealer))}
            return {
                "total": len(rows),
                "approved": approved,
                "unique_labeled": len(ready),
                "unassigned": unknown,
                "classes": [
                    {
                        "key": c.key,
                        "label": c.label,
                        "count": len(by_class[c.key]),
                        "vehicles": len(shoots[c.key]),
                        "target": 50,
                    }
                    for c in catalog
                    if c.key != "unknown"
                ],
                "quality": [
                    {"key": key, "count": len(by_quality[key]), "target": 20}
                    for key in ("blur", "exposure", "crop", "saturation", "framing", "angle", "overall")
                ],
                "dealerships": [
                    {"name": dealers.get(key, "General / external sources"), "count": len(values)}
                    for key, values in by_dealer.items()
                ],
            }
