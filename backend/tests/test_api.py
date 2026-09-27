from app import db, main
from app.providers.llm import EnrichmentFailed
from tests.conftest import TRANSCRIPT, count

AUDIO = {"audio": ("rec.webm", b"fake-audio-bytes", "audio/webm")}


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


def test_create_memory_stores_and_lists_it(client, transcriber, llm):
    resp = client.post("/api/memories", files={**AUDIO, "image": ("p.jpg", b"img-bytes", "image/jpeg")})

    assert resp.status_code == 200
    memory = resp.json()
    assert memory["title"] == "Apple Pie in Lisbon"
    assert memory["tags"] == ["Joy", "Love"]
    assert memory["transcript"] == TRANSCRIPT
    assert memory["storyStyle"] == "creative"
    assert memory["audioUrl"] and memory["imageUrl"] and memory["videoUrl"] == ""

    listed = client.get("/api/memories").json()["memories"]
    assert [m["id"] for m in listed] == [memory["id"]]

    with db.connect() as conn:
        row = conn.execute("SELECT transcript FROM memories").fetchone()
    assert row["transcript"] == TRANSCRIPT


def test_audio_is_required(client, transcriber):
    resp = client.post("/api/memories", files={"video": ("v.mp4", b"video", "video/mp4")})
    assert resp.status_code == 400
    assert transcriber.calls == 0
    assert count("memories") == 0


def test_oversize_upload_rejected(client, transcriber, monkeypatch):
    monkeypatch.setattr(main.settings, "max_audio_bytes", 4)
    resp = client.post("/api/memories", files={"audio": ("rec.webm", b"12345", "audio/webm")})
    assert resp.status_code == 413
    assert transcriber.calls == 0


def test_empty_transcript_never_produces_a_story(client, transcriber, llm):
    """Regression: the original app invented a story when transcription failed."""
    transcriber.text = ""
    resp = client.post("/api/memories", files=AUDIO)

    assert resp.status_code == 422
    assert llm.calls == 0
    assert count("memories") == 0
    assert count("media") == 0


def test_enrichment_failure_stores_nothing(client, llm):
    llm.result = EnrichmentFailed("model returned invalid output twice")
    resp = client.post("/api/memories", files=AUDIO)

    assert resp.status_code == 502
    assert count("memories") == 0
    assert count("media") == 0


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


def test_same_audio_twice_is_stored_once(client):
    client.post("/api/memories", files=AUDIO)
    client.post("/api/memories", files=AUDIO)
    assert count("memories") == 2
    assert count("media") == 1
