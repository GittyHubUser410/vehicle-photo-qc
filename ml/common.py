import hashlib
import json
from collections import Counter
from pathlib import Path

from qc.media import resolved_file
from qc.schemas import SHOT_TYPES


def read_manifest(path, data):
    manifest = json.loads(Path(path).read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("entries"):
        raise ValueError("Expected a non-empty version 1 dataset export.")
    entries = manifest["entries"]
    memberships, duplicate_labels = {}, {}
    for entry in entries:
        if entry["split"] not in ("train", "validation", "test"):
            raise ValueError("Unknown dataset split")
        shot = entry["labels"].get("shot_type")
        if shot not in SHOT_TYPES or shot == "unknown":
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
