from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
# Arbitrary constant: serialises migrations when the API and workers start together.
MIGRATION_LOCK = 872_401


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


def migrate() -> None:
    """Apply any unapplied migrations/NNN_*.sql in order, exactly once, in one transaction."""
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations"
            " (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.stem not in applied:
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
