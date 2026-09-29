-- Asynchronous ingestion: memories are created 'pending' and filled in by the worker.
--   pending -> transcribed -> ready        (or failed, with a reason in `error`)

ALTER TABLE memories
    ALTER COLUMN transcript DROP NOT NULL,
    ALTER COLUMN title DROP NOT NULL,
    ALTER COLUMN story DROP NOT NULL;

-- Rows that existed before this migration were created synchronously and are complete.
ALTER TABLE memories ADD COLUMN status TEXT NOT NULL DEFAULT 'ready'
    CHECK (status IN ('pending', 'transcribed', 'ready', 'failed'));
ALTER TABLE memories ALTER COLUMN status SET DEFAULT 'pending';

ALTER TABLE memories
    ADD COLUMN error TEXT,
    -- Client-supplied key: retrying the same upload returns the same memory.
    ADD COLUMN idempotency_key TEXT UNIQUE,
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- A story can only exist on top of a transcript, and 'ready' means everything is there.
    ADD CONSTRAINT memories_story_needs_transcript CHECK (story IS NULL OR transcript IS NOT NULL),
    ADD CONSTRAINT memories_ready_is_complete CHECK (
        status <> 'ready' OR (transcript IS NOT NULL AND title IS NOT NULL AND story IS NOT NULL)
    );

-- One job per unfinished memory; its stage advances until the memory is ready or failed.
CREATE TABLE jobs (
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

CREATE INDEX jobs_claimable_idx ON jobs (run_after, id);
