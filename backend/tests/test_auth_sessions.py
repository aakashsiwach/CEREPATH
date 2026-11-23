import hashlib
import os
from uuid import UUID
from contextlib import contextmanager

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from fastapi.testclient import TestClient

from app import main, security
from app.config import OWNER_USER_ID


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Cursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class SessionDatabase:
    def __init__(self):
        self.sessions = {}
        self.owner = {
            "id": UUID(OWNER_USER_ID),
            "email": "owner@local.invalid",
            "display_name": "Local Owner",
            "is_active": True,
        }

    def execute(self, query, params=(), **_kwargs):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("select id, email, display_name from users"):
            return Cursor(self.owner if params[0] == UUID(OWNER_USER_ID) else None)
        if normalized.startswith("insert into sessions"):
            session_id, user_id, token_hash, csrf_hash, ttl = params
            self.sessions[token_hash] = {
                "id": session_id,
                "user_id": UUID(str(user_id)),
                "csrf_token_hash": csrf_hash,
                "revoked_at": None,
                "ttl": ttl,
            }
        elif normalized.startswith("select s.user_id, s.csrf_token_hash, u.is_active"):
            session = self.sessions.get(params[0])
            if session and not session["revoked_at"]:
                return Cursor({
                    "user_id": session["user_id"],
                    "csrf_token_hash": session["csrf_token_hash"],
                    "is_active": True,
                })
            return Cursor()
        elif normalized.startswith("update sessions set revoked_at"):
            session = self.sessions.get(params[0])
            if session and session["user_id"] == params[1]:
                session["revoked_at"] = True
        return Cursor()


def install_db(monkeypatch):
    database = SessionDatabase()

    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(main, "connection", fake_connection)
    monkeypatch.setattr(security, "connection", fake_connection)
    monkeypatch.setattr(main, "APP_ENV", "local")
    monkeypatch.setattr(security, "APP_ENV", "local")
    return database


def test_login_creates_http_only_session_and_csrf_protection(monkeypatch):
    database = install_db(monkeypatch)
    client = TestClient(main.app)

    response = client.post(
        "/api/auth/login",
        json={"owner_token": "test-owner-token-that-is-long-enough"},
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["id"] == OWNER_USER_ID
    csrf = response.json()["csrf_token"]
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api" in cookie
    assert len(database.sessions) == 1
    assert list(database.sessions) == [digest(client.cookies.get("cerepath_session"))]

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["user"]["email"] == "owner@local.invalid"

    rejected = client.post("/api/auth/logout")
    assert rejected.status_code == 403

    logged_out = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logged_out.status_code == 200
    assert logged_out.json()["revoked"] is True
    assert client.get("/api/auth/session").status_code == 401


def test_local_bootstrap_login_is_disabled_outside_local_environment(monkeypatch):
    install_db(monkeypatch)
    monkeypatch.setattr(main, "APP_ENV", "production")
    response = TestClient(main.app).post(
        "/api/auth/login",
        json={"owner_token": "test-owner-token-that-is-long-enough"},
    )
    assert response.status_code == 404


def test_direct_bearer_compatibility_is_rejected_outside_local(monkeypatch):
    monkeypatch.setattr(security, "APP_ENV", "production")
    response = TestClient(main.app).get(
        "/api/auth/session",
        headers={"Authorization": "Bearer test-owner-token-that-is-long-enough"},
    )
    assert response.status_code == 401
