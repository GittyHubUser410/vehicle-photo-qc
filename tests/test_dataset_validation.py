import hashlib
import json

import pytest

from ml.common import metrics_from_confusion, read_manifest, training_splits


def test_manifest_rejects_leakage_changed_bytes_and_conflicting_labels(tmp_path):
    (tmp_path / "one.jpg").write_bytes(b"test image")
    sha = hashlib.sha256(b"test image").hexdigest()
    one = {
        "photo_id": "1",
        "shoot_id": "shoot1",
        "group_id": "g1",
        "sha256": sha,
        "image_key": "one.jpg",
        "split": "train",
        "labels": {"shot_type": "front"},
    }
    two = {**one, "photo_id": "2", "shoot_id": "shoot2", "group_id": "g2", "split": "test"}
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"schema_version": 1, "entries": [one, two]}))
    with pytest.raises(ValueError, match="leakage"):
        read_manifest(path, tmp_path)
    two["split"] = "train"
    two["labels"] = {"shot_type": "rear"}
    path.write_text(json.dumps({"schema_version": 1, "entries": [one, two]}))
    with pytest.raises(ValueError, match="conflicting"):
        read_manifest(path, tmp_path)
    path.write_text(json.dumps({"schema_version": 1, "entries": [one]}))
    (tmp_path / "one.jpg").write_bytes(b"modified")
    with pytest.raises(ValueError, match="integrity"):
        read_manifest(path, tmp_path)


def test_training_requires_independent_validation_class_coverage():
    entries = [
        {"labels": {"shot_type": c}, "split": s}
        for c, s in [("front", "train"), ("rear", "train"), ("front", "validation"), ("rear", "test")]
    ]
    with pytest.raises(ValueError, match="validation is missing"):
        training_splits(entries)


def test_metrics_report_minority_class_failures():
    metrics = metrics_from_confusion([[9, 0], [1, 0]], ["front", "rear"])
    assert metrics["accuracy"] == 0.9
    assert metrics["per_class"]["rear"]["recall"] == 0
    assert metrics["macro_f1"] < 0.5
