import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app import db
from app.config import get_settings
from app.pipeline import queue
from app.storage import media_path, read_upload, write_media

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_schema()
    yield
    db.close_pool()


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
        "status": row["status"],
        "error": row["error"],
        "audioUrl": url(row["audio_sha256"]),
        "videoUrl": url(row["video_sha256"]),
        "imageUrl": url(row["image_sha256"]),
        "title": row["title"],
        "story": row["story"],
        "transcript": row["transcript"],
        "storyStyle": row["story_style"],
        "tags": row["emotions"],
        "timestamp": row["created_at"].isoformat(),
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Memoir AI API is running"}


@app.get("/api/ready")
def readiness_check():
    try:
        db.ping()
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        return JSONResponse({"status": "unavailable", "database": "down"}, status_code=503)
    return {"status": "ready", "database": "ok"}


STAGES = ("transcribe", "enrich")
STATUSES = ("pending", "transcribed", "ready", "failed")


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Queue and pipeline health in Prometheus text format."""
    with db.connect() as conn:
        jobs = {
            (r["stage"], r["state"]): r["n"]
            for r in conn.execute(
                "SELECT stage, CASE WHEN lease_until > now() THEN 'running' ELSE 'waiting' END AS state,"
                " count(*) AS n FROM jobs GROUP BY 1, 2"
            )
        }
        retrying = {
            r["stage"]: r["n"]
            for r in conn.execute("SELECT stage, count(*) AS n FROM jobs WHERE last_error IS NOT NULL GROUP BY 1")
        }
        oldest = conn.execute(
            "SELECT coalesce(extract(epoch FROM now() - min(created_at)), 0) AS s FROM jobs"
        ).fetchone()["s"]
        statuses = {r["status"]: r["n"] for r in conn.execute("SELECT status, count(*) AS n FROM memories GROUP BY 1")}
        failed = {
            r["failed_stage"]: r["n"]
            for r in conn.execute("SELECT failed_stage, count(*) AS n FROM memories WHERE status = 'failed' GROUP BY 1")
        }

    lines = [
        "# HELP memoir_queue_jobs Jobs in the queue, by stage and whether a worker holds them.",
        "# TYPE memoir_queue_jobs gauge",
        *(
            f'memoir_queue_jobs{{stage="{stage}",state="{state}"}} {jobs.get((stage, state), 0)}'
            for stage in STAGES
            for state in ("waiting", "running")
        ),
        "# HELP memoir_queue_retrying_jobs Jobs whose last attempt failed and that are waiting to retry.",
        "# TYPE memoir_queue_retrying_jobs gauge",
        *(f'memoir_queue_retrying_jobs{{stage="{stage}"}} {retrying.get(stage, 0)}' for stage in STAGES),
        "# HELP memoir_queue_oldest_job_age_seconds Age of the oldest unfinished job (0 when the queue is empty).",
        "# TYPE memoir_queue_oldest_job_age_seconds gauge",
        f"memoir_queue_oldest_job_age_seconds {float(oldest):.3f}",
        "# HELP memoir_memories Memories by status.",
        "# TYPE memoir_memories gauge",
        *(f'memoir_memories{{status="{status}"}} {statuses.get(status, 0)}' for status in STATUSES),
        "# HELP memoir_failed_memories Failed memories by the stage they failed at.",
        "# TYPE memoir_failed_memories gauge",
        *(f'memoir_failed_memories{{stage="{stage}"}} {failed.get(stage, 0)}' for stage in STAGES),
    ]
    return "\n".join(lines) + "\n"


@app.get("/api/memories")
def get_all_memories(request: Request):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
    return {"memories": [_to_api(r, request) for r in rows]}


def _get_memory(memory_id: UUID) -> dict:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = %s", (memory_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    return row


@app.get("/api/memories/{memory_id}")
def get_memory(memory_id: UUID, request: Request):
    return _to_api(_get_memory(memory_id), request)


@app.post("/api/memories", status_code=202)
def create_memory(
    request: Request,
    audio: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    idempotency_key: str | None = Header(None, max_length=200),
):
    """Store the upload and queue it for the worker; returns 202 with the memory in 'pending'.

    With an Idempotency-Key header, retrying the same upload returns the same memory (200)
    instead of creating a second one.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="An audio recording is required")

    audio_up = read_upload(audio, settings.max_audio_bytes)
    video_up = read_upload(video, settings.max_video_bytes) if video else None
    image_up = read_upload(image, settings.max_image_bytes) if image else None
    uploads = [u for u in (audio_up, video_up, image_up) if u]

    with db.connect() as conn:
        for u in uploads:
            # DO UPDATE (not DO NOTHING) locks the row, so media GC can't delete it under us.
            conn.execute(
                "INSERT INTO media (sha256, content_type, bytes) VALUES (%s, %s, %s)"
                " ON CONFLICT (sha256) DO UPDATE SET sha256 = EXCLUDED.sha256",
                (u.sha256, u.content_type, len(u.data)),
            )
            write_media(u)

        row = conn.execute(
            "INSERT INTO memories (audio_sha256, video_sha256, image_sha256, idempotency_key)"
            " VALUES (%s, %s, %s, %s) ON CONFLICT (idempotency_key) DO NOTHING RETURNING *",
            (
                audio_up.sha256,
                video_up.sha256 if video_up else None,
                image_up.sha256 if image_up else None,
                idempotency_key,
            ),
        ).fetchone()

        if row is None:  # this key was used before
            existing = conn.execute("SELECT * FROM memories WHERE idempotency_key = %s", (idempotency_key,)).fetchone()
            if existing["audio_sha256"] != audio_up.sha256:
                raise HTTPException(
                    status_code=422, detail="Idempotency-Key was already used for a different recording"
                )
            return JSONResponse(_to_api(existing, request), status_code=200)

        queue.enqueue(conn, row["id"])

    logger.info("Queued memory %s", row["id"])
    return _to_api(row, request)


@app.post("/api/memories/{memory_id}/retry", status_code=202)
def retry_memory(memory_id: UUID, request: Request):
    """Re-queue a failed memory from the stage it failed at."""
    with db.connect() as conn:
        row = conn.execute(
            "UPDATE memories SET status = CASE WHEN transcript IS NULL THEN 'pending' ELSE 'transcribed' END,"
            " error = NULL, failed_stage = NULL, updated_at = now() WHERE id = %s AND status = 'failed' RETURNING *",
            (memory_id,),
        ).fetchone()
        if row is None:
            _get_memory(memory_id)  # 404 if it doesn't exist
            raise HTTPException(status_code=409, detail="Only failed memories can be retried")
        queue.enqueue(conn, row["id"], "transcribe" if row["transcript"] is None else "enrich")
    return _to_api(row, request)


@app.get("/api/media/{sha256}", name="get_media")
def get_media(sha256: str = PathParam(pattern="^[0-9a-f]{64}$")):
    with db.connect() as conn:
        row = conn.execute("SELECT content_type FROM media WHERE sha256 = %s", (sha256,)).fetchone()
    path = media_path(sha256)
    if not row or not path.exists():
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path, media_type=row["content_type"])
