"""Explicit holdout evaluation of a saved candidate. Does not train or activate models."""

import argparse
import json

from qc.classifier import predict
from qc.db import Dataset, ModelVersion, initialize
from qc.media import resolved_file

from .common import metrics_from_confusion, read_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_id")
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    data, engine, factory = initialize(args.data_dir)
    with factory() as session:
        model = session.get(ModelVersion, args.model_id)
        if not model:
            parser.error("Model not found in the selected app database.")
        dataset = session.get(Dataset, model.dataset_id)
        if not dataset:
            parser.error("The model's dataset is missing.")
        _, entries = read_manifest(resolved_file(data, dataset.manifest_key), data, respect_trash=False)
        test = [e for e in entries if e["split"] == "test"]
        if not test:
            parser.error("This snapshot contains no test examples.")
        matrix = [[0] * len(model.classes) for _ in model.classes]
        for entry in test:
            prediction, _ = predict(
                resolved_file(data, model.artifact_key),
                model.classes,
                resolved_file(data, entry["image_key"]),
            )
            matrix[model.classes.index(entry["labels"]["shot_type"])][model.classes.index(prediction)] += 1
        metrics = metrics_from_confusion(matrix, model.classes)
        model.metrics = {**model.metrics, "test": metrics, "test_evaluated": True}
        session.commit()
        print(json.dumps(metrics, indent=2))
    engine.dispose()


if __name__ == "__main__":
    main()
