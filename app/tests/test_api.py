"""API-level tests. Mock-provider only, and labelled as such.

Run: python3 -m pytest app/tests/test_api.py -q
Requires httpx (installed with fastapi's TestClient).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.server.main import app

EXAMPLE = Path(__file__).resolve().parents[1] / "web" / "examples"
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True


def test_providers_never_expose_tokens(client):
    text = client.get("/api/providers").text
    assert "hf_token" not in text or "hf_token_present" in text
    assert "Bearer" not in text


def test_rejects_non_image(client):
    r = client.post("/api/jobs", files={"image": ("x.txt", b"not an image", "text/plain")})
    assert r.status_code == 415


def test_rejects_oversize(client, monkeypatch):
    from app.server import main as main_mod

    monkeypatch.setattr(main_mod.settings, "max_upload_bytes", 10)
    r = client.post("/api/jobs", files={"image": ("x.png", PNG_1PX, "image/png")})
    assert r.status_code == 413


def test_mock_job_end_to_end(client):
    """SIMULATION TEST — proves upload/queue/poll/download plumbing, not inference."""
    r = client.post(
        "/api/jobs",
        files={"image": ("fox.jpg", (EXAMPLE / "fox.jpg").read_bytes(), "image/jpeg")},
        data={"provider": "mock", "seed": "1", "steps": "30"},
    )
    assert r.status_code == 202
    job_id = r.json()["id"]

    import time

    for _ in range(60):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.15)

    assert job["status"] == "succeeded", job
    assert job["simulated"] is True, "mock jobs must be marked simulated"
    assert "SIMULATED" in job["message"] or job["simulated"]

    glb = client.get(f"/api/jobs/{job_id}/download/glb")
    assert glb.status_code == 200
    assert glb.content[:4] == b"glTF"
    assert "SIMULATED" in glb.headers["content-disposition"]

    assert client.get(f"/api/jobs/{job_id}/download/obj").status_code == 200
    assert client.delete(f"/api/jobs/{job_id}").json()["deleted"] is True
    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_unconfigured_real_provider_fails_honestly(client):
    """A real provider with no credentials must fail with error_kind=provider_unavailable,
    never silently return a fake mesh."""
    r = client.post(
        "/api/jobs",
        files={"image": ("fox.jpg", (EXAMPLE / "fox.jpg").read_bytes(), "image/jpeg")},
        data={"provider": "replicate"},
    )
    assert r.status_code == 202
    job_id = r.json()["id"]

    import time

    for _ in range(60):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.15)

    assert job["status"] == "failed"
    assert job["error_kind"] == "provider_unavailable"
    assert job["files"] == {}
    assert job["simulated"] is False
