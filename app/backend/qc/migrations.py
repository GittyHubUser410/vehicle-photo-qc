"""Additive schema migrations. Preserve rows/files and back up v1 before altering it."""

import sqlite3

SCHEMA_VERSION = 3


def migrate(engine, data):
    with engine.connect() as conn:
        version = conn.exec_driver_sql("PRAGMA user_version").scalar()
        tables = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
    if version not in (0, 1, 2, 3):
        raise RuntimeError(f"Unsupported database schema {version}; use the matching app version.")
    if version == 0 and tables:
        raise RuntimeError(
            "Unversioned existing database: refusing to guess its schema. Restore the correct version."
        )
    if version == 1:
        backup = data / "migration-backups"
        backup.mkdir(exist_ok=True)
        target = backup / "before-v2.db"
        if not target.exists():
            with sqlite3.connect(data / "qc.db") as src, sqlite3.connect(target) as dst:
                src.backup(dst)
        changes = {
            "vehicle_shoots": {"deleted_at": "VARCHAR", "training_deleted_at": "VARCHAR"},
            "photos": {"deleted_at": "VARCHAR"},
            "training_examples": {"deleted_at": "VARCHAR"},
            "photo_metrics": {"context": "JSON NOT NULL DEFAULT '{}'"},
        }
        # Explicit BEGIN makes SQLite DDL transactional, including the version stamp.
        with engine.connect() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                for table, columns in changes.items():
                    existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
                    for name, sql_type in columns.items():
                        if name not in existing:
                            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                conn.exec_driver_sql("PRAGMA user_version=2")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    if version in (1, 2):
        backup = data / "migration-backups"
        backup.mkdir(exist_ok=True)
        target = backup / "before-v3.db"
        if not target.exists():
            with sqlite3.connect(data / "qc.db") as src, sqlite3.connect(target) as dst:
                src.backup(dst)
        with engine.connect() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                if "shot_types" in tables:
                    conn.exec_driver_sql(
                        "ALTER TABLE shot_types ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"
                    )
                conn.exec_driver_sql(
                    "ALTER TABLE vehicle_shoots ADD COLUMN metadata_revision INTEGER NOT NULL DEFAULT 0"
                )
                conn.exec_driver_sql("PRAGMA user_version=3")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
