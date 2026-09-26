# Memoir AI

Record a voice memory and Memoir AI turns it into a titled, tagged story you can browse later.

Started as a 2-day prototype in April 2025; now being rebuilt as a local-first memory engine.

## What it does today

1. Record audio in the browser, optionally attaching a photo or video.
2. The backend stores the media in Supabase Storage and transcribes the audio with AssemblyAI.
3. Gemini turns the transcript into a title and story, and tags it with up to three emotions from a fixed list.
4. The memory is saved to MongoDB and shown in a gallery.

## Tech stack

- **Frontend:** React, Tailwind CSS
- **Backend:** Python, FastAPI
- **Services:** MongoDB, Supabase Storage, AssemblyAI, Google Gemini

## Running locally

Create `backend/.env` with `MONGO_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `ASSEMBLYAI_API_KEY` and `GEMINI_API_KEY`.

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

`run_project.sh` starts both. The frontend expects the API at `http://localhost:8000`.

## License

MIT, see [LICENSE](LICENSE).
