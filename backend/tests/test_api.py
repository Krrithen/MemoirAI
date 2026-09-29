import uuid

from app import main
from tests.conftest import TRANSCRIPT, count, drain, job_row, memory_row

AUDIO = {"audio": ("rec.webm", b"fake-audio-bytes", "audio/webm")}
OTHER_AUDIO = {"audio": ("rec.webm", b"different-audio", "audio/webm")}


def test_health_is_static(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_ready_when_database_up(client):
    resp = client.get("/api/ready")
    assert resp.status_code == 200
    assert resp.json()["database"] == "ok"


def test_ready_returns_503_when_database_down(client, monkeypatch):
    def down():
        raise OSError("connection refused")

    monkeypatch.setattr("app.db.ping", down)
    assert client.get("/api/ready").status_code == 503


def test_upload_returns_202_pending_without_running_models(client, transcriber, llm):
    resp = client.post("/api/memories", files={**AUDIO, "image": ("p.jpg", b"img-bytes", "image/jpeg")})

    assert resp.status_code == 202
    memory = resp.json()
    assert memory["status"] == "pending"
    assert memory["title"] is None and memory["story"] is None
    assert memory["audioUrl"] and memory["imageUrl"] and memory["videoUrl"] == ""
    assert transcriber.calls == 0 and llm.calls == 0
    assert job_row(memory["id"])["stage"] == "transcribe"


def test_memory_is_ready_after_the_worker_runs(client):
    memory = client.post("/api/memories", files=AUDIO).json()
    drain()

    ready = client.get(f"/api/memories/{memory['id']}").json()
    assert ready["status"] == "ready"
    assert ready["title"] == "Apple Pie in Lisbon"
    assert ready["tags"] == ["Joy", "Love"]
    assert ready["transcript"] == TRANSCRIPT
    assert ready["storyStyle"] == "creative"
    assert [m["id"] for m in client.get("/api/memories").json()["memories"]] == [memory["id"]]


def test_unknown_memory_is_404(client):
    assert client.get(f"/api/memories/{uuid.uuid4()}").status_code == 404


def test_malformed_memory_id_is_422(client):
    assert client.get("/api/memories/not-a-uuid").status_code == 422


def test_audio_is_required(client):
    resp = client.post("/api/memories", files={"video": ("v.mp4", b"video", "video/mp4")})
    assert resp.status_code == 400
    assert count("memories") == 0


def test_oversize_upload_rejected(client, monkeypatch):
    monkeypatch.setattr(main.settings, "max_audio_bytes", 4)
    resp = client.post("/api/memories", files={"audio": ("rec.webm", b"12345", "audio/webm")})
    assert resp.status_code == 413
    assert count("memories") == 0


def test_same_idempotency_key_returns_the_same_memory(client):
    headers = {"Idempotency-Key": "upload-1"}
    first = client.post("/api/memories", files=AUDIO, headers=headers)
    second = client.post("/api/memories", files=AUDIO, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert count("memories") == 1
    assert count("jobs") == 1
    assert count("media") == 1


def test_idempotency_key_reused_for_different_audio_is_rejected(client):
    headers = {"Idempotency-Key": "upload-1"}
    client.post("/api/memories", files=AUDIO, headers=headers)
    resp = client.post("/api/memories", files=OTHER_AUDIO, headers=headers)

    assert resp.status_code == 422
    assert count("memories") == 1
    assert count("media") == 1  # the rejected upload's media row was rolled back


def test_same_audio_without_a_key_is_two_memories_sharing_one_file(client):
    client.post("/api/memories", files=AUDIO)
    client.post("/api/memories", files=AUDIO)
    assert count("memories") == 2
    assert count("media") == 1


def test_retry_requeues_a_failed_memory(client, transcriber):
    transcriber.text = ""
    memory = client.post("/api/memories", files=AUDIO).json()
    drain()
    assert memory_row(memory["id"])["status"] == "failed"

    transcriber.text = TRANSCRIPT
    resp = client.post(f"/api/memories/{memory['id']}/retry")
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"
    drain()
    assert memory_row(memory["id"])["status"] == "ready"


def test_retry_resumes_at_enrich_when_transcript_exists(client, llm):
    from app.providers.llm import EnrichmentFailed

    llm.result = EnrichmentFailed("model down")
    memory = client.post("/api/memories", files=AUDIO).json()
    with main.db.connect() as conn:  # force the dead-letter path quickly
        conn.execute("UPDATE memories SET status = 'failed', transcript = %s WHERE id = %s", (TRANSCRIPT, memory["id"]))
        conn.execute("DELETE FROM jobs")

    resp = client.post(f"/api/memories/{memory['id']}/retry")
    assert resp.json()["status"] == "transcribed"
    assert job_row(memory["id"])["stage"] == "enrich"


def test_only_failed_memories_can_be_retried(client):
    memory = client.post("/api/memories", files=AUDIO).json()
    assert client.post(f"/api/memories/{memory['id']}/retry").status_code == 409
    assert client.post(f"/api/memories/{uuid.uuid4()}/retry").status_code == 404


def test_media_is_served_with_its_content_type(client):
    memory = client.post("/api/memories", files=AUDIO).json()
    resp = client.get(memory["audioUrl"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/webm"
    assert resp.content == b"fake-audio-bytes"


def test_unknown_media_hash_is_404(client):
    assert client.get("/api/media/" + "0" * 64).status_code == 404


def test_malformed_media_hash_is_rejected(client):
    assert client.get("/api/media/not-a-hash").status_code == 422


def test_metrics_report_queue_depth_and_statuses(client, transcriber):
    client.post("/api/memories", files=AUDIO)
    client.post("/api/memories", files=OTHER_AUDIO)
    transcriber.text = ""
    drain()  # both fail at transcribe (no speech)
    client.post("/api/memories", files=AUDIO)

    body = client.get("/metrics").text
    assert 'memoir_queue_jobs{stage="transcribe",state="waiting"} 1' in body
    assert 'memoir_memories{status="failed"} 2' in body
    assert 'memoir_failed_memories{stage="transcribe"} 2' in body
    assert "memoir_queue_oldest_job_age_seconds" in body
