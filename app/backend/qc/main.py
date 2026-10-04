from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import String, cast, func, inspect, or_, select, update
from sqlalchemy.exc import IntegrityError
from .security import configure_security

from .analysis import Worker
from .banner import banner_region, banner_overlap
from .catalog import good_labels
from .workflows import (
    validate_rules,
    validate_shots,
    suggested_sequence,
    remember_sequence,
    change_labels,
    training_example,
)
from .datasets import export_dataset
from .db import (
    ROOT,
    Dataset,
    Dealer,
    Group,
    Issue,
    LabelRevision,
    Measurement,
    ModelVersion,
    Photo,
    Photographer,
    Review,
    ReviewEvent,
    Run,
    Shoot,
    TrainingExample,
    ShotType,
    initialize,
    now,
    uid,
)
from .media import MAX_BATCH_BYTES, prepare_image, resolved_file
from .schemas import (
    DEFAULT_RULES,
    DealerInput,
    GroupInput,
    ImportInput,
    LabelInput,
    NameInput,
    ReviewInput,
    ShotInput,
)


def serialize(obj):
    return {col.key: getattr(obj, col.key) for col in inspect(obj).mapper.column_attrs}


def required(session, cls, item_id):
    obj = session.get(cls, item_id)
    if obj is None:
        raise HTTPException(404, "Item not found")
    if cls is Photo and session.get(Shoot, obj.shoot_id) is None:
        raise HTTPException(404, "Vehicle is in Trash")
    return obj


def policy_for(session, dealer_id, inventory):
    if not dealer_id:
        return {"rules": DEFAULT_RULES.copy(), "dealer_version": None, "group_version": None, "origins": {}}
    dealer = required(session, Dealer, dealer_id)
    group = session.get(Group, dealer.group_id) if dealer.group_id else None
    overrides = dealer.new_rules if inventory == "new" else dealer.used_rules
    parent = group.rules if group else {}
    return {
        "rules": {**DEFAULT_RULES, **parent, **overrides},
        "dealer_version": dealer.version,
        "group_version": group.version if group else None,
        "group_name": group.name if group else None,
        "origins": {
            k: "dealer" if k in overrides else "group" if k in parent else "default" for k in DEFAULT_RULES
        },
    }


def seed(factory):
    with factory() as session:
        if not session.scalar(select(func.count()).select_from(Dealer)):
            group = Group(name="Sample Automotive Group", rules={})
            session.add(group)
            session.flush()
            session.add_all([Dealer(name=f"Dealership {i}", group_id=group.id) for i in range(1, 4)])
        if not session.scalar(select(func.count()).select_from(Photographer)):
            session.add(Photographer(name="Local photographer"))
        session.commit()


