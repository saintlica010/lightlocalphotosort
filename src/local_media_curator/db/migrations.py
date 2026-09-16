from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE media (
    id INTEGER PRIMARY KEY,
    absolute_path TEXT NOT NULL UNIQUE,
    normalized_path TEXT NOT NULL UNIQUE,
    media_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    extension TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    duration_ms INTEGER,
    captured_at TEXT,
    modified_at TEXT,
    imported_at TEXT NOT NULL,
    rejected INTEGER NOT NULL DEFAULT 0,
    missing INTEGER NOT NULL DEFAULT 0,
    fingerprint TEXT
);

CREATE TABLE lists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE list_items (
    list_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,
    sort_key INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (list_id, media_id),
    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE source_folders (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    recursive INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_media_rejected ON media(rejected);
CREATE INDEX idx_media_captured_at ON media(captured_at);
CREATE INDEX idx_list_items_order ON list_items(list_id, sort_key);
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current >= SCHEMA_VERSION:
        return
    if current < 1:
        conn.executescript(_SCHEMA_V1)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
