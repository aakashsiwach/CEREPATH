from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from decimal import Decimal
from pathlib import PurePath
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import Response

from ..db import connection
from ..security import require_owner
from .cognitive.hippocampal_indexing import HippocampalIndexer
from .cognitive.prefrontal_cortex import PrefrontalCognitiveController
from .cognitive.prediction_error import RewardPredictionError
from .document_ingestion import (
    MAX_UPLOAD_BYTES,
    DocumentExtractionError,
    chunk_document,
    extract_document,
)
from .embeddings import (
    EmbeddingProviderError,
    LocalOllamaEmbeddingProvider,
)

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


class ConceptInput(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4_000)
    source_id: UUID | None = None


class ConceptRelationInput(BaseModel):
    from_concept_id: UUID
    to_concept_id: UUID
    relation_type: Literal[
        "related_to", "prerequisite_of", "part_of", "example_of",
        "contradicts", "causes", "supports",
    ]
    evidence: str = Field(default="", max_length=4_000)
    source_id: UUID | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


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
    embedding_status = "disabled"
    vector_value = None
    try:
        embedding_provider = LocalOllamaEmbeddingProvider.from_environment()
    except EmbeddingProviderError:
        embedding_provider = None
        embedding_status = "configuration_error"
    if embedding_provider is not None:
        try:
            vector_value = embedding_provider.to_pgvector(
                embedding_provider.embed([f"{body.title.strip()}\n{normalized_content}"])[0]
            )
            embedding_status = "local_ollama"
        except (EmbeddingProviderError, IndexError):
            embedding_status = "unavailable"

    with connection() as conn:
        knowledge = conn.execute(
            """
            INSERT INTO semantic_knowledge (
                id, user_id, knowledge_type, title, content, source_type,
                source_ref, content_sha256, confidence, embedding
            )
            VALUES (%s, %s, %s, %s, %s, 'owner_taught', %s, %s, %s, %s::vector)
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
                vector_value,
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
        "embedding_status": embedding_status,
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


def retrieve_relevant_knowledge(
    conn: Any,
    user_id: UUID,
    query: str,
    *,
    limit: int = 8,
) -> tuple[list[dict[str, Any]], Any, str]:
    """Hybrid lexical/vector recall across owner knowledge and document passages."""
    normalized_query = " ".join(query.split())[:2_000]
    candidates: dict[str, dict[str, Any]] = {}
    embedding_status = "disabled"
    query_vector: str | None = None

    try:
        embedding_provider = LocalOllamaEmbeddingProvider.from_environment()
    except EmbeddingProviderError:
        embedding_provider = None
        embedding_status = "configuration_error"

    if embedding_provider is not None:
        try:
            vectors = embedding_provider.embed([normalized_query])
            query_vector = embedding_provider.to_pgvector(vectors[0])
            embedding_status = "local_ollama"
        except (EmbeddingProviderError, IndexError):
            embedding_status = "unavailable"

    lexical_knowledge = conn.execute(
        """
        SELECT id, knowledge_type, title, content, source_type, source_ref,
               confidence, reinforcement_count, updated_at,
               LEAST(ts_rank_cd(search_vector, websearch_to_tsquery('simple', %s)) * 10.0, 1.0)
                   AS retrieval_score
        FROM semantic_knowledge
        WHERE user_id = %s AND status = 'active'
          AND search_vector @@ websearch_to_tsquery('simple', %s)
        ORDER BY retrieval_score DESC, reinforcement_count DESC, updated_at DESC
        LIMIT 40
        """,
        (normalized_query, user_id, normalized_query),
    ).fetchall()
    for row in lexical_knowledge:
        item = dict(row)
        candidates[str(item["id"])] = item

    lexical_chunks = conn.execute(
        """
        SELECT c.id, c.content, c.page_number, c.source_id,
               s.title AS source_title, s.filename,
               'document' AS source_type,
               s.id::text AS source_ref,
               0.85::numeric AS confidence,
               1 AS reinforcement_count,
               c.created_at AS updated_at,
               LEAST(ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', %s)) * 10.0, 1.0)
                   AS retrieval_score
        FROM knowledge_chunks c
        JOIN knowledge_sources s ON s.id = c.source_id AND s.user_id = c.user_id
        WHERE c.user_id = %s AND s.status = 'processed'
          AND c.search_vector @@ websearch_to_tsquery('simple', %s)
        ORDER BY retrieval_score DESC, c.chunk_index
        LIMIT 60
        """,
        (normalized_query, user_id, normalized_query),
    ).fetchall()
    for row in lexical_chunks:
        item = dict(row)
        item["knowledge_type"] = "document_chunk"
        item["title"] = item.get("source_title") or item.get("filename") or "Document"
        item["confidence"] = float(item.get("confidence", 0.85))
        candidates[f"chunk:{item['id']}"] = item

    if query_vector is not None:
        vector_knowledge = conn.execute(
            """
            SELECT id, knowledge_type, title, content, source_type, source_ref,
                   confidence, reinforcement_count, updated_at,
                   GREATEST(1.0 - (embedding <=> %s::vector), 0.0) AS retrieval_score
            FROM semantic_knowledge
            WHERE user_id = %s AND status = 'active' AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 40
            """,
            (query_vector, user_id, query_vector),
        ).fetchall()
        for row in vector_knowledge:
            item = dict(row)
            key = str(item["id"])
            if key in candidates:
                item["retrieval_score"] = max(
                    float(item["retrieval_score"]),
                    float(candidates[key].get("retrieval_score", 0.0)),
                )
            candidates[key] = item

        vector_chunks = conn.execute(
            """
            SELECT c.id, c.content, c.page_number, c.source_id,
                   s.title AS source_title, s.filename,
                   'document' AS source_type,
                   s.id::text AS source_ref,
                   0.85::numeric AS confidence,
                   1 AS reinforcement_count,
                   c.created_at AS updated_at,
                   GREATEST(1.0 - (c.embedding <=> %s::vector), 0.0) AS retrieval_score
            FROM knowledge_chunks c
            JOIN knowledge_sources s ON s.id = c.source_id AND s.user_id = c.user_id
            WHERE c.user_id = %s AND s.status = 'processed' AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT 60
            """,
            (query_vector, user_id, query_vector),
        ).fetchall()
        for row in vector_chunks:
            item = dict(row)
            item["knowledge_type"] = "document_chunk"
            item["title"] = item.get("source_title") or item.get("filename") or "Document"
            item["confidence"] = float(item.get("confidence", 0.85))
            key = f"chunk:{item['id']}"
            if key in candidates:
                item["retrieval_score"] = max(
                    float(item["retrieval_score"]),
                    float(candidates[key].get("retrieval_score", 0.0)),
                )
            candidates[key] = item

    selected = _prefrontal_cortex.select_relevant(
        normalized_query, list(candidates.values()), limit=limit
    )
    from .cognitive.metacognition import MetacognitiveMonitor

    assessment = MetacognitiveMonitor().assess_retrieval(selected)
    return selected, assessment, embedding_status


@router.get("/recall")
def recall_knowledge(
    q: str = Query(min_length=2, max_length=500),
    limit: int = Query(default=8, ge=1, le=20),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    """Recall owner knowledge and document passages with hybrid ranking."""
    query = " ".join(q.split())
    with connection() as conn:
        selected, assessment, embedding_status = retrieve_relevant_knowledge(
            conn, user_id, query, limit=limit
        )
    return {
        "query": query,
        "items": [_serialize(item) for item in selected],
        "evidence_state": assessment.evidence_state,
        "embedding_status": embedding_status,
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


@router.post("/documents", status_code=201)
def ingest_document(
    file: UploadFile = File(...),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    """Store an original owner document, extract text, chunk and optionally embed locally."""
    raw_filename = file.filename or "document"
    filename = PurePath(raw_filename.replace("\\", "/")).name
    filename = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)[:500]
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=422, detail="A valid filename is required.")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    file.file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 20 MiB upload limit.")

    try:
        segments, extension = extract_document(filename, data)
        chunks = chunk_document(segments)
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    digest = hashlib.sha256(data).hexdigest()
    title = PurePath(filename).stem[:500] or filename
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    extracted_text = "\n\n".join(segment.text for segment in segments)

    embedding_status = "disabled"
    vectors: list[list[float] | None] = [None] * len(chunks)
    try:
        embedding_provider = LocalOllamaEmbeddingProvider.from_environment()
    except EmbeddingProviderError:
        embedding_provider = None
        embedding_status = "configuration_error"

    if embedding_provider is not None:
        try:
            vectors = embedding_provider.embed([chunk.content for chunk in chunks])
            embedding_status = "local_ollama"
        except EmbeddingProviderError:
            embedding_status = "unavailable"
            vectors = [None] * len(chunks)

    source_id = uuid4()
    experience_id = uuid4()
    with connection() as conn:
        existing = conn.execute(
            """
            SELECT id, title, filename, byte_size, status, created_at,
                   (SELECT COUNT(*) FROM knowledge_chunks c
                    WHERE c.source_id = knowledge_sources.id AND c.user_id = knowledge_sources.user_id) AS chunk_count
            FROM knowledge_sources
            WHERE user_id = %s AND content_sha256 = %s
            """,
            (user_id, digest),
        ).fetchone()
        if existing:
            return {
                "duplicate": True,
                "message": "This exact document is already in Cerepath's knowledge store.",
                "source": _serialize(dict(existing)),
                "embedding_status": embedding_status,
            }

        source = conn.execute(
            """
            INSERT INTO knowledge_sources (
                id, user_id, source_type, title, filename, file_extension, media_type,
                byte_size, content_sha256, original_bytes, extracted_text, extraction_metadata
            )
            VALUES (%s, %s, 'document', %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, title, filename, file_extension, media_type, byte_size,
                      status, created_at
            """,
            (
                source_id, user_id, title, filename, extension, media_type,
                len(data), digest, data, extracted_text,
                json.dumps({
                    "segments": len(segments),
                    "chunks": len(chunks),
                    "extracted_characters": len(extracted_text),
                    "embedding_provider": embedding_status,
                    "chunk_characters": 1800,
                    "chunk_overlap_characters": 240,
                }),
            ),
        ).fetchone()

        for chunk, vector in zip(chunks, vectors, strict=True):
            vector_value = (
                embedding_provider.to_pgvector(vector)
                if vector is not None and embedding_provider is not None
                else None
            )
            conn.execute(
                """
                INSERT INTO knowledge_chunks (
                    id, source_id, user_id, chunk_index, content, page_number,
                    character_count, content_sha256, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                """,
                (
                    uuid4(), source_id, user_id, chunk.chunk_index, chunk.content,
                    chunk.page_number, chunk.character_count,
                    hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                    vector_value,
                ),
            )

        conn.execute(
            """
            INSERT INTO cognitive_experiences
                (id, user_id, event_type, related_knowledge_id, source_type, details)
            VALUES (%s, %s, 'perception', NULL, 'document', %s::jsonb)
            """,
            (
                experience_id, user_id,
                json.dumps({
                    "source_id": str(source_id),
                    "filename": filename,
                    "content_sha256": digest,
                    "chunks": len(chunks),
                    "embedding_status": embedding_status,
                }),
            ),
        )

    return {
        "duplicate": False,
        "message": "Document stored, extracted and indexed in Cerepath's local knowledge base.",
        "source": _serialize(dict(source)),
        "chunk_count": len(chunks),
        "embedding_count": sum(vector is not None for vector in vectors),
        "embedding_status": embedding_status,
    }


@router.get("/sources")
def list_knowledge_sources(
    limit: int = Query(default=100, ge=1, le=200),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.filename, s.file_extension, s.media_type,
                   s.byte_size, s.status, s.extraction_metadata, s.created_at,
                   COUNT(c.id) AS chunk_count,
                   COUNT(c.embedding) AS embedded_chunk_count
            FROM knowledge_sources s
            LEFT JOIN knowledge_chunks c ON c.source_id = s.id AND c.user_id = s.user_id
            WHERE s.user_id = %s
            GROUP BY s.id
            ORDER BY s.created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@router.get("/sources/{source_id}/download")
def download_knowledge_source(
    source_id: UUID,
    user_id: UUID = Depends(require_owner),
) -> Response:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT filename, media_type, original_bytes
            FROM knowledge_sources WHERE id = %s AND user_id = %s
            """,
            (source_id, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    safe_filename = str(row["filename"])
    return Response(
        content=bytes(row["original_bytes"]),
        media_type=str(row["media_type"]),
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post("/sources/{source_id}/archive")
def archive_knowledge_source(
    source_id: UUID,
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            UPDATE knowledge_sources
            SET status = 'archived', updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING id, status
            """,
            (source_id, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    return {"source": _serialize(dict(row)), "message": "Source archived; original bytes are retained."}


@router.post("/concepts", status_code=201)
def create_concept(
    body: ConceptInput,
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    canonical_name = " ".join(body.canonical_name.split())
    normalized_name = canonical_name.casefold()
    with connection() as conn:
        if body.source_id:
            source = conn.execute(
                "SELECT id FROM knowledge_sources WHERE id = %s AND user_id = %s",
                (body.source_id, user_id),
            ).fetchone()
            if not source:
                raise HTTPException(status_code=404, detail="Knowledge source not found.")
        row = conn.execute(
            """
            INSERT INTO knowledge_concepts (id, user_id, canonical_name, description, normalized_name, source_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, normalized_name) DO UPDATE SET
                canonical_name = EXCLUDED.canonical_name,
                description = CASE WHEN EXCLUDED.description = '' THEN knowledge_concepts.description
                                   ELSE EXCLUDED.description END,
                source_id = COALESCE(knowledge_concepts.source_id, EXCLUDED.source_id),
                updated_at = NOW()
            RETURNING id, canonical_name, description, source_id, created_at, updated_at
            """,
            (uuid4(), user_id, canonical_name, body.description, normalized_name, body.source_id),
        ).fetchone()
    return {"concept": _serialize(dict(row))}


@router.get("/graph")
def get_knowledge_graph(
    limit: int = Query(default=500, ge=1, le=2000),
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    with connection() as conn:
        concepts = conn.execute(
            """
            SELECT id, canonical_name, description, source_id, created_at, updated_at
            FROM knowledge_concepts WHERE user_id = %s
            ORDER BY canonical_name LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
        relations = conn.execute(
            """
            SELECT r.id, r.from_concept_id, f.canonical_name AS from_name,
                   r.to_concept_id, t.canonical_name AS to_name,
                   r.relation_type, r.evidence, r.source_id, r.confidence,
                   r.owner_verified, r.created_at
            FROM knowledge_relations r
            JOIN knowledge_concepts f
              ON f.id = r.from_concept_id AND f.user_id = r.user_id
            JOIN knowledge_concepts t
              ON t.id = r.to_concept_id AND t.user_id = r.user_id
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
    return {
        "concepts": [_serialize(dict(row)) for row in concepts],
        "relations": [_serialize(dict(row)) for row in relations],
    }


@router.post("/relations", status_code=201)
def create_knowledge_relation(
    body: ConceptRelationInput,
    user_id: UUID = Depends(require_owner),
) -> dict[str, Any]:
    if body.from_concept_id == body.to_concept_id:
        raise HTTPException(status_code=422, detail="A concept cannot be related to itself.")
    with connection() as conn:
        concepts = conn.execute(
            """
            SELECT id FROM knowledge_concepts
            WHERE user_id = %s AND id = ANY(%s)
            """,
            (user_id, [body.from_concept_id, body.to_concept_id]),
        ).fetchall()
        if len(concepts) != 2:
            raise HTTPException(status_code=404, detail="One or both concepts were not found.")
        if body.source_id:
            source = conn.execute(
                "SELECT id FROM knowledge_sources WHERE id = %s AND user_id = %s",
                (body.source_id, user_id),
            ).fetchone()
            if not source:
                raise HTTPException(status_code=404, detail="Knowledge source not found.")
        row = conn.execute(
            """
            INSERT INTO knowledge_relations (
                id, user_id, from_concept_id, to_concept_id,
                relation_type, evidence, source_id, confidence, owner_verified
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (user_id, from_concept_id, to_concept_id, relation_type)
            DO UPDATE SET evidence = EXCLUDED.evidence,
                          source_id = COALESCE(EXCLUDED.source_id, knowledge_relations.source_id),
                          confidence = EXCLUDED.confidence,
                          owner_verified = TRUE
            RETURNING id, from_concept_id, to_concept_id, relation_type,
                      evidence, source_id, confidence, owner_verified, created_at
            """,
            (
                uuid4(), user_id, body.from_concept_id, body.to_concept_id,
                body.relation_type, body.evidence, body.source_id, body.confidence,
            ),
        ).fetchone()
    return {"relation": _serialize(dict(row))}


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
