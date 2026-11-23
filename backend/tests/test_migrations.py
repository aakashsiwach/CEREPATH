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
