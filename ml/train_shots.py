"""Train an ImageNet-initialized ResNet18 head. Save a candidate; never auto-activate."""

import argparse
import hashlib
import json
import random
from collections import Counter

import numpy as np

from qc.db import Dataset, ModelVersion, initialize, uid
from qc.media import resolved_file

from .common import metrics_from_confusion, read_manifest, training_splits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Path to an exported dataset JSON")
    parser.add_argument("--data-dir", help="Same QC_DATA_DIR used by the app")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error("Epochs, batch size, and learning rate must be positive.")
    data, engine, factory = initialize(args.data_dir)
    manifest, entries = read_manifest(args.manifest, data)
    classes, splits = training_splits(entries)
    with factory() as session:
        dataset = session.get(Dataset, manifest["id"])
        if not dataset:
            parser.error("This dataset is not registered in the selected app database.")
        if (
            hashlib.sha256(resolved_file(data, dataset.manifest_key).read_bytes()).hexdigest()
            != dataset.sha256
        ):
            parser.error("Registered manifest integrity check failed.")
        if json.loads(resolved_file(data, dataset.manifest_key).read_text()) != manifest:
            parser.error("The supplied manifest differs from the registered snapshot.")
    try:
        import torch
        from PIL import Image, ImageOps
        from torch.utils.data import DataLoader, Dataset as TorchDataset
        from torchvision.models import ResNet18_Weights, resnet18
    except ImportError as exc:
        raise SystemExit(
            "Install PyTorch and torchvision in this environment first. See docs/TRAINING.md."
        ) from exc
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = (
        "cuda"
        if args.device == "auto" and torch.cuda.is_available()
        else "cpu"
        if args.device == "auto"
        else args.device
    )
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is not available. Check your NVIDIA driver and PyTorch installation, or use --device cpu."
        )
    weights = ResNet18_Weights.DEFAULT
    transform = weights.transforms()

    class Photos(TorchDataset):
        def __init__(self, rows):
            self.rows = rows

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            row = self.rows[index]
            with Image.open(resolved_file(data, row["image_key"])) as image:
                tensor = transform(ImageOps.exif_transpose(image).convert("RGB"))
            return tensor, classes.index(row["labels"]["shot_type"])

    # num_workers=0 is deliberately compatible with Windows and small local datasets.
    train = DataLoader(
        Photos(splits["train"]),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        generator=torch.Generator().manual_seed(args.seed),
    )
    validation = DataLoader(Photos(splits["validation"]), batch_size=args.batch_size, num_workers=0)
    model = resnet18(weights=weights)
    for parameter in model.parameters():
        parameter.requires_grad = False
    model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
    model.to(device)
    counts = Counter(e["labels"]["shot_type"] for e in splits["train"])
    class_weights = torch.tensor(
        [len(splits["train"]) / (len(classes) * counts[c]) for c in classes], device=device
    )
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.fc.parameters(), lr=args.learning_rate)
    model_id = uid()
    folder = data / "models" / model_id
    folder.mkdir(parents=True)
    best_score, best_metrics, history = -1, {}, []
    print(
        f"Device: {device}. Classes: {classes}. Train: {len(splits['train'])}; validation: {len(splits['validation'])}. Test set stays untouched."
    )
    for epoch in range(args.epochs):
        # Keep frozen backbone BatchNorm statistics frozen as well.
        model.eval()
        model.fc.train()
        total_loss = 0
        for images, targets in train:
            images, targets = images.to(device), targets.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(images), targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(targets)
        matrix = [[0] * len(classes) for _ in classes]
        model.eval()
        with torch.inference_mode():
            for images, targets in validation:
                predictions = model(images.to(device)).argmax(1).cpu().tolist()
                for expected, predicted in zip(targets.tolist(), predictions, strict=True):
                    matrix[expected][predicted] += 1
        metrics = metrics_from_confusion(matrix, classes)
        history.append(
            {"epoch": epoch + 1, "train_loss": total_loss / len(splits["train"]), "validation": metrics}
        )
        print(
            f"Epoch {epoch + 1}: validation macro F1 {metrics['macro_f1']:.4f}, accuracy {metrics['accuracy']:.4f}"
        )
        if metrics["macro_f1"] > best_score:
            best_score, best_metrics = metrics["macro_f1"], metrics
            torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, folder / "weights.pt")
    report = {
        "validation": best_metrics,
        "history": history,
        "dataset_id": manifest["id"],
        "dataset_schema_version": manifest["schema_version"],
        "evidence_schema_version": manifest["evidence_schema_version"],
        "label_purpose": manifest["purpose"],
        "parameters": vars(args),
        "architecture": "resnet18-frozen-backbone",
        "torch_version": torch.__version__,
        "preprocessing": "ResNet18_Weights.DEFAULT.transforms; EXIF orientation applied; no horizontal flips",
        "test_evaluated": False,
    }
    (folder / "report.json").write_text(json.dumps(report, indent=2))
    with factory() as session:
        session.add(
            ModelVersion(
                id=model_id,
                name=f"Shot classifier {model_id[:8]}",
                artifact_key=f"models/{model_id}/weights.pt",
                dataset_id=manifest["id"],
                metrics=report,
                classes=classes,
                status="candidate",
            )
        )
        session.commit()
    engine.dispose()
    print(f"Saved candidate {model_id}. It is NOT active. Review metrics in Models & Help before activation.")


if __name__ == "__main__":
    main()
