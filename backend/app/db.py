from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@contextmanager
def connect():
    """One connection per unit of work; commits on success, rolls back on error."""
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        yield conn


def init_schema() -> None:
    with connect() as conn:
        conn.execute(SCHEMA_PATH.read_text())
