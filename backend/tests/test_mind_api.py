import os
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from fastapi.testclient import TestClient

from app import main
from app.intelligence import mind as mind_module


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class MindDatabase:
    def __init__(self):
        self.knowledge = {}
        self.experiences = []

    def execute(self, query, params=(), **_kwargs):
        normalized = " ".join(query.split()).lower()
        now = datetime.now(timezone.utc)

        if normalized.startswith("insert into semantic_knowledge"):
            (
                knowledge_id, user_id, knowledge_type, title, content,
                source_ref, digest, confidence, embedding,
            ) = params
            existing = next(
                (item for item in self.knowledge.values()
                 if item["user_id"] == user_id and item["content_sha256"] == digest),
                None,
            )
            if existing:
                existing["title"] = title
                existing["knowledge_type"] = knowledge_type
                existing["source_ref"] = source_ref or existing["source_ref"]
                existing["confidence"] = max(existing["confidence"], float(confidence))
                existing["embedding"] = embedding or existing.get("embedding")
                existing["reinforcement_count"] += 1
                existing["updated_at"] = now
                row = existing
            else:
                row = {
                    "id": knowledge_id,
                    "user_id": user_id,
                    "knowledge_type": knowledge_type,
                    "title": title,
                    "content": content,
                    "source_type": "owner_taught",
                    "source_ref": source_ref,
                    "content_sha256": digest,
                    "confidence": float(confidence),
                    "embedding": embedding,
                    "reinforcement_count": 1,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                }
                self.knowledge[str(knowledge_id)] = row
            return Cursor(row=row)

        if normalized.startswith("insert into cognitive_experiences"):
            experience_id, user_id, knowledge_id, details = params
            event_type = "lesson_encoded" if "'lesson_encoded'" in normalized else "feedback"
            source_type = "owner_taught" if event_type == "lesson_encoded" else "owner_feedback"
            self.experiences.append({
                "id": experience_id,
                "user_id": user_id,
                "event_type": event_type,
                "knowledge_id": knowledge_id,
                "source_type": source_type,
                "details": details,
            })
            return Cursor()

        if normalized.startswith("select id, knowledge_type, title, content, source_type") and "and search_vector @@" not in normalized:
            user_id, limit = params
            rows = [
                {key: value for key, value in item.items()
                 if key in {
                     "id", "knowledge_type", "title", "content", "source_type",
                     "source_ref", "confidence", "reinforcement_count", "status",
                     "created_at", "updated_at",
                 }}
                for item in self.knowledge.values()
                if item["user_id"] == user_id and item["status"] in {"active", "needs_review"}
            ]
            rows.sort(key=lambda item: item["updated_at"], reverse=True)
            return Cursor(rows=rows[:limit])

        if normalized.startswith("select id, knowledge_type, title, content, source_type") and "and search_vector @@" in normalized:
            query, user_id, _query_again = params
            terms = set(query.lower().split())
            rows = []
            for item in self.knowledge.values():
                if item["user_id"] != user_id or item["status"] != "active":
                    continue
                text = f"{item['title']} {item['content']}".lower()
                if any(term in text for term in terms):
                    rows.append({**item, "retrieval_score": 0.8})
            return Cursor(rows=rows)

        if normalized.startswith("select id from semantic_knowledge"):
            knowledge_id, user_id = params
            item = self.knowledge.get(str(knowledge_id))
            valid = item and item["user_id"] == user_id and item["status"] in {"active", "needs_review"}
            return Cursor(row={"id": knowledge_id} if valid else None)

        if normalized.startswith("update semantic_knowledge set status = 'needs_review'"):
            knowledge_id, user_id = params
            item = self.knowledge.get(str(knowledge_id))
            if item and item["user_id"] == user_id:
                item["status"] = "needs_review"
                item["updated_at"] = now
            return Cursor()

        if normalized.startswith("select") and "as active_knowledge" in normalized:
            user_id, _u2, _u3, _u4 = params
            owned = [item for item in self.knowledge.values() if item["user_id"] == user_id]
            owner_experiences = [item for item in self.experiences if item["user_id"] == user_id]
            return Cursor(row={
                "active_knowledge": sum(item["status"] == "active" for item in owned),
                "needs_review": sum(item["status"] == "needs_review" for item in owned),
                "experiences": len(owner_experiences),
                "feedback_events": sum(item["event_type"] == "feedback" for item in owner_experiences),
            })

        return Cursor()


def _client(monkeypatch, database, user_id):
    @contextmanager
    def fake_connection():
        yield database

    monkeypatch.setattr(mind_module, "connection", fake_connection)
    main.app.dependency_overrides[mind_module.require_owner] = lambda: user_id
    return TestClient(main.app)


def test_owner_can_teach_and_recall_local_knowledge(monkeypatch):
    database = MindDatabase()
    owner_id = uuid4()
    client = _client(monkeypatch, database, owner_id)
    try:
        taught = client.post("/api/mind/teach", json={
            "knowledge_type": "concept",
            "title": "Java Collections",
            "content": "Java Collections include List, Set, Queue and Map.",
            "source_ref": "owner-notes/java.md",
            "confidence": 0.9,
        })
        assert taught.status_code == 201
        assert taught.json()["knowledge"]["status"] == "active"
        assert taught.json()["knowledge"]["source_type"] == "owner_taught"

        recalled = client.get("/api/mind/recall", params={"q": "Java Collections"})
        assert recalled.status_code == 200
        assert len(recalled.json()["items"]) == 1
        assert recalled.json()["items"][0]["title"] == "Java Collections"
        assert recalled.json()["evidence_state"] == "strong_retrieval_match"

        state = client.get("/api/mind/state")
        assert state.status_code == 200
        assert state.json()["active_knowledge"] == 1
        assert state.json()["consciousness_claim"] is False
    finally:
        main.app.dependency_overrides.clear()


def test_reteaching_same_content_reinforces_instead_of_duplicating(monkeypatch):
    database = MindDatabase()
    owner_id = uuid4()
    client = _client(monkeypatch, database, owner_id)
    payload = {
        "knowledge_type": "fact",
        "title": "PostgreSQL",
        "content": "PostgreSQL supports transactions.",
    }
    try:
        first = client.post("/api/mind/teach", json=payload)
        second = client.post("/api/mind/teach", json=payload)
        assert first.status_code == 201
        assert second.status_code == 201
        assert len(database.knowledge) == 1
        assert second.json()["knowledge"]["reinforcement_count"] == 2
    finally:
        main.app.dependency_overrides.clear()


def test_owner_feedback_quarantines_incorrect_knowledge(monkeypatch):
    database = MindDatabase()
    owner_id = uuid4()
    client = _client(monkeypatch, database, owner_id)
    try:
        taught = client.post("/api/mind/teach", json={
            "knowledge_type": "fact",
            "title": "Python",
            "content": "Python is a programming language.",
        })
        knowledge_id = taught.json()["knowledge"]["id"]
        response = client.post("/api/mind/feedback", json={
            "knowledge_id": knowledge_id,
            "outcome": "incorrect",
            "expected_reward": 0.8,
            "note": "Owner correction required.",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "needs_review"

        recalled = client.get("/api/mind/recall", params={"q": "Python"})
        assert recalled.json()["items"] == []
        state = client.get("/api/mind/state")
        assert state.json()["needs_review"] == 1
        assert state.json()["feedback_events"] == 1
    finally:
        main.app.dependency_overrides.clear()
