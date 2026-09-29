import threading
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# Arbitrary constant: serialises schema creation when the API and workers start together.
SCHEMA_LOCK = 872_401

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ConnectionPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            s = get_settings()
            _pool = ConnectionPool(
                s.database_url,
                min_size=1,
                max_size=s.db_pool_max,
                timeout=s.db_pool_timeout_s,
                kwargs={"row_factory": dict_row},
                # Validate each connection before handing it out, so a database restart
                # doesn't leave dead connections in the pool.
                check=ConnectionPool.check_connection,
                open=True,
            )
    return _pool


def close_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


@contextmanager
def connect():
    """One pooled connection per unit of work; commits on success, rolls back on error."""
    with _get_pool().connection() as conn:
        yield conn


def ping(timeout_s: int = 2) -> None:
    """Raise if the database can't answer SELECT 1 within timeout_s (a fresh connection, not the pool)."""
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
