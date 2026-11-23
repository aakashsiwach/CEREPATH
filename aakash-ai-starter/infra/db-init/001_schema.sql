CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    category TEXT NOT NULL DEFAULT 'general',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'owner-approved',
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.900 CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS memories_category_idx ON memories(category);
CREATE INDEX IF NOT EXISTS memories_created_at_idx ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS memories_metadata_idx ON memories USING GIN(metadata);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY,
    action_type TEXT NOT NULL CHECK (action_type IN ('memory.add', 'memory.update', 'memory.delete')),
    target_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_by TEXT NOT NULL DEFAULT 'owner-session',
    decided_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS approvals_status_created_idx ON approvals(status, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_events_created_at_idx ON audit_events(created_at DESC);
