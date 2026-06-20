-- AtelierAI — Postgres-схема для production (NEW, для перехода с sqlite).
-- При миграции меняется только db.py (asyncpg); остальные модули не трогаются.

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    status      VARCHAR(20) DEFAULT 'pending'
                CHECK (status IN ('pending','analyzed','generated','exported'))
);

CREATE TABLE IF NOT EXISTS skirt_analyses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID REFERENCES sessions(id) ON DELETE CASCADE,
    image_key    TEXT NOT NULL,
    skirt_type   VARCHAR(20) NOT NULL
                 CHECK (skirt_type IN ('straight','pencil','a_line','half_circle','full_circle')),
    confidence   DECIMAL(3,2),
    ai_response  JSONB NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pattern_jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE,
    analysis_id   UUID REFERENCES skirt_analyses(id),
    measurements  JSONB NOT NULL,
    skirt_type    VARCHAR(20) NOT NULL,
    svg_key       TEXT,
    pdf_key       TEXT,
    pieces        JSONB,
    status        VARCHAR(20) DEFAULT 'completed',
    error_msg     TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analyses_session ON skirt_analyses(session_id);
CREATE INDEX IF NOT EXISTS idx_jobs_session ON pattern_jobs(session_id);
