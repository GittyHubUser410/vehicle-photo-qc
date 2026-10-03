# Vehicle Photo QC

A local prototype for reviewing dealership vehicle photos and building a carefully labeled training library.

**Version 0.1: a working application foundation with real technical image checks.** It is not yet a trained vehicle-crop or angle evaluator. The interface labels technical scores as provisional and shows which checks are unavailable.

## Start on Windows

Install **Python 3.12** (including the Windows Python launcher) and **Node.js 22.12 or later**. Git is optional if you download the ZIP from GitHub.

1. Download this repository using **Code → Download ZIP**, then extract it somewhere on your SSD. Or clone it:

   ```powershell
   git clone https://github.com/GittyHubUser410/vehicle-photo-qc.git
   cd vehicle-photo-qc
   ```

2. Open PowerShell in the extracted project folder. Run the one-time setup:

   ```powershell
   .\scripts\setup-windows.ps1
   ```

3. Start the app:

   ```powershell
   .\scripts\start-windows.ps1
   ```

4. Open **http://127.0.0.1:8000** in Chrome or Edge. Keep the terminal open. Press **Ctrl+C** to stop the app.

If your computer does not allow PowerShell scripts, use the manual commands in [WINDOWS.md](docs/WINDOWS.md). No virtual-environment activation or change to your system execution policy is needed for the manual route.

**You do not need CUDA or PyTorch to start.** Uploading, labeling, review, and the initial technical checks work on the CPU. Add PyTorch later for model training.

### Choose the photo drive

By default, all application data lives in `data/` inside this project. To use a different SSD folder, set this before starting the app and before training:

```powershell
$env:QC_DATA_DIR = "D:\VehiclePhotoQC\data"
.\scripts\start-windows.ps1
```

This setting applies to the current PowerShell session. Use the same folder on later starts. An empty folder starts a new library; changing the variable does not migrate an existing library. The example `.env.example` is reference material, not automatically loaded.

## Your first session

1. Open **Dealership Setup**. Rename the three placeholder dealerships and sample conglomerate. Add your photographers. Configure new and used standards separately. The placeholders have no required-shot list or minimum count until you set them.
2. Open **Evaluate Vehicle**. Choose a dealership or General QC, enter vehicle details, and select photos. Dealership, photographer, and new/used selections are remembered on this browser. Each has its own clear control.
3. Check the numbered photo tray. Drag to reorder or use the arrows; this explicit order is the order saved. JPEG, PNG, and WebP are supported, up to 200 photos per shoot, 25 MB each, and 1 GB per batch. Export HEIC/RAW files to JPEG first.
4. Click **Evaluate photos**. Original bytes are copied unchanged, oriented thumbnails are generated, and a local background worker measures technical quality.
5. Open **Vehicle Results** or **Review Queue**. Opening a queue item marks it viewed; **Resolve / remove from queue** closes it. The photo and review history remain saved. A reviewer name is an annotation, not an authenticated account.
6. Use **Training Library → Upload training data** for dedicated examples. Choose Stage Now for outside sources, or **Add to Training Library** from an operational photo. Label the shot and individual defects, then approve it. Uploaded photos do not automatically train anything.

See [TRAINING.md](docs/TRAINING.md) for collection guidance, dataset exports, and the optional GPU training commands.

## What works

| Area | Included |
|---|---|
| Dashboard | Recent photo strip, daily counts, average technical score, training progress, and prominent serious-review link |
| Upload | Batch import, numbered draggable sequence, phone-friendly reorder buttons, remembered fields, optional note |
| Vehicle results | Search, sort, filters, pagination, and detail window that leaves the list in place |
| Photo library | Vehicle galleries, original view, dimensions, selected EXIF, operational-to-training promotion |
| Review queue | Separate viewed/resolved state, queue badges, reviewer notes, resolution reason, complete activity history |
| Training library | Per-issue human labels, explicit eligibility, revision protection, immutable dataset manifests |
| Dealership setup | Conglomerate inheritance, per-dealer overrides, separate new/used rules, versioned import-time snapshots |
| Technical analysis | OpenCV sharpness, exposure/clipping, saturation estimates; real measurements, not generated demo scores |
| Required shots | Count rules; missing shots and ordered-subsequence checks once every photo has a usable shot type |
| Banner | Configurable top-area and clearance guide over the photo; visual preview only |
| ML foundation | Optional ResNet18 shot-classifier training, per-class validation metrics, holdout evaluation, manual activation |
| Storage | SQLite with WAL and foreign keys, immutable original files, persistent processing state, restart recovery |
| UI | Desktop sidebar, mobile navigation, responsive cards and full-screen phone details |

