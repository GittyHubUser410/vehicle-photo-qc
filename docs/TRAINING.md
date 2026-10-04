# Collecting examples and training the first classifier

## What this model learns

The included optional model classifies **shot type** from the approved examples in its dataset. The expanded shared shot catalog includes exterior, interior, controls, detail categories, and legacy labels. Existing models retain their original vocabulary; adding categories does not retrain or alter them.

It does **not** learn crop quality, angle acceptability, plastic, or overall dealership quality. The app collects those labels now so specialized models can be added later without relabeling everything. The initial sharpness/exposure/saturation checks remain image-processing heuristics.

## Collect and label

1. Upload complete vehicle shoots. Use a representative mix of accepted, rejected, and borderline photos from each dealership plus Stage Now.
2. Keep the same dealership/source and stock number for repeated shoots of the same vehicle. This helps keep that vehicle in a single data split. For outside sources, use a consistent source name and vehicle identifier in stock number. No VIN decoding or automatic vehicle identity matching is implemented.
3. Label the shot type separately from its quality. A blurry front shot is still a front shot.
4. Use driver/passenger relative to the vehicle, not to the image viewer. Record and consistently apply your policy for right-hand-drive vehicles before mixing them into training.
5. New examples default to **Good** to reduce entry. Inspect these defaults before approval. Copy Settings and bulk paste preserve shot types, but clear approval. Mark defect dimensions independently. Use **Unknown** if you have not inspected a dimension; absence of a label does not mean good.
6. Add environmental context where practical: lighting, wet/snow/dry ground, and location. Season defaults to Northern Hemisphere meteorological season by shoot date and can be overridden at import.
7. Check **Approved for training** only after reviewing the label. Changing a prediction does not silently approve training data.

Begin with enough independent shoots to show each target shot class across different vehicle shapes, colors, cameras, and conditions. Upload counts alone do not establish readiness. The training command refuses a dataset lacking class coverage in training or validation, or without any test vehicles.

## Export a frozen dataset

Click **Export approved dataset** in Training Library. A JSON manifest is saved under `data/datasets/` and is available to download. It records photo IDs, original-file keys and hashes, label revisions, contextual fields, and split membership. It does not copy or expose image files in GitHub.

- All photos from a shoot stay together.
- Repeated vehicles with the same source/dealership and stock number stay together.
- Exact duplicate image bytes join their shoots into the same group, including transitive duplicates.
- Groups receive a deterministic 70/15/15 train/validation/test allocation for the selected seed. Actual ratios can differ significantly on small datasets.
- The trainer verifies file hashes, checks for split leakage, rejects contradictory labels on identical bytes, and removes exact duplicate images before training.

Perceptually similar/recompressed images and vehicles entered under different identities are **not** automatically detected. Review the collection for those before training. Do not move individual photographs across splits to make the ratios look better.

Trashed photos are excluded from new exports and future training runs, including runs using older manifests against the current data directory. Restore and review them if they should be included again. Existing holdout evaluation uses the unchanged historical snapshot.

**Use the same saved manifest when comparing model candidates.** New exports are new snapshots; adding data or connecting previously separate groups can change split assignment. Do not use a regenerated snapshot as though it were the same held-out benchmark. Long-term locked test-cohort management is a future feature.

## Install PyTorch for your PC

The app environment is `.venv`. Use the current official selector at https://pytorch.org/get-started/locally/ to choose **Windows / Pip / Python / the supported CUDA build** for your NVIDIA driver. Run the selected install command through this environment's Python, for example using this prefix:

```powershell
.\.venv\Scripts\python.exe -m pip install ...
```

Install both `torch` and `torchvision` as a matching pair. Do not guess a CUDA wheel URL from an old guide. Verify afterward:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

For a CPU-only experiment, `pip install -e ".[ml]"` through the same Python adds the optional packages, but an explicit official CPU/CUDA selection is preferable for controlling download size and GPU support. The first training run downloads ImageNet ResNet18 weights from PyTorch; the photo files themselves stay local.

## Train a candidate

Run from the repository root, with the same `QC_DATA_DIR` as the app:

```powershell
.\.venv\Scripts\python.exe -m ml.train_shots "D:\VehiclePhotoQC\data\datasets\YOUR_DATASET_ID.json" --epochs 10 --batch-size 32 --device auto
```

The baseline freezes the pretrained ResNet18 backbone and trains a new classification head. It uses class-weighted cross-entropy, fixed preprocessing, and no horizontal flips (flips would interchange driver/passenger views). It keeps frozen BatchNorm statistics fixed. Validation macro F1 selects the saved candidate; class-level precision/recall/F1 and the confusion matrix are recorded. Exact numeric reproducibility can still vary across hardware and library versions.

The test split is not used for training or candidate selection. Model artifacts, parameters, epoch metrics, dataset ID, and a report are saved under `data/models/<model-id>/`. Training writes a **candidate** entry in the app database. It never activates the model.

## Evaluate and activate

Use validation performance to develop/select a candidate. When ready for a deliberate holdout check:

```powershell
.\.venv\Scripts\python.exe -m ml.evaluate YOUR_MODEL_ID
```

This evaluates the candidate on its saved dataset's test split and records the report. Repeatedly choosing models against the same test set will bias that benchmark; use validation for routine tuning.

Open **Models & Help** to inspect metrics. Check per-class performance, not just overall accuracy. Inspect representative errors, including snow, dark vehicles, mixed lighting, and each dealership. When appropriate, choose **Activate this model**. Previous active versions become archived and remain available for rollback. You can disable automatic classification at any time.

Runtime classification uses CPU inference so the app does not require a GPU to open. It applies the exact same torchvision preprocessing as training. Human operational shot labels override predictions. Low-confidence predictions leave the shot unknown; missing-shot checks then defer. An 80% softmax threshold is only an initial screening setting, not a calibrated correctness guarantee.

The included training runner must still be tested against your actual dataset and RTX hardware. A passing software test is not evidence that the classifier is accurate enough for manager decisions.
