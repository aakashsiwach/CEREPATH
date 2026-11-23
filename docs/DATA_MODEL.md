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

## Not stored automatically

Chat transcripts are not persisted in the first milestone. Browser page content and screenshots are returned to the current client but are not automatically saved as memories. The owner must explicitly propose any persistent memory addition.

## Future additions

- `tasks` and `task_steps` for resumable execution.
- `skills` and `skill_versions` for evaluated reusable procedures.
- `knowledge_sources` for imported documents and provenance.
- `evaluations` for regression tests and capability scores.
- `devices` and `sessions` for secure multi-device access.
