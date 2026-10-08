"""Bounded A.1 acceptance: values/evidence, immutable runs and frozen dataset semantics."""

import copy
import hashlib
import json
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select

from ml.common import read_manifest
from qc import classifier
from qc.analysis import check_record
from qc.db import LabelRevision, ModelVersion, PhotoShotRevision, Run
from qc.evidence import coverage_state, evidence, system_actor
from qc.main import create_app
from qc.migrations import migrate
from test_revisions import batch, detail, save, strip_v4
from test_workflows import analyze


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, start_worker=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def shot(client, p, verify=False, **changes):
    return client.put(
        f"/api/photos/{p['id']}/shot",
        json={
            "shot_type": p["shot_type"],
            "revision": p["shot_revision"],
            "verify": verify,
            **changes,
        },
    )


def test_import_promotion_membership_defaults_suggestion_only_E01(client, app):
    sid = batch(client, purpose="training", shot_types=["front", "rear", "unknown"])
    for p in detail(client, sid)["photos"]:
        assert p["shot_evidence"]["state"] == "suggested"
        assert set(e["state"] for e in p["training"]["label_evidence"].values()) == {"suggested"}
        assert p["training"]["eligible"] and not p["training"]["exportable"]
    other = batch(client)
    p = detail(client, other)["photos"][0]
    promoted = client.post(f"/api/photos/{p['id']}/training").json()
    assert promoted["label_evidence"]["shot_type"]["state"] == "suggested"
    assert not promoted["exportable"]
    client.put(f"/api/shoots/{other}/training-membership", json={"enabled": True})
    assert all(not p["training"]["exportable"] for p in detail(client, other)["photos"])
    assert client.post("/api/datasets").status_code == 422


def test_field_confirmation_changes_note_unknown_validation_E02_E05(client):
    sid = batch(client, 1, purpose="training")
    p = detail(client, sid)["photos"][0]
    t = save(client, p)
    assert not t["exportable"]
    p = detail(client, sid)["photos"][0]
    t = save(client, p, verify_fields=["shot_type"])
    assert t["exportable"] and t["label_evidence"]["blur"]["state"] == "suggested"
    e = t["label_evidence"]["shot_type"]
    assert e["actor_basis"] == "local_declared" and e["recorded_at"]
    assert e["value_revision"] == 2
    p = detail(client, sid)["photos"][0]
    t = save(client, p, labels={**t["labels"], "note": "unrelated"})
    assert t["label_evidence"]["shot_type"] == e and t["exportable"]
    p = detail(client, sid)["photos"][0]
    t = save(client, p, verify_fields=["blur"], labels={**t["labels"], "blur": "bad"})
    assert t["label_evidence"]["shot_type"] == e
    assert t["label_evidence"]["blur"]["state"] == "verified"
    p = detail(client, sid)["photos"][0]
    t = save(client, p, labels={**t["labels"], "shot_type": "rear"})
    assert not t["exportable"] and t["label_evidence"]["shot_type"]["state"] == "suggested"
    p = detail(client, sid)["photos"][0]
    t = save(
        client, p, labels={**t["labels"], "shot_type": "unknown"}, eligible=False, verify_fields=["shot_type"]
    )
    assert t["label_evidence"]["shot_type"]["state"] == "verified"
    assert not t["exportable"] and "unknown_value" in t["exclusion_reasons"]
    for fields in (["note"], ["fake"], ["blur", "blur"]):
        r = client.put(
            f"/api/photos/{p['id']}/training",
            json={"labels": t["labels"], "revision": t["revision"], "verify_fields": fields},
        )
        assert r.status_code == 422
    assert (
        client.put(
            f"/api/photos/{p['id']}/training",
            json={"labels": t["labels"], "label_evidence": {"state": "verified"}},
        ).status_code
        == 422
    )


