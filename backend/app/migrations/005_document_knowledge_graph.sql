CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'document' CHECK (
        source_type IN ('document', 'manual', 'web')
    ),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 500),
    filename TEXT NOT NULL CHECK (length(filename) BETWEEN 1 AND 500),
    file_extension TEXT NOT NULL,
    media_type TEXT NOT NULL,
    byte_size BIGINT NOT NULL CHECK (byte_size > 0),
    content_sha256 CHAR(64) NOT NULL,
    original_bytes BYTEA NOT NULL,
    extracted_text TEXT NOT NULL,
    extraction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'processed' CHECK (
        status IN ('processed', 'needs_review', 'archived')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, content_sha256),
    UNIQUE (id, user_id)
);

CREATE INDEX IF NOT EXISTS knowledge_sources_user_created_idx
    ON knowledge_sources(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 10000),
    page_number INTEGER CHECK (page_number IS NULL OR page_number > 0),
    character_count INTEGER NOT NULL CHECK (character_count > 0),
    content_sha256 CHAR(64) NOT NULL,
    embedding VECTOR(384),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(content, '')), 'A')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, chunk_index),
    FOREIGN KEY (source_id, user_id)
        REFERENCES knowledge_sources(id, user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_user_source_idx
    ON knowledge_chunks(user_id, source_id, chunk_index);

CREATE INDEX IF NOT EXISTS knowledge_chunks_search_idx
    ON knowledge_chunks USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS semantic_knowledge_embedding_idx
    ON semantic_knowledge USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE TABLE IF NOT EXISTS knowledge_concepts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    canonical_name TEXT NOT NULL CHECK (length(canonical_name) BETWEEN 1 AND 240),
    description TEXT NOT NULL DEFAULT '',
    normalized_name TEXT NOT NULL,
    source_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, normalized_name),
    UNIQUE (id, user_id),
    FOREIGN KEY (source_id, user_id)
        REFERENCES knowledge_sources(id, user_id) ON DELETE SET NULL (source_id)
);

CREATE INDEX IF NOT EXISTS knowledge_concepts_user_name_idx
    ON knowledge_concepts(user_id, normalized_name);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_concept_id UUID NOT NULL,
    to_concept_id UUID NOT NULL,
    relation_type TEXT NOT NULL CHECK (
        relation_type IN (
            'related_to', 'prerequisite_of', 'part_of', 'example_of',
            'contradicts', 'causes', 'supports'
        )
    ),
    evidence TEXT NOT NULL DEFAULT '',
    source_id UUID,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.800 CHECK (confidence >= 0 AND confidence <= 1),
    owner_verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (from_concept_id <> to_concept_id),
    UNIQUE (user_id, from_concept_id, to_concept_id, relation_type),
    FOREIGN KEY (from_concept_id, user_id)
        REFERENCES knowledge_concepts(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (to_concept_id, user_id)
        REFERENCES knowledge_concepts(id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id, user_id)
        REFERENCES knowledge_sources(id, user_id) ON DELETE SET NULL (source_id)
);

CREATE INDEX IF NOT EXISTS knowledge_relations_user_idx
    ON knowledge_relations(user_id, relation_type);
