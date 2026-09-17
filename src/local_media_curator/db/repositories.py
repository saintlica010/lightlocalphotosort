from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from local_media_curator.domain.ordering import next_sort_key
from local_media_curator.domain.paths import normalize_path

_IN_CHUNK = 400

_SORT_EXPRESSIONS = {
    "file_name": "file_name COLLATE NOCASE",
    "captured_at": "captured_at",
    "modified_at": "modified_at",
    "file_size": "file_size",
    "imported_at": "imported_at",
}


def _order_clause(sort_by: str) -> str:
    return _SORT_EXPRESSIONS.get(sort_by, _SORT_EXPRESSIONS["file_name"])


def _normalize_extension(extension: str) -> str:
    ext = extension.lower()
    return ext if ext.startswith(".") else f".{ext}"


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

    def remove(self, path: Path) -> None:
        stored = normalize_path(path)
        self._conn.execute("DELETE FROM source_folders WHERE path = ?", (stored,))
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
                imported_at, culling_state, missing, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'undecided', 0, NULL)
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

    def set_culling_state(self, media_ids: list[int], state: str) -> None:
        if not media_ids:
            return
        if state not in {"undecided", "picked", "rejected"}:
            raise ValueError(f"Invalid culling state: {state}")
        placeholders = ",".join("?" * len(media_ids))
        self._conn.execute(
            f"""
            UPDATE media
            SET culling_state = ?, rejected = ?
            WHERE id IN ({placeholders})
            """,
            (state, int(state == "rejected"), *media_ids),
        )


    def culling_states(self, media_ids: list[int]) -> dict[int, str]:
        if not media_ids:
            return {}
        placeholders = ",".join("?" * len(media_ids))
        rows = self._conn.execute(
            f"SELECT id, culling_state FROM media WHERE id IN ({placeholders})",
            tuple(media_ids),
        )
        return {int(row[0]): str(row[1]) for row in rows}

    def set_rejected(self, media_ids: list[int], rejected: bool) -> None:
        """Phase 1 compatibility wrapper; culling_state remains authoritative."""
        self.set_culling_state(media_ids, "rejected" if rejected else "undecided")

    def rejection_states(self, media_ids: list[int]) -> dict[int, bool]:
        return {
            media_id: state == "rejected"
            for media_id, state in self.culling_states(media_ids).items()
        }

    def list_media(
        self,
        *,
        include_rejected: bool = False,
        rejected_only: bool = False,
        culling_state: str | None = None,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
        source_folder: str | None = None,
        missing: bool | None = None,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if culling_state is not None:
            if culling_state not in {"undecided", "picked", "rejected"}:
                raise ValueError(f"Invalid culling state: {culling_state}")
            clauses.append("culling_state = ?")
            params.append(culling_state)
        elif rejected_only:
            clauses.append("culling_state = 'rejected'")
        elif not include_rejected:
            clauses.append("culling_state != 'rejected'")
        self._append_filters(clauses, params, media_type, extension, source_folder, missing)
        return self._select_media(clauses, params, sort_by)

    def list_unassigned(
        self,
        *,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
        source_folder: str | None = None,
        missing: bool | None = None,
        culling_state: str | None = None,
    ) -> list[sqlite3.Row]:
        clauses = [
            "id NOT IN (SELECT media_id FROM list_items)",
        ]
        params: list[object] = []
        if culling_state is not None:
            if culling_state not in {"undecided", "picked", "rejected"}:
                raise ValueError(f"Invalid culling state: {culling_state}")
            clauses.append("culling_state = ?")
            params.append(culling_state)
        else:
            clauses.append("culling_state != 'rejected'")
        self._append_filters(clauses, params, media_type, extension, source_folder, missing)
        return self._select_media(clauses, params, sort_by)

    def _append_filters(
        self,
        clauses: list[str],
        params: list[object],
        media_type: str | None,
        extension: str | None,
        source_folder: str | None,
        missing: bool | None,
    ) -> None:
        if source_folder:
            prefix = source_folder.rstrip("\\/") + os.sep
            clauses.append("substr(normalized_path, 1, ?) = ?")
            params.extend((len(prefix), prefix))
        if missing is not None:
            clauses.append("missing = ?")
            params.append(int(missing))
        if media_type:
            clauses.append("media_type = ?")
            params.append(media_type)
        if extension:
            clauses.append("extension = ?")
            params.append(_normalize_extension(extension))

    def _select_media(
        self,
        clauses: list[str],
        params: list[object],
        sort_by: str,
    ) -> list[sqlite3.Row]:
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM media {where} ORDER BY {_order_clause(sort_by)}, id"
        return list(self._conn.execute(sql, params))

    def get_by_ids(self, media_ids: list[int]) -> list[sqlite3.Row]:
        if not media_ids:
            return []
        placeholders = ",".join("?" * len(media_ids))
        rows = self._conn.execute(
            f"SELECT * FROM media WHERE id IN ({placeholders})",
            tuple(media_ids),
        )
        by_id = {int(row["id"]): row for row in rows}
        return [by_id[media_id] for media_id in media_ids if media_id in by_id]


class ProjectSettingsRepository:
    """Small key/value store for project-owned preferences."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM project_settings WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None or row[0] is None else str(row[0])

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO project_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM project_settings WHERE key = ?", (key,))


class ListRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def list_all(self) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                """
                SELECT id, name, description, created_at, updated_at
                FROM lists
                ORDER BY name COLLATE NOCASE, id
                """
            )
        )

    def get_by_name(self, name: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM lists WHERE name = ?",
            (name,),
        ).fetchone()

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
        # The setting is deliberately not a foreign key so the preference
        # table stays generic. Clear it atomically with list deletion.
        self._conn.execute(
            "DELETE FROM project_settings WHERE key = 'target_list_id' AND value = ?",
            (str(list_id),),
        )

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
        next_key = next_sort_key(int(max_key) if max_key is not None else None)
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
            next_key = next_sort_key(next_key)

    def items_with_sort_keys(self, list_id: int) -> list[tuple[int, int]]:
        rows = self._conn.execute(
            "SELECT media_id, sort_key FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (list_id,),
        )
        return [(int(row[0]), int(row[1])) for row in rows]

    def set_sort_keys(self, list_id: int, media_keys: list[tuple[int, int]]) -> None:
        for media_id, sort_key in media_keys:
            self._conn.execute(
                "UPDATE list_items SET sort_key = ? WHERE list_id = ? AND media_id = ?",
                (sort_key, list_id, media_id),
            )

    def items_for_ids(
        self, list_id: int, media_ids: list[int]
    ) -> list[tuple[int, int, str]]:
        if not media_ids:
            return []
        placeholders = ",".join("?" * len(media_ids))
        rows = self._conn.execute(
            f"""
            SELECT media_id, sort_key, added_at
            FROM list_items
            WHERE list_id = ? AND media_id IN ({placeholders})
            """,
            (list_id, *media_ids),
        )
        return [(int(row[0]), int(row[1]), str(row[2])) for row in rows]

    def insert_item_rows(
        self, list_id: int, rows: list[tuple[int, int, str]]
    ) -> None:
        for media_id, sort_key, added_at in rows:
            self._conn.execute(
                """
                INSERT INTO list_items (list_id, media_id, sort_key, added_at)
                VALUES (?, ?, ?, ?)
                """,
                (list_id, media_id, sort_key, added_at),
            )

    def remove_items(self, list_id: int, media_ids: list[int]) -> None:
        if not media_ids:
            return
        placeholders = ",".join("?" * len(media_ids))
        self._conn.execute(
            f"DELETE FROM list_items WHERE list_id = ? AND media_id IN ({placeholders})",
            (list_id, *media_ids),
        )

    def list_names_for_media(self, media_id: int) -> list[str]:
        return self.list_names_for_media_ids([media_id]).get(media_id, [])

    def list_names_for_media_ids(self, media_ids: list[int]) -> dict[int, list[str]]:
        mapping: dict[int, list[str]] = {int(media_id): [] for media_id in media_ids}
        if not media_ids:
            return mapping
        unique_ids = list(dict.fromkeys(int(media_id) for media_id in media_ids))
        for start in range(0, len(unique_ids), _IN_CHUNK):
            chunk = unique_ids[start : start + _IN_CHUNK]
            placeholders = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                f"""
                SELECT list_items.media_id, lists.name
                FROM list_items
                JOIN lists ON lists.id = list_items.list_id
                WHERE list_items.media_id IN ({placeholders})
                ORDER BY lists.name COLLATE NOCASE, lists.id
                """,
                tuple(chunk),
            )
            for row in rows:
                mapping[int(row[0])].append(str(row[1]))
        return mapping
