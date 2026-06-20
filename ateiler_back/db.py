"""
AtelierAI — DB layer (NEW FILE, additive).

Для MVP — stdlib sqlite3 (без внешних зависимостей, работает сразу).
Схема совпадает по смыслу с Postgres-версией (schema.sql) — при переходе на
Postgres меняется только этот файл (asyncpg), остальные модули не трогаются.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

DB_PATH = "/data/skirt/atelier.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS skirt_analyses (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    image_key    TEXT NOT NULL,
    skirt_type   TEXT NOT NULL,
    confidence   REAL,
    ai_response  TEXT NOT NULL,           -- JSON
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pattern_jobs (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    analysis_id   TEXT,
    measurements  TEXT NOT NULL,          -- JSON
    skirt_type    TEXT NOT NULL,
    svg_key       TEXT,
    pdf_key       TEXT,
    pieces        TEXT,                   -- JSON list of names
    status        TEXT NOT NULL DEFAULT 'queued',
    error_msg     TEXT,
    created_at    TEXT NOT NULL,
    completed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_session ON skirt_analyses(session_id);
CREATE INDEX IF NOT EXISTS idx_jobs_session ON pattern_jobs(session_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(SCHEMA)


def create_session() -> str:
    sid = str(uuid.uuid4())
    with _conn() as c:
        c.execute("INSERT INTO sessions(id, created_at, status) VALUES (?,?,?)",
                  (sid, _now(), "pending"))
    return sid


def save_analysis(session_id: str, image_key: str, ai: Dict) -> str:
    aid = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            """INSERT INTO skirt_analyses
               (id, session_id, image_key, skirt_type, confidence, ai_response, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (aid, session_id, image_key, ai["skirt_type"],
             float(ai.get("confidence", 0)), json.dumps(ai, ensure_ascii=False), _now()))
        c.execute("UPDATE sessions SET status='analyzed' WHERE id=?", (session_id,))
    return aid


def get_latest_analysis(session_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute(
            """SELECT * FROM skirt_analyses WHERE session_id=?
               ORDER BY created_at DESC LIMIT 1""", (session_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["ai_response"] = json.loads(d["ai_response"])
    return d


def save_job(session_id: str, analysis_id: Optional[str], measurements: Dict,
             skirt_type: str, svg_key: str, pdf_key: str, pieces: list,
             job_id: Optional[str] = None) -> str:
    jid = job_id or str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            """INSERT INTO pattern_jobs
               (id, session_id, analysis_id, measurements, skirt_type,
                svg_key, pdf_key, pieces, status, created_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (jid, session_id, analysis_id, json.dumps(measurements, ensure_ascii=False),
             skirt_type, svg_key, pdf_key, json.dumps(pieces, ensure_ascii=False),
             "completed", _now(), _now()))
        c.execute("UPDATE sessions SET status='generated' WHERE id=?", (session_id,))
    return jid


def get_job(job_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM pattern_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["measurements"] = json.loads(d["measurements"])
    d["pieces"] = json.loads(d["pieces"]) if d["pieces"] else []
    return d
