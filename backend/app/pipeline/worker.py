"""Background worker: claims jobs and runs the transcribe and enrich stages.

Run with:  uv run python -m app.pipeline.worker
Several can run at once; the queue makes sure each job is processed by one at a time.
"""

import logging
import mimetypes
import os
import signal
import socket
import threading
import time
import uuid
from collections.abc import Callable

import psycopg

from app import db
from app.config import get_settings
from app.pipeline import gc, queue
from app.providers import get_llm, get_transcriber
from app.providers.transcriber import TranscriptionFailed
from app.storage import media_path

logger = logging.getLogger(__name__)


def _transcribe(job: queue.Job, worker_id: str) -> None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT m.audio_sha256, media.content_type FROM memories m"
            " JOIN media ON media.sha256 = m.audio_sha256 WHERE m.id = %s",
            (job.memory_id,),
        ).fetchone()
    audio = media_path(row["audio_sha256"]).read_bytes()
    suffix = mimetypes.guess_extension(row["content_type"].split(";")[0]) or ""
    transcript = get_transcriber().transcribe(audio, suffix)
    if not queue.complete_transcribe(job, worker_id, transcript):
        logger.warning("Lost the lease on job %s during transcription; result discarded", job.id)


def _enrich(job: queue.Job, worker_id: str) -> None:
    with db.connect() as conn:
        transcript = conn.execute("SELECT transcript FROM memories WHERE id = %s", (job.memory_id,)).fetchone()[
            "transcript"
        ]
    enrichment = get_llm().enrich(transcript)
    if not queue.complete_enrich(job, worker_id, enrichment, get_settings().story_style):
        logger.warning("Lost the lease on job %s during enrichment; result discarded", job.id)


STAGES = {"transcribe": _transcribe, "enrich": _enrich}


class LeaseKeeper:
    """Heartbeats a job's lease from a background thread while its stage runs.

    Without it, a stage that ran longer than the lease (a long recording, a slow model)
    would be claimed by a second worker and run twice.
    """

    def __init__(self, job: queue.Job, worker_id: str):
        self.job = job
        self.worker_id = worker_id
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"lease-{job.id}", daemon=True)

    def _run(self) -> None:
        interval = get_settings().job_lease_s / 3
        while not self._stop.wait(interval):
            try:
                if not queue.heartbeat(self.job, self.worker_id):
                    logger.warning("Lost the lease on job %s; its result will be discarded", self.job.id)
                    return
            except Exception as e:  # a missed beat is fine; the next one may succeed
                logger.warning("Lease heartbeat for job %s failed: %s", self.job.id, e)

    def __enter__(self) -> "LeaseKeeper":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join()


def process(job: queue.Job, worker_id: str) -> None:
    started = time.perf_counter()
    try:
        with LeaseKeeper(job, worker_id):
            STAGES[job.stage](job, worker_id)
        outcome = "done"
    except TranscriptionFailed as e:
        # Bad input (no speech, undecodable audio): retrying won't help.
        outcome = queue.fail(job, worker_id, str(e), permanent=True)
    except Exception as e:
        outcome = queue.fail(job, worker_id, f"{type(e).__name__}: {e}", permanent=False)
        if outcome == "retrying":
            logger.warning("Job %s stage=%s attempt %d failed, will retry: %s", job.id, job.stage, job.attempts, e)
    logger.info(
        "job=%s memory=%s stage=%s attempt=%d outcome=%s seconds=%.2f",
        job.id,
        job.memory_id,
        job.stage,
        job.attempts,
        outcome,
        time.perf_counter() - started,
    )


def run_once(worker_id: str) -> bool:
    """Claim and process one job. Returns False when nothing was due."""
    job = queue.claim(worker_id)
    if job is None:
        return False
    if job.attempts > get_settings().job_max_attempts:
        queue.give_up(job, worker_id)
        logger.error("job=%s memory=%s gave up after repeated crashes or timeouts", job.id, job.memory_id)
    else:
        process(job, worker_id)
    return True


def run_forever(worker_id: str, should_stop: Callable[[], bool], sleep: Callable[[float], None] = time.sleep) -> None:
    """Process jobs until should_stop() is true. Never dies on a database outage or a bug
    in one iteration: database errors back off (1s, 2s, 4s... up to worker_db_retry_cap_s),
    anything else is logged and the loop carries on."""
    settings = get_settings()
    next_gc = 0.0
    db_failures = 0
    while not should_stop():
        try:
            if time.monotonic() >= next_gc:
                gc.collect_garbage()
                next_gc = time.monotonic() + settings.media_gc_interval_s
            worked = run_once(worker_id)
            db_failures = 0
        except psycopg.OperationalError as e:
            db_failures += 1
            delay = min(settings.worker_db_retry_cap_s, 2.0 ** (db_failures - 1))
            logger.error("Database unavailable (%s); retrying in %.0fs", e, delay)
            sleep(delay)
            continue
        except Exception:
            logger.exception("Unexpected error in the worker loop; continuing")
            sleep(settings.worker_poll_s)
            continue
        if not worked:
            sleep(settings.worker_poll_s)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"

    stopping = False

    def stop(signum, _frame):
        nonlocal stopping
        stopping = True
        logger.info("Received %s; finishing the current job, then exiting", signal.Signals(signum).name)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    # Wait for the database rather than crashing if the worker starts first.
    while not stopping:
        try:
            db.init_schema()
            break
        except psycopg.OperationalError as e:
            logger.error("Database unavailable at startup (%s); retrying in 2s", e)
            time.sleep(2)

    logger.info("Worker %s started", worker_id)
    run_forever(worker_id, lambda: stopping)
    db.close_pool()
    logger.info("Worker %s stopped", worker_id)


if __name__ == "__main__":
    main()
