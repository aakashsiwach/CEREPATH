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
