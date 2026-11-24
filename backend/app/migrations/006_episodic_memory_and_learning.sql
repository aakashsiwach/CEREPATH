CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_id_user_uidx
    ON chat_messages(id, user_id);

CREATE UNIQUE INDEX IF NOT EXISTS semantic_knowledge_id_user_uidx
    ON semantic_knowledge(id, user_id);

ALTER TABLE cognitive_experiences
    DROP CONSTRAINT IF EXISTS cognitive_experiences_event_type_check;

ALTER TABLE cognitive_experiences
    ADD CONSTRAINT cognitive_experiences_event_type_check
    CHECK (event_type IN (
        'perception',
        'lesson_encoded',
        'recall',
        'feedback',
        'reflection',
        'consolidation',
        'conversation_episode',
        'spaced_review'
    ));

CREATE TABLE IF NOT EXISTS episodic_memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL,
    user_message_id UUID NOT NULL,
    assistant_message_id UUID NOT NULL,
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 14000),
    content_sha256 CHAR(64) NOT NULL,
    embedding VECTOR(384),
    importance_score NUMERIC(4,3) NOT NULL DEFAULT 0.500
        CHECK (importance_score >= 0 AND importance_score <= 1),
    reinforcement_count INTEGER NOT NULL DEFAULT 1 CHECK (reinforcement_count >= 1),
    recall_count INTEGER NOT NULL DEFAULT 0 CHECK (recall_count >= 0),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_recalled_at TIMESTAMPTZ,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(content, '')), 'A')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, content_sha256),
    FOREIGN KEY (conversation_id, user_id)
        REFERENCES chat_conversations(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id, user_id)
        REFERENCES chat_messages(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_message_id, user_id)
        REFERENCES chat_messages(id, user_id) ON DELETE CASCADE,
    CHECK (user_message_id <> assistant_message_id)
);

CREATE INDEX IF NOT EXISTS episodic_memories_user_created_idx
    ON episodic_memories(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS episodic_memories_user_seen_idx
    ON episodic_memories(user_id, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS episodic_memories_search_idx
    ON episodic_memories USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS episodic_memories_embedding_idx
    ON episodic_memories USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE TABLE IF NOT EXISTS learning_schedules (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_id UUID NOT NULL,
    repetition_count INTEGER NOT NULL DEFAULT 0 CHECK (repetition_count >= 0),
    interval_days INTEGER NOT NULL DEFAULT 0 CHECK (interval_days >= 0),
    ease_factor NUMERIC(4,2) NOT NULL DEFAULT 2.50 CHECK (ease_factor >= 1.30),
    lapse_count INTEGER NOT NULL DEFAULT 0 CHECK (lapse_count >= 0),
    last_grade SMALLINT CHECK (last_grade IS NULL OR last_grade BETWEEN 0 AND 5),
    last_reviewed_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mastery_score NUMERIC(4,3) NOT NULL DEFAULT 0.000
        CHECK (mastery_score >= 0 AND mastery_score <= 1),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, knowledge_id),
    FOREIGN KEY (knowledge_id, user_id)
        REFERENCES semantic_knowledge(id, user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS learning_schedules_due_idx
    ON learning_schedules(user_id, due_at)
    WHERE status = 'active';

-- Existing taught knowledge receives an initial due review schedule.
INSERT INTO learning_schedules (id, user_id, knowledge_id)
SELECT gen_random_uuid(), user_id, id
FROM semantic_knowledge
ON CONFLICT (user_id, knowledge_id) DO NOTHING;