def create_app(data_dir=None, start_worker=True, seed_data=True):
    data, engine, factory = initialize(data_dir)
    if seed_data:
        seed(factory)
    worker = Worker(factory, data)

    @asynccontextmanager
    async def lifespan(app):
        if start_worker:
            worker.start()
        yield
        if start_worker:
            worker.stop()
        engine.dispose()

    app = FastAPI(title="Vehicle Photo QC", version="0.1.0", lifespan=lifespan)
    app.state.factory, app.state.data, app.state.worker = factory, data, worker
    security = configure_security(app)

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(
            {"detail": "That name already exists or a referenced record changed. Refresh and try again."},
            status_code=409,
        )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": "0.1.0",
            "analysis": "provisional technical measurements",
            "accounts": security.remote,
        }

    @app.get("/api/config")
    def config():
        with factory() as session:
            return {
                "groups": [serialize(x) for x in session.scalars(select(Group).order_by(Group.name))],
                "dealerships": [
                    serialize(x)
                    | {
                        "effective_new": policy_for(session, x.id, "new"),
                        "effective_used": policy_for(session, x.id, "used"),
                    }
                    for x in session.scalars(select(Dealer).order_by(Dealer.name))
                ],
                "photographers": [
                    serialize(x) for x in session.scalars(select(Photographer).order_by(Photographer.name))
                ],
                "shot_types": list(
                    session.scalars(
                        select(ShotType.key).where(ShotType.archived.is_(False)).order_by(ShotType.position)
                    )
                ),
                "shot_type_labels": {x.key: x.label for x in session.scalars(select(ShotType))},
                "shot_catalog": [
                    serialize(x) for x in session.scalars(select(ShotType).order_by(ShotType.position))
                ],
                "default_rules": DEFAULT_RULES,
            }

    @app.post("/api/groups", status_code=201)
    def add_group(body: GroupInput):
        with factory() as session:
            validate_rules(session, body.rules)
            obj = Group(**body.model_dump())
            session.add(obj)
            session.commit()
            return serialize(obj)

    @app.put("/api/groups/{item_id}")
    def edit_group(item_id: str, body: GroupInput):
        with factory() as session:
            obj = required(session, Group, item_id)
            validate_rules(session, body.rules)
            obj.name, obj.rules = body.name, body.rules
            obj.version += 1
            session.commit()
            return serialize(obj)

    @app.post("/api/dealerships", status_code=201)
    def add_dealer(body: DealerInput):
        with factory() as session:
            validate_rules(session, body.new_rules)
            validate_rules(session, body.used_rules)
            if body.group_id:
                required(session, Group, body.group_id)
            obj = Dealer(**body.model_dump())
            session.add(obj)
            session.commit()
            return serialize(obj)

    @app.put("/api/dealerships/{item_id}")
    def edit_dealer(item_id: str, body: DealerInput):
        with factory() as session:
            obj = required(session, Dealer, item_id)
            validate_rules(session, body.new_rules)
            validate_rules(session, body.used_rules)
            if body.group_id:
                required(session, Group, body.group_id)
            for key, val in body.model_dump().items():
                setattr(obj, key, val)
            obj.version += 1
            session.commit()
            return serialize(obj)

    @app.post("/api/photographers", status_code=201)
    def add_photographer(body: NameInput):
        with factory() as session:
            obj = Photographer(name=body.name)
            session.add(obj)
            session.commit()
            return serialize(obj)

    @app.put("/api/photographers/{item_id}")
    def edit_photographer(item_id: str, body: NameInput):
        with factory() as session:
            obj = required(session, Photographer, item_id)
            obj.name = body.name
            session.commit()
            return serialize(obj)

    def import_batch(body, files, prepared=None, shoot_id=None):
        if not 1 <= len(files) <= 200:
            raise HTTPException(422, "Select between 1 and 200 photos per shoot.")
        created = []
        with factory() as session:
            try:
                if body.photographer_id:
                    required(session, Photographer, body.photographer_id)
                policy = policy_for(session, body.dealership_id, body.inventory_type)
                values = body.model_dump(exclude={"season", "shot_types"}, mode="json")
                sequence = body.shot_types
                if sequence is not None and len(sequence) != len(files):
                    raise HTTPException(422, "One shot type is required for each uploaded photo.")
                if sequence is None:
                    suggested = suggested_sequence(session, body.dealership_id, body.inventory_type, policy)[
                        "sequence"
                    ]
                    sequence = [suggested[i] if i < len(suggested) else "unknown" for i in range(len(files))]
                validate_shots(session, sequence)
                if body.mode == "general" and body.purpose == "training" and not body.source:
                    values["source"] = "Stage Now"
                month = body.shoot_date.month
                season = body.season or (
                    "winter"
                    if month in (12, 1, 2)
                    else "spring"
                    if month < 6
                    else "summer"
                    if month < 9
                    else "autumn"
                )
                shoot = Shoot(
                    **({"id": shoot_id} if shoot_id else {}),
                    **values,
                    season=season,
                    season_source="manual" if body.season else "northern_meteorological",
                    policy=policy,
                )
                session.add(shoot)
                session.flush()
                total = 0
                for position, upload in enumerate(files, 1):
                    if prepared is None:
                        photo_id = uid()
                        details, paths = prepare_image(upload, photo_id, data)
                        created.extend(paths)
                    else:
                        import shutil

                        item = prepared[position - 1]
                        photo_id, details = item["photo_id"], item["details"]
                        for key in (details["original_key"], details["thumbnail_key"]):
                            destination = data / key
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            created.append(destination)
                            shutil.copyfile(item["root"] / key, destination)
                    total += details["byte_size"]
                    if total > MAX_BATCH_BYTES:
                        raise ValueError("One shoot must be 1 GB or smaller.")
                    filename = (upload.filename or "photo").replace("\\", "/").split("/")[-1][:255]
                    photo = Photo(
                        id=photo_id,
                        shoot_id=shoot.id,
                        position=position,
                        original_filename=filename,
                        shot_type=sequence[position - 1],
                        **details,
                    )
                    session.add(photo)
                    session.flush()
                    if body.purpose == "training":
                        session.add(
                            TrainingExample(
                                photo_id=photo.id,
                                origin=values["source"] or "dedicated_upload",
                                labels=good_labels(photo.shot_type),
                                eligible=True,
                            )
                        )
                remember_sequence(session, shoot, policy)
                session.commit()
                return {"id": shoot.id, "status": shoot.status, "photo_count": len(files)}
            except Exception as exc:
                session.rollback()
                for path in created:
                    path.unlink(missing_ok=True)
                if isinstance(exc, ValueError):
                    raise HTTPException(422, str(exc)) from exc
                raise
            finally:
                if prepared is None:
                    for upload in files:
                        upload.file.close()

    @app.post("/api/shoots", status_code=201)
    def import_shoot(metadata: str = Form(...), files: list[UploadFile] = File(...)):
        try:
            body = ImportInput.model_validate_json(metadata)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
        return import_batch(body, files)

    from .uploads import register_upload_routes

    register_upload_routes(app, factory, data, import_batch)

    def summary(session, shoot, training_only=False):
        dealer = session.get(Dealer, shoot.dealership_id) if shoot.dealership_id else None
        photographer = session.get(Photographer, shoot.photographer_id) if shoot.photographer_id else None
        photos = session.scalars(
            select(Photo).where(Photo.shoot_id == shoot.id).order_by(Photo.position)
        ).all()
        if training_only:
            active_ids = set(session.scalars(select(TrainingExample.photo_id)))
            photos = [p for p in photos if p.id in active_ids]
        open_count = session.scalar(
            select(func.count())
            .select_from(Review)
            .where(Review.shoot_id == shoot.id, Review.resolved_at.is_(None))
        )
        previous = bool(session.scalar(select(Review.id).where(Review.shoot_id == shoot.id).limit(1)))
        issues = (
            session.scalar(
                select(func.count()).select_from(Issue).where(Issue.run_id == shoot.current_run_id)
            )
            if shoot.current_run_id
            else 0
        )
        return serialize(shoot) | {
            "dealership_name": dealer.name if dealer else (shoot.source or "General QC"),
            "photographer_name": photographer.name if photographer else "Not specified",
            "photo_count": len(photos),
            "review_count": open_count,
            "previously_queued": previous,
            "issue_count": issues,
            "previews": [{"id": p.id, "position": p.position} for p in photos[:3]],
            "concerns": list(
                session.scalars(
                    select(Review.reason)
                    .where(Review.shoot_id == shoot.id, Review.resolved_at.is_(None))
                    .limit(3)
                )
            ),
        }

    @app.get("/api/shoots")
    def list_shoots(
        q: str = "",
        dealership_id: str = "",
        photographer_id: str = "",
        inventory_type: str = "",
        purpose: str = "evaluation",
        previously_queued: str = "",
        issue: str = "",
        shot_type: str = "",
        date_from: str = "",
        date_to: str = "",
        season: str = "",
        lighting: str = "",
        color: str = "",
        max_score: float | None = Query(None, ge=0, le=100),
        status: str = "",
        eligible: str = "",
        sort: str = "newest",
        limit: int = Query(30, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        with factory() as session:
            stmt = select(Shoot)
            if purpose == "training":
                stmt = stmt.where(Shoot.training_deleted_at.is_(None))
                training_ids = select(Photo.shoot_id).join(
                    TrainingExample, TrainingExample.photo_id == Photo.id
                )
                if eligible:
                    training_ids = training_ids.where(TrainingExample.eligible.is_(eligible == "yes"))
                stmt = stmt.where(Shoot.id.in_(training_ids))
            else:
                stmt = stmt.where(Shoot.purpose == "evaluation")
            if q:
                term = f"%{q}%"
                stmt = stmt.where(
                    or_(
                        Shoot.stock_number.ilike(term),
                        Shoot.make.ilike(term),
                        Shoot.model.ilike(term),
                        Shoot.color.ilike(term),
                        Shoot.note.ilike(term),
                        cast(Shoot.year, String).ilike(term),
                    )
                )
            for column, value in (
                (Shoot.dealership_id, dealership_id),
                (Shoot.photographer_id, photographer_id),
                (Shoot.inventory_type, inventory_type),
                (Shoot.season, season),
                (Shoot.lighting, lighting),
                (Shoot.color, color),
                (Shoot.status, status),
            ):
                if value:
                    stmt = stmt.where(column == value)
            if date_from:
                stmt = stmt.where(Shoot.shoot_date >= date_from)
            if date_to:
                stmt = stmt.where(Shoot.shoot_date <= date_to)
            if max_score is not None:
                stmt = stmt.where(Shoot.score <= max_score)
            if previously_queued:
                expression = Shoot.id.in_(select(Review.shoot_id))
                stmt = stmt.where(expression if previously_queued == "yes" else ~expression)
            if issue:
                stmt = stmt.where(
                    Shoot.id.in_(
                        select(Issue.shoot_id)
                        .where(Issue.kind == issue, Issue.run_id == Shoot.current_run_id)
                        .correlate(Shoot)
                    )
                )
            if shot_type:
                stmt = stmt.where(Shoot.id.in_(select(Photo.shoot_id).where(Photo.shot_type == shot_type)))
            total = session.scalar(select(func.count()).select_from(stmt.subquery()))
            ordering = {
                "newest": Shoot.created_at.desc(),
                "oldest": Shoot.created_at.asc(),
                "lowest": Shoot.score.asc().nulls_last(),
                "highest": Shoot.score.desc().nulls_last(),
                "stock": Shoot.stock_number.asc(),
            }.get(sort, Shoot.created_at.desc())
            shoots = session.scalars(stmt.order_by(ordering, Shoot.id).offset(offset).limit(limit)).all()
            return {"items": [summary(session, s, purpose == "training") for s in shoots], "total": total}

    @app.get("/api/shoots/{shoot_id}")
    def shoot_detail(shoot_id: str):
        with factory() as session:
            shoot = required(session, Shoot, shoot_id)
            measurements = (
                {
                    m.photo_id: serialize(m)
                    for m in session.scalars(
                        select(Measurement).where(Measurement.run_id == shoot.current_run_id)
                    )
                }
                if shoot.current_run_id
                else {}
            )
            photos = []
            for photo in session.scalars(
                select(Photo).where(Photo.shoot_id == shoot_id).order_by(Photo.position)
            ):
                training = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == photo.id))
                photos.append(
                    serialize(photo)
                    | {
                        "display_filename": display_filename(session, shoot, photo),
                        "analysis": measurements.get(photo.id),
                        "training": serialize(training)
                        if training and not shoot.training_deleted_at
                        else None,
                    }
                )
            for rank, photo in enumerate(photos, 1):
                region = banner_region(shoot.policy["rules"], rank, photo["shot_type"])
                photo["banner"] = {**region, "check": banner_overlap(region)}
            return summary(session, shoot) | {
                "photos": photos,
                "issues": [
                    serialize(i)
                    for i in session.scalars(select(Issue).where(Issue.run_id == shoot.current_run_id))
                ]
                if shoot.current_run_id
                else [],
                "reviews": [
                    serialize(r)
                    | {
                        "events": [
                            serialize(e)
                            for e in session.scalars(
                                select(ReviewEvent)
                                .where(ReviewEvent.review_id == r.id)
                                .order_by(ReviewEvent.created_at)
                            )
                        ]
                    }
                    for r in session.scalars(
                        select(Review).where(Review.shoot_id == shoot_id).order_by(Review.created_at.desc())
                    )
                ],
                "runs": [
                    serialize(r)
                    for r in session.scalars(
                        select(Run).where(Run.shoot_id == shoot_id).order_by(Run.created_at.desc())
                    )
                ],
            }

    @app.post("/api/shoots/{shoot_id}/reanalyze")
    def reanalyze(shoot_id: str):
        with factory() as session:
            shoot = required(session, Shoot, shoot_id)
            # Preserve the exact import-time standards snapshot for comparable historical results.
            result = session.execute(
                update(Shoot)
                .where(Shoot.id == shoot.id, Shoot.status.not_in(["queued", "processing"]))
                .values(status="queued", error=None)
            )
            if not result.rowcount:
                raise HTTPException(409, "This shoot is already queued or processing.")
            session.commit()
            return {"status": "queued"}

    from .library_routes import display_filename, register_library_routes

    register_library_routes(app, factory, policy_for, required)

    @app.get("/api/photos/{photo_id}/{variant}")
    def photo_file(photo_id: str, variant: str, download: bool = False):
        if variant not in ("thumbnail", "original"):
            raise HTTPException(404)
        with factory() as session:
            photo = required(session, Photo, photo_id)
            try:
                path = resolved_file(
                    data, photo.thumbnail_key if variant == "thumbnail" else photo.original_key
                )
            except FileNotFoundError:
                raise HTTPException(404, "Image file is missing. Restore it from your backup.")
            shoot = required(session, Shoot, photo.shoot_id)
            return FileResponse(
                path,
                filename=display_filename(session, shoot, photo) if download else None,
                headers={"Cache-Control": "private, max-age=86400"},
            )

    @app.put("/api/photos/{photo_id}/shot")
    def set_shot(photo_id: str, body: ShotInput):
        with factory() as session:
            photo = required(session, Photo, photo_id)
            shoot = required(session, Shoot, photo.shoot_id)
            if shoot.status in ("queued", "processing"):
                raise HTTPException(409, "Wait for analysis to finish before changing shot types.")
            validate_shots(session, [body.shot_type])
            if photo.shot_type != body.shot_type:
                example = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == photo.id))
                if example and not shoot.training_deleted_at:
                    change_labels(session, example, {**example.labels, "shot_type": body.shot_type})
            photo.shot_type = body.shot_type
            shoot.checks = {**shoot.checks, "required_shots": "needs_reanalysis"}
            session.flush()
            remember_sequence(session, shoot, policy_for(session, shoot.dealership_id, shoot.inventory_type))
            session.commit()
            return serialize(photo)

    @app.post("/api/photos/{photo_id}/training")
    def promote(photo_id: str):
        with factory() as session:
            photo = required(session, Photo, photo_id)
            shoot = required(session, Shoot, photo.shoot_id)
            if shoot.training_deleted_at:
                raise HTTPException(409, "This vehicle's training membership is in Trash. Restore it first.")
            example = training_example(session, photo)
            session.commit()
            return serialize(example)

    @app.put("/api/photos/{photo_id}/training")
    def save_labels(photo_id: str, body: LabelInput):
        with factory() as session:
            photo = required(session, Photo, photo_id)
            if required(session, Shoot, photo.shoot_id).training_deleted_at:
                raise HTTPException(409, "This training vehicle is in Trash.")
            validate_shots(session, [body.labels.shot_type])
            example = session.scalar(select(TrainingExample).where(TrainingExample.photo_id == photo_id))
            if not example:
                raise HTTPException(404, "Add this photo to Training first.")
            result = session.execute(
                update(TrainingExample)
                .where(TrainingExample.id == example.id, TrainingExample.revision == body.revision)
                .values(
                    labels=body.labels.model_dump(),
                    eligible=body.eligible,
                    revision=body.revision + 1,
                    updated_at=now(),
                    labeled_by=body.actor,
                )
            )
            if not result.rowcount:
                raise HTTPException(409, "This label was edited elsewhere. Reload before saving.")
            session.add(
                LabelRevision(
                    example_id=example.id,
                    revision=body.revision + 1,
                    labels=body.labels.model_dump(),
                    eligible=body.eligible,
                    actor=body.actor,
                )
            )
            session.commit()
            session.refresh(example)
            return serialize(example)

    @app.get("/api/reviews")
    def list_reviews(
        q: str = "",
        severity: str = "",
        viewed: str = "",
        state: str = "open",
        dealership_id: str = "",
        sort: str = "priority",
        limit: int = Query(30, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        with factory() as session:
            stmt = select(Review).join(Shoot, Review.shoot_id == Shoot.id)
            if state != "all":
                stmt = stmt.where(
                    Review.resolved_at.is_(None) if state == "open" else Review.resolved_at.is_not(None)
                )
            if q:
                stmt = stmt.where(
                    or_(
                        Review.reason.ilike(f"%{q}%"),
                        Review.note.ilike(f"%{q}%"),
                        Shoot.stock_number.ilike(f"%{q}%"),
                        Shoot.model.ilike(f"%{q}%"),
                    )
                )
            if severity:
                stmt = stmt.where(Review.severity == severity)
            if viewed:
                stmt = stmt.where(
                    Review.viewed_at.is_not(None) if viewed == "yes" else Review.viewed_at.is_(None)
                )
            if dealership_id:
                stmt = stmt.where(Shoot.dealership_id == dealership_id)
            total = session.scalar(select(func.count()).select_from(stmt.subquery()))
            from sqlalchemy import case

            priority = case((Review.severity == "severe", 0), (Review.severity == "moderate", 1), else_=2)
            ordering = (
                [priority, Review.created_at]
                if sort == "priority"
                else [Review.created_at.asc() if sort == "oldest" else Review.created_at.desc()]
            )
            items = session.scalars(stmt.order_by(*ordering, Review.id).offset(offset).limit(limit)).all()
            return {
                "items": [
                    serialize(r) | {"shoot": summary(session, session.get(Shoot, r.shoot_id))} for r in items
                ],
                "total": total,
            }

    @app.patch("/api/reviews/{review_id}")
    def review_action(review_id: str, body: ReviewInput):
        with factory() as session:
            review = required(session, Review, review_id)
            changed = True
            if body.action == "view":
                changed = review.viewed_at is None
                if changed:
                    review.viewed_at, review.viewed_by = now(), body.actor
            elif body.action == "resolve":
                changed = review.resolved_at is None
                if changed:
                    review.resolved_at, review.resolved_by, review.resolution = (
                        now(),
                        body.actor,
                        body.resolution,
                    )
            elif body.action == "reopen":
                if session.scalar(
                    select(Review.id).where(
                        Review.shoot_id == review.shoot_id,
                        Review.photo_id == review.photo_id,
                        Review.resolved_at.is_(None),
                        Review.id != review.id,
                    )
                ):
                    raise HTTPException(409, "This photo already has an open review.")
                changed = review.resolved_at is not None
                review.resolved_at, review.resolved_by, review.resolution = None, None, None
            if body.note is not None:
                review.note = body.note
            if changed:
                session.add(
                    ReviewEvent(
                        review_id=review.id, action=body.action, actor=body.actor, note=body.note or ""
                    )
                )
            session.commit()
            return serialize(review)

    @app.get("/api/dashboard")
    def dashboard(today: str = ""):
        with factory() as session:
            current_date = today or date.today().isoformat()
            base = select(Shoot).where(Shoot.purpose == "evaluation")
            total = session.scalar(select(func.count()).select_from(base.subquery()))
            daily_shoots = select(Shoot.id).where(
                Shoot.shoot_date == current_date, Shoot.purpose == "evaluation"
            )
            photos_today = session.scalar(
                select(func.count()).select_from(Photo).where(Photo.shoot_id.in_(daily_shoots))
            )
            reviews = session.scalar(
                select(func.count()).select_from(Review).where(Review.resolved_at.is_(None))
            )
            severe = session.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.resolved_at.is_(None), Review.severity == "severe")
            )
            unviewed = session.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.resolved_at.is_(None), Review.viewed_at.is_(None))
            )
            recent = session.execute(
                select(Photo, Shoot)
                .join(Shoot)
                .where(Shoot.purpose == "evaluation")
                .order_by(Photo.created_at.desc())
                .limit(12)
            ).all()
            trend = session.execute(
                select(Shoot.shoot_date, func.avg(Shoot.score), func.count(Shoot.id))
                .where(Shoot.purpose == "evaluation", Shoot.score.is_not(None))
                .group_by(Shoot.shoot_date)
                .order_by(Shoot.shoot_date.desc())
                .limit(7)
            ).all()
            return {
                "total_shoots": total,
                "photos_today": photos_today,
                "shoots_today": session.scalar(select(func.count()).select_from(daily_shoots.subquery())),
                "average_score": session.scalar(
                    select(func.avg(Shoot.score)).where(Shoot.purpose == "evaluation")
                ),
                "review_count": reviews,
                "severe_count": severe,
                "unviewed_count": unviewed,
                "training_count": session.scalar(
                    select(func.count())
                    .select_from(TrainingExample)
                    .join(Photo, TrainingExample.photo_id == Photo.id)
                    .join(Shoot, Photo.shoot_id == Shoot.id)
                    .where(Shoot.training_deleted_at.is_(None))
                ),
                "approved_count": session.scalar(
                    select(func.count())
                    .select_from(TrainingExample)
                    .join(Photo, TrainingExample.photo_id == Photo.id)
                    .join(Shoot, Photo.shoot_id == Shoot.id)
                    .where(TrainingExample.eligible.is_(True), Shoot.training_deleted_at.is_(None))
                ),
                "recent_photos": [
                    {"id": p.id, "shoot_id": s.id, "stock": s.stock_number, "position": p.position}
                    for p, s in recent
                ],
                "recent_shoots": [
                    summary(session, s)
                    for s in session.scalars(base.order_by(Shoot.created_at.desc()).limit(5))
                ],
                "trend": [
                    {"date": d, "score": round(score, 1), "count": c} for d, score, c in reversed(trend)
                ],
            }

    @app.post("/api/datasets", status_code=201)
    def create_dataset(seed: int = 42):
        with factory() as session:
            try:
                dataset, manifest = export_dataset(session, data, seed)
                counts = {
                    split: sum(e["split"] == split for e in manifest["entries"])
                    for split in ("train", "validation", "test")
                }
                return serialize(dataset) | {"splits": counts, "download_url": f"/api/datasets/{dataset.id}"}
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

    @app.get("/api/datasets/{item_id}")
    def get_dataset(item_id: str):
        with factory() as session:
            dataset = required(session, Dataset, item_id)
            return FileResponse(resolved_file(data, dataset.manifest_key), filename=f"dataset-{item_id}.json")

    @app.get("/api/models")
    def models():
        with factory() as session:
            return [
                serialize(m)
                for m in session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
            ]

    @app.post("/api/models/{item_id}/activate")
    def activate_model(item_id: str):
        with factory() as session:
            model = required(session, ModelVersion, item_id)
            try:
                from .classifier import load_model

                load_model(str(resolved_file(data, model.artifact_key)), tuple(model.classes))
            except Exception as exc:
                raise HTTPException(
                    422,
                    "Cannot load this candidate. Install the ML dependencies and check the local model files.",
                ) from exc
            for previous in session.scalars(select(ModelVersion).where(ModelVersion.status == "active")):
                previous.status = "archived"
            model.status = "active"
            session.commit()
            return serialize(model)

    @app.post("/api/models/deactivate")
    def deactivate_models():
        with factory() as session:
            session.execute(
                update(ModelVersion).where(ModelVersion.status == "active").values(status="archived")
            )
            session.commit()
            return {"status": "manual_only"}

    from .workflow_routes import register_workflow_routes

    register_workflow_routes(app, factory, policy_for, required)

    dist = ROOT / "app" / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
