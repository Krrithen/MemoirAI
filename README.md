# Memoir AI

[![CI](https://github.com/Krrithen/MemoirAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Krrithen/MemoirAI/actions/workflows/ci.yml)

Record a voice memory and Memoir AI turns it into a titled, tagged story you can browse later. Everything runs on your own machine: no API keys, no cloud services.

Started as a 2-day prototype in April 2025; now being rebuilt as a local-first memory engine.

## What it does today

1. Record audio in the browser, optionally attaching a photo or video.
2. The upload is stored and queued, and the API answers immediately (`202`) with the memory in `pending`.
3. A background worker transcribes the audio locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
4. A local model served by [Ollama](https://ollama.com) (default `qwen3:8b`) retells the transcript as a short first-person story (adding atmosphere, but keeping every name, place, date and number as said), writes a title, and tags up to three emotions from a fixed list. Output is constrained to a JSON schema and validated.
5. The gallery shows the memory as processing, then ready. Media is stored on local disk under its SHA-256 hash; everything else lives in Postgres.

## How ingestion works

```
POST /api/memories ──► memories(status=pending) + jobs(stage=transcribe)   one transaction, 202
                                   │
        worker: claim (FOR UPDATE SKIP LOCKED + lease) ─► transcribe ─► pending → transcribed
                                   │                     enrich     ─► transcribed → ready
                                   └─ on error: retry with exponential backoff + jitter,
                                      after 5 attempts (or on bad input) → failed, with the reason
```

What it guarantees:

- **No duplicates on retry.** Sending the same upload again with the same `Idempotency-Key` header returns the same memory. The frontend sends one key per recording.
- **Crash-safe stages.** A job is leased, not deleted, while it runs, and the worker renews the lease every few minutes while a stage is still going. If a worker dies, the lease expires and another worker picks the job up. A stage's output, the memory's status and the job update commit in one transaction, and every write is fenced on the lease, so a worker that lost its lease can't overwrite the new owner's result. Stages run at least once; their writes are idempotent.
- **No story without a transcript.** Recordings with no speech fail straight away (no retries) with a clear reason. The database enforces it too: a story can't exist without a transcript, and `ready` means transcript, title and story are all present.
- **Failed memories can be retried** from the stage they failed at (`POST /api/memories/{id}/retry`, or the Retry button).
- **No orphaned media.** The worker garbage-collects stored files no memory references (after a 1-hour grace period), without racing uploads of the same bytes.

- **Workers ride out outages.** If Postgres goes away, the worker backs off (up to 30 s between tries) and resumes when it's back; temporary transcriber or model errors (network, model download, memory) are retried, while undecodable audio and silence fail straight away.
- **Durable media.** Files are fsynced before the atomic rename, and a truncated file is detected by size and rewritten.

What it doesn't: a single Postgres with no replication, no accounts (every memory is visible to whoever runs it), and at-least-once stages (a worker that loses its lease, e.g. a paused laptop, may repeat a stage; only the current lease holder's result is kept).

`GET /metrics` exposes queue depth by stage, retrying jobs, the oldest job's age, memories by status and failures by stage, in Prometheus format.

The original transcript is always stored and shown next to the story ("What you said"). Stories are creative by default; set `STORY_STYLE=faithful` for a light edit that adds nothing the speaker didn't say. How much each style adds is measured in [docs/results/faithfulness.md](docs/results/faithfulness.md); rerun with `uv run --project backend python eval/faithfulness/run.py --label <name>`.

## Tech stack

- **Frontend:** React, Tailwind CSS
- **Backend:** Python, FastAPI, Postgres (psycopg)
- **Models:** faster-whisper (speech to text), Ollama (story and tags)

## Running locally

Prerequisites: [uv](https://docs.astral.sh/uv/), Node 18+, Docker, and [Ollama](https://ollama.com/download). uv installs the right Python version itself.

```bash
# Model and database
ollama pull qwen3:8b
docker compose up -d

# Backend API (http://localhost:8000) and a worker, in two terminals
cd backend
uv sync
uv run uvicorn app.main:app --reload
uv run python -m app.pipeline.worker

# Frontend (http://localhost:3000)
cd frontend
npm install
npm start
```

The Whisper model (`small` by default) downloads on the first transcription and is cached after that. You can run several workers; each job is processed by one at a time. The schema lives in `backend/app/schema.sql` and is created on startup. While the project is pre-release it isn't migrated: after changing it, reset the database with `docker compose down -v`.

`GET /api/health` reports that the API process is up; `GET /api/ready` also checks the database (2 s timeout) and returns 503 if it's unreachable.

From `backend/`: `uv run pytest` runs the tests (needs `docker compose up -d`; they use a throwaway `memoir_test` database and fake models), and `uv run ruff check .` lints.

## Configuration

Every setting has a local default, so no `.env` is needed. Override with environment variables:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql://memoir:memoir@localhost:5433/memoir` |
| `MEDIA_DIR` | `data/media` |
| `OLLAMA_MODEL` | `qwen3:8b` |
| `WHISPER_MODEL` | `small` |
| `STORY_STYLE` | `creative` (or `faithful`) |
| `JOB_MAX_ATTEMPTS` / `JOB_LEASE_S` | `5` / `600` |
| `REACT_APP_API_URL` (frontend) | `http://localhost:8000` |

Hosted providers are optional and off by default, kept for comparing against the local path: set `TRANSCRIBER=assemblyai` with `ASSEMBLYAI_API_KEY`, or `LLM=gemini` with `GEMINI_API_KEY`, after `uv sync --extra hosted`.

## License

MIT, see [LICENSE](LICENSE).
