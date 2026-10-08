import hashlib
import io
import json
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from qc.analysis import Worker, analyze_shoot, coverage_findings
from qc.db import Photo, Run, Shoot
from qc.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, start_worker=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def image_bytes(color=(130, 130, 130), noise=False, exif=None):
    out = io.BytesIO()
    if noise:
        im = Image.fromarray(np.random.default_rng(5).integers(30, 225, (200, 300, 3), dtype=np.uint8))
    else:
        im = Image.new("RGB", (300, 200), color)
    im.save(out, format="JPEG", **({"exif": exif} if exif else {}))
    return out.getvalue()


def upload(client, files=None, **overrides):
    metadata = {"mode": "general", "shoot_date": "2026-10-03", "stock_number": "U12345", **overrides}
    return client.post(
        "/api/shoots",
        data={"metadata": json.dumps(metadata)},
        files=files or [("files", ("photo.jpg", image_bytes(), "image/jpeg"))],
    )


def analyze(app, shoot_id):
    analyze_shoot(app.state.factory, app.state.data, shoot_id)


def test_import_order_immutable_original_exif_and_season(client, app):
    exif = Image.Exif()
    exif[274] = 6
    exif[271] = "Test camera"
    original = image_bytes(exif=exif)
    response = upload(
        client,
        [
            ("files", ("second.jpg", original, "image/jpeg")),
            ("files", ("first.jpg", image_bytes(noise=True), "image/jpeg")),
        ],
    )
    assert response.status_code == 201, response.text
    shoot = client.get(f"/api/shoots/{response.json()['id']}").json()
    assert [p["original_filename"] for p in shoot["photos"]] == ["second.jpg", "first.jpg"]
    assert [p["position"] for p in shoot["photos"]] == [1, 2]
    p = shoot["photos"][0]
    assert (p["width"], p["height"]) == (200, 300)
    assert p["exif"]["camera_make"] == "Test camera"
    assert client.get(f"/api/photos/{p['id']}/original").content == original
    assert (app.state.data / p["original_key"]).read_bytes() == original
    assert hashlib.sha256(original).hexdigest() == p["sha256"]
    assert shoot["season"] == "autumn"


def test_batch_rollback_leaves_no_photos_or_orphans(client, app):
    response = upload(
        client,
        [
            ("files", ("valid.jpg", image_bytes(), "image/jpeg")),
            ("files", ("bad.jpg", b"not an image", "image/jpeg")),
        ],
    )
    assert response.status_code == 422
    with app.state.factory() as session:
        assert session.scalar(select(func.count()).select_from(Photo)) == 0
        assert session.scalar(select(func.count()).select_from(Shoot)) == 0
    assert not [p for p in (app.state.data / "originals").rglob("*") if p.is_file()]
    assert not [p for p in (app.state.data / "thumbnails").rglob("*") if p.is_file()]
    assert not list((app.state.data / "tmp").iterdir())


def test_review_view_is_not_resolve_and_history_survives(client, app):
    shoot_id = upload(client).json()["id"]
    analyze(app, shoot_id)
    reviews = client.get("/api/reviews").json()
    assert reviews["total"] == 1
    review_id = reviews["items"][0]["id"]
    viewed = client.patch(f"/api/reviews/{review_id}", json={"action": "view"}).json()
    assert viewed["viewed_at"] and not viewed["resolved_at"]
    assert client.get("/api/reviews").json()["total"] == 1
    client.patch(
        f"/api/reviews/{review_id}",
        json={"action": "resolve", "note": "Reviewed; reshoot requested", "resolution": "reshoot_requested"},
    )
    assert client.get("/api/reviews").json()["total"] == 0
    assert client.get("/api/shoots?previously_queued=yes").json()["total"] == 1
    history = client.get(f"/api/shoots/{shoot_id}").json()["reviews"]
    assert history[0]["note"] == "Reviewed; reshoot requested"
    assert [e["action"] for e in history[0]["events"]] == ["view", "resolve"]
    assert client.get(f"/api/photos/{reviews['items'][0]['photo_id']}/original").status_code == 200
    client.patch(f"/api/reviews/{review_id}", json={"action": "reopen"})
    assert client.get("/api/reviews").json()["total"] == 1


def test_rerun_retains_analyses_without_duplicate_open_reviews(client, app):
    shoot_id = upload(client).json()["id"]
    analyze(app, shoot_id)
    first = client.get(f"/api/shoots/{shoot_id}").json()["current_run_id"]
    assert client.post(f"/api/shoots/{shoot_id}/reanalyze").status_code == 200
    assert client.post(f"/api/shoots/{shoot_id}/reanalyze").status_code == 409
    analyze(app, shoot_id)
    detail = client.get(f"/api/shoots/{shoot_id}").json()
    assert first != detail["current_run_id"]
    assert len(detail["runs"]) == 2
    assert len(detail["reviews"]) == 1


def test_rule_inheritance_new_used_snapshot_and_input_validation(client, app):
    config = client.get("/api/config").json()
    group, dealer = config["groups"][0], config["dealerships"][0]
    client.put(
        f"/api/groups/{group['id']}", json={"name": group["name"], "rules": {"min_photos": 5, "blur_min": 99}}
    )
    dealer_body = {
        "name": dealer["name"],
        "group_id": group["id"],
        "new_rules": {"min_photos": 2},
        "used_rules": {},
    }
    assert client.put(f"/api/dealerships/{dealer['id']}", json=dealer_body).status_code == 200
    c = client.get("/api/config").json()["dealerships"][0]
    assert c["effective_new"]["rules"]["min_photos"] == 2
    assert c["effective_used"]["rules"]["min_photos"] == 5
    assert c["effective_new"]["origins"]["blur_min"] == "group"
    shoot_id = upload(client, mode="dealership", dealership_id=dealer["id"], inventory_type="new").json()[
        "id"
    ]
    client.put(f"/api/groups/{group['id']}", json={"name": group["name"], "rules": {"blur_min": 5}})
    assert client.get(f"/api/shoots/{shoot_id}").json()["policy"]["rules"]["blur_min"] == 99
    assert (
        client.put(
            f"/api/groups/{group['id']}", json={"name": group["name"], "rules": {"bogus": 5}}
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/groups/{group['id']}", json={"name": group["name"], "rules": {"bright_max": 2}}
        ).status_code
        == 422
    )


