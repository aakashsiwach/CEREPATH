import os
from urllib.parse import urlparse
from uuid import UUID, uuid4

import psycopg
import pytest

TEST_DATABASE_URL = os.getenv("CEREPATH_TEST_DATABASE_URL")
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL or "postgresql://cerepath:cerepath-ci@localhost:5432/cerepath")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from app import db
from app.config import OWNER_USER_ID


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="Set CEREPATH_TEST_DATABASE_URL to run PostgreSQL integration tests")
def test_identity_migration_backfills_existing_records_and_is_repeatable(monkeypatch):
    database_url = TEST_DATABASE_URL
    database_name = urlparse(database_url).path.lstrip("/")
    if not database_name.endswith("_test"):
        raise AssertionError("Use a dedicated disposable PostgreSQL database whose name ends in _test")
    monkeypatch.setattr(db, "DATABASE_URL", database_url)

    memory_id = uuid4()
    approval_id = uuid4()
    with psycopg.connect(database_url) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            """
            CREATE TABLE memories (
                id UUID PRIMARY KEY,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE approvals (
                id UUID PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE audit_events (
                id BIGSERIAL PRIMARY KEY,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                details JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute("INSERT INTO memories (id) VALUES (%s)", (memory_id,))
        conn.execute("INSERT INTO approvals (id) VALUES (%s)", (approval_id,))
        conn.execute(
            """
            INSERT INTO audit_events (actor, action, resource_type)
            VALUES ('owner', 'memory.created', 'memory')
            """
        )

    db.apply_migrations()
    db.apply_migrations()

    owner_id = UUID(OWNER_USER_ID)
    with psycopg.connect(database_url) as conn:
        memory = conn.execute("SELECT user_id FROM memories WHERE id = %s", (memory_id,)).fetchone()
        approval = conn.execute("SELECT user_id FROM approvals WHERE id = %s", (approval_id,)).fetchone()
        audit = conn.execute("SELECT user_id FROM audit_events LIMIT 1").fetchone()
        owner_count = conn.execute("SELECT count(*) FROM users WHERE id = %s", (owner_id,)).fetchone()[0]
        migration_count = conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
        session_table = conn.execute(
            "SELECT to_regclass('public.sessions') IS NOT NULL"
        ).fetchone()[0]
        conversation_table = conn.execute(
            "SELECT to_regclass('public.chat_conversations') IS NOT NULL"
        ).fetchone()[0]
        message_table = conn.execute(
            "SELECT to_regclass('public.chat_messages') IS NOT NULL"
        ).fetchone()[0]
        semantic_table = conn.execute(
            "SELECT to_regclass('public.semantic_knowledge') IS NOT NULL"
        ).fetchone()[0]
        experience_table = conn.execute(
            "SELECT to_regclass('public.cognitive_experiences') IS NOT NULL"
        ).fetchone()[0]

    assert memory[0] == owner_id
    assert approval[0] == owner_id
    assert audit[0] == owner_id
    assert owner_count == 1
    assert migration_count == 3
    assert session_table is True
    assert conversation_table is True
    assert message_table is True
    assert semantic_table is True
    assert experience_table is True
