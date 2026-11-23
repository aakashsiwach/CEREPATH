from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from .config import DATABASE_URL


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Open one short-lived database connection and commit on successful exit."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


def apply_migrations() -> None:
    """Apply versioned SQL migrations in one transaction and record applied versions."""
    migration_dir = Path(__file__).parent / "migrations"
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        for migration in sorted(migration_dir.glob("*.sql")):
            version = migration.name
            applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s", (version,)
            ).fetchone()
            if applied:
                continue
            sql = migration.read_text(encoding="utf-8")
            # Migration files contain plain SQL statements without procedural semicolons.
            for statement in sql.split(";"):
                if statement.strip():
                    conn.execute(statement, prepare=False)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
