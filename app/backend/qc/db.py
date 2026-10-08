from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
    or_,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session, with_loader_criteria

ROOT = Path(__file__).resolve().parents[3]


def now() -> str:
    return datetime.now(UTC).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Group(Identity, Base):
    __tablename__ = "conglomerates"
    name: Mapped[str] = mapped_column(String(150), unique=True)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Dealer(Identity, Base):
    __tablename__ = "dealerships"
    name: Mapped[str] = mapped_column(String(150), unique=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("conglomerates.id"))
    new_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    used_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Photographer(Identity, Base):
    __tablename__ = "photographers"
    name: Mapped[str] = mapped_column(String(150), unique=True)


class Shoot(Identity, Base):
    __tablename__ = "vehicle_shoots"
    dealership_id: Mapped[str | None] = mapped_column(ForeignKey("dealerships.id"), index=True)
    photographer_id: Mapped[str | None] = mapped_column(ForeignKey("photographers.id"), index=True)
    mode: Mapped[str] = mapped_column(String, default="dealership")
    purpose: Mapped[str] = mapped_column(String, default="evaluation", index=True)
    source: Mapped[str] = mapped_column(String, default="")
    stock_number: Mapped[str] = mapped_column(String(100), default="", index=True)
    inventory_type: Mapped[str] = mapped_column(String, default="used")
    year: Mapped[int | None] = mapped_column(Integer)
    make: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    trim: Mapped[str] = mapped_column(String(100), default="")
    color: Mapped[str] = mapped_column(String(100), default="")
    shoot_date: Mapped[str] = mapped_column(String, index=True)
    season: Mapped[str] = mapped_column(String)
    season_source: Mapped[str] = mapped_column(String, default="northern_meteorological")
    lighting: Mapped[str] = mapped_column(String, default="unknown")
    ground: Mapped[str] = mapped_column(String, default="unknown")
    location: Mapped[str] = mapped_column(String, default="unknown")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    policy: Mapped[dict] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float)
    current_run_id: Mapped[str | None] = mapped_column(String)
    checks: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted_at: Mapped[str | None] = mapped_column(String)
    training_deleted_at: Mapped[str | None] = mapped_column(String)
    metadata_revision: Mapped[int] = mapped_column(Integer, default=0)


class Photo(Identity, Base):
    __tablename__ = "photos"
    shoot_id: Mapped[str] = mapped_column(ForeignKey("vehicle_shoots.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String)
    original_key: Mapped[str] = mapped_column(String)
    thumbnail_key: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    byte_size: Mapped[int] = mapped_column(Integer)
    exif: Mapped[dict] = mapped_column(JSON, default=dict)
    shot_type: Mapped[str] = mapped_column(String, default="unknown", index=True)
    shot_revision: Mapped[int] = mapped_column(Integer, default=0)
    shot_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted_at: Mapped[str | None] = mapped_column(String)
    __table_args__ = (UniqueConstraint("shoot_id", "position"),)


class PhotoShotRevision(Identity, Base):
    __tablename__ = "photo_shot_revisions"
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    shot_type: Mapped[str] = mapped_column(String)
    shot_evidence: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("photo_id", "revision"),)


class Run(Identity, Base):
    __tablename__ = "analysis_runs"
    shoot_id: Mapped[str] = mapped_column(ForeignKey("vehicle_shoots.id"), index=True)
    evidence_schema_version: Mapped[int] = mapped_column(Integer, default=0)
    check_results: Mapped[list] = mapped_column(JSON, default=list)
    pipeline_version: Mapped[str] = mapped_column(String)
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"))
    policy_snapshot: Mapped[dict] = mapped_column(JSON)
    completed_at: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")


class Measurement(Identity, Base):
    __tablename__ = "photo_metrics"
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    metrics: Mapped[dict] = mapped_column(JSON)
    predicted_shot: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Float)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("run_id", "photo_id"),)


class Issue(Identity, Base):
    __tablename__ = "issue_detections"
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    shoot_id: Mapped[str] = mapped_column(ForeignKey("vehicle_shoots.id"), index=True)
    photo_id: Mapped[str | None] = mapped_column(ForeignKey("photos.id"), index=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)


class Review(Identity, Base):
    __tablename__ = "review_queue_items"
    shoot_id: Mapped[str] = mapped_column(ForeignKey("vehicle_shoots.id"), index=True)
    photo_id: Mapped[str | None] = mapped_column(ForeignKey("photos.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"))
    reason: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String)
    viewed_at: Mapped[str | None] = mapped_column(String)
    viewed_by: Mapped[str | None] = mapped_column(String)
    resolved_at: Mapped[str | None] = mapped_column(String, index=True)
    resolved_by: Mapped[str | None] = mapped_column(String)
    resolution: Mapped[str | None] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")


