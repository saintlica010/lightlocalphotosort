from pathlib import Path

from local_media_curator.db.connection import connect
from local_media_curator.db.migrations import (
    SCHEMA_VERSION,
    _SCHEMA_V1,
    apply_migrations,
)
from local_media_curator.db.repositories import MediaRepository


def test_database_migration(tmp_path: Path) -> None:
    db = tmp_path / "project.sqlite3"
    conn = connect(db)
    apply_migrations(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
    assert version == 2
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
    media_cols = {row[1] for row in conn.execute("PRAGMA table_info(media)")}
    assert "culling_state" in media_cols
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()


def test_schema_v1_migrates_state_and_list_order_without_loss(tmp_path: Path) -> None:
    db = tmp_path / "phase1.sqlite3"
    conn = connect(db)
    conn.executescript(_SCHEMA_V1)
    conn.executemany(
        """
        INSERT INTO media (
            absolute_path, normalized_path, media_type, file_name, extension,
            file_size, imported_at, rejected
        ) VALUES (?, ?, 'image', ?, '.jpg', 10, '2026-01-01T00:00:00', ?)
        """,
        [
            ("C:/photos/A.jpg", "c:/photos/a.jpg", "A.jpg", 1),
            ("C:/photos/B.jpg", "c:/photos/b.jpg", "B.jpg", 0),
        ],
    )
    list_id = conn.execute(
        """
        INSERT INTO lists (name, created_at, updated_at)
        VALUES ('Website', '2026-01-01T00:00:00', '2026-01-01T00:00:00')
        RETURNING id
        """
    ).fetchone()[0]
    media_ids = [row[0] for row in conn.execute("SELECT id FROM media ORDER BY id")]
    conn.executemany(
        """
        INSERT INTO list_items (list_id, media_id, sort_key, added_at)
        VALUES (?, ?, ?, '2026-01-01T00:00:00')
        """,
        [(list_id, media_ids[1], 2048), (list_id, media_ids[0], 1024)],
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()

    apply_migrations(conn)

    states = {
        row["file_name"]: row["culling_state"]
        for row in conn.execute("SELECT file_name, culling_state FROM media")
    }
    assert states == {"A.jpg": "rejected", "B.jpg": "undecided"}
    assert [row[0] for row in conn.execute(
        "SELECT media_id FROM list_items WHERE list_id = ? ORDER BY sort_key",
        (list_id,),
    )] == [media_ids[0], media_ids[1]]
    assert conn.execute(
        "SELECT rejected FROM media WHERE file_name = 'A.jpg'"
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT rejected FROM media WHERE file_name = 'B.jpg'"
    ).fetchone()[0] == 0
    conn.close()


def test_culling_state_is_authoritative_and_legacy_writes_remain_compatible(
    tmp_path: Path,
) -> None:
    conn = connect(tmp_path / "project.sqlite3")
    apply_migrations(conn)
    conn.execute("PRAGMA recursive_triggers = ON")
    media_id = MediaRepository(conn).insert(
        absolute_path="C:/photos/A.jpg",
        normalized_path="c:/photos/a.jpg",
        media_type="image",
        file_name="A.jpg",
        extension=".jpg",
        file_size=10,
        width=10,
        height=10,
        duration_ms=None,
        captured_at=None,
        modified_at="2026-01-01T00:00:00",
        imported_at="2026-01-01T00:00:00",
    )
    repo = MediaRepository(conn)

    repo.set_culling_state([media_id], "picked")
    assert tuple(conn.execute(
        "SELECT culling_state, rejected FROM media WHERE id = ?", (media_id,)
    ).fetchone()) == ("picked", 0)

    repo.set_culling_state([media_id], "rejected")
    assert tuple(conn.execute(
        "SELECT culling_state, rejected FROM media WHERE id = ?", (media_id,)
    ).fetchone()) == ("rejected", 1)

    repo.set_culling_state([media_id], "picked")
    assert tuple(conn.execute(
        "SELECT culling_state, rejected FROM media WHERE id = ?", (media_id,)
    ).fetchone()) == ("picked", 0)

    conn.execute("UPDATE media SET rejected = 1 WHERE id = ?", (media_id,))
    assert conn.execute(
        "SELECT culling_state FROM media WHERE id = ?", (media_id,)
    ).fetchone()[0] == "rejected"
    conn.execute("UPDATE media SET rejected = 0 WHERE id = ?", (media_id,))
    assert conn.execute(
        "SELECT culling_state FROM media WHERE id = ?", (media_id,)
    ).fetchone()[0] == "undecided"
    conn.close()


def test_existing_v2_project_gets_target_list_settings_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "phase2a.sqlite3")
    apply_migrations(conn)
    conn.execute("DROP TABLE project_settings")
    conn.execute("PRAGMA user_version = 2")
    conn.commit()

    apply_migrations(conn)

    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'project_settings'"
    ).fetchone() is not None
    conn.close()
