# Windows setup and troubleshooting

## Before starting

- Install Python **3.12** and include the Windows Python launcher (`py`).
- Install Node.js **22.12 or later**. Open a fresh PowerShell window afterward.
- Extract or clone the project to your SSD. An ordinary folder such as `C:\Projects\vehicle-photo-qc` is suitable.
- An NVIDIA GPU is not required for imports or technical checks. Set up GPU training after the app works.

## Manual setup (no PowerShell scripts or activation required)

Run these commands from the repository's top-level folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
cd app\frontend
npm.cmd ci
npm.cmd run build
cd ..\..
.\.venv\Scripts\python.exe -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000. On later visits, only run the final command (or `scripts\start-windows.ps1`).

## Put photos on another drive

Before starting the app:

```powershell
$env:QC_DATA_DIR = "D:\VehiclePhotoQC\data"
```

Set this every time in a new terminal, or add it to your own local startup shortcut/script. Keep that path the same when training or backing up. The app creates the directory if necessary. If you already have data, stop the app and copy the **entire** data directory to the new location before changing the setting.

## Common problems

| Symptom | Action |
|---|---|
| `py` is not recognized | Install Python with its Windows launcher; reopen the terminal. |
| Python 3.12 cannot be found | Install Python 3.12, then run `py -3.12 --version`. |
| `npm.ps1` is blocked | Use `npm.cmd` as shown above; no execution-policy change is required. |
| Port 8000 is already in use | Stop the other app instance with Ctrl+C. Do not start two instances against the same library. |
| Browser shows 404 at the home page | Run `npm.cmd run build` in `app/frontend`, then restart the backend. |
| Interface says the local server is unavailable | Keep the backend terminal running; check http://127.0.0.1:8000/api/health. |
| Upload fails | Use JPEG/PNG/WebP, at most 25 MB each, 200 files and 1 GB per shoot. HEIC/RAW need conversion. |
| A batch contains one corrupt image | The batch rolls back. Remove or re-export that file and import again. |
| Analysis says failed | The original remains saved. Check terminal logs, disk space, and model files. Disable the active model if necessary, then click Reanalyze. |
| Library looks empty after a restart | Check that `QC_DATA_DIR` points at the same folder as before. |
| Phone cannot open the PC app | Local startup accepts only this PC. For approved remote users, configure [remote access](REMOTE-ACCESS.md). |

## Update the code later

Stop the app, make a backup, then pull or download the updated source. Do not overwrite or delete your data folder. Rerun setup to install dependencies and build the updated interface. Database schema version 1 is the initial bootstrap; future schema changes must ship with explicit migration instructions.

## Browser tests on Windows

From the repository root:

```powershell
$env:QC_TEST_PYTHON = (Resolve-Path .venv\Scripts\python.exe).Path
cd app\frontend
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

Stop the normal app first. Tests launch a disposable database, so they do not modify your photo library.
