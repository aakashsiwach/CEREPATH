import os
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from fastapi.testclient import TestClient

from app import main
from app.intelligence import chat as chat_module


def test_memory_context_uses_relevant_approved_records_only():
    rows = [
        {"category": "work", "title": "Banking project", "content": "Implemented card payment processing."},
        {"category": "personal", "title": "Coffee", "content": "Likes espresso."},
        {"category": "skills", "title": "Java", "content": "Uses Spring Boot and RabbitMQ."},
    ]
    selected = chat_module._select_memories(rows, "payment processing")
    assert [item["title"] for item in selected] == ["Banking project"]


def test_memory_context_is_marked_as_reference_data():
    messages = chat_module._system_messages([
        {"category": "work", "title": "Profile", "content": "Backend engineer"}
    ])
    assert messages[0]["role"] == "system"
    assert "private personal AI assistant" in messages[0]["content"]
    assert "untrusted reference data" in messages[1]["content"]
    assert "Backend engineer" in messages[1]["content"]


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class ChatDatabase:
    def __init__(self):
        self.conversations = {}
        self.messages = []
        self.memories = [{
            "category": "work",
            "title": "Banking project",
            "content": "Worked on card payment processing.",
        }]

    def execute(self, query, params=(), **_kwargs):
        normalized = " ".join(query.split()).lower()

        if normalized.startswith("select id from chat_conversations where id"):
            row = self.conversations.get(str(params[0]))
            return Cursor(row if row and row["user_id"] == params[1] else None)

        if normalized.startswith("insert into chat_conversations"):
            conversation_id, user_id, title = params
            row = {
                "id": conversation_id,
                "user_id": user_id,
                "title": title,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self.conversations[str(conversation_id)] = row
            return Cursor()

        if normalized.startswith("insert into chat_messages"):
            if "'user'" in normalized:
                message_id, conversation_id, user_id, content = params
                self.messages.append({
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": content,
                    "provider": None,
                    "model": None,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc),
                })
            else:
                message_id, conversation_id, user_id, content, provider, model = params
                self.messages.append({
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": content,
                    "provider": provider,
                    "model": model,
                    "status": "complete",
                    "created_at": datetime.now(timezone.utc),
                })
            return Cursor()

        if normalized.startswith("select role, content from ("):
            conversation_id, user_id, limit = params
            rows = [
                {"role": row["role"], "content": row["content"], "created_at": row["created_at"], "id": row["id"]}
                for row in self.messages
                if row["conversation_id"] == conversation_id
                and row["user_id"] == user_id
                and row["status"] in {"pending", "complete"}
            ][-limit:]
            return Cursor(rows=rows)

        if normalized.startswith("select category, title, content from memories"):
            user_id, = params
            return Cursor(rows=self.memories)

        if normalized.startswith("update chat_messages set status = 'complete'"):
            message_id, user_id = params
            for row in self.messages:
                if row["id"] == message_id and row["user_id"] == user_id:
                    row["status"] = "complete"
            return Cursor()

        if normalized.startswith("update chat_conversations set updated_at"):
            return Cursor()

        if normalized.startswith("select id, title, created_at, updated_at from chat_conversations"):
            user_id, = params
            rows = [row for row in self.conversations.values() if row["user_id"] == user_id]
            return Cursor(rows=rows)

        if normalized.startswith("select id from chat_conversations where id ="):
            conversation_id, user_id = params
            row = self.conversations.get(str(conversation_id))
            return Cursor(row if row and row["user_id"] == user_id else None)

        if normalized.startswith("select id, role, content, provider, model, status, created_at from chat_messages"):
            conversation_id, user_id = params
            rows = [
                {key: row[key] for key in ("id", "role", "content", "provider", "model", "status", "created_at")}
                for row in self.messages
                if row["conversation_id"] == conversation_id and row["user_id"] == user_id
            ]
            return Cursor(rows=rows)

        return Cursor()


class FakeProvider:
    name = "bynara"
    model = "gpt-5.6-luna"

    async def complete(self, messages):
        assert any("Banking project" in item["content"] for item in messages)
        assert messages[-1] == {"role": "user", "content": "Help with payment processing"}
        return type("Reply", (), {
            "text": "Here is the answer.",
            "provider": self.name,
            "model": self.model,
        })()


def test_chat_persists_messages_and_scopes_conversation_history(monkeypatch):
    database = ChatDatabase()
    owner_id = uuid4()

    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(chat_module, "connection", fake_connection)
    monkeypatch.setattr(chat_module, "build_model_provider", lambda: FakeProvider())
    main.app.dependency_overrides[chat_module.require_owner] = lambda: owner_id
    client = TestClient(main.app)

    try:
        response = client.post("/api/chat", json={"message": "Help with payment processing"})
        assert response.status_code == 200
        result = response.json()
        conversation_id = result["conversation_id"]
        assert result["persisted"] is True
        assert result["memory_context_items"] == 1
        assert result["assistant_message"]["content"] == "Here is the answer."
        assert result["assistant_message"]["provider"] == "bynara"
        assert len(database.messages) == 2
        assert [item["status"] for item in database.messages] == ["complete", "complete"]

        history = client.get(f"/api/conversations/{conversation_id}/messages")
        assert history.status_code == 200
        assert [item["role"] for item in history.json()["items"]] == ["user", "assistant"]
        assert history.json()["items"][1]["content"] == "Here is the answer."

        conversation_list = client.get("/api/conversations")
        assert conversation_list.status_code == 200
        assert conversation_list.json()["items"][0]["id"] == conversation_id
    finally:
        main.app.dependency_overrides.clear()


def test_chat_rejects_conversation_owned_by_another_user(monkeypatch):
    database = ChatDatabase()
    other_id = uuid4()
    owner_id = uuid4()
    foreign_conversation_id = uuid4()
    database.conversations[str(foreign_conversation_id)] = {
        "id": foreign_conversation_id,
        "user_id": other_id,
        "title": "Private conversation",
    }

    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(chat_module, "connection", fake_connection)
    monkeypatch.setattr(chat_module, "build_model_provider", lambda: FakeProvider())
    main.app.dependency_overrides[chat_module.require_owner] = lambda: owner_id
    client = TestClient(main.app)

    try:
        response = client.post(
            "/api/chat",
            json={"message": "Can I read this?", "conversation_id": str(foreign_conversation_id)},
        )
        assert response.status_code == 404
        assert database.messages == []
    finally:
        main.app.dependency_overrides.clear()
