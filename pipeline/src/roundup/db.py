"""SQLite storage: the pipeline's source of truth (data/roundup.db, committed to git)."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from roundup.config import DB_PATH
from roundup.models import Paper

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id             TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL,
    title          TEXT NOT NULL,
    authors        TEXT NOT NULL,          -- JSON list
    abstract       TEXT,
    url            TEXT NOT NULL,
    published_date TEXT,                   -- YYYY-MM-DD
    paywalled      INTEGER NOT NULL,
    fetched_at     TEXT NOT NULL,
    raw_meta       TEXT NOT NULL           -- JSON
);
CREATE INDEX IF NOT EXISTS papers_published ON papers (published_date);

-- One row per paper. 'screened' rows are final; 'no_abstract' and 'error' are retried.
CREATE TABLE IF NOT EXISTS screenings (
    paper_id        TEXT PRIMARY KEY REFERENCES papers (id),
    status          TEXT NOT NULL,         -- screened | no_abstract | error
    relevance_score INTEGER,
    market_focus    TEXT,                  -- EM | DM | Transversal
    focus_rationale TEXT,
    topics          TEXT,                  -- JSON list
    regions         TEXT,                  -- JSON list
    model           TEXT,
    prompt_version  TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    error           TEXT,
    screened_at     TEXT NOT NULL
);

-- Outcome of every collection run for every source.
CREATE TABLE IF NOT EXISTS source_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    status      TEXT NOT NULL,             -- ok | error
    items_found INTEGER NOT NULL,
    items_new   INTEGER NOT NULL,
    error       TEXT,
    duration_s  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS issues (
    month               TEXT PRIMARY KEY,  -- YYYY-MM
    editor_note         TEXT NOT NULL,
    selection_rationale TEXT NOT NULL,
    pool_size           INTEGER NOT NULL,
    papers_screened     INTEGER NOT NULL,
    model               TEXT NOT NULL,
    prompt_version      TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER NOT NULL,
    built_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS issue_papers (
    month            TEXT NOT NULL REFERENCES issues (month),
    paper_id         TEXT NOT NULL REFERENCES papers (id),
    position         INTEGER NOT NULL,
    selection_reason TEXT NOT NULL,
    headline         TEXT NOT NULL,
    summary          TEXT NOT NULL,
    takeaways        TEXT NOT NULL,        -- JSON list
    why_it_matters   TEXT NOT NULL,
    market_focus     TEXT NOT NULL,
    focus_rationale  TEXT NOT NULL,
    PRIMARY KEY (month, paper_id)
);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def upsert_papers(conn: sqlite3.Connection, papers: list[Paper]) -> int:
    """Insert papers we haven't seen; fill in an abstract that was missing before. Returns the number of new papers."""
    new = 0
    for p in papers:
        row = conn.execute("SELECT abstract FROM papers WHERE id = ?", (p.id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    p.id, p.source_id, p.title, json.dumps(p.authors), p.abstract, p.url,
                    p.published_date.isoformat() if p.published_date else None,
                    int(p.paywalled), p.fetched_at.isoformat(timespec="seconds"), json.dumps(p.raw_meta),
                ),
            )
            new += 1
        elif not row["abstract"] and p.abstract:
            conn.execute("UPDATE papers SET abstract = ? WHERE id = ?", (p.abstract, p.id))
    conn.commit()
    return new


def record_run(conn: sqlite3.Connection, source_id: str, started_at: str, status: str,
               items_found: int, items_new: int, error: str | None, duration_s: float) -> None:
    conn.execute(
        "INSERT INTO source_runs (source_id, started_at, status, items_found, items_new, error, duration_s)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (source_id, started_at, status, items_found, items_new, error, round(duration_s, 2)),
    )
    conn.commit()


def papers_to_screen(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Papers never screened, plus earlier 'no_abstract' or 'error' results, which are retried. Newest first.

    Placeholder results from FakeLLM (model 'fake') are also redone, so a dev run can never make them permanent.
    """
    return conn.execute(
        """SELECT p.* FROM papers p LEFT JOIN screenings s ON s.paper_id = p.id
           WHERE s.paper_id IS NULL OR s.status != 'screened' OR s.model = 'fake'
           ORDER BY p.published_date DESC"""
    ).fetchall()


def save_screening(conn: sqlite3.Connection, paper_id: str, status: str, *, result: dict | None = None,
                   model: str | None = None, prompt_version: str | None = None, input_tokens: int = 0,
                   output_tokens: int = 0, error: str | None = None) -> None:
    result = result or {}
    conn.execute(
        "INSERT OR REPLACE INTO screenings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            paper_id, status, result.get("relevance_score"), result.get("market_focus"),
            result.get("focus_rationale"), json.dumps(result.get("topics", [])),
            json.dumps(result.get("regions", [])), model, prompt_version, input_tokens, output_tokens,
            error, now_utc(),
        ),
    )
    conn.commit()
