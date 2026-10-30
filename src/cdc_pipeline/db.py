from __future__ import annotations

import sqlite3
from pathlib import Path


REGIONS = ("apac", "eu", "na")

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    input_count INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    applied_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    stale_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT
);

CREATE TABLE IF NOT EXISTS current_accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT,
    region_id TEXT REFERENCES regions(region_id),
    balance REAL,
    event_ts TEXT NOT NULL,
    event_id TEXT NOT NULL,
    is_deleted INTEGER NOT NULL CHECK (is_deleted IN (0, 1)),
    source_file TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS event_history (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('insert', 'update', 'delete')),
    event_ts TEXT NOT NULL,
    event_fingerprint TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('applied', 'stale')),
    source_file TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS quarantine (
    reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id),
    source_file TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    event_id TEXT,
    raw_record TEXT NOT NULL,
    reason TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_account_time
    ON event_history(account_id, event_ts, event_id);
CREATE INDEX IF NOT EXISTS idx_quarantine_run
    ON quarantine(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_status_time
    ON pipeline_runs(status, started_at);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(SCHEMA)
    connection.executemany(
        "INSERT OR IGNORE INTO regions(region_id) VALUES (?)",
        ((region,) for region in REGIONS),
    )
    connection.commit()
    return connection
