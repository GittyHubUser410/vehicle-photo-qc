import sqlite3

import pytest
from fastapi.testclient import TestClient

from ml.common import read_manifest
from qc.banner import banner_overlap, banner_region
from qc.catalog import DEFAULT_SEQUENCE, QUALITY_KEYS
from qc.db import ModelVersion
from qc.main import create_app
from test_workflows import analyze, image_bytes, upload


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, start_worker=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def batch(client, count=3, **kwargs):
    files = [("files", (f"{i}.jpg", image_bytes((50 + i * 30, 80, 120)), "image/jpeg")) for i in range(count)]
    response = upload(client, files, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def detail(client, sid):
    response = client.get(f"/api/shoots/{sid}")
    assert response.status_code == 200, response.text
    return response.json()


def save(client, photo, **overrides):
    body = {
        "labels": photo["training"]["labels"],
        "revision": photo["training"]["revision"],
        "eligible": True,
        **overrides,
    }
    response = client.put(f"/api/photos/{photo['id']}/training", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_good_defaults_and_shot_sync_without_overwriting_manual_training(client, app):
    sid = batch(client, purpose="training")
    analyze(app, sid)
    photos = detail(client, sid)["photos"]
    assert [p["shot_type"] for p in photos] == DEFAULT_SEQUENCE[:3]
    for p in photos:
        assert all(p["training"]["labels"][key] == "good" for key in QUALITY_KEYS)
        assert p["training"]["labels"]["shot_type"] == p["shot_type"]
        assert p["training"]["eligible"]
    p = photos[0]
    save(client, p, labels={**p["training"]["labels"], "shot_type": "rear"})
    url = f"/api/photos/{p['id']}/shot"
    assert client.put(url, json={"shot_type": p["shot_type"]}).status_code == 200
    assert detail(client, sid)["photos"][0]["training"]["labels"]["shot_type"] == "rear"
    assert client.put(url, json={"shot_type": "front"}).status_code == 200
    updated = detail(client, sid)["photos"][0]
    assert updated["training"]["labels"]["shot_type"] == "front"
    assert not updated["training"]["eligible"]


def test_bulk_paste_preserves_shots_and_rolls_back_stale_targets(client):
    sid = batch(client, purpose="training")
    photos = detail(client, sid)["photos"]
    save(client, photos[1], labels={**photos[1]["training"]["labels"], "shot_type": "rear"})
    photos = detail(client, sid)["photos"]
    request = {
        "labels": {**photos[0]["training"]["labels"], "exposure": "bad", "note": "Overexposed"},
        "targets": [{"photo_id": p["id"], "revision": p["training"]["revision"]} for p in photos[1:]],
    }
    request["targets"][-1]["revision"] = 99
    assert client.post("/api/training/paste", json=request).status_code == 409
    assert detail(client, sid)["photos"][1]["training"]["labels"]["exposure"] == "good"
    request["targets"][-1]["revision"] = 0
    assert client.post("/api/training/paste", json=request).status_code == 200
    after = detail(client, sid)["photos"]
    for before, after in zip(photos[1:], after[1:]):
        assert after["shot_type"] == before["shot_type"]
        assert after["training"]["labels"]["shot_type"] == before["training"]["labels"]["shot_type"]
        assert after["training"]["labels"]["exposure"] == "bad"
        assert not after["training"]["eligible"]


def test_sequences_memory_rules_invalidation_and_dealer_isolation(client, app):
    dealer = client.get("/api/config").json()["dealerships"][0]
    did = dealer["id"]
    args = {"mode": "dealership", "dealership_id": did, "inventory_type": "used"}
    body = {
        "name": dealer["name"],
        "group_id": None,
        "new_rules": {},
        "used_rules": {"required_shots": ["front", "rear"]},
    }
    assert client.put(f"/api/dealerships/{did}", json=body).status_code == 200

    def seq(inventory="used"):
        return client.get(f"/api/sequence?dealership_id={did}&inventory_type={inventory}").json()["sequence"]

    assert seq() == ["front", "rear"]
    sid = batch(client, 3, **args, shot_types=["front", "wheel", "rear"])
    assert seq() == ["front", "wheel", "rear"]
    assert seq("new") == DEFAULT_SEQUENCE
    assert [p["shot_type"] for p in detail(client, batch(client, 4, **args))["photos"]] == [
        "front",
        "wheel",
        "rear",
        "unknown",
    ]
    body["used_rules"]["required_shots"] = ["rear", "front"]
    client.put(f"/api/dealerships/{did}", json=body)
    assert seq() == ["rear", "front"]
    analyze(app, sid)
    photo = detail(client, sid)["photos"][0]
    client.put(f"/api/photos/{photo['id']}/shot", json={"shot_type": "engine"})
    assert seq() == ["rear", "front"]
    assert client.get("/api/sequence").json()["sequence"] == DEFAULT_SEQUENCE
    generic = detail(client, batch(client, 9))["photos"]
    assert [p["shot_type"] for p in generic] == DEFAULT_SEQUENCE + ["unknown"]


def test_trash_filters_preserves_files_and_restores_without_approval(client, app):
    sid = batch(client, 2)
    analyze(app, sid)
    photos = detail(client, sid)["photos"]
    for p in photos:
        client.post(f"/api/photos/{p['id']}/training")
    photos = detail(client, sid)["photos"]
    for p in photos:
        save(client, p, verify_fields=["shot_type"])
    exported = client.post("/api/datasets").json()
    snapshot = client.get(exported["download_url"]).json()
    path = app.state.data / f"datasets/{snapshot['id']}.json"
    original_snapshot = path.read_bytes()
    first = photos[0]
    assert client.post(f"/api/photos/{first['id']}/trash", json={"scope": "training"}).status_code == 200
    assert len(detail(client, sid)["photos"]) == 2
    training_card = client.get("/api/shoots?purpose=training").json()["items"][0]
    assert training_card["photo_count"] == 1
    assert training_card["previews"][0]["id"] == photos[1]["id"]
    assert len(read_manifest(path, app.state.data)[1]) == 1
    assert len(read_manifest(path, app.state.data, respect_trash=False)[1]) == 2
    assert client.post(f"/api/shoots/{sid}/trash", json={"scope": "all"}).status_code == 200
    for url in ["/api/shoots", "/api/shoots?purpose=training", "/api/reviews"]:
        assert client.get(url).json()["total"] == 0
    assert client.get("/api/dashboard").json()["training_count"] == 0
    assert client.get(f"/api/photos/{first['id']}/original").status_code == 404
    assert client.post("/api/datasets").status_code == 422
    with pytest.raises(ValueError, match="approved"):
        read_manifest(path, app.state.data)
    assert path.read_bytes() == original_snapshot
    for p in photos:
        assert (app.state.data / p["original_key"]).is_file()
    assert client.post(f"/api/trash/shoot/{sid}/restore", json={"scope": "all"}).status_code == 200
    assert client.get("/api/reviews").json()["total"] == 2
    assert not detail(client, sid)["photos"][1]["training"]["eligible"]
    assert (
        client.post(f"/api/trash/photo/{first['id']}/restore", json={"scope": "training"}).status_code == 200
    )
    assert not detail(client, sid)["photos"][0]["training"]["eligible"]
    with pytest.raises(ValueError, match="approved"):
        read_manifest(path, app.state.data)
    assert client.post(f"/api/shoots/{sid}/trash", json={"scope": "training"}).status_code == 200
    assert client.get("/api/shoots?purpose=training").json()["total"] == 0
    assert client.get("/api/shoots").json()["total"] == 1
    assert client.post(f"/api/trash/shoot/{sid}/restore", json={"scope": "training"}).status_code == 200
    assert client.post(f"/api/photos/{first['id']}/trash", json={"scope": "all"}).status_code == 200
    analyze(app, sid)
    assert len(detail(client, sid)["photos"]) == 1
    assert client.get("/api/reviews").json()["total"] == 1
    assert client.post(f"/api/trash/photo/{first['id']}/restore", json={"scope": "all"}).status_code == 200
    analyze(app, sid)
    assert len(detail(client, sid)["photos"]) == 2


def test_banner_scope_analysis_context_and_configurable_catalog(client, app):
    rules = {"banner_top_pct": 10, "banner_clearance_pct": 2, "banner_application": "first"}
    assert banner_overlap(banner_region(rules, 1, "front"), 0.05) == "overlap"
    assert banner_overlap(banner_region(rules, 2, "front"), 0.05) == "not_applicable"
    rules["banner_application"] = "all"
    assert banner_overlap(banner_region(rules, 2, "front"), 0.2) == "clear"
    rules["banner_shot_types"] = ["front"]
    assert banner_overlap(banner_region(rules, 1, "unknown")) == "needs_shot_label"
    assert banner_overlap(banner_region(rules, 1, "rear")) == "not_applicable"
    assert (
        banner_overlap(banner_region({**rules, "banner_application": "none"}, 1, "front")) == "not_applicable"
    )
    assert banner_region({"banner_top_pct": 10}, 2, "front")["applicable"]
    added = client.post("/api/shot-types", json={"name": "Charging port"})
    assert added.status_code == 201
    config = client.get("/api/config").json()
    assert list(config["shot_type_labels"].values()).count("Center console") == 1
    assert client.post("/api/shot-types", json={"name": "center console"}).status_code == 409
    dealer = config["dealerships"][0]
    assert (
        client.put(
            f"/api/dealerships/{dealer['id']}",
            json={
                "name": dealer["name"],
                "used_rules": {
                    **rules,
                    "banner_application": "first",
                    "required_shots": ["charging_port"],
                    "banner_shot_types": [],
                },
            },
        ).status_code
        == 200
    )
    sid = batch(client, 2, mode="dealership", dealership_id=dealer["id"])
    analyze(app, sid)
    photos = detail(client, sid)["photos"]
    assert photos[0]["shot_type"] == "charging_port"
    assert photos[0]["analysis"]["context"]["banner_overlap"] == "unavailable"
    assert photos[1]["analysis"]["context"]["banner_overlap"] == "not_applicable"


def test_v1_migration_preserves_rows_labels_files_and_models(tmp_path):
    old = create_app(tmp_path, start_worker=False)
    with TestClient(old) as c:
        sid = batch(c, 1, purpose="training")
        analyze(old, sid)
        p = detail(c, sid)["photos"][0]
        save(c, p, labels={"shot_type": "interior", "exposure": "unknown", "note": "Historic label"})
    with old.state.factory() as session:
        session.add(
            ModelVersion(
                name="Existing model",
                artifact_key="models/existing.pt",
                classes=["front", "interior"],
                metrics={"accuracy": 0.9},
            )
        )
        session.commit()
    (tmp_path / "models/existing.pt").write_bytes(b"existing weights sentinel")
    old.state.engine.dispose() if hasattr(old.state, "engine") else None
    database = tmp_path / "qc.db"
    with sqlite3.connect(database) as conn:
        strip_v4(conn)
        for table, column in [
            ("vehicle_shoots", "metadata_revision"),
            ("vehicle_shoots", "deleted_at"),
            ("vehicle_shoots", "training_deleted_at"),
            ("photos", "deleted_at"),
            ("training_examples", "deleted_at"),
            ("photo_metrics", "context"),
        ]:
            conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        conn.execute("DROP TABLE shot_types")
        conn.execute("DROP TABLE dealer_sequences")
        conn.execute("PRAGMA user_version=1")
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before = {
            table: (
                [r[1] for r in conn.execute(f"PRAGMA table_info({table})")],
                conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall(),
            )
            for table in tables
        }
    files = {
        str(p.relative_to(tmp_path)): p.read_bytes()
        for folder in ["originals", "thumbnails", "models"]
        for p in (tmp_path / folder).rglob("*")
        if p.is_file()
    }
    upgraded = create_app(tmp_path, start_worker=False)
    with TestClient(upgraded) as c:
        got = detail(c, sid)["photos"][0]
        assert got["training"]["labels"]["exposure"] == "unknown"
        assert got["training"]["labels"]["shot_type"] == "interior"
    with sqlite3.connect(database) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
        for table, (columns, rows) in before.items():
            assert conn.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY rowid").fetchall() == rows
    assert list((tmp_path / "migration-backups").glob("before-v4-from-v1-*.db"))
    for key, content in files.items():
        assert (tmp_path / key).read_bytes() == content
    create_app(tmp_path, start_worker=False)  # Idempotent upgrade/startup.


def strip_v4(conn):
    """Recreate pre-evidence columns, rather than merely falsifying the version stamp."""
    conn.execute("DROP TABLE photo_shot_revisions")
    for table, column in [
        ("photos", "shot_revision"),
        ("photos", "shot_evidence"),
        ("training_examples", "label_evidence"),
        ("training_label_revisions", "label_evidence"),
        ("analysis_runs", "check_results"),
        ("analysis_runs", "evidence_schema_version"),
    ]:
        conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
