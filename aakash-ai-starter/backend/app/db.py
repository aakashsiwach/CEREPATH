from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from .config import DATABASE_URL


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Open one short-lived database connection and commit on successful exit."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn
