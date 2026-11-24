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
        self.schedules = {}
        self.episodes = {}

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

        if normalized.startswith("insert into learning_schedules"):
            schedule_id, user_id, knowledge_id = params
            self.schedules[str(knowledge_id)] = {
                "id": schedule_id,
                "user_id": user_id,
                "knowledge_id": knowledge_id,
                "repetition_count": 0,
                "interval_days": 0,
                "ease_factor": 2.5,
                "lapse_count": 0,
                "mastery_score": 0.0,
            }
            return Cursor()

        if normalized.startswith("insert into episodic_memories"):
            (
                episode_id, user_id, conversation_id, user_message_id,
                assistant_message_id, content, digest, embedding,
            ) = params
            existing = next(
                (item for item in self.episodes.values()
                 if item["user_id"] == user_id and item["content_sha256"] == digest),
                None,
            )
            if existing:
                existing["conversation_id"] = conversation_id
                existing["user_message_id"] = user_message_id
                existing["assistant_message_id"] = assistant_message_id
                existing["reinforcement_count"] += 1
                existing["last_seen_at"] = now
                existing["embedding"] = embedding or existing.get("embedding")
                row = existing
            else:
                row = {
                    "id": episode_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "user_message_id": user_message_id,
                    "assistant_message_id": assistant_message_id,
                    "content": content,
                    "content_sha256": digest,
                    "embedding": embedding,
                    "importance_score": 0.5,
                    "reinforcement_count": 1,
                    "recall_count": 0,
                    "last_seen_at": now,
                    "last_recalled_at": None,
                    "created_at": now,
                }
                self.episodes[str(episode_id)] = row
            return Cursor(row={"id": row["id"]})

        if normalized.startswith("insert into cognitive_experiences"):
            event_type = next(
                (name for name in ("conversation_episode", "spaced_review", "lesson_encoded", "feedback", "recall")
                 if f"'{name}'" in normalized),
                "feedback",
            )
            if event_type in {"conversation_episode", "recall"}:
                experience_id, user_id, details = params
                knowledge_id = None
            else:
                experience_id, user_id, knowledge_id, details = params
            source_type = (
                "owner_taught" if event_type == "lesson_encoded"
                else "owner_feedback" if event_type == "feedback"
                else event_type
            )
            self.experiences.append({
                "id": experience_id,
                "user_id": user_id,
                "event_type": event_type,
                "knowledge_id": knowledge_id,
                "source_type": source_type,
                "details": details,
            })
            return Cursor()

        if normalized.startswith("select id, content, conversation_id") and "from episodic_memories" in normalized:
            query, user_id, _query_again = params
            terms = set(query.lower().split())
            rows = [
                {
                    **item,
                    "knowledge_type": "episodic_memory",
                    "source_type": "conversation",
                    "source_ref": str(item["conversation_id"]),
                    "source_title": "Previous conversation",
                    "confidence": 0.8,
                    "retrieval_score": 0.8,
                }
                for item in self.episodes.values()
                if item["user_id"] == user_id
                and any(term in item["content"].lower() for term in terms)
            ]
            return Cursor(rows=rows)

        if normalized.startswith("update episodic_memories"):
            user_id, episode_ids = params
            for episode_id in episode_ids:
                item = self.episodes.get(str(episode_id))
                if item and item["user_id"] == user_id:
                    item["recall_count"] += 1
                    item["last_recalled_at"] = now
            return Cursor()

        if normalized.startswith("select id, conversation_id, content"):
            user_id, limit = params
            rows = [
                {key: value for key, value in item.items()
                 if key in {"id", "conversation_id", "content", "importance_score",
                            "reinforcement_count", "recall_count", "last_seen_at",
                            "last_recalled_at", "created_at"}}
                for item in self.episodes.values() if item["user_id"] == user_id
            ]
            rows.sort(key=lambda item: item["last_seen_at"], reverse=True)
            return Cursor(rows=rows[:limit])

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

        if normalized.startswith("select k.id as knowledge_id"):
            user_id, limit = params
            rows = []
            for schedule in self.schedules.values():
                knowledge = self.knowledge.get(str(schedule["knowledge_id"]))
                if knowledge and schedule["user_id"] == user_id and knowledge["status"] == "active":
                    rows.append({
                        "knowledge_id": knowledge["id"],
                        "knowledge_type": knowledge["knowledge_type"],
                        "title": knowledge["title"],
                        "content": knowledge["content"],
                        **schedule,
                        "due_at": now,
                        "last_grade": None,
                    })
            return Cursor(rows=rows[:limit])

        if normalized.startswith("select k.id, s.repetition_count"):
            knowledge_id, user_id = params
            schedule = self.schedules.get(str(knowledge_id))
            knowledge = self.knowledge.get(str(knowledge_id))
            if not schedule or not knowledge or schedule["user_id"] != user_id or knowledge["status"] != "active":
                return Cursor()
            return Cursor(row={
                "id": knowledge_id,
                **schedule,
            })

        if normalized.startswith("update learning_schedules"):
            repetition_count, interval_days, ease_factor, lapse_count, grade, due_at, mastery_score, user_id, knowledge_id = params
            schedule = self.schedules.get(str(knowledge_id))
            if schedule and schedule["user_id"] == user_id:
                schedule.update({
                    "repetition_count": repetition_count,
                    "interval_days": interval_days,
                    "ease_factor": float(ease_factor),
                    "lapse_count": lapse_count,
                    "last_grade": grade,
                    "due_at": due_at,
                    "mastery_score": float(mastery_score),
                })
            return Cursor()

        if normalized.startswith("select") and "as active_knowledge" in normalized:
            user_id, _u2, _u3, _u4, _u5, _u6, _u7 = params
            owned = [item for item in self.knowledge.values() if item["user_id"] == user_id]
            owner_experiences = [item for item in self.experiences if item["user_id"] == user_id]
            owner_schedules = [item for item in self.schedules.values() if item["user_id"] == user_id]
            owner_episodes = [item for item in self.episodes.values() if item["user_id"] == user_id]
            return Cursor(row={
                "active_knowledge": sum(item["status"] == "active" for item in owned),
                "needs_review": sum(item["status"] == "needs_review" for item in owned),
                "experiences": len(owner_experiences),
                "feedback_events": sum(item["event_type"] == "feedback" for item in owner_experiences),
                "episodic_memories": len(owner_episodes),
                "due_reviews": sum(item["repetition_count"] == 0 for item in owner_schedules),
                "average_mastery": (
                    sum(item["mastery_score"] for item in owner_schedules) / len(owner_schedules)
                    if owner_schedules else 0.0
                ),
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



def test_completed_dialogue_is_saved_as_episodic_memory_and_recalled(monkeypatch):
    database = MindDatabase()
    owner_id = uuid4()
    conversation_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    episode_id = mind_module.store_episodic_memory(
        database,
        user_id=owner_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        user_text="I am learning distributed systems",
        assistant_text="We discussed quorum and replication.",
    )
    assert str(episode_id) in database.episodes
    assert database.episodes[str(episode_id)]["content_sha256"]

    client = _client(monkeypatch, database, owner_id)
    try:
        recalled = client.get("/api/mind/recall", params={"q": "quorum replication"})
        assert recalled.status_code == 200
        assert any(item["knowledge_type"] == "episodic_memory" for item in recalled.json()["items"])
        assert database.episodes[str(episode_id)]["recall_count"] == 1

        listing = client.get("/api/mind/episodic-memories")
        assert listing.status_code == 200
        assert len(listing.json()["items"]) == 1
    finally:
        main.app.dependency_overrides.clear()


def test_spaced_review_schedules_next_retrieval_and_updates_mastery(monkeypatch):
    database = MindDatabase()
    owner_id = uuid4()
    client = _client(monkeypatch, database, owner_id)
    try:
        taught = client.post("/api/mind/teach", json={
            "knowledge_type": "concept",
            "title": "Hippocampal memory",
            "content": "The hippocampus supports formation of new episodic memories.",
        })
        assert taught.status_code == 201
        knowledge_id = taught.json()["knowledge"]["id"]

        due = client.get("/api/mind/reviews/due")
        assert due.status_code == 200
        assert len(due.json()["items"]) == 1

        reviewed = client.post(f"/api/mind/reviews/{knowledge_id}", json={
            "grade": 4,
            "note": "I recalled the concept correctly.",
        })
        assert reviewed.status_code == 200
        assert reviewed.json()["interval_days"] == 1
        assert reviewed.json()["repetition_count"] == 1
        assert reviewed.json()["mastery_score"] > 0
        assert any(item["event_type"] == "spaced_review" for item in database.experiences)
    finally:
        main.app.dependency_overrides.clear()
