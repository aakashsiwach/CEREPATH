# Data model

The initial schema lives in `infra/db-init/001_schema.sql`.

## `users`

Identity records contain a stable UUID, unique email, display name, provider and optional provider subject. The local milestone seeds one owner identity (`owner@local.invalid`). External identity-provider subjects are reserved for the OIDC/passkey integration milestone.

## `sessions`

Sessions store only SHA-256 hashes of opaque random session tokens and CSRF tokens. They include owner ID, expiry, creation/last-seen timestamps and revocation time. The browser receives an HTTP-only session cookie; it never receives the stored token hash.

## `memories`

Approved owner knowledge only, scoped by a non-null `user_id` foreign key. Existing rows are migrated to the single local owner. Each row has a category, title, content, source, confidence, JSON metadata, optional 384-dimensional vector embedding and timestamps. The starter does not generate embeddings.

## `approvals`

A pending proposal records the owning `user_id`, exact action type, optional target ID, JSON payload, reason, status, decision actor and timestamps. The API only supports memory add/update/delete operations in this milestone.

## `audit_events`

Append-only event records identify `user_id`, actor, action, resource and details. Production hardening should restrict direct table mutation and ship audit exports to independently controlled storage.

## Cognitive memory tables

- `semantic_knowledge` stores owner-taught facts, concepts, procedures, skills, preferences and principles. It includes provenance, a normalized-content hash, confidence, reinforcement count, review status, optional vector embedding and a generated PostgreSQL full-text search vector.
- `cognitive_experiences` stores owner-scoped lesson-encoding, recall, feedback, conversation-episode and spaced-review events, with links to semantic knowledge where applicable.
- `episodic_memories` stores completed user/assistant dialogue episodes, source message/conversation foreign keys, a content hash, optional local embedding, importance, reinforcement and recall counters.
- `learning_schedules` stores owner-rated retrieval-practice history, SM-2 interval/ease/lapse state, next due time and self-rated mastery separately from factual confidence.
- `chat_conversations` and `chat_messages` remain the source dialogue log; episodic memories are a derived, searchable index that links back to the source messages.

## Documents and knowledge graph

- `knowledge_sources` stores original uploaded bytes, extracted text, filename/media metadata, content SHA-256, extraction metadata and lifecycle status. Archiving excludes a source from recall but retains the original bytes.
- `knowledge_chunks` stores bounded overlapping text passages, chunk hashes, PDF page numbers, generated full-text search vectors and optional 384-dimensional embeddings.
- `knowledge_concepts` stores owner-managed canonical concepts with optional source provenance.
- `knowledge_relations` stores typed, evidence-bearing, owner-verified links between concepts. Composite owner-scoped foreign keys prevent cross-owner concept/source links.

Local embeddings are optional. With `EMBEDDING_PROVIDER=ollama`, the API uses the configured local Ollama embedding model; the schema expects 384 dimensions. With embeddings disabled or unavailable, PostgreSQL full-text search continues to work. No hosted embedding provider is used.

## Not stored automatically

Documents require an explicit owner upload. Completed dialogue is automatically indexed as local episodic memory; the source chat remains in the chat log. Browser page content and screenshots are not automatically converted into knowledge. Model-generated claims and relationships are not silently promoted into semantic knowledge. The owner must explicitly create concept relationships and rate retrieval-practice performance.

## Future additions

- Source-grounded concept extraction proposals with owner review.
- Contradiction detection and evidence-backed knowledge versioning.
- Consolidation/replay jobs with provenance and rollback.
- `tasks` and `task_steps` for resumable execution.
- `skills` and `skill_versions` for evaluated reusable procedures.
- `evaluations` for regression tests and capability scores.
- `devices` for secure multi-device access.
