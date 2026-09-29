import os
import time

from app import db
from app.pipeline import gc
from app.storage import Upload, media_path, write_media
from tests.conftest import count


def age_media(sha: str | None = None, seconds: int = 7200) -> None:
    with db.connect() as conn:
        conn.execute(
            "UPDATE media SET created_at = now() - make_interval(secs => %s) WHERE %s::text IS NULL OR sha256 = %s",
            (seconds, sha, sha),
        )


def add_unreferenced_media(data: bytes) -> str:
    upload = Upload(data=data, content_type="audio/webm", filename="x.webm")
    sha = write_media(upload)
    with db.connect() as conn:
        conn.execute("INSERT INTO media (sha256, content_type, bytes) VALUES (%s, 'audio/webm', %s)", (sha, len(data)))
    return sha


def test_old_unreferenced_media_is_deleted_with_its_file(client):
    sha = add_unreferenced_media(b"orphaned upload")
    age_media(sha)

    result = gc.collect_garbage()
    assert result["rows"] == 1
    assert count("media") == 0
    assert not media_path(sha).exists()


def test_referenced_media_is_kept(client):
    memory = client.post("/api/memories", files={"audio": ("r.webm", b"kept audio", "audio/webm")}).json()
    age_media()

    assert gc.collect_garbage()["rows"] == 0
    assert client.get(memory["audioUrl"]).status_code == 200


def test_recent_unreferenced_media_is_kept(client):
    sha = add_unreferenced_media(b"just uploaded")
    assert gc.collect_garbage()["rows"] == 0
    assert media_path(sha).exists()


def test_old_orphan_file_without_a_row_is_deleted(client):
    sha = write_media(Upload(data=b"file with no row", content_type="audio/webm", filename="x"))
    path = media_path(sha)
    old = time.time() - 7200
    os.utime(path, (old, old))

    assert gc.collect_garbage()["orphan_files"] == 1
    assert not path.exists()


def test_reupload_after_gc_restores_the_file(client):
    data = b"collected then uploaded again"
    sha = add_unreferenced_media(data)
    age_media(sha)
    gc.collect_garbage()
    assert not media_path(sha).exists()

    memory = client.post("/api/memories", files={"audio": ("r.webm", data, "audio/webm")}).json()
    assert client.get(memory["audioUrl"]).content == data


def test_gc_never_deletes_media_that_a_concurrent_upload_starts_using(client):
    """Race: a memory referencing old, unreferenced media commits while GC is deleting it."""
    import threading

    import psycopg

    from tests.conftest import TEST_URL

    sha = add_unreferenced_media(b"about to be reused")
    age_media(sha)

    with psycopg.connect(TEST_URL) as uploader:
        # The upload's transaction references the media first (and holds the FK lock)...
        uploader.execute("INSERT INTO memories (audio_sha256) VALUES (%s)", (sha,))
        results = []
        collector = threading.Thread(target=lambda: results.append(gc.collect_garbage()))
        collector.start()  # ...GC's DELETE blocks on that lock
        collector.join(timeout=0.5)
        assert collector.is_alive()
        uploader.commit()  # the upload commits; GC must not delete the now-referenced row
        collector.join(timeout=5)

    assert results and (results[0].get("skipped") or results[0]["rows"] == 0)
    assert count("media") == 1
    assert media_path(sha).exists()