class ReviewEvent(Identity, Base):
    __tablename__ = "review_events"
    review_id: Mapped[str] = mapped_column(ForeignKey("review_queue_items.id"), index=True)
    action: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")


class TrainingExample(Identity, Base):
    __tablename__ = "training_examples"
    photo_id: Mapped[str] = mapped_column(ForeignKey("photos.id"), unique=True)
    origin: Mapped[str] = mapped_column(String)
    labels: Mapped[dict] = mapped_column(JSON, default=dict)
    label_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    labeled_by: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[str] = mapped_column(String, default=now)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[str | None] = mapped_column(String)


class ShotType(Base):
    __tablename__ = "shot_types"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(150), unique=True)
    position: Mapped[int] = mapped_column(Integer)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class DealerSequence(Base):
    __tablename__ = "dealer_sequences"
    dealership_id: Mapped[str] = mapped_column(ForeignKey("dealerships.id"), primary_key=True)
    inventory_type: Mapped[str] = mapped_column(String, primary_key=True)
    sequence: Mapped[list] = mapped_column(JSON)
    rules_signature: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class ActiveSession(Session):
    """Default reads exclude trash; explicit trash/history operations opt in."""


@event.listens_for(ActiveSession, "do_orm_execute")
def active_records(state):
    if (
        not state.is_select
        or state.session.info.get("include_deleted")
        or state.execution_options.get("include_deleted")
    ):
        return
    live_shoots = select(Shoot.id).where(Shoot.deleted_at.is_(None))
    live_photos = select(Photo.id).where(Photo.deleted_at.is_(None), Photo.shoot_id.in_(live_shoots))
    state.statement = state.statement.options(
        with_loader_criteria(Shoot, Shoot.deleted_at.is_(None), include_aliases=True),
        with_loader_criteria(Photo, Photo.deleted_at.is_(None), include_aliases=True),
        with_loader_criteria(TrainingExample, TrainingExample.deleted_at.is_(None), include_aliases=True),
        with_loader_criteria(
            Review,
            Review.shoot_id.in_(live_shoots)
            & or_(Review.photo_id.is_(None), Review.photo_id.in_(live_photos)),
            include_aliases=True,
        ),
        with_loader_criteria(
            Issue,
            Issue.shoot_id.in_(live_shoots) & or_(Issue.photo_id.is_(None), Issue.photo_id.in_(live_photos)),
            include_aliases=True,
        ),
    )


class LabelRevision(Identity, Base):
    __tablename__ = "training_label_revisions"
    example_id: Mapped[str] = mapped_column(ForeignKey("training_examples.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    labels: Mapped[dict] = mapped_column(JSON)
    label_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    eligible: Mapped[bool] = mapped_column(Boolean)
    actor: Mapped[str] = mapped_column(String)


class Dataset(Identity, Base):
    __tablename__ = "training_datasets"
    manifest_key: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    count: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)


class ModelVersion(Identity, Base):
    __tablename__ = "model_versions"
    name: Mapped[str] = mapped_column(String)
    artifact_key: Mapped[str] = mapped_column(String)
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("training_datasets.id"))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    classes: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="candidate")


Index("ix_shoot_filter", Shoot.purpose, Shoot.dealership_id, Shoot.shoot_date)


def initialize(data_dir: str | Path | None = None):
    data = Path(data_dir or os.environ.get("QC_DATA_DIR", ROOT / "data")).resolve()
    for folder in ("originals", "thumbnails", "datasets", "models", "tmp"):
        (data / folder).mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{(data / 'qc.db').as_posix()}", connect_args={"check_same_thread": False, "timeout": 30}
    )

    @event.listens_for(engine, "connect")
    def pragmas(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")

    from .migrations import migrate, SCHEMA_VERSION

    migrate(engine, data)
    with engine.connect() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            Base.metadata.create_all(conn)
            conn.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    factory = sessionmaker(engine, class_=ActiveSession, expire_on_commit=False)
    from .catalog import SHOT_CATALOG

    with factory() as session:
        for position, (key, label) in enumerate(SHOT_CATALOG):
            if session.get(ShotType, key) is None:
                session.add(ShotType(key=key, label=label, position=position))
        session.commit()
    return data, engine, factory
