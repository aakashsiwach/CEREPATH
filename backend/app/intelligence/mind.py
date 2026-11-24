from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import connection
from ..security import require_owner
from .cognitive.hippocampal_indexing import HippocampalIndexer
from .cognitive.prefrontal_cortex import PrefrontalCognitiveController
from .cognitive.prediction_error import RewardPredictionError

router = APIRouter(prefix="/api/mind", tags=["digital-mind"])
_hippocampus = HippocampalIndexer()
_prefrontal_cortex = PrefrontalCognitiveController()


class TeachKnowledgeInput(BaseModel):
    knowledge_type: Literal["fact", "concept", "procedure", "skill", "preference", "principle"] = "fact"
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=20_000)
    source_ref: str | None = Field(default=None, max_length=2_000)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class KnowledgeFeedbackInput(BaseModel):
    knowledge_id: UUID
    outcome: Literal["helpful", "incomplete", "incorrect"]
    expected_reward: float = Field(default=0.5, ge=0.0, le=1.0)
    note: str = Field(default="", max_length=2_000)


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@router.post("/teach", status_code=201)
def teach_knowledge(
    body: TeachKnowledgeInput,
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    """Persist an explicit owner-taught lesson as searchable semantic knowledge."""
    trace = _hippocampus.encode(
        title=body.title,
        content=body.content,
        episode_type="lesson",
        source_type="owner_taught",
    )
    normalized_content = _hippocampus.normalize_content(body.content)
    knowledge_id = uuid4()
    experience_id = uuid4()

    with connection() as conn:
        knowledge = conn.execute(
            """
            INSERT INTO semantic_knowledge (
                id, user_id, knowledge_type, title, content, source_type,
                source_ref, content_sha256, confidence
            )
            VALUES (%s, %s, %s, %s, %s, 'owner_taught', %s, %s, %s)
            ON CONFLICT (user_id, content_sha256) DO UPDATE SET
                title = EXCLUDED.title,
                knowledge_type = EXCLUDED.knowledge_type,
                source_ref = COALESCE(EXCLUDED.source_ref, semantic_knowledge.source_ref),
                confidence = GREATEST(semantic_knowledge.confidence, EXCLUDED.confidence),
                reinforcement_count = semantic_knowledge.reinforcement_count + 1,
                status = CASE
                    WHEN semantic_knowledge.status = 'needs_review' THEN 'needs_review'
                    ELSE 'active'
                END,
                updated_at = NOW()
            RETURNING id, knowledge_type, title, content, source_type, source_ref,
                      confidence, reinforcement_count, status, created_at, updated_at
            """,
            (
                knowledge_id,
                user_id,
                body.knowledge_type,
                body.title.strip(),
                normalized_content,
                body.source_ref,
                trace.content_sha256,
                body.confidence,
            ),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO cognitive_experiences
                (id, user_id, event_type, related_knowledge_id, source_type, details)
            VALUES (%s, %s, 'lesson_encoded', %s, 'owner_taught', %s::jsonb)
            """,
            (
                experience_id,
                user_id,
                knowledge["id"],
                json.dumps({
                    "content_sha256": trace.content_sha256,
                    "knowledge_type": body.knowledge_type,
                    "title": body.title.strip(),
                    "source_ref": body.source_ref,
                }),
            ),
        )

    return {
        "experience_id": str(experience_id),
        "message": "Lesson stored in Cerepath's local semantic memory.",
        "knowledge": _serialize(dict(knowledge)),
    }


@router.get("/knowledge")
def list_knowledge(
    limit: int = Query(default=100, ge=1, le=200),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, knowledge_type, title, content, source_type, source_ref,
                   confidence, reinforcement_count, status, created_at, updated_at
            FROM semantic_knowledge
            WHERE user_id = %s AND status IN ('active', 'needs_review')
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@router.get("/recall")
def recall_knowledge(
    q: str = Query(min_length=2, max_length=500),
    limit: int = Query(default=8, ge=1, le=20),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    """Retrieve owner-taught concepts using PostgreSQL full-text cues and attention ranking."""
    query = " ".join(q.split())
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, knowledge_type, title, content, source_type, source_ref,
                   confidence, reinforcement_count, updated_at,
                   ts_rank_cd(search_vector, websearch_to_tsquery('simple', %s)) AS retrieval_score
            FROM semantic_knowledge
            WHERE user_id = %s
              AND status = 'active'
              AND search_vector @@ websearch_to_tsquery('simple', %s)
            ORDER BY retrieval_score DESC, reinforcement_count DESC, updated_at DESC
            LIMIT 40
            """,
            (query, user_id, query),
        ).fetchall()

    selected = _prefrontal_cortex.select_relevant(
        query, [dict(row) for row in rows], limit=limit
    )
    return {
        "query": query,
        "items": [_serialize(item) for item in selected],
        "evidence_state": (
            "no_local_evidence" if not selected
            else "retrieved_owner_taught_knowledge"
        ),
        "note": "Retrieval relevance is not proof that a claim is true.",
    }


@router.post("/feedback")
def record_knowledge_feedback(
    body: KnowledgeFeedbackInput,
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    """Record owner feedback; incorrect knowledge is quarantined for review."""
    observed_reward = {
        "helpful": 1.0,
        "incomplete": 0.25,
        "incorrect": 0.0,
    }[body.outcome]
    prediction_error = RewardPredictionError.calculate(
        body.expected_reward, observed_reward
    )

    experience_id = uuid4()
    with connection() as conn:
        knowledge = conn.execute(
            """
            SELECT id FROM semantic_knowledge
            WHERE id = %s AND user_id = %s AND status IN ('active', 'needs_review')
            """,
            (body.knowledge_id, user_id),
        ).fetchone()
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge item not found")

        if body.outcome == "incorrect":
            conn.execute(
                """
                UPDATE semantic_knowledge SET status = 'needs_review', updated_at = NOW()
                WHERE id = %s AND user_id = %s
                """,
                (body.knowledge_id, user_id),
            )

        conn.execute(
            """
            INSERT INTO cognitive_experiences
                (id, user_id, event_type, related_knowledge_id, source_type, details)
            VALUES (%s, %s, 'feedback', %s, 'owner_feedback', %s::jsonb)
            """,
            (
                experience_id,
                user_id,
                body.knowledge_id,
                json.dumps({
                    "outcome": body.outcome,
                    "note": body.note,
                    "expected_reward": prediction_error.expected_reward,
                    "observed_reward": prediction_error.observed_reward,
                    "reward_prediction_error": prediction_error.delta,
                }),
            ),
        )

    return {
        "experience_id": str(experience_id),
        "knowledge_id": str(body.knowledge_id),
        "outcome": body.outcome,
        "reward_prediction_error": prediction_error.delta,
        "status": "needs_review" if body.outcome == "incorrect" else "recorded",
        "note": "This is an owner-feedback metric inspired by reward-prediction-error research, not a dopamine signal.",
    }


@router.get("/state")
def mind_state(user_id: UUID = Depends(require_owner)) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM semantic_knowledge
                 WHERE user_id = %s AND status = 'active') AS active_knowledge,
                (SELECT COUNT(*) FROM semantic_knowledge
                 WHERE user_id = %s AND status = 'needs_review') AS needs_review,
                (SELECT COUNT(*) FROM cognitive_experiences
                 WHERE user_id = %s) AS experiences,
                (SELECT COUNT(*) FROM cognitive_experiences
                 WHERE user_id = %s AND event_type = 'feedback') AS feedback_events
            """,
            (user_id, user_id, user_id, user_id),
        ).fetchone()
    return {
        "architecture": "cognitive_kernel_v0.1",
        "memory_system": "hippocampal_indexing_plus_semantic_knowledge",
        "attention_system": "prefrontal_relevance_controller",
        "working_memory": "baddeley_bounded_context",
        "metacognition": "retrieval_evidence_monitor",
        "active_knowledge": int(row["active_knowledge"]),
        "needs_review": int(row["needs_review"]),
        "experiences": int(row["experiences"]),
        "feedback_events": int(row["feedback_events"]),
        "consciousness_claim": False,
    }