def test_general_qc_ignores_dealer_requirements(client, app):
    shoot_id = upload(client).json()["id"]
    analyze(app, shoot_id)
    detail = client.get(f"/api/shoots/{shoot_id}").json()
    assert detail["checks"]["required_shots"] == "not_applicable"
    assert detail["checks"]["critical_crop"] == "unavailable"
    assert detail["checks"]["shot_classification"] == "manual_only"


def test_required_shots_wait_for_labels_and_sequence_is_subsequence():
    rules = {"min_photos": 2, "required_shots": ["front", "rear"], "strict_sequence": True}
    findings, state = coverage_findings(["front", "unknown"], rules, False)
    assert not findings and state == "needs_shot_labels"
    findings, state = coverage_findings(["front", "interior", "rear"], rules, False)
    assert not findings and state == "checked"
    findings, _ = coverage_findings(["rear", "front"], rules, False)
    assert findings[0][0] == "SEQUENCE"
    findings, _ = coverage_findings(["front", "interior"], rules, False)
    assert findings[0][0] == "MISSING_REQUIRED_SHOT"


def test_training_approval_revision_and_duplicate_safe_dataset(client, app):
    shoot1 = upload(client, purpose="training", source="Stage Now").json()["id"]
    shoot2 = upload(client, purpose="training", source="Stage Now", stock_number="OTHER").json()["id"]
    analyze(app, shoot1)
    assert client.get("/api/reviews").json()["total"] == 0
    assert client.post("/api/datasets").status_code == 422
    for shoot_id in (shoot1, shoot2):
        photo = client.get(f"/api/shoots/{shoot_id}").json()["photos"][0]
        url = f"/api/photos/{photo['id']}/training"
        assert client.put(url, json={"labels": {}, "eligible": True, "revision": 0}).status_code == 422
        saved = client.put(
            url,
            json={
                "labels": {"shot_type": "front", "blur": "bad"},
                "eligible": True,
                "revision": 0,
                "verify_fields": ["shot_type"],
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == 1
        assert client.put(url, json={"labels": {"shot_type": "rear"}, "revision": 0}).status_code == 409
    exported = client.post("/api/datasets").json()
    snapshot = client.get(exported["download_url"]).json()
    assert len(snapshot["entries"]) == 2
    assert len({e["split"] for e in snapshot["entries"]}) == 1
    assert len({e["group_id"] for e in snapshot["entries"]}) == 1
    assert snapshot["entries"][0]["labels"]["shot_type"] == "front"
    client.put(url, json={"labels": {"shot_type": "rear"}, "eligible": False, "revision": 1})
    assert client.get(exported["download_url"]).json() == snapshot


def test_filters_and_promotion_to_training(client, app):
    shoot_id = upload(
        client,
        make="Ford",
        model="Explorer",
        photographer_id=client.get("/api/config").json()["photographers"][0]["id"],
    ).json()["id"]
    analyze(app, shoot_id)
    assert client.get("/api/shoots?q=explorer&issue=BLUR&season=autumn&max_score=80").json()["total"] == 1
    assert client.get("/api/shoots?q=toyota").json()["total"] == 0
    photo = client.get(f"/api/shoots/{shoot_id}").json()["photos"][0]
    assert client.post(f"/api/photos/{photo['id']}/training").status_code == 200
    assert client.get("/api/shoots?purpose=training").json()["total"] == 1
    assert client.get("/api/shoots?purpose=evaluation").json()["total"] == 1
    assert client.put(f"/api/photos/{photo['id']}/shot", json={"shot_type": "front"}).status_code == 200
    assert client.get("/api/shoots?shot_type=front").json()["total"] == 1
    assert client.get(f"/api/shoots/{shoot_id}").json()["checks"]["required_shots"] == "needs_reanalysis"


def test_queue_survives_restart_and_recovers_interrupted_work(client, app):
    shoot_id = upload(client).json()["id"]
    with app.state.factory() as session:
        session.get(Shoot, shoot_id).status = "processing"
        session.add(
            Run(shoot_id=shoot_id, pipeline_version="interrupted-test", policy_snapshot={}, status="running")
        )
        session.commit()
    worker = Worker(app.state.factory, app.state.data)
    worker.start()
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            detail = client.get(f"/api/shoots/{shoot_id}").json()
            if detail["status"] == "complete":
                break
            time.sleep(0.05)
        assert detail["status"] == "complete"
        assert {r["status"] for r in detail["runs"]} == {"interrupted", "complete"}
    finally:
        worker.stop()


def test_untrusted_origin_host_and_invalid_reference_are_rejected(client):
    assert (
        client.post(
            "/api/photographers", json={"name": "Injected"}, headers={"Origin": "https://example.com"}
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "evil.example.com"}).status_code == 400
    assert upload(client, mode="dealership", dealership_id="missing").status_code == 404
    assert upload(client, mode="general", dealership_id="missing").status_code == 422
    assert client.get("/api/photos/missing/original").status_code == 404
