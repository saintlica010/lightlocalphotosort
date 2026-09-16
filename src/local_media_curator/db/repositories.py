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
