CREATE TABLE IF NOT EXISTS semantic_knowledge (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_type TEXT NOT NULL CHECK (
        knowledge_type IN ('fact', 'concept', 'procedure', 'skill', 'preference', 'principle')
    ),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 240),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 20000),
    source_type TEXT NOT NULL DEFAULT 'owner_taught' CHECK (
        source_type IN ('owner_taught', 'document', 'conversation', 'web', 'model_suggestion')
    ),
    source_ref TEXT,
    content_sha256 CHAR(64) NOT NULL,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.800 CHECK (confidence >= 0 AND confidence <= 1),
    reinforcement_count INTEGER NOT NULL DEFAULT 1 CHECK (reinforcement_count >= 1),
    status TEXT NOT NULL DEFAULT 'active' CHECK (
        status IN ('active', 'needs_review', 'superseded', 'archived')
    ),
    embedding VECTOR(384),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(content, '')), 'B')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, content_sha256)
);

CREATE INDEX IF NOT EXISTS semantic_knowledge_user_updated_idx
    ON semantic_knowledge(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS semantic_knowledge_search_idx
    ON semantic_knowledge USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS semantic_knowledge_status_idx
    ON semantic_knowledge(user_id, status, knowledge_type);

CREATE TABLE IF NOT EXISTS cognitive_experiences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('perception', 'lesson_encoded', 'recall', 'feedback', 'reflection', 'consolidation')
    ),
    related_knowledge_id UUID REFERENCES semantic_knowledge(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL DEFAULT 'owner_taught',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS cognitive_experiences_user_created_idx
    ON cognitive_experiences(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS cognitive_experiences_knowledge_idx
    ON cognitive_experiences(related_knowledge_id, created_at DESC);
