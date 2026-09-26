import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import db
from app.config import get_settings
from app.providers import get_llm, get_transcriber
from app.providers.llm import EnrichmentFailed
from app.providers.transcriber import TranscriptionFailed
from app.storage import media_path, read_upload, write_media

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_schema()
    yield


app = FastAPI(title="Memoir AI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_api(row: dict, request: Request) -> dict:
    def url(sha: str | None) -> str:
        return str(request.url_for("get_media", sha256=sha)) if sha else ""

    return {
        "id": str(row["id"]),
        "audioUrl": url(row["audio_sha256"]),
        "videoUrl": url(row["video_sha256"]),
        "imageUrl": url(row["image_sha256"]),
        "title": row["title"],
        "story": row["story"],
        "tags": row["emotions"],
        "timestamp": row["created_at"].isoformat(),
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Memoir AI API is running"}


@app.get("/api/memories")
def get_all_memories(request: Request):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
    return {"memories": [_to_api(r, request) for r in rows]}


# Sync handlers: FastAPI runs them in a threadpool, so slow model calls
# don't block the event loop for other requests.
@app.post("/api/memories")
def create_memory(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
):
    if not audio:
        raise HTTPException(status_code=400, detail="An audio recording is required")

    audio_up = read_upload(audio, settings.max_audio_bytes)
    video_up = read_upload(video, settings.max_video_bytes) if video else None
    image_up = read_upload(image, settings.max_image_bytes) if image else None

    # Run the model stages before storing anything, so a failure leaves no
    # partial memory and no orphaned media behind.
    try:
        transcript = get_transcriber().transcribe(audio_up.data, Path(audio_up.filename).suffix)
    except TranscriptionFailed as e:
        logger.warning("Transcription failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    logger.info("Transcribed %d characters", len(transcript))

    try:
        enrichment = get_llm().enrich(transcript)
    except EnrichmentFailed as e:
        logger.error("Enrichment failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

    uploads = [u for u in (audio_up, video_up, image_up) if u]
    for u in uploads:
        write_media(u)

    with db.connect() as conn:
        for u in uploads:
            conn.execute(
                "INSERT INTO media (sha256, content_type, bytes) VALUES (%s, %s, %s)"
                " ON CONFLICT (sha256) DO NOTHING",
                (u.sha256, u.content_type, len(u.data)),
            )
        row = conn.execute(
            "INSERT INTO memories (audio_sha256, video_sha256, image_sha256, transcript, title, story, emotions)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (
                audio_up.sha256,
                video_up.sha256 if video_up else None,
                image_up.sha256 if image_up else None,
                transcript,
                enrichment.title,
                enrichment.story,
                enrichment.emotions,
            ),
        ).fetchone()

    logger.info("Stored memory %s", row["id"])
    return _to_api(row, request)


@app.get("/api/media/{sha256}", name="get_media")
def get_media(sha256: str = PathParam(pattern="^[0-9a-f]{64}$")):
    with db.connect() as conn:
        row = conn.execute("SELECT content_type FROM media WHERE sha256 = %s", (sha256,)).fetchone()
    path = media_path(sha256)
    if not row or not path.exists():
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path, media_type=row["content_type"])
