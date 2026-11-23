import json
import os
from contextlib import contextmanager

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from fastapi.testclient import TestClient

from app import main


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeDatabase:
    def __init__(self):
        self.approvals = {}
        self.memories = {}
        self.audit_events = []

    def execute(self, query, params=(), **_kwargs):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("insert into approvals"):
            approval_id, user_id, action_type, target_id, payload, reason = params
            self.approvals[str(approval_id)] = {
                "id": approval_id,
                "user_id": user_id,
                "action_type": action_type,
                "target_id": target_id,
                "payload": json.loads(payload),
                "reason": reason,
                "status": "pending",
            }
        elif normalized.startswith("select 1 from memories"):
            memory_id, user_id = params
            row = self.memories.get(str(memory_id))
            return FakeCursor({"exists": 1} if row and row["user_id"] == user_id else None)
        elif normalized.startswith("select id, action_type, target_id, payload, reason, status from approvals"):
            approval = self.approvals.get(str(params[0]))
            if approval and approval["user_id"] == params[1]:
                return FakeCursor(approval)
            return FakeCursor()
        elif normalized.startswith("insert into memories"):
            memory_id, user_id, category, title, content, source, confidence, metadata = params
            self.memories[str(memory_id)] = {
                "id": memory_id,
                "user_id": user_id,
                "category": category,
                "title": title,
                "content": content,
                "source": source,
                "confidence": confidence,
                "metadata": json.loads(metadata),
            }
        elif normalized.startswith("update approvals set status='approved'"):
            self.approvals[str(params[0])]["status"] = "approved"
        elif normalized.startswith("insert into audit_events"):
            self.audit_events.append((query, params))
        return FakeCursor()


def test_health_is_public_but_owner_api_requires_authentication():
    client = TestClient(main.app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_memory_add_is_pending_until_exact_owner_approval(monkeypatch):
    database = FakeDatabase()

    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(main, "connection", fake_connection)
    client = TestClient(main.app)
    headers = {"Authorization": "Bearer test-owner-token-that-is-long-enough"}

    proposed = client.post(
        "/api/approvals",
        headers=headers,
        json={
            "action_type": "memory.add",
            "payload": {"title": "Preferred stack", "content": "Python and PostgreSQL", "category": "preference"},
            "reason": "Owner asked to remember this preference.",
        },
    )
    assert proposed.status_code == 201
    approval_id = proposed.json()["id"]
    assert database.approvals[approval_id]["status"] == "pending"
    assert database.memories == {}

    approved = client.post(
        f"/api/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["changed_memory"] is True
    assert len(database.memories) == 1
    assert database.approvals[approval_id]["status"] == "approved"

    replay = client.post(
        f"/api/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "approve"},
    )
    assert replay.status_code == 409
    assert len(database.memories) == 1
