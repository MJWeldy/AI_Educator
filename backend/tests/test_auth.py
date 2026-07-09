import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import get_db
from app.main import app


@pytest.fixture()
def client(seeded_db):
    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def server_client(seeded_db, monkeypatch):
    """A TestClient with server (auth-required) mode enabled."""
    monkeypatch.setattr(settings, "require_auth", True)

    def override_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_me_reports_auth_required_when_logged_out(server_client):
    me = server_client.get("/api/auth/me").json()
    assert me["require_auth"] is True and me["user"] is None


def test_protected_endpoint_401_without_login(server_client):
    assert server_client.get("/api/tasks/today").status_code == 401
    assert server_client.get("/api/courses").status_code == 401


def test_register_login_logout_flow(server_client):
    reg = server_client.post("/api/auth/register", json={"username": "Alice", "password": "hunter2"})
    assert reg.status_code == 200 and reg.json()["username"] == "Alice"

    # Session cookie now authenticates protected routes.
    assert server_client.get("/api/auth/me").json()["user"]["username"] == "Alice"
    assert server_client.get("/api/tasks/today").status_code == 200

    server_client.post("/api/auth/logout")
    assert server_client.get("/api/auth/me").json()["user"] is None
    assert server_client.get("/api/tasks/today").status_code == 401

    # Log back in (case-insensitive username).
    assert server_client.post("/api/auth/login", json={"username": "alice", "password": "hunter2"}).status_code == 200
    assert server_client.get("/api/auth/me").json()["user"]["username"] == "Alice"


def test_login_rejects_bad_credentials(server_client):
    server_client.post("/api/auth/register", json={"username": "Bob", "password": "secret1"})
    server_client.post("/api/auth/logout")
    assert server_client.post("/api/auth/login", json={"username": "Bob", "password": "wrong"}).status_code == 401
    assert server_client.post("/api/auth/login", json={"username": "nobody", "password": "secret1"}).status_code == 401


def test_register_rejects_duplicate_and_short_password(server_client):
    server_client.post("/api/auth/register", json={"username": "Carol", "password": "longenough"})
    assert server_client.post("/api/auth/register", json={"username": "carol", "password": "another1"}).status_code == 409
    assert server_client.post("/api/auth/register", json={"username": "Dave", "password": "x"}).status_code == 400


def test_profile_switching_disabled_in_server_mode(server_client):
    server_client.post("/api/auth/register", json={"username": "Erin", "password": "password1"})
    assert server_client.post("/api/profiles", json={"name": "sock puppet"}).status_code == 403
    assert server_client.post("/api/profiles/1/select").status_code == 403
    # The profile list shows only yourself.
    profiles = server_client.get("/api/profiles").json()["profiles"]
    assert len(profiles) == 1 and profiles[0]["name"] == "Erin"


def test_accounts_are_isolated(server_client):
    server_client.post("/api/auth/register", json={"username": "Frank", "password": "password1"})
    slug = server_client.get("/api/courses").json()[0]["slug"]
    server_client.put(f"/api/courses/{slug}/enroll")
    assert next(c for c in server_client.get("/api/courses").json() if c["slug"] == slug)["enrolled"]

    # A second account starts clean — no enrollment leakage.
    server_client.post("/api/auth/logout")
    server_client.post("/api/auth/register", json={"username": "Grace", "password": "password1"})
    assert not next(c for c in server_client.get("/api/courses").json() if c["slug"] == slug)["enrolled"]


def test_auth_endpoints_noop_in_local_mode(client):
    # Without server mode, register/login are disabled and me() reports it.
    assert client.get("/api/auth/me").json() == {"require_auth": False, "user": None}
    assert client.post("/api/auth/register", json={"username": "x", "password": "yyyyyy"}).status_code == 409
