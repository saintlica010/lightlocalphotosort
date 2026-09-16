from pathlib import Path

from local_media_curator.db.connection import connect
from local_media_curator.db.migrations import SCHEMA_VERSION, apply_migrations


def test_database_migration(tmp_path: Path) -> None:
    db = tmp_path / "project.sqlite3"
    conn = connect(db)
    apply_migrations(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"media", "lists", "list_items", "source_folders"} <= tables
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(list_items)")
    }
    assert "sort_key" in cols
    assert "position" not in cols
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()
