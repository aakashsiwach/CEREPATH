import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from contextlib import contextmanager
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app import main


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class ScopedDatabase:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=(), **_kwargs):
        normalized = " ".join(query.split()).lower()
        self.calls.append((normalized, params))
        if normalized.startswith("select 1 from memories"):
            return Cursor()
        return Cursor(rows=[])


def install_owner(monkeypatch, owner_id):
    database = ScopedDatabase()

    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(main, "connection", fake_connection)
    main.app.dependency_overrides[main.require_owner] = lambda: owner_id
    return database


def test_memory_and_approval_reads_are_scoped_to_current_user(monkeypatch):
    owner_id = uuid4()
    database = install_owner(monkeypatch, owner_id)
    client = TestClient(main.app)

    assert client.get("/api/memories").status_code == 200
    assert client.get("/api/approvals").status_code == 200

    try:
        scoped_reads = [
            (query, params) for query, params in database.calls
            if query.startswith("select id, category") or query.startswith("select id, action_type")
        ]
        assert len(scoped_reads) == 2
        for query, params in scoped_reads:
            assert "where user_id = %s" in query
            assert params == (owner_id,)
    finally:
        main.app.dependency_overrides.clear()


def test_cannot_create_approval_for_another_users_memory(monkeypatch):
    owner_id = uuid4()
    foreign_memory_id = uuid4()
    database = install_owner(monkeypatch, owner_id)
    client = TestClient(main.app)

    response = client.post(
        "/api/approvals",
        json={
            "action_type": "memory.update",
            "target_id": str(foreign_memory_id),
            "payload": {"content": "attempted cross-user update"},
            "reason": "Test that foreign memory cannot be targeted.",
        },
    )

    try:
        assert response.status_code == 404
        query, params = database.calls[0]
        assert "where id = %s and user_id = %s" in query
        assert params == (foreign_memory_id, owner_id)
    finally:
        main.app.dependency_overrides.clear()
