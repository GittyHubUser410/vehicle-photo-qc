import sqlite3

import pytest
from fastapi.testclient import TestClient

from qc.main import create_app
from test_revisions import batch, detail, save
from test_workflows import analyze


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, start_worker=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def metadata(shoot, **changes):
    keys = [
        "mode",
        "dealership_id",
        "photographer_id",
        "source",
        "stock_number",
        "inventory_type",
        "year",
        "make",
        "model",
        "trim",
        "color",
        "shoot_date",
        "season",
        "lighting",
        "ground",
        "location",
        "note",
        "metadata_revision",
    ]
    return {**{k: shoot[k] for k in keys}, **changes}


def test_vehicle_edit_retains_bytes_labels_history_and_rejects_stale_edits(client, app):
    sid = batch(client, purpose="training", year=2021, make="Ford", model="Explorer")
    analyze(app, sid)
    before = detail(client, sid)
    p = before["photos"][0]
    original = client.get(f"/api/photos/{p['id']}/original").content
    dealer = client.get("/api/config").json()["dealerships"][0]["id"]
    body = metadata(before, dealership_id=dealer, mode="dealership", year=2024, stock_number="NEW-1")
    result = client.put(f"/api/shoots/{sid}", json=body)
    assert result.status_code == 200, result.text
    assert result.json()["reanalysis"]
    analyze(app, sid)
    after = detail(client, sid)
    assert after["purpose"] == "training"
    assert after["year"] == 2024 and after["dealership_id"] == dealer
    assert len(after["runs"]) == len(before["runs"]) + 1
    assert after["photos"][0]["training"] == p["training"]
    assert after["photos"][0]["original_filename"] == p["original_filename"]
    assert "2024_Ford_Explorer" in after["photos"][0]["display_filename"]
    assert client.get(f"/api/photos/{p['id']}/original").content == original
    download = client.get(f"/api/photos/{p['id']}/original?download=true")
    assert download.content == original
    assert "2024_Ford_Explorer" in download.headers["content-disposition"]
    assert client.put(f"/api/shoots/{sid}", json=body).status_code == 409
    assert client.put(f"/api/shoots/{sid}", json=metadata(after, dealership_id="missing")).status_code == 404


def test_bulk_membership_is_atomic_isolated_and_preserves_labels(client, app):
    sid, other = batch(client), batch(client, purpose="training")
    analyze(app, sid)
    photos = detail(client, sid)["photos"]
    other_before = detail(client, other)["photos"]
    url = f"/api/shoots/{sid}/training-membership"
    assert client.put(url, json={"enabled": True}).status_code == 200
    p = detail(client, sid)["photos"][0]
    save(client, p, labels={**p["training"]["labels"], "exposure": "bad", "note": "Keep this label"})
    assert client.put(url, json={"enabled": False, "photo_ids": [p["id"]]}).status_code == 200
    got = detail(client, sid)["photos"]
    assert got[0]["training"] is None and all(p["training"] for p in got[1:])
    assert client.get(f"/api/photos/{p['id']}/original").status_code == 200
    assert client.put(url, json={"enabled": True}).status_code == 200
    restored = detail(client, sid)["photos"][0]["training"]
    assert restored["labels"]["exposure"] == "bad" and not restored["eligible"]
    assert (
        client.put(
            url, json={"enabled": False, "photo_ids": [photos[0]["id"], other_before[0]["id"]]}
        ).status_code
        == 422
    )
    assert detail(client, sid)["photos"][0]["training"] is not None
    assert client.put(url, json={"enabled": False}).status_code == 200
    assert all(p["training"] is None for p in detail(client, sid)["photos"])
    assert detail(client, other)["photos"] == other_before


def test_catalog_archive_rename_order_preserves_model_keys_and_restart(client, app, tmp_path):
    sid = batch(client, purpose="training", shot_types=["front", "rear", "engine"])
    original = detail(client, sid)["photos"]
    assert client.patch("/api/shot-types/front", json={"name": "Front view"}).status_code == 200
    assert client.patch("/api/shot-types/front", json={"name": "Rear"}).status_code == 409
    assert client.patch("/api/shot-types/front", json={"archived": True}).status_code == 200
    config = client.get("/api/config").json()
    assert "front" not in config["shot_types"] and config["shot_type_labels"]["front"] == "Front view"
    assert detail(client, sid)["photos"] == original
    keys = list(reversed(config["shot_types"]))
    assert client.put("/api/shot-types/order", json={"keys": keys}).status_code == 200
    assert client.get("/api/config").json()["shot_types"] == keys
    assert client.put("/api/shot-types/order", json={"keys": keys[:-1]}).status_code == 409
    assert client.patch("/api/shot-types/unknown", json={"archived": True}).status_code == 422
    assert client.get("/api/sequence").json()["sequence"][1] == "unknown"
    # Historical labels remain valid for dataset export even when a category is hidden.
    assert client.post("/api/datasets").status_code == 201
    with TestClient(create_app(tmp_path, start_worker=False)) as restarted:
        assert "front" not in restarted.get("/api/config").json()["shot_types"]
    assert client.patch("/api/shot-types/front", json={"archived": False}).status_code == 200
    assert "front" in client.get("/api/config").json()["shot_types"]
    dealer = client.get("/api/config").json()["dealerships"][0]
    response = client.put(
        "/api/dealerships/" + dealer["id"],
        json={"name": dealer["name"], "new_rules": {"required_shots": ["front"]}},
    )
    assert response.status_code == 200, response.text
    assert client.patch("/api/shot-types/front", json={"archived": True}).status_code == 409


def test_readiness_counts_human_labels_unique_bytes_and_excludes_trash(client, app):
    sid = batch(client, purpose="training", shot_types=["front", "rear", "unknown"])
    dup = batch(client, purpose="training", shot_types=["front", "rear", "unknown"])
    p = detail(client, sid)["photos"][0]
    save(client, p, labels={**p["training"]["labels"], "blur": "bad"})
    data = client.get("/api/training/readiness").json()
    assert data["approved"] == 6 and data["unique_labeled"] == 2 and data["unassigned"] == 2
    assert next(c for c in data["quality"] if c["key"] == "blur")["count"] == 1
    analyze(app, sid)
    assert client.post(f"/api/shoots/{sid}/trash", json={"scope": "training"}).status_code == 200
    data = client.get("/api/training/readiness").json()
    assert data["approved"] == 3
    assert next(c for c in data["quality"] if c["key"] == "blur")["count"] == 0
    assert client.put(f"/api/shoots/{dup}/training-membership", json={"enabled": False}).status_code == 200
    assert client.get("/api/training/readiness").json()["unique_labeled"] == 0


def test_v2_additive_migration_keeps_existing_records_and_files(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        sid = batch(client, purpose="training")
        before = detail(client, sid)
    database = tmp_path / "qc.db"
    with sqlite3.connect(database) as conn:
        conn.execute("ALTER TABLE shot_types DROP COLUMN archived")
        conn.execute("ALTER TABLE vehicle_shoots DROP COLUMN metadata_revision")
        conn.execute("PRAGMA user_version=2")
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        after = detail(client, sid)
        assert after == before
    assert (tmp_path / "migration-backups/before-v3.db").exists()
    with sqlite3.connect(database) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
