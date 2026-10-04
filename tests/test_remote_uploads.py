import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from qc.main import create_app
from test_workflows import image_bytes


def test_staging_is_atomic_ordered_retryable_and_survives_restart(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as c:
        body = {
            "metadata": {
                "mode": "general",
                "shoot_date": "2026-10-04",
                "purpose": "training",
                "shot_types": ["rear", "front"],
            },
            "count": 2,
        }
        batch = c.post("/api/uploads", json=body).json()["id"]
        url = f"/api/uploads/{batch}"
        assert (
            c.put(url + "/photos/0", files={"file": ("rear.jpg", image_bytes(), "image/jpeg")}).status_code
            == 200
        )
        assert c.put(url + "/photos/1", files={"file": ("bad.jpg", b"bad", "image/jpeg")}).status_code == 422
        assert c.post(url + "/complete").status_code == 409
        assert c.get("/api/shoots?purpose=training").json()["total"] == 0
        assert not list((tmp_path / "originals").rglob("*.jpg"))
    restarted = create_app(tmp_path, start_worker=False)
    with TestClient(restarted) as c:
        assert c.get(url).json()["received"] == [0]
        assert (
            c.put(url + "/photos/0", files={"file": ("rear.jpg", image_bytes(), "image/jpeg")}).status_code
            == 200
        )
        assert (
            c.put(
                url + "/photos/1", files={"file": ("front.jpg", image_bytes((60, 70, 80)), "image/jpeg")}
            ).status_code
            == 200
        )
        result = c.post(url + "/complete")
        assert result.status_code == 201, result.text
        sid = result.json()["id"]
        assert c.post(url + "/complete").json()["id"] == sid
        assert c.get(url).json()["result"]["id"] == sid
        assert c.get("/api/shoots?purpose=training").json()["total"] == 1
        photos = c.get(f"/api/shoots/{sid}").json()["photos"]
        assert [p["shot_type"] for p in photos] == ["rear", "front"]
        assert all(p["training"]["eligible"] for p in photos)
        assert c.get(f"/api/photos/{photos[0]['id']}/original").content == image_bytes()
        assert c.delete(url).status_code == 409
        # Recover a DB commit whose acknowledgement was not saved before interruption.
        state_path = tmp_path / "upload-staging" / batch / "state.json"
        state = json.loads(state_path.read_text())
        state.pop("result")
        state_path.write_text(json.dumps(state))
        assert c.post(url + "/complete").json()["id"] == sid
        assert c.get("/api/shoots?purpose=training").json()["total"] == 1


def test_cancel_and_unknown_shot_defaults_do_not_change_existing_data(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as c:
        body = {
            "metadata": {
                "mode": "general",
                "purpose": "training",
                "shoot_date": "2026-10-04",
                "shot_types": ["unknown"],
            },
            "count": 1,
        }
        bid = c.post("/api/uploads", json=body).json()["id"]
        url = f"/api/uploads/{bid}"
        c.put(url + "/photos/0", files={"file": ("one.jpg", image_bytes(), "image/jpeg")})
        assert c.delete(url).status_code == 200
        assert not (tmp_path / "upload-staging" / bid).exists()
        assert c.get("/api/shoots?purpose=training").json()["total"] == 0
        bid = c.post("/api/uploads", json=body).json()["id"]
        url = f"/api/uploads/{bid}"
        c.put(url + "/photos/0", files={"file": ("one.jpg", image_bytes(), "image/jpeg")})
        sid = c.post(url + "/complete").json()["id"]
        p = c.get(f"/api/shoots/{sid}").json()["photos"][0]
        assert p["training"]["eligible"]
        assert c.post("/api/datasets").status_code == 422  # No classifier training on Unassigned.
        save = c.put(
            f"/api/photos/{p['id']}/training",
            json={"labels": {"shot_type": "front"}, "eligible": False, "revision": 0},
        )
        assert save.status_code == 200
    with TestClient(create_app(tmp_path, start_worker=False)) as c:
        assert not c.get(f"/api/shoots/{sid}").json()["photos"][0]["training"]["eligible"]


def test_remote_mode_verifies_signatures_claims_origins_and_upload_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("QC_PUBLIC_URL", "https://photos.example.com")
    monkeypatch.setenv("QC_ACCESS_TEAM_DOMAIN", "team.cloudflareaccess.com")
    monkeypatch.setenv("QC_ACCESS_AUD", "expected-audience")
    app = create_app(tmp_path, start_worker=False)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        app.state.security.keys,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=private.public_key()),
    )
    claims = {
        "sub": "user-one",
        "email": "one@example.com",
        "iss": "https://team.cloudflareaccess.com",
        "aud": "expected-audience",
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
    }

    def headers(**overrides):
        return {
            "Cf-Access-Jwt-Assertion": jwt.encode({**claims, **overrides}, private, algorithm="RS256"),
            "Origin": "https://photos.example.com",
        }

    with TestClient(app, base_url="https://photos.example.com") as c:
        for path in ["/", "/api/config", "/api/health", "/api/photos/missing/original"]:
            assert c.get(path).status_code == 401
        for patch in [{"aud": "other"}, {"iss": "https://evil.example.com"}, {"exp": int(time.time()) - 30}]:
            assert c.get("/api/config", headers=headers(**patch)).status_code == 401
        forged = jwt.encode(
            claims, rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm="RS256"
        )
        assert c.get("/api/config", headers={"Cf-Access-Jwt-Assertion": forged}).status_code == 401
        valid = headers()
        response = c.get("/api/config", headers=valid)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert c.get("/api/config", headers={**valid, "Host": "evil.example.com"}).status_code == 400
        assert (
            c.post(
                "/api/photographers",
                json={"name": "Blocked"},
                headers={**valid, "Origin": "https://evil.example.com"},
            ).status_code
            == 403
        )
        no_origin = {k: v for k, v in valid.items() if k != "Origin"}
        assert c.post("/api/photographers", json={"name": "Blocked"}, headers=no_origin).status_code == 403
        body = {"metadata": {"mode": "general", "shoot_date": "2026-10-04"}, "count": 1}
        bid = c.post("/api/uploads", json=body, headers=valid).json()["id"]
        assert (
            c.get(f"/api/uploads/{bid}", headers=headers(sub="user-two", email="two@example.com")).status_code
            == 404
        )
        assert (
            c.delete(
                f"/api/uploads/{bid}", headers=headers(sub="user-two", email="two@example.com")
            ).status_code
            == 404
        )
        assert c.get("http://localhost:8000/api/config").status_code == 401


def test_incomplete_remote_configuration_fails_closed_and_local_rejects_tunnel(tmp_path, monkeypatch):
    monkeypatch.setenv("QC_PUBLIC_URL", "https://photos.example.com")
    with pytest.raises(RuntimeError, match="requires"):
        create_app(tmp_path, start_worker=False)
    monkeypatch.delenv("QC_PUBLIC_URL")
    with TestClient(create_app(tmp_path, start_worker=False)) as c:
        assert c.get("/api/config", headers={"cf-ray": "tunnel-request"}).status_code == 403
        assert c.get("/api/config").status_code == 200
