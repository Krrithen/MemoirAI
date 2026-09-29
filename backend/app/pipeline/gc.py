"""Media garbage collection: delete stored media that no memory references.

Safe against a concurrent upload of the same bytes:
- Rows are deleted and their files unlinked inside one transaction that holds the row
  locks. An upload of the same bytes upserts that row (ON CONFLICT DO UPDATE), so it
  waits for us, then re-inserts the row and rewrites the file if it's gone.
- If a memory started referencing the row in the meantime, the foreign key makes the
  DELETE fail, so a referenced file is never removed.
- Files on disk with no row are only removed after the grace period, so a file that's
  being written for a not-yet-committed upload is left alone.
"""

import logging
import time
from pathlib import Path

import psycopg

from app import db
from app.config import get_settings
from app.storage import media_path

logger = logging.getLogger(__name__)

GC_LOCK = 872_402  # only one worker collects at a time


def collect_garbage() -> dict:
    grace_s = get_settings().media_gc_grace_s
    try:
        deleted_rows, known = _collect_rows(grace_s)
    except psycopg.errors.ForeignKeyViolation:
        # A memory started using media we were about to delete; the whole round rolled back.
        logger.info("Media GC skipped a round: media became referenced while being collected")
        return {"skipped": True}
    if known is None:
        return {"skipped": True}

    orphan_files = _collect_orphan_files(known, grace_s)
    if deleted_rows or orphan_files:
        logger.info("Media GC removed %d unreferenced media and %d orphan files", len(deleted_rows), orphan_files)
    return {"skipped": False, "rows": len(deleted_rows), "orphan_files": orphan_files}


def _collect_rows(grace_s: int) -> tuple[list[str], set[str] | None]:
    """Delete unreferenced media rows and their files in one transaction. Returns (deleted, all known)."""
    with db.connect() as conn:
        if not conn.execute("SELECT pg_try_advisory_xact_lock(%s) AS ok", (GC_LOCK,)).fetchone()["ok"]:
            return [], None  # another worker is collecting
        deleted_rows = [
            r["sha256"]
            for r in conn.execute(
                """
                DELETE FROM media
                 WHERE created_at < now() - make_interval(secs => %s)
                   AND NOT EXISTS (
                        SELECT 1 FROM memories
                         WHERE media.sha256 IN (audio_sha256, video_sha256, image_sha256))
                RETURNING sha256
                """,
                (grace_s,),
            )
        ]
        for sha in deleted_rows:
            media_path(sha).unlink(missing_ok=True)
        known = {r["sha256"] for r in conn.execute("SELECT sha256 FROM media")}
    return deleted_rows, known


def _collect_orphan_files(known: set[str], grace_s: int) -> int:
    """Delete files on disk that have no media row and are older than the grace period."""
    orphan_files = 0
    root = Path(get_settings().media_dir)
    cutoff = time.time() - grace_s
    if root.exists():
        for path in root.glob("*/*"):
            if path.is_file() and path.name not in known and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                orphan_files += 1
    return orphan_files
