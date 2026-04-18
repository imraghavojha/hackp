from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    url TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_json TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS events_user_id_id_idx ON events(user_id, id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    html_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_event_window_json TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    transformation_summary_json TEXT NOT NULL,
    artifact_json TEXT NOT NULL,
    ui_prefs_json TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    status TEXT NOT NULL,
    signature TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS tools_user_status_idx ON tools(user_id, status);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    feedback TEXT NOT NULL,
    context TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_state (
    user_id TEXT PRIMARY KEY,
    last_processed_event_id INTEGER NOT NULL DEFAULT 0,
    last_detection_at TEXT,
    last_activity_at TEXT
);
"""


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.commit()