def test_stale_confirmation_cross_domain_history_E06_E09(client, app):
    sid = batch(client, 1, purpose="training")
    analyze(app, sid)
    p = detail(client, sid)["photos"][0]
    save(client, p, labels={**p["training"]["labels"], "shot_type": "rear"}, verify_fields=["shot_type"])
    assert shot(client, p, True).status_code == 200
    current = detail(client, sid)["photos"][0]
    assert current["shot_evidence"]["state"] == "verified"
    assert current["training"]["labels"]["shot_type"] == "rear"  # same operational value never syncs
    before = copy.deepcopy(current)
    assert shot(client, p, True).status_code == 409
    assert (
        client.put(f"/api/photos/{p['id']}/shot", json={"shot_type": "front", "verify": True}).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/photos/{p['id']}/training",
            json={"labels": p["training"]["labels"], "revision": 0, "verify_fields": ["shot_type"]},
        ).status_code
        == 409
    )
    assert detail(client, sid)["photos"][0] == before
    # Legacy write may invalidate a same-value verified operational field, never verify it.
    assert client.put(f"/api/photos/{p['id']}/shot", json={"shot_type": "front"}).status_code == 200
    current = detail(client, sid)["photos"][0]
    assert current["shot_evidence"]["state"] == "suggested"
    assert current["training"]["label_evidence"]["shot_type"]["state"] == "suggested"
    assert not current["training"]["eligible"]
    with app.state.factory() as session:
        assert len(list(session.scalars(select(PhotoShotRevision)))) == 2
        assert len(list(session.scalars(select(LabelRevision)))) == 2


def test_equal_paste_invalidates_copied_evidence_atomic_rollback_E07_E08(client, app):
    sid = batch(client, 2, purpose="training")
    for p in detail(client, sid)["photos"]:
        save(client, p, verify_fields=["shot_type", "blur", "crop"])
    photos = detail(client, sid)["photos"]
    before = photos[1]["training"]["label_evidence"]["shot_type"]
    r = client.post(
        "/api/training/paste",
        json={
            "labels": photos[0]["training"]["labels"],
            "targets": [{"photo_id": photos[1]["id"], "revision": 1}],
        },
    )
    assert r.status_code == 200
    pasted = detail(client, sid)["photos"][1]["training"]
    assert pasted["label_evidence"]["shot_type"] == before
    assert pasted["label_evidence"]["blur"]["state"] == "suggested"
    assert not pasted["eligible"]
    other = batch(client, 2)
    targets = detail(client, other)["photos"]
    r = client.post(
        "/api/training/paste",
        json={
            "labels": photos[0]["training"]["labels"],
            "targets": [
                {"photo_id": targets[0]["id"], "revision": None},
                {"photo_id": targets[1]["id"], "revision": 99},
            ],
        },
    )
    assert r.status_code == 409
    assert all(p["training"] is None for p in detail(client, other)["photos"])


def test_trash_membership_review_do_not_verify_E10_E11(client, app):
    sid = batch(client, 1)
    analyze(app, sid)
    p = detail(client, sid)["photos"][0]
    client.post(f"/api/photos/{p['id']}/training")
    p = detail(client, sid)["photos"][0]
    t = save(client, p, verify_fields=["shot_type"])
    rid = detail(client, sid)["reviews"][0]["id"]
    for action in ("resolve", "reopen"):
        client.patch(f"/api/reviews/{rid}", json={"action": action, "resolution": "false_positive"})
        assert detail(client, sid)["photos"][0]["training"] == t
    url = f"/api/shoots/{sid}/training-membership"
    client.put(url, json={"enabled": False})
    client.put(url, json={"enabled": True})
    restored = detail(client, sid)["photos"][0]["training"]
    assert restored["label_evidence"] == t["label_evidence"] and not restored["eligible"]
    client.post(f"/api/photos/{p['id']}/trash", json={"scope": "training"})
    client.post(f"/api/trash/photo/{p['id']}/restore", json={"scope": "training"})
    restored = detail(client, sid)["photos"][0]["training"]
    assert restored["label_evidence"] == t["label_evidence"] and not restored["eligible"]
    with pytest.raises(ValueError, match="Human"):
        evidence("front", 1, state="verified", actor=system_actor())


