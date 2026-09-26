# Memoir AI

Record a voice memory and Memoir AI turns it into a titled, tagged story you can browse later. Everything runs on your own machine: no API keys, no cloud services.

Started as a 2-day prototype in April 2025; now being rebuilt as a local-first memory engine.

## What it does today

1. Record audio in the browser, optionally attaching a photo or video.
2. The backend transcribes the audio locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. A local model served by [Ollama](https://ollama.com) (default `qwen3:8b`) writes a title and story from the transcript and tags it with up to three emotions from a fixed list. Output is constrained to a JSON schema and validated.
4. Media is stored on local disk under its SHA-256 hash; the memory is saved to Postgres and shown in a gallery.

If the recording has no speech, the request fails with a clear error and nothing is stored. A story is never generated without a transcript.

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

# Backend (http://localhost:8000)
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend (http://localhost:3000)
cd frontend
npm install
npm start
```

The Whisper model (`small` by default) downloads on the first transcription and is cached after that.

`GET /api/health` reports that the API process is up; `GET /api/ready` also checks the database (2 s timeout) and returns 503 if it's unreachable.

Lint with `uv run ruff check .` from `backend/`.

## Configuration

Every setting has a local default, so no `.env` is needed. Override with environment variables:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql://memoir:memoir@localhost:5433/memoir` |
| `MEDIA_DIR` | `data/media` |
| `OLLAMA_MODEL` | `qwen3:8b` |
| `WHISPER_MODEL` | `small` |
| `REACT_APP_API_URL` (frontend) | `http://localhost:8000` |

Hosted providers are optional and off by default, kept for comparing against the local path: set `TRANSCRIBER=assemblyai` with `ASSEMBLYAI_API_KEY`, or `LLM=gemini` with `GEMINI_API_KEY`, after `uv sync --extra hosted`.

## License

MIT, see [LICENSE](LICENSE).
