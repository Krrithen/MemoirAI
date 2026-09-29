from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# Arbitrary constant: serialises schema creation when the API and workers start together.
SCHEMA_LOCK = 872_401


@contextmanager
def connect():
    """One connection per unit of work; commits on success, rolls back on error."""
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        yield conn


def ping(timeout_s: int = 2) -> None:
    """Raise if the database can't answer SELECT 1 within timeout_s."""
    with psycopg.connect(
        get_settings().database_url,
        connect_timeout=timeout_s,
        options=f"-c statement_timeout={timeout_s * 1000}",
    ) as conn:
        conn.execute("SELECT 1")


def init_schema() -> None:
    """Create any missing tables from schema.sql (existing tables are left as they are)."""
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK,))
        conn.execute(SCHEMA_PATH.read_text())
