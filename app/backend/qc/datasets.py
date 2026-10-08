import hashlib
import json

from sqlalchemy import select

from .evidence import EVIDENCE_VERSION, exclusion_reasons
from .db import Dataset, Photo, Shoot, TrainingExample, uid


def export_dataset(session, data, seed=42):
    rows = session.execute(
        select(TrainingExample, Photo, Shoot)
        .join(Photo, TrainingExample.photo_id == Photo.id)
        .join(Shoot, Photo.shoot_id == Shoot.id)
        .where(
            TrainingExample.eligible.is_(True),
            Shoot.training_deleted_at.is_(None),
            TrainingExample.labels["shot_type"].as_string() != "unknown",
        )
        .order_by(Shoot.id, Photo.position)
    ).all()
    rows = [(t, p, s) for t, p, s in rows if not exclusion_reasons(t, p, s)]
    if not rows:
        raise ValueError(
            "Explicitly verify shot labels and approve active photos in the Training Library, then export again."
        )
    # Union connected shoots by exact duplicate bytes and known vehicle identity.
    # This prevents even transitive duplicates from crossing train/validation/test.
    parents = {s.id: s.id for _, _, s in rows}

    def root(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    seen = {}
    for _, photo, shoot in rows:
        keys = ["sha:" + photo.sha256]
        if shoot.stock_number:
            keys.append(
                "vehicle:"
                + (shoot.dealership_id or shoot.source or "general")
                + ":"
                + shoot.stock_number.casefold()
            )
        for key in keys:
            if key in seen:
                a, b = root(shoot.id), root(seen[key])
                parents[max(a, b)] = min(a, b)
            seen[key] = shoot.id
    entries = []
    for example, photo, shoot in rows:
        group = root(shoot.id)
        bucket = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()[:8], 16) % 100
        entries.append(
            {
                "photo_id": photo.id,
                "training_example_id": example.id,
                "label_evidence": example.label_evidence,
                "approval_snapshot": example.eligible,
                "shoot_id": shoot.id,
                "group_id": group,
                "split": "train" if bucket < 70 else "validation" if bucket < 85 else "test",
                "image_key": photo.original_key,
                "sha256": photo.sha256,
                "labels": example.labels,
                "label_revision": example.revision,
                "source": shoot.source,
                "dealership_id": shoot.dealership_id,
                "lighting": shoot.lighting,
                "season": shoot.season,
                "ground": shoot.ground,
            }
        )
    dataset_id = uid()
    document = {
        "schema_version": 2,
        "purpose": "shot_type",
        "evidence_schema_version": EVIDENCE_VERSION,
        "id": dataset_id,
        "seed": seed,
        "split_method": "grouped by shoot, known vehicle, and exact duplicates; 70/15/15 hash allocation",
        "entries": entries,
    }
    encoded = json.dumps(document, indent=2).encode()
    key = f"datasets/{dataset_id}.json"
    (data / key).write_bytes(encoded)
    dataset = Dataset(
        id=dataset_id,
        manifest_key=key,
        sha256=hashlib.sha256(encoded).hexdigest(),
        count=len(entries),
        seed=seed,
    )
    session.add(dataset)
    session.commit()
    return dataset, document
