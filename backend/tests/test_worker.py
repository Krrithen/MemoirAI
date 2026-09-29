"""Queue and worker behaviour: stages, retries, dead-letter, leases and fencing."""

import pytest

from app import db
from app.pipeline import queue, worker
from app.providers.llm import EnrichmentFailed
from tests.conftest import TRANSCRIPT, count, drain, fast_forward_jobs, job_row, memory_row

AUDIO = {"audio": ("rec.webm", b"fake-audio-bytes", "audio/webm")}


@pytest.fixture
def memory_id(client):
    return client.post("/api/memories", files=AUDIO).json()["id"]


def expire_leases() -> None:
    with db.connect() as conn:
        conn.execute("UPDATE jobs SET lease_until = now() - interval '1 second' WHERE lease_until IS NOT NULL")


def test_stages_advance_pending_transcribed_ready(memory_id, transcriber, llm):
    assert worker.run_once("w") is True  # transcribe
    row = memory_row(memory_id)
    assert row["status"] == "transcribed" and row["transcript"] == TRANSCRIPT and row["story"] is None
    assert job_row(memory_id)["stage"] == "enrich"

    assert worker.run_once("w") is True  # enrich
    row = memory_row(memory_id)
    assert row["status"] == "ready" and row["title"] == "Apple Pie in Lisbon"
    assert job_row(memory_id) is None
    assert worker.run_once("w") is False
    assert transcriber.calls == 1 and llm.calls == 1


def test_no_speech_fails_immediately_without_a_story(memory_id, transcriber, llm):
    """Regression: the original app invented a story when transcription failed."""
    transcriber.text = ""
    drain()

    row = memory_row(memory_id)
    assert row["status"] == "failed"
    assert "No speech" in row["error"]
    assert row["story"] is None and row["title"] is None
    assert transcriber.calls == 1  # permanent failure: not retried
    assert llm.calls == 0
    assert count("jobs") == 0


def test_transient_failure_retries_with_backoff(memory_id, llm):
    llm.result = EnrichmentFailed("Ollama request failed: connection refused")
    drain()

    job = job_row(memory_id)
    assert memory_row(memory_id)["status"] == "transcribed"
    assert job["stage"] == "enrich" and job["attempts"] == 1
    assert "connection refused" in job["last_error"]
    assert job["lease_until"] is None
    with db.connect() as conn:
        delay = conn.execute("SELECT extract(epoch FROM run_after - now()) AS s FROM jobs").fetchone()["s"]
    assert delay > 0  # not due yet: backing off
    assert worker.run_once("w") is False

    llm.result = llm.__class__().result  # the model recovers
    fast_forward_jobs()
    drain()
    assert memory_row(memory_id)["status"] == "ready"


def test_gives_up_after_max_attempts(memory_id, llm, monkeypatch):
    monkeypatch.setattr(worker.get_settings(), "job_max_attempts", 3)
    llm.result = EnrichmentFailed("model returned invalid output twice")
    drain()  # transcribe + first enrich attempt
    for _ in range(2):
        fast_forward_jobs()
        drain()

    row = memory_row(memory_id)
    assert row["status"] == "failed"
    assert row["error"].startswith("Gave up after 3 attempts")
    assert row["transcript"] == TRANSCRIPT  # earlier stage results are kept
    assert llm.calls == 3
    assert count("jobs") == 0


def test_backoff_grows_exponentially_and_is_capped(monkeypatch):
    s = worker.get_settings()
    monkeypatch.setattr(s, "job_backoff_base_s", 2.0)
    monkeypatch.setattr(s, "job_backoff_cap_s", 30.0)
    for attempts, full in [(1, 2), (2, 4), (3, 8), (4, 16), (5, 30), (9, 30)]:
        delay = queue.backoff_seconds(attempts)
        assert full / 2 <= delay <= full


def test_expired_lease_is_reclaimed_and_the_old_owner_is_fenced_out(memory_id):
    stale = queue.claim("worker-a")  # A claims, then stalls (or crashes)
    assert queue.claim("worker-b") is None  # lease still valid: nobody else can take it

    expire_leases()
    fresh = queue.claim("worker-b")
    assert fresh is not None and fresh.id == stale.id and fresh.attempts == 2

    assert queue.complete_transcribe(stale, "worker-a", "stale result") is False
    assert queue.fail(stale, "worker-a", "stale error", permanent=True) == "lost"
    assert queue.complete_transcribe(fresh, "worker-b", TRANSCRIPT) is True
    assert memory_row(memory_id)["transcript"] == TRANSCRIPT


