"""Additive, transactional upgrades with a unique verified pre-upgrade SQLite backup."""

import json
from contextlib import closing
import sqlite3
import uuid

SCHEMA_VERSION = 4


def legacy_evidence(value, revision):
    return {
        "evidence_schema_version": 1,
        "state": "legacy_unverified",
        "source": "legacy_migration",
        "value": value,
        "value_revision": revision,
        "recorded_at": None,
        "actor_id": "migration",
        "actor_display": "migration",
        "actor_basis": "system",
        "source_ref": None,
    }


def backup_database(data, version):
    folder = data / "migration-backups"
    folder.mkdir(exist_ok=True)
    target = folder / f"before-v{SCHEMA_VERSION}-from-v{version}-{uuid.uuid4().hex}.db"
    # Exclusive reservation prevents reuse of a stale or unrelated backup.
    with target.open("xb"):
        pass
    with closing(sqlite3.connect(data / "qc.db")) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Pre-migration backup failed integrity check; refusing migration.")
        if dst.execute("PRAGMA user_version").fetchone()[0] != version:
            raise RuntimeError("Pre-migration backup version changed; stop the app before upgrading.")
        dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return target


def migrate(engine, data):
    with engine.connect() as conn:
        version = conn.exec_driver_sql("PRAGMA user_version").scalar()
        tables = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
    if version not in range(SCHEMA_VERSION + 1):
        raise RuntimeError(f"Unsupported database schema {version}; use the matching app version.")
    if version == 0 and tables:
        raise RuntimeError(
            "Unversioned existing database: refusing to guess its schema. Restore the correct version."
        )
    if version in (0, SCHEMA_VERSION):
        return
    backup_database(data, version)
    with engine.connect() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            if conn.exec_driver_sql("PRAGMA user_version").scalar() != version:
                raise RuntimeError(
                    "Database version changed during backup; stop all app instances and retry."
                )
            changes = {
                "photos": {
                    "shot_revision": "INTEGER NOT NULL DEFAULT 0",
                    "shot_evidence": "JSON NOT NULL DEFAULT '{}'",
                },
                "training_examples": {"label_evidence": "JSON NOT NULL DEFAULT '{}'"},
                "training_label_revisions": {"label_evidence": "JSON NOT NULL DEFAULT '{}'"},
                "analysis_runs": {
                    "evidence_schema_version": "INTEGER NOT NULL DEFAULT 0",
                    "check_results": "JSON NOT NULL DEFAULT '[]'",
                },
            }
            if version == 1:
                changes["vehicle_shoots"] = {"deleted_at": "VARCHAR", "training_deleted_at": "VARCHAR"}
                changes["photos"]["deleted_at"] = "VARCHAR"
                changes["training_examples"]["deleted_at"] = "VARCHAR"
                changes["photo_metrics"] = {"context": "JSON NOT NULL DEFAULT '{}'"}
            if version <= 2:
                changes.setdefault("vehicle_shoots", {})["metadata_revision"] = "INTEGER NOT NULL DEFAULT 0"
                if "shot_types" in tables:
                    changes["shot_types"] = {"archived": "BOOLEAN NOT NULL DEFAULT 0"}
            for table, columns in changes.items():
                existing = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
                for name, sql_type in columns.items():
                    if name not in existing:
                        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
            from .db import Base

            # Include tables absent in v1 in the same transaction as the final stamp.
            Base.metadata.create_all(conn)
            for row in conn.exec_driver_sql("SELECT id, shot_type FROM photos").all():
                conn.exec_driver_sql(
                    "UPDATE photos SET shot_evidence=? WHERE id=?",
                    (json.dumps(legacy_evidence(row[1], 0)), row[0]),
                )
            for table in ("training_examples", "training_label_revisions"):
                for row in conn.exec_driver_sql(f"SELECT id, labels, revision FROM {table}").all():
                    labels = json.loads(row[1])
                    envelope = {k: legacy_evidence(v, row[2]) for k, v in labels.items() if k != "note"}
                    conn.exec_driver_sql(
                        f"UPDATE {table} SET label_evidence=? WHERE id=?", (json.dumps(envelope), row[0])
                    )
            conn.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