def test_remote_confirmation_uses_validated_subject_I01(client, app):
    sid = batch(client, 1, purpose="training")
    analyze(app, sid)
    p = detail(client, sid)["photos"][0]
    security = app.state.security
    security.remote = True
    security.verify = lambda token: {"sub": "trusted-subject", "email": "reviewer@example.test"}
    security.public_url = "http://testserver"  # test-only trusted origin in existing middleware
    headers = {"Cf-Access-Jwt-Assertion": "test-fixture", "Origin": "http://127.0.0.1:8000"}
    body = {
        "labels": p["training"]["labels"],
        "revision": 0,
        "eligible": True,
        "verify_fields": ["shot_type"],
        "actor": "Impersonated manager",
    }
    result = client.put(f"/api/photos/{p['id']}/training", json=body, headers=headers)
    assert result.status_code == 200, result.text
    ev = result.json()["label_evidence"]["shot_type"]
    assert (ev["actor_id"], ev["actor_display"], ev["actor_basis"]) == (
        "trusted-subject",
        "reviewer@example.test",
        "authenticated",
    )
    result = client.put(
        f"/api/photos/{p['id']}/shot",
        json={"shot_type": p["shot_type"], "revision": 0, "verify": True, "actor": "Spoof"},
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["shot_evidence"]["actor_id"] == "trusted-subject"
    security.remote = False


def test_schema2_round_trip_live_vs_frozen_and_integrity_D01_D07(client, app, tmp_path):
    sid = batch(client, 3, purpose="training")
    photos = detail(client, sid)["photos"]
    t = save(client, photos[0], verify_fields=["shot_type"])
    assert t["exportable"] and t["label_evidence"]["blur"]["state"] == "suggested"
    exported = client.post("/api/datasets")
    assert exported.status_code == 201, exported.text
    manifest = client.get(exported.json()["download_url"]).json()
    assert manifest["schema_version"] == 2 and len(manifest["entries"]) == 1
    assert manifest["entries"][0]["label_evidence"] == t["label_evidence"]
    readiness = client.get("/api/training/readiness").json()
    assert readiness["exportable"] == 1 and readiness["unique_labeled"] == 1
    assert all(q["count"] == 0 for q in readiness["quality"])
    path = app.state.data / f"datasets/{manifest['id']}.json"
    original = path.read_bytes()
    assert read_manifest(path, app.state.data)[0] == manifest
    p = detail(client, sid)["photos"][0]
    save(client, p, labels={**t["labels"], "note": "note only"})
    assert read_manifest(path, app.state.data)[1]
    p = detail(client, sid)["photos"][0]
    save(client, p, labels={**t["labels"], "shot_type": "rear"})
    with pytest.raises(ValueError, match="current verified"):
        read_manifest(path, app.state.data)
    assert (
        read_manifest(path, app.state.data, respect_trash=False)[1][0]["labels"]["shot_type"]
        == t["labels"]["shot_type"]
    )
    assert path.read_bytes() == original
    supplied = tmp_path / "supplied.json"
    changed = copy.deepcopy(manifest)
    changed["seed"] = 0
    supplied.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="differs"):
        read_manifest(supplied, app.state.data, respect_trash=False)
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="integrity"):
        read_manifest(path, app.state.data, respect_trash=False)
    path.write_bytes(original)
    image = app.state.data / manifest["entries"][0]["image_key"]
    image.write_bytes(b"changed image")
    with pytest.raises(ValueError, match="Original image integrity"):
        read_manifest(path, app.state.data, respect_trash=False)