def test_worker_crash_mid_stage_is_recovered(memory_id, transcriber):
    job = queue.claim("crashed-worker")  # claimed, then the process dies: no complete/fail
    assert job.stage == "transcribe"

    expire_leases()
    drain("new-worker")
    assert memory_row(memory_id)["status"] == "ready"
    assert transcriber.calls == 1  # the crashed worker never got to call it


def test_repeated_crashes_end_in_failed_not_an_endless_loop(memory_id, monkeypatch):
    monkeypatch.setattr(worker.get_settings(), "job_max_attempts", 2)
    for i in range(2):
        queue.claim(f"crashing-worker-{i}")
        expire_leases()

    assert worker.run_once("w") is True  # third claim exceeds the limit
    row = memory_row(memory_id)
    assert row["status"] == "failed"
    assert "Gave up after 2 attempts at stage 'transcribe'" in row["error"]
    assert count("jobs") == 0


def test_concurrent_claims_never_share_a_job(client):
    ids = {
        client.post("/api/memories", files={"audio": ("r.webm", bytes([i]) * 8, "audio/webm")}).json()["id"]
        for i in range(3)
    }
    claimed = [queue.claim(f"worker-{i}") for i in range(4)]

    jobs = [j for j in claimed if j is not None]
    assert len(jobs) == 3
    assert {str(j.memory_id) for j in jobs} == ids
    assert claimed[3] is None


# --- Week 4 hardening --------------------------------------------------------------


def test_loop_backs_off_and_keeps_going_when_the_database_is_down(monkeypatch):
    import psycopg

    outcomes = [psycopg.OperationalError("connection refused")] * 3 + [True, False]
    calls, sleeps = [], []

    def fake_run_once(worker_id):
        calls.append(worker_id)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    monkeypatch.setattr(worker.gc, "collect_garbage", lambda: {"skipped": True})
    worker.run_forever("w", should_stop=lambda: len(calls) >= len(outcomes), sleep=sleeps.append)

    assert len(calls) == 5  # survived three failures and processed afterwards
    assert sleeps[:3] == [1.0, 2.0, 4.0]  # exponential backoff while the database is down


def test_loop_survives_an_unexpected_error(monkeypatch):
    calls = []

    def fake_run_once(worker_id):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("bug in one iteration")
        return False

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    monkeypatch.setattr(worker.gc, "collect_garbage", lambda: {"skipped": True})
    worker.run_forever("w", should_stop=lambda: len(calls) >= 2, sleep=lambda s: None)
    assert len(calls) == 2


def test_transcriber_network_error_is_retried_not_failed(memory_id, monkeypatch):
    class Offline:
        def transcribe(self, audio, suffix):
            raise ConnectionError("couldn't download the model")

    monkeypatch.setattr(worker, "get_transcriber", lambda: Offline())
    drain()

    assert memory_row(memory_id)["status"] == "pending"
    job = job_row(memory_id)
    assert job["attempts"] == 1 and "ConnectionError" in job["last_error"]


def test_failed_memory_records_its_stage(memory_id, llm, monkeypatch):
    monkeypatch.setattr(worker.get_settings(), "job_max_attempts", 1)
    llm.result = EnrichmentFailed("model down")
    drain()
    assert memory_row(memory_id)["failed_stage"] == "enrich"


def test_heartbeat_keeps_a_slow_stage_from_being_claimed_twice(memory_id, transcriber, monkeypatch):
    import threading
    import time

    monkeypatch.setattr(worker.get_settings(), "job_lease_s", 1)
    original = transcriber.transcribe

    def slow_transcribe(audio, suffix):
        time.sleep(2.5)  # well past the 1 s lease
        return original(audio, suffix)

    monkeypatch.setattr(transcriber, "transcribe", slow_transcribe)
    runner = threading.Thread(target=worker.run_once, args=("slow-worker",))
    runner.start()
    time.sleep(0.2)
    stolen = []
    while runner.is_alive():
        job = queue.claim("other-worker")
        if job:
            stolen.append(job)
        time.sleep(0.1)
    runner.join()

    assert stolen == []
    assert memory_row(memory_id)["status"] == "transcribed"
    assert transcriber.calls == 1


def test_heartbeat_reports_a_lost_lease(memory_id):
    job = queue.claim("a")
    assert queue.heartbeat(job, "a") is True
    expire_leases()
    assert queue.heartbeat(job, "a") is False