## What remains

- Vehicle detection/segmentation, critical-crop detection, and exterior-angle judgments.
- Automatic banner-overlap decisions and arbitrary uploaded banner graphics.
- Plastic, floor-mat, and steering-wheel checks.
- Full vehicle-quality scoring that combines technical, framing, angle, and dealership criteria.
- Authenticated accounts, remote phone access, hosted deployment, and HomeNet/DigiLot integrations.
- Browser-based training controls; training is an explicit Python command for now.

**The current score is only a technical screening score.** It starts at 100 and deducts 35/20/10 points for severe/moderate/minor technical findings. A shoot score is the mean of its photo technical scores. Missing-shot/sequence findings appear separately and do not change this number. A technically high-scoring image can still have poor framing, a wrong angle, or a cropped vehicle. Dark vehicles, bright backgrounds, and low-texture scenes can produce false positives. Inspect the original before requesting a reshoot.

Required-shot checks defer when any photo has an unknown shot type. You can set human shot types in the results window and reanalyze. If a trained classifier is active, predictions at 80% softmax confidence or higher can fill unknown shot types; this cutoff is provisional and not a calibrated probability. Human shot labels take precedence.

Reanalysis keeps the original standards snapshot. It adds a new analysis run, preserves prior measurements, and does not automatically close open review items. Future uploads receive the latest dealership standards.

## Development

Python 3.12 and Node.js 22.12+ are the tested targets.

```bash
python -m venv .venv
# Linux/macOS commands; Windows equivalents are in docs/WINDOWS.md.
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
cd app/frontend
npm ci
npm run build
cd ../..
.venv/bin/python -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

For interface development, run `npm run dev` in `app/frontend` in another terminal. Vite at port 5173 forwards `/api` requests to the backend. Production-style local use serves the built interface directly from FastAPI at port 8000. API documentation: http://127.0.0.1:8000/docs.

Run **one app instance and one worker only** against a data directory. The worker runs inside the backend process; do not add multiple Uvicorn workers. This is intentionally a single-PC, unauthenticated prototype bound to loopback. The phone layout is implemented, but phone access across a network is not enabled by changing a UI setting.

### Tests

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app/backend ml tests scripts
cd app/frontend
npm run build
npx playwright install chromium
# Uses a disposable database and starts its own server. Stop your normal server first.
QC_TEST_PYTHON=/absolute/path/to/vehicle-photo-qc/.venv/bin/python npm run test:e2e
```

On Windows, set `$env:QC_TEST_PYTHON = (Resolve-Path .venv\Scripts\python.exe).Path` in the repository root before changing into `app/frontend`. Browser tests cover import/reordering, results, review resolution, training approval, and phone-sized dealership editing. GitHub Actions runs backend checks on Linux and Windows and browser checks on Linux. CUDA training requires validation on your own hardware and labeled dataset.

## Data and backups

Only code and documentation belong in this repository. `.gitignore` excludes photos, databases, model weights, exports, and local environments. Keep custom data directories outside the repository or under the ignored `data/` folder.

Stop the app and any training process, then run:

```powershell
.\.venv\Scripts\python.exe scripts\backup.py "E:\PhotoQCBackups" --app-stopped
```

The script backs up SQLite through its backup API, then copies originals, thumbnails, dataset snapshots, and models. Use a separate drive if possible. To restore, stop the app and point `QC_DATA_DIR` at the complete backup folder, or copy its contents into an empty data folder. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for schema and processing details.

## Project map

```text
app/backend/qc/     FastAPI routes, SQLAlchemy schema, storage, worker, rules
app/frontend/       React + TypeScript interface and browser tests
ml/                 Optional training and holdout-evaluation commands
scripts/            Windows setup/start, backup, disposable test server
tests/              Backend workflow and dataset-validation tests
docs/               Architecture, Windows, training, and implementation notes
data/               Generated local data (ignored by Git)
```
