from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 2

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

_SCHEMA_V2 = """
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
    culling_state TEXT NOT NULL DEFAULT 'undecided'
        CHECK (culling_state IN ('undecided', 'picked', 'rejected')),
    -- Legacy compatibility projection. Runtime code uses culling_state.
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

CREATE INDEX idx_media_culling_state ON media(culling_state);
CREATE INDEX idx_media_captured_at ON media(captured_at);
CREATE INDEX idx_list_items_order ON list_items(list_id, sort_key);

CREATE TABLE project_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TRIGGER media_sync_culling_state
AFTER UPDATE OF rejected ON media
WHEN NEW.rejected != OLD.rejected
    AND NEW.culling_state = OLD.culling_state
BEGIN
    UPDATE media
    SET culling_state = CASE WHEN NEW.rejected = 1 THEN 'rejected' ELSE 'undecided' END
    WHERE id = NEW.id;
END;
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current >= SCHEMA_VERSION:
        _ensure_v2_support_tables(conn)
        conn.commit()
        return
    if current < 1:
        conn.executescript(_SCHEMA_V2)
        current = 2
    if current < 2:
        _migrate_v1_to_v2(conn)
    _ensure_v2_support_tables(conn)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _ensure_v2_support_tables(conn: sqlite3.Connection) -> None:
    """Create additive v2 support tables for already-migrated projects.

    Phase 2A projects may already report schema version 2, so the target-list
    setting cannot be added only inside the numeric migration step. This
    idempotent check keeps both fresh and existing v2 projects safe.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Add the v2 state in place so list foreign keys and ordering survive."""
    conn.commit()
    conn.execute("BEGIN")
    try:
        conn.execute(
            """
            ALTER TABLE media ADD COLUMN culling_state TEXT NOT NULL
                DEFAULT 'undecided'
                CHECK (culling_state IN ('undecided', 'picked', 'rejected'))
            """
        )
        conn.execute(
            """
            UPDATE media
            SET culling_state = CASE
                WHEN rejected = 1 THEN 'rejected'
                ELSE 'undecided'
            END
            """
        )
        conn.execute("CREATE INDEX idx_media_culling_state ON media(culling_state)")
        # Keep direct writes from older integrations coherent during the
        # transition. Application code still treats culling_state as the
        # authoritative field and never reads rejected for decisions.
        conn.execute(
            """
            CREATE TRIGGER media_sync_culling_state
            AFTER UPDATE OF rejected ON media
            WHEN NEW.rejected != OLD.rejected
                AND NEW.culling_state = OLD.culling_state
            BEGIN
                UPDATE media
                SET culling_state = CASE WHEN NEW.rejected = 1 THEN 'rejected' ELSE 'undecided' END
                WHERE id = NEW.id;
            END
            """
        )
    except Exception:
        conn.rollback()
        raise
