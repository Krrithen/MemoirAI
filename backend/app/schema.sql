-- The whole schema. Tables are created if missing, never altered: while the project is
-- pre-release, change this file and reset the database (`docker compose down -v`).

-- Media is content-addressed: the same bytes are stored once.
CREATE TABLE IF NOT EXISTS media (
    sha256        TEXT PRIMARY KEY,
    content_type  TEXT NOT NULL,
    bytes         BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A memory is created 'pending' and filled in by the worker:
--   pending -> transcribed -> ready        (or failed, with a reason in `error`)
CREATE TABLE IF NOT EXISTS memories (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audio_sha256     TEXT NOT NULL REFERENCES media(sha256),
    video_sha256     TEXT REFERENCES media(sha256),
    image_sha256     TEXT REFERENCES media(sha256),
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'transcribed', 'ready', 'failed')),
    error            TEXT,
    failed_stage     TEXT,                  -- the stage a failed memory stopped at
    transcript       TEXT CHECK (length(btrim(transcript)) > 0),
    title            TEXT,
    story            TEXT,
    emotions         TEXT[] NOT NULL DEFAULT '{}',
    -- Which prompt wrote the story: 'creative' (may add atmosphere) or 'faithful' (adds nothing).
    story_style      TEXT,
    -- Client-supplied key: retrying the same upload returns the same memory.
    idempotency_key  TEXT UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- A story can only exist on top of a transcript, and 'ready' means everything is there.
    CONSTRAINT memories_story_needs_transcript CHECK (story IS NULL OR transcript IS NOT NULL),
    CONSTRAINT memories_ready_is_complete CHECK (
        status <> 'ready' OR (transcript IS NOT NULL AND title IS NOT NULL AND story IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS memories_created_at_idx ON memories (created_at DESC);

-- One job per unfinished memory; its stage advances until the memory is ready or failed.
CREATE TABLE IF NOT EXISTS jobs (
    id           BIGSERIAL PRIMARY KEY,
    memory_id    UUID NOT NULL UNIQUE REFERENCES memories(id) ON DELETE CASCADE,
    stage        TEXT NOT NULL CHECK (stage IN ('transcribe', 'enrich')),
    attempts     INT NOT NULL DEFAULT 0,       -- claims of the current stage, crashes included
    run_after    TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_until  TIMESTAMPTZ,                  -- set while a worker holds the job
    locked_by    TEXT,
    last_error   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_claimable_idx ON jobs (run_after, id);
