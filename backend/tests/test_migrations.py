from pathlib import Path


def test_identity_migration_adds_user_ownership_and_revocable_sessions():
    migration = Path(__file__).parents[1] / "app" / "migrations" / "002_identity_sessions.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS users" in sql
    assert "ALTER TABLE memories ADD COLUMN IF NOT EXISTS user_id UUID" in sql
    assert "ALTER TABLE approvals ADD COLUMN IF NOT EXISTS user_id UUID" in sql
    assert "ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS user_id UUID" in sql
    assert "CREATE TABLE IF NOT EXISTS sessions" in sql
    assert "token_hash CHAR(64) NOT NULL UNIQUE" in sql
    assert "revoked_at TIMESTAMPTZ" in sql
    assert "ON DELETE RESTRICT" in sql


def test_chat_migration_adds_owner_scoped_conversations_and_messages():
    migration = Path(__file__).parents[1] / "app" / "migrations" / "003_chat_history.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS chat_conversations" in sql
    assert "CREATE TABLE IF NOT EXISTS chat_messages" in sql
    assert "REFERENCES chat_conversations(id, user_id)" in sql
    assert "CHECK (role IN ('user', 'assistant'))" in sql
    assert "status IN ('pending', 'complete', 'failed')" in sql


def test_cognitive_migration_adds_owner_scoped_semantic_knowledge_and_experiences():
    migration = Path(__file__).parents[1] / "app" / "migrations" / "004_cognitive_architecture.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS semantic_knowledge" in sql
    assert "REFERENCES users(id) ON DELETE CASCADE" in sql
    assert "content_sha256 CHAR(64) NOT NULL" in sql
    assert "embedding VECTOR(384)" in sql
    assert "GENERATED ALWAYS AS" in sql
    assert "CREATE TABLE IF NOT EXISTS cognitive_experiences" in sql
    assert "REFERENCES semantic_knowledge(id) ON DELETE SET NULL" in sql


def test_document_memory_migration_adds_owner_scoped_sources_chunks_and_graph():
    migration = Path(__file__).parents[1] / "app" / "migrations" / "005_document_knowledge_graph.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS knowledge_sources" in sql
    assert "original_bytes BYTEA NOT NULL" in sql
    assert "CREATE TABLE IF NOT EXISTS knowledge_chunks" in sql
    assert "embedding VECTOR(384)" in sql
    assert "CREATE TABLE IF NOT EXISTS knowledge_concepts" in sql
    assert "CREATE TABLE IF NOT EXISTS knowledge_relations" in sql
    assert "FOREIGN KEY (from_concept_id, user_id)" in sql
    assert "FOREIGN KEY (source_id, user_id)" in sql


def test_digital_learning_migration_adds_episodic_memory_and_spaced_reviews():
    migration = Path(__file__).parents[1] / "app" / "migrations" / "006_episodic_memory_and_learning.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS episodic_memories" in sql
    assert "conversation_episode" in sql
    assert "embedding VECTOR(384)" in sql
    assert "CREATE TABLE IF NOT EXISTS learning_schedules" in sql
    assert "ease_factor NUMERIC(4,2)" in sql
    assert "mastery_score NUMERIC(4,3)" in sql
    assert "FOREIGN KEY (conversation_id, user_id)" in sql
