"""Postgres job queue: one row per unfinished memory, advanced stage by stage.

- claim() takes one due job with FOR UPDATE SKIP LOCKED, so concurrent workers never
  take the same job, and sets a lease. If the worker dies, the lease expires and the
  job becomes claimable again: stages run at least once.
- Every write after a (slow) stage is fenced on (locked_by, attempts) and a live lease,
  so a worker whose lease was taken over can't overwrite the new owner's work. The stage
  result and the memory's status change commit in the same transaction as the job update.
"""

import random
from dataclasses import dataclass
from uuid import UUID

from psycopg import Connection

from app import db
from app.config import get_settings
from app.providers.llm import Enrichment


@dataclass(frozen=True)
class Job:
    id: int
    memory_id: UUID
    stage: str
    attempts: int


def enqueue(conn: Connection, memory_id: UUID, stage: str = "transcribe") -> None:
    """Add a job inside the caller's transaction (the same one that creates or resets the memory)."""
    conn.execute("INSERT INTO jobs (memory_id, stage) VALUES (%s, %s)", (memory_id, stage))


def claim(worker_id: str) -> Job | None:
    with db.connect() as conn:
        row = conn.execute(
            """
            UPDATE jobs
               SET lease_until = now() + make_interval(secs => %s),
                   locked_by = %s,
                   attempts = attempts + 1
             WHERE id = (
                    SELECT id FROM jobs
                     WHERE run_after <= now()
                       AND (lease_until IS NULL OR lease_until < now())
                     ORDER BY run_after, id
                     FOR UPDATE SKIP LOCKED
                     LIMIT 1)
            RETURNING id, memory_id, stage, attempts
            """,
            (get_settings().job_lease_s, worker_id),
        ).fetchone()
    return Job(**row) if row else None


def _still_owned(conn: Connection, job: Job, worker_id: str) -> bool:
    """Lock the job row and check this worker still holds this claim of it."""
    return (
        conn.execute(
            "SELECT 1 FROM jobs WHERE id = %s AND locked_by = %s AND attempts = %s AND lease_until > now() FOR UPDATE",
            (job.id, worker_id, job.attempts),
        ).fetchone()
        is not None
    )


def complete_transcribe(job: Job, worker_id: str, transcript: str) -> bool:
    with db.connect() as conn:
        if not _still_owned(conn, job, worker_id):
            return False
        conn.execute(
            "UPDATE memories SET transcript = %s, status = 'transcribed', updated_at = now() WHERE id = %s",
            (transcript, job.memory_id),
        )
        conn.execute(
            "UPDATE jobs SET stage = 'enrich', attempts = 0, run_after = now(),"
            " lease_until = NULL, locked_by = NULL, last_error = NULL WHERE id = %s",
            (job.id,),
        )
    return True


def complete_enrich(job: Job, worker_id: str, enrichment: Enrichment, story_style: str) -> bool:
    with db.connect() as conn:
        if not _still_owned(conn, job, worker_id):
            return False
        conn.execute(
            "UPDATE memories SET title = %s, story = %s, emotions = %s, story_style = %s,"
            " status = 'ready', error = NULL, updated_at = now() WHERE id = %s",
            (enrichment.title, enrichment.story, enrichment.emotions, story_style, job.memory_id),
        )
        conn.execute("DELETE FROM jobs WHERE id = %s", (job.id,))
    return True


def backoff_seconds(attempts: int) -> float:
    """Exponential backoff with jitter: a random delay in [d/2, d], d = base * 2^(attempts-1), capped."""
    s = get_settings()
    delay = min(s.job_backoff_cap_s, s.job_backoff_base_s * 2 ** (attempts - 1))
    return delay * random.uniform(0.5, 1.0)


def fail(job: Job, worker_id: str, error: str, permanent: bool) -> str:
    """Record a failed attempt. Returns 'retrying', 'failed', or 'lost' (lease no longer ours)."""
    exhausted = job.attempts >= get_settings().job_max_attempts
    with db.connect() as conn:
        if not _still_owned(conn, job, worker_id):
            return "lost"
        if permanent or exhausted:
            reason = error if permanent else f"Gave up after {job.attempts} attempts: {error}"
            _dead_letter(conn, job, reason)
            return "failed"
        conn.execute(
            "UPDATE jobs SET run_after = now() + make_interval(secs => %s),"
            " lease_until = NULL, locked_by = NULL, last_error = %s WHERE id = %s",
            (backoff_seconds(job.attempts), error, job.id),
        )
    return "retrying"


def give_up(job: Job, worker_id: str) -> bool:
    """For a job claimed more times than allowed (its workers kept crashing or timing out)."""
    with db.connect() as conn:
        if not _still_owned(conn, job, worker_id):
            return False
        last = conn.execute("SELECT last_error FROM jobs WHERE id = %s", (job.id,)).fetchone()["last_error"]
        reason = f"Gave up after {job.attempts - 1} attempts at stage '{job.stage}'"
        _dead_letter(conn, job, f"{reason}: {last}" if last else f"{reason} (the worker stopped each time)")
    return True


def _dead_letter(conn: Connection, job: Job, reason: str) -> None:
    conn.execute(
        "UPDATE memories SET status = 'failed', error = %s, updated_at = now() WHERE id = %s",
        (reason, job.memory_id),
    )
    conn.execute("DELETE FROM jobs WHERE id = %s", (job.id,))
