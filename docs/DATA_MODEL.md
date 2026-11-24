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
- `cognitive_experiences` stores owner-scoped lesson-encoding and feedback events, with links to semantic knowledge where applicable.
- `chat_conversations` and `chat_messages` store the owner-scoped conversational episodes. They remain separate from durable semantic knowledge.

## Not stored automatically

Documents are not ingested automatically. Browser page content and screenshots are returned to the current client but are not automatically converted into knowledge. The owner must explicitly use the teaching API to store semantic knowledge. Model-generated claims are not silently promoted into durable knowledge.

## Future additions

- `knowledge_sources` and `knowledge_chunks` for imported documents and source provenance.
- Local embedding generation and hybrid semantic retrieval over `semantic_knowledge`.
- Concept graph tables for explicit concept-to-concept relations.
- Consolidation jobs with reversible, evidence-linked semantic updates.
- `tasks` and `task_steps` for resumable execution.
- `skills` and `skill_versions` for evaluated reusable procedures.
- `evaluations` for regression tests and capability scores.
- `devices` for secure multi-device access.
