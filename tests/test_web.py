from pathlib import Path

import pytest

from uz801_manager.demo import DemoADB
from uz801_manager.web import create_app

BASE = "http://127.0.0.1:8765"


@pytest.fixture
def web(tmp_path):
    app = create_app(directory=tmp_path / "state", adb=DemoADB(delay=0), demo=True, token="test-session")
    client = app.test_client()
    headers = {"X-UZ801-Token": "test-session", "Origin": BASE}
    yield app, client, headers
    app.extensions["uz801"]["jobs"].shutdown()


def post(web, path, value):
    app, client, headers = web
    response = client.post(path, json=value, base_url=BASE, headers=headers)
    thread = app.extensions["uz801"]["jobs"].thread
    if thread:
        thread.join(10)
    return response


def test_initial_render_no_device_read(web):
    app, client, headers = web
    assert client.get("/", base_url=BASE).status_code == 200
    state = client.get("/api/state", headers=headers, base_url=BASE).get_json()
    assert state["device"] is None
    assert state["jobs"] == []
    assert state["readiness"]["flash_enabled"] is False


@pytest.mark.parametrize("headers", [{}, {"X-UZ801-Token": "wrong"}, {"X-UZ801-Token": "test-session", "Origin": "http://evil.example"}, {"X-UZ801-Token": "test-session", "Sec-Fetch-Site": "cross-site"}])
def test_no_cross_origin_or_unauthenticated_read(web, headers):
    _, client, _ = web
    assert client.get("/api/state", base_url=BASE, headers=headers).status_code == 403


@pytest.mark.parametrize("origin", [None, "http://evil.example", "http://localhost:8765"])
def test_csrf(web, origin):
    _, client, _ = web
    headers = {"X-UZ801-Token": "test-session"}
    if origin:
        headers["Origin"] = origin
    assert client.post("/api/inspect", json={"consent": True}, base_url=BASE, headers=headers).status_code == 403


def test_dns_rebinding_host(web):
    _, client, headers = web
    assert client.get("/api/state", base_url="http://evil.example:8765", headers=headers).status_code == 403


def test_consent_required(web):
    response = post(web, "/api/inspect", {"consent": False})
    assert response.status_code == 400
    assert response.get_json()["code"] == "CONSENT_REQUIRED"


@pytest.mark.parametrize("approval", [None, False, 1, "true"])
def test_large_backup_needs_separate_explicit_consent(web, tmp_path, approval):
    post(web, "/api/inspect", {"consent": True})
    response = post(web, "/api/backup", {"consent": True, "backup_approved": approval,
                                         "mode": "full", "folder": str(tmp_path)})
    assert response.status_code == 400
    assert response.get_json()["code"] == "BACKUP_CONSENT_REQUIRED"
    assert not list(tmp_path.glob("backup-*"))


def test_inspect_backup_verify_http_workflow(web, tmp_path):
    app, client, headers = web
    assert post(web, "/api/inspect", {"consent": True}).status_code == 202
    assert post(web, "/api/backup", {"consent": True, "backup_approved": True, "mode": "full", "folder": str(tmp_path)}).status_code == 202
    state = client.get("/api/state", base_url=BASE, headers=headers).get_json()
    job = state["jobs"][0]
    assert job["status"] == "complete", job
    folder = job["detail"]["folder"]
    assert post(web, "/api/verify", {"folder": folder}).status_code == 202
    assert app.extensions["uz801"]["jobs"].history()[0]["detail"]["verification"]["sha256"] == "PASS"
    assert "fingerprint" not in str(state)
    assert "serial" not in str(state["device"])


@pytest.mark.parametrize("path", ["/api/flash", "/api/erase", "/api/restore", "/api/reboot", "/api/command"])
def test_no_write_routes(web, path):
    assert post(web, path, {"consent": True}).status_code == 404


def test_no_shell_filename_paths(web):
    assert post(web, "/api/verify", {"folder": "../secrets"}).status_code == 400
    assert post(web, "/api/verify", {"folder": []}).status_code == 400


def test_security_headers(web):
    _, client, _ = web
    response = client.get("/", base_url=BASE)
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"
