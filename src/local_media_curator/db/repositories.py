from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from local_media_curator.domain.paths import normalize_path


class SourceFolderRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def add(self, path: Path, *, recursive: bool = True) -> None:
        stored = normalize_path(path)
        self._conn.execute(
            """
            INSERT INTO source_folders (path, recursive, enabled)
            VALUES (?, ?, 1)
            ON CONFLICT(path) DO UPDATE SET
                recursive = excluded.recursive,
                enabled = 1
            """,
            (stored, int(recursive)),
        )
        self._conn.commit()

    def list_enabled(self) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                """
                SELECT id, path, recursive, enabled
                FROM source_folders
                WHERE enabled = 1
                ORDER BY id
                """
            )
        )


class MediaRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def get_by_normalized_path(self, normalized_path: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM media WHERE normalized_path = ?",
            (normalized_path,),
        ).fetchone()

    def list_under_folder(self, folder_normalized: str) -> list[sqlite3.Row]:
        prefix = folder_normalized.rstrip("\\/") + os.sep
        # Exact prefix match — avoid LIKE so '_' / '%' in paths are not wildcards.
        return list(
            self._conn.execute(
                "SELECT * FROM media WHERE substr(normalized_path, 1, ?) = ?",
                (len(prefix), prefix),
            )
        )

    def insert(
        self,
        *,
        absolute_path: str,
        normalized_path: str,
        media_type: str,
        file_name: str,
        extension: str,
        file_size: int | None,
        width: int | None,
        height: int | None,
        duration_ms: int | None,
        captured_at: str | None,
        modified_at: str | None,
        imported_at: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO media (
                absolute_path, normalized_path, media_type, file_name, extension,
                file_size, width, height, duration_ms, captured_at, modified_at,
                imported_at, rejected, missing, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL)
            """,
            (
                absolute_path,
                normalized_path,
                media_type,
                file_name,
                extension,
                file_size,
                width,
                height,
                duration_ms,
                captured_at,
                modified_at,
                imported_at,
            ),
        )
        return int(cur.lastrowid)

    def update_file_metadata(
        self,
        media_id: int,
        *,
        file_size: int | None,
        width: int | None,
        height: int | None,
        captured_at: str | None,
        modified_at: str | None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE media
            SET file_size = ?, width = ?, height = ?, captured_at = ?,
                modified_at = ?, missing = 0
            WHERE id = ?
            """,
            (file_size, width, height, captured_at, modified_at, media_id),
        )

    def set_missing(self, media_id: int, missing: bool = True) -> None:
        self._conn.execute(
            "UPDATE media SET missing = ? WHERE id = ?",
            (int(missing), media_id),
        )


SORT_KEY_GAP = 1024


class ListRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def insert(
        self,
        *,
        name: str,
        description: str | None,
        created_at: str,
        updated_at: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO lists (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, created_at, updated_at),
        )
        return int(cur.lastrowid)

    def rename(self, list_id: int, name: str, updated_at: str) -> None:
        self._conn.execute(
            "UPDATE lists SET name = ?, updated_at = ? WHERE id = ?",
            (name, updated_at, list_id),
        )

    def delete(self, list_id: int) -> None:
        self._conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))

    def count_items(self, list_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM list_items WHERE list_id = ?",
            (list_id,),
        ).fetchone()
        return int(row[0])

    def ordered_media_ids(self, list_id: int) -> list[int]:
        rows = self._conn.execute(
            "SELECT media_id FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (list_id,),
        )
        return [int(row[0]) for row in rows]

    def add_items(self, list_id: int, media_ids: list[int], added_at: str) -> None:
        if not media_ids:
            return
        existing = {
            int(row[0])
            for row in self._conn.execute(
                "SELECT media_id FROM list_items WHERE list_id = ?",
                (list_id,),
            )
        }
        max_key = self._conn.execute(
            "SELECT MAX(sort_key) FROM list_items WHERE list_id = ?",
            (list_id,),
        ).fetchone()[0]
        next_key = int(max_key or 0) + SORT_KEY_GAP
        for media_id in media_ids:
            if media_id in existing:
                continue
            self._conn.execute(
                """
                INSERT INTO list_items (list_id, media_id, sort_key, added_at)
                VALUES (?, ?, ?, ?)
                """,
                (list_id, media_id, next_key, added_at),
            )
            existing.add(media_id)
            next_key += SORT_KEY_GAP

    def remove_items(self, list_id: int, media_ids: list[int]) -> None:
        if not media_ids:
            return
        placeholders = ",".join("?" * len(media_ids))
        self._conn.execute(
            f"DELETE FROM list_items WHERE list_id = ? AND media_id IN ({placeholders})",
            (list_id, *media_ids),
        )

    def list_names_for_media(self, media_id: int) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT lists.name
            FROM list_items
            JOIN lists ON lists.id = list_items.list_id
            WHERE list_items.media_id = ?
            ORDER BY lists.name
            """,
            (media_id,),
        )
        return [str(row[0]) for row in rows]
