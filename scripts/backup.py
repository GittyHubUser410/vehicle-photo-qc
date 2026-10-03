"""Offline backup: stop the app and any training process before running this command."""

import argparse
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from qc.db import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="New backup folder, preferably on a separate drive")
    parser.add_argument("--data-dir", default=os.environ.get("QC_DATA_DIR", str(ROOT / "data")))
    parser.add_argument(
        "--app-stopped", action="store_true", help="Confirm the app and training processes are stopped"
    )
    args = parser.parse_args()
    if not args.app_stopped:
        parser.error(
            "Stop the app and training, then pass --app-stopped to make a consistent photo/database backup."
        )
    source = Path(args.data_dir).resolve()
    destination = Path(args.destination).resolve()
    if destination.is_relative_to(source):
        parser.error("The backup folder must be outside the active data folder.")
    if not (source / "qc.db").is_file():
        parser.error("No application database in the selected data directory.")
    target = destination / ("vehicle-qc-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    target.mkdir(parents=True, exist_ok=False)
    # SQLite's backup API produces a consistent database including any remaining WAL data.
    with sqlite3.connect(source / "qc.db") as original, sqlite3.connect(target / "qc.db") as backup:
        original.backup(backup)
    for folder in ("originals", "thumbnails", "datasets", "models"):
        if (source / folder).exists():
            shutil.copytree(source / folder, target / folder)
    print(f"Backup complete: {target}")


if __name__ == "__main__":
    main()
