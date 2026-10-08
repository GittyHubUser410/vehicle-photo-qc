import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from qc.evidence import is_verified
from qc.media import resolved_file
from qc.schemas import SHOT_TYPES


def read_manifest(path, data, respect_trash=True, *, inspect_legacy=False):
    manifest = json.loads(Path(path).read_text())
    schema = manifest.get("schema_version")
    if schema == 1 and not inspect_legacy:
        raise ValueError(
            "Legacy schema 1 is not verified ground truth. Reverify labels and re-export a schema 2 dataset."
        )
    if schema not in (1, 2) or not manifest.get("entries"):
        raise ValueError("Expected a non-empty schema 2 dataset export.")
    if schema == 2 and (
        manifest.get("purpose") != "shot_type" or manifest.get("evidence_schema_version") != 1
    ):
        raise ValueError("Expected shot_type purpose and evidence schema 1; reverify and re-export.")
    entries = manifest["entries"]
    known_shots = set(SHOT_TYPES)
    database = Path(data) / "qc.db"
    live = None
    if database.is_file():
        with sqlite3.connect(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version >= 2:
                known_shots.update(row[0] for row in connection.execute("SELECT key FROM shot_types"))
            if schema == 2:
                registered = connection.execute(
                    "SELECT manifest_key, sha256 FROM training_datasets WHERE id=?", (manifest.get("id"),)
                ).fetchone()
                if not registered:
                    raise ValueError("This dataset is not registered in the selected app database.")
                snapshot = resolved_file(data, registered[0]).read_bytes()
                if hashlib.sha256(snapshot).hexdigest() != registered[1]:
                    raise ValueError("Registered manifest integrity check failed.")
                if json.loads(snapshot) != manifest:
                    raise ValueError("The supplied manifest differs from the registered snapshot.")
                if respect_trash:
                    if version < 4:
                        raise ValueError("Upgrade the app and reverify labels before training.")
                    live = {
                        r[0]: r
                        for r in connection.execute("""
                        SELECT t.id, t.labels, t.label_evidence, t.eligible, t.deleted_at,
                               p.deleted_at, s.deleted_at, s.training_deleted_at, p.id
                        FROM training_examples t JOIN photos p ON p.id=t.photo_id
                        JOIN vehicle_shoots s ON s.id=p.shoot_id
                    """)
                    }
            elif respect_trash and version >= 2:
                removed = {
                    row[0]
                    for row in connection.execute("""
                    SELECT p.id FROM photos p JOIN vehicle_shoots s ON s.id=p.shoot_id
                    LEFT JOIN training_examples t ON t.photo_id=p.id
                    WHERE p.deleted_at IS NOT NULL OR s.deleted_at IS NOT NULL
                    OR s.training_deleted_at IS NOT NULL OR t.deleted_at IS NOT NULL OR t.eligible = 0
                """)
                }
                entries = [e for e in entries if e["photo_id"] not in removed]
    elif schema == 2:
        raise ValueError("Schema 2 requires the app database to validate the registered snapshot.")
    memberships, duplicate_labels = {}, {}
    for entry in entries:
        if schema == 2:
            item = entry.get("label_evidence", {}).get("shot_type")
            if (
                not is_verified(item, entry.get("labels", {}).get("shot_type"))
                or not entry.get("approval_snapshot")
                or not entry.get("training_example_id")
                or item["value_revision"] > entry.get("label_revision", -1)
            ):
                raise ValueError("Unverified snapshot evidence. Reverify labels and re-export.")
        if entry["split"] not in ("train", "validation", "test"):
            raise ValueError("Unknown dataset split")
        shot = entry["labels"].get("shot_type")
        if shot not in known_shots or shot == "unknown":
            raise ValueError("Each example must have a supported shot label.")
        for key in ("group_id", "shoot_id", "sha256"):
            group = (key, entry[key])
            if group in memberships and memberships[group] != entry["split"]:
                raise ValueError("Dataset leakage: a shoot, vehicle group, or duplicate crosses splits.")
            memberships[group] = entry["split"]
        if entry["sha256"] in duplicate_labels and duplicate_labels[entry["sha256"]] != shot:
            raise ValueError(
                "The same image has conflicting shot labels. Correct the labels and export again."
            )
        duplicate_labels[entry["sha256"]] = shot
        path = resolved_file(data, entry["image_key"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Original image integrity check failed: {entry['photo_id']}")
    if live is not None:
        valid = []
        for entry in entries:
            current = live.get(entry["training_example_id"])
            if not current or not current[3] or any(current[4:8]) or current[8] != entry["photo_id"]:
                continue
            labels, evidence = json.loads(current[1]), json.loads(current[2])
            shot = labels.get("shot_type")
            if (
                shot == entry["labels"]["shot_type"]
                and is_verified(evidence.get("shot_type"), shot)
                and evidence.get("shot_type") == entry["label_evidence"]["shot_type"]
            ):
                valid.append(entry)
        entries = valid
    if not entries:
        raise ValueError(
            "No approved photos with current verified evidence remain. Reverify and export a new dataset."
        )
    # Identical bytes contribute only once; their group membership is already checked.
    unique = {e["sha256"]: e for e in entries}
    return manifest, list(unique.values())


def training_splits(entries):
    classes = sorted({e["labels"]["shot_type"] for e in entries})
    if len(classes) < 2:
        raise ValueError("At least two distinct shot classes are required.")
    splits = {name: [e for e in entries if e["split"] == name] for name in ("train", "validation", "test")}
    for name in ("train", "validation"):
        counts = Counter(e["labels"]["shot_type"] for e in splits[name])
        missing = [c for c in classes if counts[c] == 0]
        if missing:
            raise ValueError(
                f"{name} is missing classes: {', '.join(missing)}. Collect more independent vehicle shoots; do not move individual photos across splits."
            )
    if not splits["test"]:
        raise ValueError("No held-out test vehicles. Collect more independent shoots before training.")
    return classes, splits


def metrics_from_confusion(matrix, classes):
    per_class = {}
    for index, name in enumerate(classes):
        tp = matrix[index][index]
        support = sum(matrix[index])
        predicted = sum(row[index] for row in matrix)
        precision = tp / predicted if predicted else 0
        recall = tp / support if support else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_class[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    total = sum(sum(row) for row in matrix)
    return {
        "accuracy": round(sum(matrix[i][i] for i in range(len(classes))) / total, 4) if total else 0,
        "macro_f1": round(sum(c["f1"] for c in per_class.values()) / len(classes), 4),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "class_order": classes,
        "sample_count": total,
    }