def test_legacy_loader_and_cli_fail_before_model_metrics_writes_D04(client, app, tmp_path):
    sid = batch(client, 1, purpose="training")
    p = detail(client, sid)["photos"][0]
    save(client, p, verify_fields=["shot_type"])
    export = client.post("/api/datasets").json()
    path = app.state.data / f"datasets/{export['id']}.json"
    manifest = json.loads(path.read_text())
    manifest["schema_version"] = 1
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Reverify"):
        read_manifest(path, app.state.data, respect_trash=False)
    assert read_manifest(path, app.state.data, inspect_legacy=True)[1]
    with app.state.factory() as session:
        model = ModelVersion(
            name="legacy active",
            artifact_key="models/legacy.pt",
            classes=["front"],
            dataset_id=export["id"],
            status="active",
            metrics={"accuracy": 0.5},
        )
        session.add(model)
        session.commit()
        mid = model.id
    for module, argument in (("ml.train_shots", str(path)), ("ml.evaluate", mid)):
        result = subprocess.run(
            [sys.executable, "-m", module, argument, "--data-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0 and "Reverify" in result.stderr
    with app.state.factory() as session:
        model = session.get(ModelVersion, mid)
        assert model.metrics == {"accuracy": 0.5} and model.status == "active"
    assert not list((tmp_path / "models").iterdir())


@pytest.mark.parametrize("state", ["suggested", "predicted", "legacy_unverified", None])
def test_unverified_schema2_not_bypassed_by_frozen_mode_D05(client, app, state):
    sid = batch(client, 1, purpose="training")
    save(client, detail(client, sid)["photos"][0], verify_fields=["shot_type"])
    exported = client.post("/api/datasets").json()
    path = app.state.data / f"datasets/{exported['id']}.json"
    manifest = json.loads(path.read_text())
    if state is None:
        manifest["entries"][0]["label_evidence"].pop("shot_type")
    else:
        manifest["entries"][0]["label_evidence"]["shot_type"]["state"] = state
    path.write_text(json.dumps(manifest))
    from qc.db import Dataset

    with app.state.factory() as session:
        session.get(Dataset, exported["id"]).sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        session.commit()
    with pytest.raises(ValueError, match="Unverified"):
        read_manifest(path, app.state.data, respect_trash=False)


@pytest.mark.parametrize("verified", [False, True], ids=["suggested", "human-verified"])
@pytest.mark.parametrize(
    "scenario, execution, outcome, reason",
    [
        ("low", "completed", "unknown", "low_confidence"),
        ("threshold", "completed", "pass", "resolved"),
        ("absent", "unavailable", "unknown", "model_unavailable"),
        ("exception", "error", "unknown", "prediction_error"),
    ],
)
def test_classifier_execution_independent_of_resolution_R1(
    client, app, monkeypatch, verified, scenario, execution, outcome, reason
):
    sid = batch(client, 1, shot_types=["front"])
    analyze(app, sid)
    previous = detail(client, sid)
    photo = previous["photos"][0]
    if verified:
        assert shot(client, photo, True).status_code == 200
    model_id = None
    if scenario != "absent":
        (app.state.data / "models/stub.pt").write_bytes(b"stub")
        with app.state.factory() as session:
            model = ModelVersion(
                name="stub", artifact_key="models/stub.pt", classes=["rear"], status="active"
            )
            session.add(model)
            session.commit()
            model_id = model.id
    calls = []
    confidence = 0.79 if scenario == "low" else 0.8

    def predict(*args):
        calls.append(args)
        if scenario == "exception":
            raise RuntimeError("deterministic prediction failure")
        return "rear", confidence

    monkeypatch.setattr(classifier, "predict", predict)
    assert client.post(f"/api/shoots/{sid}/reanalyze").status_code == 200
    analyze(app, sid)
    result = detail(client, sid)
    assert result["status"] == "complete"
    assert result["score"] == previous["score"]
    assert next(r for r in result["runs"] if r["id"] == previous["current_run_id"]) == previous["runs"][0]
    assert len(calls) == (0 if scenario == "absent" else 1)
    analyzed = result["photos"][0]["analysis"]
    inputs = analyzed["context"]["evidence"]
    check = next(c for c in result["qc_evidence"]["checks"] if c["check_id"] == "shot_classification")
    assert (check["execution"], check["outcome"], check["reason_code"]) == (execution, outcome, reason)
    assert check["model_id"] == model_id
    assert check["run_id"] == result["current_run_id"]
    assert check["input_provenance"] == {
        k: v for k, v in inputs.items() if k not in ("checks", "evidence_schema_version")
    }
    assert check in inputs["checks"]
    run = next(r for r in result["runs"] if r["id"] == result["current_run_id"])
    assert check in run["check_results"]
    assert inputs["resolved_shot"] == (
        "front" if verified else "rear" if scenario == "threshold" else "unknown"
    )
    assert inputs["used_evidence"]["state"] == (
        "verified" if verified else "predicted" if scenario == "threshold" else "unresolved"
    )
    if verified:
        assert inputs["used_evidence"] == result["photos"][0]["shot_evidence"]
    if scenario in ("low", "threshold"):
        assert inputs["prediction"] == {
            "evidence_schema_version": 1,
            "state": "predicted",
            "value": "rear",
            "confidence": confidence,
            "model_id": model_id,
            "run_id": result["current_run_id"],
            "source": "model",
        }
        assert analyzed["predicted_shot"] == "rear"
        assert analyzed["confidence"] == confidence
    else:
        assert inputs["prediction"] is None
        assert analyzed["predicted_shot"] is None and analyzed["confidence"] is None


@pytest.mark.parametrize("confidence, expected", [(0.79, "unknown"), (0.8, "rear")])
def test_prediction_threshold_precedence_and_freshness_Q01_Q03_Q08_Q09(
    client, app, monkeypatch, confidence, expected
):
    dealer = client.get("/api/config").json()["dealerships"][0]
    client.put(
        f"/api/dealerships/{dealer['id']}",
        json={"name": dealer["name"], "used_rules": {"required_shots": ["rear"], "strict_sequence": True}},
    )
    sid = batch(client, 1, mode="dealership", dealership_id=dealer["id"], shot_types=["rear"])
    analyze(app, sid)
    first = detail(client, sid)
    assert first["checks"]["required_shots"] == "needs_shot_labels"
    assert first["qc_evidence"]["coverage"] == "incomplete"
    p = first["photos"][0]
    (app.state.data / "models/stub.pt").write_bytes(b"stub")
    with app.state.factory() as session:
        model = ModelVersion(name="stub", artifact_key="models/stub.pt", classes=["rear"], status="active")
        session.add(model)
        session.commit()
    monkeypatch.setattr(classifier, "predict", lambda *args: ("rear", confidence))
    client.post(f"/api/shoots/{sid}/reanalyze")
    analyze(app, sid)
    predicted = detail(client, sid)
    input_ev = predicted["photos"][0]["analysis"]["context"]["evidence"]
    assert input_ev["resolved_shot"] == expected
    assert input_ev["prediction"]["state"] == "predicted" and input_ev["prediction"]["model_id"]
    assert shot(client, p, True, shot_type="front").status_code == 200
    stale = detail(client, sid)
    assert stale["qc_evidence"]["freshness"] == "stale"
    assert stale["runs"] == predicted["runs"]
    client.post(f"/api/shoots/{sid}/reanalyze")
    analyze(app, sid)
    verified = detail(client, sid)
    inp = verified["photos"][0]["analysis"]["context"]["evidence"]
    assert inp["resolved_shot"] == "front" and inp["used_evidence"]["state"] == "verified"
    assert inp["prediction"]["value"] == "rear"
    assert verified["score"] == first["score"]
    assert verified["qc_evidence"]["freshness"] == "current"
    assert next(r for r in verified["runs"] if r["id"] == predicted["current_run_id"]) == predicted["runs"][0]


def test_photo_count_independent_unavailable_error_and_general_Q04_Q07(client, app, monkeypatch):
    dealer = client.get("/api/config").json()["dealerships"][0]
    client.put(
        f"/api/dealerships/{dealer['id']}",
        json={
            "name": dealer["name"],
            "used_rules": {
                "min_photos": 3,
                "required_shots": ["front"],
                "banner_top_pct": 10,
                "banner_shot_types": ["front"],
            },
        },
    )
    sid = batch(client, 1, mode="dealership", dealership_id=dealer["id"])
    analyze(app, sid)
    d = detail(client, sid)
    checks = {c["check_id"]: c for c in d["qc_evidence"]["checks"]}
    assert checks["photo_count"]["outcome"] == "concern"
    assert checks["required_shots"]["execution"] == "not_run"
    assert checks["banner_clearance"]["applicability"] == "unknown"
    assert checks["critical_crop"]["execution"] == "unavailable"
    assert all(c["outcome"] != "pass" for c in checks.values() if c["execution"] != "completed")
    with app.state.factory() as session:
        run = session.get(Run, d["current_run_id"])
        fixtures = [
            check_record(key, run, outcome="concern" if key == "photo_count" else "pass")
            for key in (
                "blur",
                "exposure",
                "saturation",
                "photo_count",
                "required_shots",
                "sequence",
                "shot_classification",
                "vehicle_segmentation",
                "critical_crop",
                "angle",
                "banner_clearance",
            )
        ]
        assert coverage_state(fixtures) == "complete"  # complete does not mean pass
        assert coverage_state([{**c, "outcome": "pass"} for c in fixtures]) == "complete"
        assert (
            coverage_state([check_record("simulated", run, execution="error", outcome="unknown")])
            == "incomplete"
        )
    general = batch(client, 1)
    analyze(app, general)
    general_checks = {c["check_id"]: c for c in detail(client, general)["qc_evidence"]["checks"]}
    assert general_checks["photo_count"]["reason_code"] == "general_mode"
    assert general_checks["banner_clearance"]["applicability"] == "not_applicable"
    # A model exception is recorded as execution error, never as a detected defect.
    (app.state.data / "models/bad.pt").write_bytes(b"stub")
    with app.state.factory() as session:
        session.add(
            ModelVersion(name="broken", artifact_key="models/bad.pt", classes=["front"], status="active")
        )
        session.commit()
    monkeypatch.setattr(
        classifier, "predict", lambda *a: (_ for _ in ()).throw(RuntimeError("fixture failure"))
    )
    client.post(f"/api/shoots/{sid}/reanalyze")
    analyze(app, sid)
    c = next(
        c for c in detail(client, sid)["qc_evidence"]["checks"] if c["check_id"] == "shot_classification"
    )
    assert c["execution"] == "error" and c["outcome"] == "unknown"


def test_openapi_evidence_requests_and_typed_responses(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert schemas["LabelInput"]["properties"]["verify_fields"]
    assert schemas["ShotInput"]["properties"]["revision"]
    assert schemas["ShotInput"]["properties"]["verify"]["default"] is False
    assert schemas["TrainingResponse"]["properties"]["label_evidence"]["additionalProperties"][
        "$ref"
    ].endswith("EvidenceResponse")
    assert schemas["ShootDetailResponse"]["properties"]["qc_evidence"]["$ref"].endswith("QCResponse")


def file_hashes(data):
    return {
        str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("originals", "thumbnails", "datasets", "models")
        for p in (data / folder).rglob("*")
        if p.is_file()
    }


def table_snapshot(conn):
    return {
        table: (
            [c[1] for c in conn.execute(f"PRAGMA table_info({table})")],
            conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall(),
        )
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def legacy_fixture(data, version):
    old = create_app(data, start_worker=False)
    with TestClient(old) as c:
        dealer = c.get("/api/config").json()["dealerships"][0]
        c.put(
            f"/api/dealerships/{dealer['id']}",
            json={
                "name": dealer["name"],
                "used_rules": {"required_shots": ["front", "rear"], "strict_sequence": True},
            },
        )
        c.post("/api/shot-types", json={"name": "Preserved custom detail"})
        sid = batch(c, 2, purpose="training", mode="dealership", dealership_id=dealer["id"])
        analyze(old, sid)
        p = detail(c, sid)["photos"][0]
        save(c, p, actor="Historical reviewer", verify_fields=["shot_type"])
        # Keep a frozen artifact plus an active model, metrics, rules and catalog.
        exported = c.post("/api/datasets").json()
        path = data / f"datasets/{exported['id']}.json"
        manifest = json.loads(path.read_text())
        manifest["schema_version"] = 1
        path.write_text(json.dumps(manifest))
        with old.state.factory() as session:
            from qc.db import Dataset

            session.get(Dataset, exported["id"]).sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            session.add(
                ModelVersion(
                    name="Preserved active",
                    artifact_key="models/existing.pt",
                    dataset_id=exported["id"],
                    classes=["front", "rear"],
                    status="active",
                    metrics={"accuracy": 0.87, "test_evaluated": True},
                )
            )
            session.commit()
        (data / "models/existing.pt").write_bytes(b"immutable sentinel weights")
        # Retain review history as well as training revisions.
        ev = batch(c, 1)
        analyze(old, ev)
        rid = detail(c, ev)["reviews"][0]["id"]
        c.patch(f"/api/reviews/{rid}", json={"action": "resolve", "resolution": "false_positive"})
    old.state.factory.kw["bind"].dispose()
    with sqlite3.connect(data / "qc.db") as conn:
        # A real pre-A.1 row has no run evidence snapshots.
        for mid, context in conn.execute("SELECT id, context FROM photo_metrics").fetchall():
            ctx = json.loads(context)
            ctx.pop("evidence", None)
            conn.execute("UPDATE photo_metrics SET context=? WHERE id=?", (json.dumps(ctx), mid))
        strip_v4(conn)
        if version <= 2:
            conn.execute("ALTER TABLE vehicle_shoots DROP COLUMN metadata_revision")
            conn.execute("ALTER TABLE shot_types DROP COLUMN archived")
        if version == 1:
            for table, column in (
                ("vehicle_shoots", "deleted_at"),
                ("vehicle_shoots", "training_deleted_at"),
                ("photos", "deleted_at"),
                ("training_examples", "deleted_at"),
                ("photo_metrics", "context"),
            ):
                conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
            conn.execute("DROP TABLE shot_types")
            conn.execute("DROP TABLE dealer_sequences")
        conn.execute(f"PRAGMA user_version={version}")
    return sid


@pytest.mark.parametrize("version", [1, 2, 3])
def test_migration_preservation_backup_repeat_and_restore_M01_M02_M05(tmp_path, version):
    import shutil

    data = tmp_path / "original"
    sid = legacy_fixture(data, version)
    with sqlite3.connect(data / "qc.db") as conn:
        before = table_snapshot(conn)
    files = file_hashes(data)
    full_backup = tmp_path / "full-backup"
    shutil.copytree(data, full_backup)
    upgraded = create_app(data, start_worker=False)
    with TestClient(upgraded) as c:
        d = detail(c, sid)
        assert d["qc_evidence"]["coverage"] == "unknown"
        assert d["qc_evidence"]["freshness"] == "historical_unknown"
        assert d["photos"][0]["training"]["eligible"]
        assert d["photos"][0]["training"]["revision"] > 0
        assert d["photos"][0]["training"]["labeled_by"] == "Historical reviewer"
        for p in d["photos"]:
            assert p["shot_evidence"]["state"] == "legacy_unverified"
            assert not p["training"]["exportable"]
            assert all(e["state"] == "legacy_unverified" for e in p["training"]["label_evidence"].values())
        assert c.post("/api/datasets").status_code == 422
    with sqlite3.connect(data / "qc.db") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        for table, (columns, rows) in before.items():
            assert conn.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY rowid").fetchall() == rows
        assert conn.execute("SELECT count(*) FROM photo_shot_revisions").fetchone()[0] == 0
    assert file_hashes(data) == files
    backups = list((data / "migration-backups").glob(f"before-v4-from-v{version}-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert table_snapshot(conn) == before
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    upgraded.state.factory.kw["bind"].dispose()
    create_app(data, start_worker=False).state.factory.kw["bind"].dispose()
    assert len(list((data / "migration-backups").glob("*.db"))) == 1
    assert file_hashes(data) == files
    # Restore to another disposable directory; never run old code on upgraded data.
    restored = tmp_path / "restored"
    shutil.copytree(full_backup, restored)
    with sqlite3.connect(restored / "qc.db") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == version
        assert table_snapshot(conn) == before
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert file_hashes(restored) == files


def test_migration_failure_rolls_back_final_stamp_and_retries_M03(tmp_path):
    legacy_fixture(tmp_path, 3)
    database = tmp_path / "qc.db"
    with sqlite3.connect(database) as conn:
        before = table_snapshot(conn)
    engine = create_engine(f"sqlite:///{database}")

    def fail_stamp(conn, cursor, statement, parameters, context, executemany):
        if statement == "PRAGMA user_version=4":
            raise RuntimeError("injected before final stamp")

    event.listen(engine, "before_cursor_execute", fail_stamp)
    with pytest.raises(RuntimeError, match="injected"):
        migrate(engine, tmp_path)
    with sqlite3.connect(database) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        assert table_snapshot(conn) == before
    backups = list((tmp_path / "migration-backups").glob("*.db"))
    assert len(backups) == 1
    event.remove(engine, "before_cursor_execute", fail_stamp)
    migrate(engine, tmp_path)
    assert len(list((tmp_path / "migration-backups").glob("*.db"))) == 2  # never reuse an unrelated backup
    engine.dispose()


@pytest.mark.parametrize("version", [0, 5])
def test_fail_closed_unknown_populated_or_future_schema_M04(tmp_path, version):
    database = tmp_path / "qc.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE sentinel(value TEXT)")
        conn.execute("INSERT INTO sentinel VALUES ('unchanged')")
        conn.execute(f"PRAGMA user_version={version}")
    original = database.read_bytes()
    engine = create_engine(f"sqlite:///{database}")
    with pytest.raises(RuntimeError, match="Unsupported|Unversioned"):
        migrate(engine, tmp_path)
    engine.dispose()
    assert database.read_bytes() == original
    assert not (tmp_path / "migration-backups").exists()


@pytest.mark.parametrize(
    "mode, allowed, verified, expected",
    [
        ("none", [], False, "not_applicable"),
        ("first", [], False, "applicable"),
        ("all", [], False, "applicable"),
        ("all", ["front"], False, "unknown"),
        ("all", ["front"], True, "applicable"),
        ("all", ["rear"], True, "not_applicable"),
    ],
)
def test_banner_applicability_and_unconfigured_checks_Q05(client, app, mode, allowed, verified, expected):
    dealer = client.get("/api/config").json()["dealerships"][0]
    client.put(
        f"/api/dealerships/{dealer['id']}",
        json={
            "name": dealer["name"],
            "used_rules": {"banner_application": mode, "banner_top_pct": 10, "banner_shot_types": allowed},
        },
    )
    sid = batch(client, 2, mode="dealership", dealership_id=dealer["id"], shot_types=["front", "rear"])
    analyze(app, sid)
    if verified:
        for p in detail(client, sid)["photos"]:
            assert shot(client, p, True).status_code == 200
        client.post(f"/api/shoots/{sid}/reanalyze")
        analyze(app, sid)
    d = detail(client, sid)
    banner = [c for c in d["qc_evidence"]["checks"] if c["check_id"] == "banner_clearance"]
    assert banner[0]["applicability"] == expected
    if mode == "first":
        assert banner[1]["applicability"] == "not_applicable"
    required = next(c for c in d["qc_evidence"]["checks"] if c["check_id"] == "required_shots")
    assert required["reason_code"] == "not_configured" and required["outcome"] == "unknown"


def test_failed_technical_execution_has_no_passing_evidence(client, app, monkeypatch):
    import qc.analysis as analysis

    sid = batch(client, 1)
    monkeypatch.setattr(analysis, "technical_metrics", lambda *a: (_ for _ in ()).throw(OSError("fixture")))
    analyze(app, sid)
    d = detail(client, sid)
    assert d["status"] == "failed" and d["score"] is None
    run = d["runs"][0]
    assert run["evidence_schema_version"] == 1 and run["status"] == "failed"
    assert any(c["execution"] == "error" for c in run["check_results"])
    assert all(c["outcome"] == "unknown" for c in run["check_results"])


def test_migration_refuses_version_change_during_backup(tmp_path, monkeypatch):
    import qc.migrations as migrations

    legacy_fixture(tmp_path, 3)
    original_backup = migrations.backup_database

    def changed_version(data, version):
        target = original_backup(data, version)
        with sqlite3.connect(data / "qc.db") as conn:
            conn.execute("PRAGMA user_version=5")
        return target

    monkeypatch.setattr(migrations, "backup_database", changed_version)
    engine = create_engine(f"sqlite:///{tmp_path / 'qc.db'}")
    with pytest.raises(RuntimeError, match="version changed"):
        migrate(engine, tmp_path)
    with sqlite3.connect(tmp_path / "qc.db") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
        assert "shot_evidence" not in {r[1] for r in conn.execute("PRAGMA table_info(photos)")}
    engine.dispose()


def test_schema3_upgrade_preserves_training_trash_and_revoked_approval(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as c:
        sid = batch(c, 1, purpose="training")
        analyze(app, sid)
        p = detail(c, sid)["photos"][0]
        save(c, p, verify_fields=["shot_type"])
        c.post(f"/api/photos/{p['id']}/trash", json={"scope": "training"})
        trash = c.get("/api/trash").json()
    app.state.factory.kw["bind"].dispose()
    with sqlite3.connect(tmp_path / "qc.db") as conn:
        strip_v4(conn)
        conn.execute("PRAGMA user_version=3")
        before = table_snapshot(conn)
    with TestClient(create_app(tmp_path, start_worker=False)) as c:
        assert c.get("/api/trash").json() == trash
        assert detail(c, sid)["photos"][0]["training"] is None
        with sqlite3.connect(tmp_path / "qc.db") as conn:
            for table, (columns, rows) in before.items():
                assert (
                    conn.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY rowid").fetchall() == rows
                )
        c.post(f"/api/trash/photo/{p['id']}/restore", json={"scope": "training"})
        restored = detail(c, sid)["photos"][0]["training"]
        assert not restored["eligible"] and not restored["exportable"]
        assert restored["label_evidence"]["shot_type"]["state"] == "legacy_unverified"
