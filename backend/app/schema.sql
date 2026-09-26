-- Media is content-addressed: the same bytes are stored once.
CREATE TABLE IF NOT EXISTS media (
    sha256        TEXT PRIMARY KEY,
    content_type  TEXT NOT NULL,
    bytes         BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS memories (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audio_sha256  TEXT NOT NULL REFERENCES media(sha256),
    video_sha256  TEXT REFERENCES media(sha256),
    image_sha256  TEXT REFERENCES media(sha256),
    transcript    TEXT NOT NULL CHECK (length(btrim(transcript)) > 0),
    title         TEXT NOT NULL,
    story         TEXT NOT NULL,
    emotions      TEXT[] NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memories_created_at_idx ON memories (created_at DESC);
