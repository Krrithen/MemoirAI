"""Tests run against a real Postgres (docker compose, port 5433) with fake model providers.

A throwaway `memoir_test` database is created per session; tables are truncated between tests.
"""

import os
import shutil
import tempfile

import psycopg
import pytest

ADMIN_URL = os.environ.get("TEST_ADMIN_DATABASE_URL", "postgresql://memoir:memoir@localhost:5433/memoir")
TEST_DB = "memoir_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"

# Must be set before app modules read settings.
os.environ["DATABASE_URL"] = TEST_URL
MEDIA_DIR = tempfile.mkdtemp(prefix="memoir-media-")
os.environ["MEDIA_DIR"] = MEDIA_DIR

from fastapi.testclient import TestClient  # noqa: E402

from app import db, main  # noqa: E402
from app.pipeline import worker  # noqa: E402
from app.providers.llm import Enrichment  # noqa: E402
from app.providers.transcriber import TranscriptionFailed  # noqa: E402

TRANSCRIPT = "Last summer my grandmother and I baked apple pie in her kitchen in Lisbon."


class FakeTranscriber:
    def __init__(self):
        self.text = TRANSCRIPT
        self.calls = 0

    def transcribe(self, audio: bytes, suffix: str) -> str:
        self.calls += 1
        if not self.text:
            raise TranscriptionFailed("No speech found in the recording")
        return self.text


class FakeLLM:
    def __init__(self):
        self.result: Enrichment | Exception = Enrichment(
            title="Apple Pie in Lisbon",
            story="Last summer, my grandmother and I baked apple pie in her kitchen in Lisbon.",
            emotions=["Joy", "Love"],
        )
        self.calls = 0

    def enrich(self, transcript: str) -> Enrichment:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture(scope="session", autouse=True)
def test_database():
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as e:
        pytest.exit(f"Postgres not reachable at {ADMIN_URL}. Run `docker compose up -d` first. ({e})")
    with admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DB}")
    db.init_schema()
    yield
    db.close_pool()
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    shutil.rmtree(MEDIA_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables():
    with db.connect() as conn:
        conn.execute("TRUNCATE jobs, memories, media")


@pytest.fixture
def transcriber(monkeypatch) -> FakeTranscriber:
    fake = FakeTranscriber()
    monkeypatch.setattr(worker, "get_transcriber", lambda: fake)
    return fake


@pytest.fixture
def llm(monkeypatch) -> FakeLLM:
    fake = FakeLLM()
    monkeypatch.setattr(worker, "get_llm", lambda: fake)
    return fake


@pytest.fixture
def client(transcriber, llm):
    with TestClient(main.app) as c:
        yield c


def count(table: str) -> int:
    with db.connect() as conn:
        return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def drain(worker_id: str = "test-worker") -> int:
    """Run the worker until no job is due. Returns how many jobs it processed."""
    n = 0
    while worker.run_once(worker_id):
        n += 1
    return n


def fast_forward_jobs() -> None:
    """Make every job due now (skips retry backoff delays)."""
    with db.connect() as conn:
        conn.execute("UPDATE jobs SET run_after = now()")


def memory_row(memory_id) -> dict:
    with db.connect() as conn:
        return conn.execute("SELECT * FROM memories WHERE id = %s", (memory_id,)).fetchone()


def job_row(memory_id) -> dict | None:
    with db.connect() as conn:
        return conn.execute("SELECT * FROM jobs WHERE memory_id = %s", (memory_id,)).fetchone()
