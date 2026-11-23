CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    identity_provider TEXT NOT NULL DEFAULT 'local-bootstrap',
    provider_subject TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_provider_subject_idx
    ON users(identity_provider, provider_subject)
    WHERE provider_subject IS NOT NULL;

INSERT INTO users (id, email, display_name, identity_provider)
VALUES ('00000000-0000-4000-8000-000000000001', 'owner@local.invalid', 'Local Owner', 'local-bootstrap')
ON CONFLICT (id) DO NOTHING;

ALTER TABLE memories ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE memories SET user_id = '00000000-0000-4000-8000-000000000001' WHERE user_id IS NULL;
UPDATE approvals SET user_id = '00000000-0000-4000-8000-000000000001' WHERE user_id IS NULL;
UPDATE audit_events SET user_id = '00000000-0000-4000-8000-000000000001' WHERE user_id IS NULL;

ALTER TABLE memories ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE approvals ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE audit_events ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE memories ADD CONSTRAINT memories_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE approvals ADD CONSTRAINT approvals_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE audit_events ADD CONSTRAINT audit_events_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS memories_user_updated_idx ON memories(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS approvals_user_status_created_idx ON approvals(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_user_created_idx ON audit_events(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    csrf_token_hash CHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS sessions_user_expiry_idx ON sessions(user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS sessions_active_token_idx ON sessions(token_hash, expires_at)
    WHERE revoked_at IS NULL;
