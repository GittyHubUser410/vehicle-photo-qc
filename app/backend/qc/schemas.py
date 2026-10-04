from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

import re

from .catalog import SHOT_CATALOG

# Compatibility export for older integrations; runtime validation uses the DB catalog.
SHOT_TYPES = [key for key, _ in SHOT_CATALOG]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Rules(Strict):
    blur_min: float = Field(65, ge=0, le=10000)
    dark_max: float = Field(0.6, ge=0, le=1)
    bright_max: float = Field(0.35, ge=0, le=1)
    saturation_max: float = Field(0.85, ge=0, le=1)
    min_photos: int = Field(0, ge=0, le=200)
    required_shots: list[str] = Field(default_factory=list, max_length=200)
    strict_sequence: bool = False
    banner_application: Literal["none", "first", "all"] = "all"
    banner_shot_types: list[str] = Field(default_factory=list, max_length=200)
    banner_top_pct: float = Field(0, ge=0, le=40)
    banner_clearance_pct: float = Field(2, ge=0, le=30)
    angle_tolerance_deg: float = Field(10, ge=0, le=90)

    @field_validator("required_shots")
    @classmethod
    def shots(cls, values):
        if len(values) != len(set(values)) or any(
            v == "unknown" or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", v) for v in values
        ):
            raise ValueError("Use unique supported shot types.")
        return values


DEFAULT_RULES = Rules().model_dump()


def validated_overrides(value: dict) -> dict:
    normalized = Rules(**{**DEFAULT_RULES, **value}).model_dump()
    return {key: normalized[key] for key in value}


class GroupInput(Strict):
    name: str = Field(min_length=1, max_length=150)
    rules: dict = Field(default_factory=dict)
    _rules = field_validator("rules")(validated_overrides)


class DealerInput(Strict):
    name: str = Field(min_length=1, max_length=150)
    group_id: str | None = None
    new_rules: dict = Field(default_factory=dict)
    used_rules: dict = Field(default_factory=dict)
    _rules = field_validator("new_rules", "used_rules")(validated_overrides)


class NameInput(Strict):
    name: str = Field(min_length=1, max_length=150)


class ImportInput(Strict):
    dealership_id: str | None = None
    photographer_id: str | None = None
    mode: Literal["dealership", "general"] = "dealership"
    purpose: Literal["evaluation", "training"] = "evaluation"
    source: str = Field("", max_length=150)
    stock_number: str = Field("", max_length=100)
    inventory_type: Literal["new", "used"] = "used"
    year: int | None = Field(None, ge=1900, le=2100)
    make: str = Field("", max_length=100)
    model: str = Field("", max_length=100)
    trim: str = Field("", max_length=100)
    color: str = Field("", max_length=100)
    shoot_date: date
    season: Literal["spring", "summer", "autumn", "winter"] | None = None
    lighting: Literal["unknown", "sunny", "cloudy", "shade", "indoor", "mixed"] = "unknown"
    ground: Literal["unknown", "dry", "wet", "snow"] = "unknown"
    location: Literal["unknown", "outdoor_lot", "staging_area", "photo_booth", "indoor_bay", "other"] = (
        "unknown"
    )
    note: str = Field("", max_length=2000)
    shot_types: list[str] | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def valid_mode(self):
        if self.mode == "dealership" and not self.dealership_id:
            raise ValueError("Choose a dealership, or choose General QC / Stage Now.")
        if self.mode == "general" and self.dealership_id:
            raise ValueError("General QC does not use a dealership.")
        return self


def validated_shot(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", value):
        raise ValueError("Unsupported shot type")
    return value


class ShotInput(Strict):
    shot_type: str
    _shot = field_validator("shot_type")(validated_shot)


class Labels(Strict):
    shot_type: str = "unknown"
    angle: Literal["unknown", "good", "too_front", "too_rear", "other_bad"] = "unknown"
    blur: Literal["unknown", "good", "bad"] = "unknown"
    crop: Literal["unknown", "good", "bad"] = "unknown"
    exposure: Literal["unknown", "good", "bad"] = "unknown"
    saturation: Literal["unknown", "good", "bad"] = "unknown"
    framing: Literal["unknown", "good", "bad"] = "unknown"
    overall: Literal["unknown", "good", "borderline", "bad"] = "unknown"
    note: str = Field("", max_length=2000)
    _shot = field_validator("shot_type")(validated_shot)


class LabelInput(Strict):
    labels: Labels
    eligible: bool = False
    actor: str = Field("Local reviewer", min_length=1, max_length=150)
    revision: int = Field(0, ge=0)

    @model_validator(mode="after")
    def eligible_label(self):
        if self.eligible and self.labels.shot_type == "unknown":
            raise ValueError("An approved training example needs a shot-type label.")
        return self


class ReviewInput(Strict):
    action: Literal["view", "note", "resolve", "reopen"]
    actor: str = Field("Local reviewer", min_length=1, max_length=150)
    note: str | None = Field(None, max_length=2000)
    resolution: Literal["accepted", "reshoot_requested", "false_positive", "other"] = "accepted"


class PasteTarget(Strict):
    photo_id: str
    revision: int | None = None


class PasteInput(Strict):
    targets: list[PasteTarget] = Field(min_length=1, max_length=200)
    labels: Labels
    actor: str = Field("Local reviewer", min_length=1, max_length=150)


class TrashInput(Strict):
    scope: Literal["all", "training"] = "all"


class VehicleEditInput(ImportInput):
    metadata_revision: int = Field(ge=0)


class TrainingMembershipInput(Strict):
    enabled: bool
    photo_ids: list[str] | None = Field(None, min_length=1, max_length=200)


class ShotOrderInput(Strict):
    keys: list[str] = Field(min_length=1, max_length=1000)


class ShotEditInput(Strict):
    name: str | None = Field(None, min_length=1, max_length=150)
    archived: bool | None = None
