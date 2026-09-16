from __future__ import annotations

import sqlite3
from datetime import datetime

from local_media_curator.db.repositories import ListRepository
from local_media_curator.domain.models import Project
from local_media_curator.domain.ordering import (
    SORT_KEY_GAP,
    keys_between,
    normalize_list,
)

__all__ = ["SORT_KEY_GAP", "ListService"]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _resolve_order(
    current: list[tuple[int, int]], media_ids_in_order: list[int]
) -> list[int]:
    member_set = {media_id for media_id, _key in current}
    mentioned = [media_id for media_id in media_ids_in_order if media_id in member_set]
    mentioned_set = set(mentioned)
    rest = [media_id for media_id, _key in current if media_id not in mentioned_set]
    return mentioned + rest


def _try_assign_keys(
    order: list[int], existing: dict[int, int]
) -> list[int] | None:
    n = len(order)
    kept: list[int | None] = [None] * n
    last_kept: int | None = None
    for index, media_id in enumerate(order):
        current = existing.get(media_id)
        if current is None:
            continue
        if last_kept is None or current > last_kept:
            kept[index] = current
            last_kept = current
    assigned: list[int] = [0] * n
    index = 0
    while index < n:
        kept_key = kept[index]
        if kept_key is not None:
            assigned[index] = kept_key
            index += 1
            continue
        end = index
        while end < n and kept[end] is None:
            end += 1
        left = kept[index - 1] if index > 0 else None
        right = kept[end] if end < n else None
        filled = keys_between(left, right, end - index)
        if filled is None:
            return None
        for offset, key in enumerate(filled):
            assigned[index + offset] = key
            kept[index + offset] = key
        index = end
    return assigned


class ListService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._lists = ListRepository(project.connection)

    def all_lists(self) -> list[dict[str, object]]:
        return [
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "description": row["description"],
            }
            for row in self._lists.list_all()
        ]

    def create(self, name: str, description: str | None = None) -> int:
        now = _now_iso()
        conn = self._project.connection
        try:
            list_id = self._lists.insert(
                name=name,
                description=description,
                created_at=now,
                updated_at=now,
            )
            conn.commit()
            return list_id
        except sqlite3.IntegrityError:
            conn.rollback()
            existing = self._lists.get_by_name(name)
            if existing is not None:
                return int(existing["id"])
            raise

    def rename(self, list_id: int, name: str) -> None:
        conn = self._project.connection
        try:
            self._lists.rename(list_id, name, _now_iso())
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise

    def delete(self, list_id: int) -> None:
        self._lists.delete(list_id)
        self._project.connection.commit()

    def add_items(self, list_id: int, media_ids: list[int]) -> None:
        self._lists.add_items(list_id, media_ids, _now_iso())
        self._project.connection.commit()

    def remove_items(self, list_id: int, media_ids: list[int]) -> None:
        self._lists.remove_items(list_id, media_ids)
        self._project.connection.commit()

    def count(self, list_id: int) -> int:
        return self._lists.count_items(list_id)

    def ordered_media_ids(self, list_id: int) -> list[int]:
        return self._lists.ordered_media_ids(list_id)

    def list_names_for_media(self, media_id: int) -> list[str]:
        return self._lists.list_names_for_media(media_id)

    def list_names_for_media_ids(self, media_ids: list[int]) -> dict[int, list[str]]:
        return self._lists.list_names_for_media_ids(media_ids)

    def items_with_sort_keys(self, list_id: int) -> list[tuple[int, int]]:
        return self._lists.items_with_sort_keys(list_id)

    def restore_sort_keys(
        self, list_id: int, media_keys: list[tuple[int, int]]
    ) -> None:
        conn = self._project.connection
        try:
            self._lists.set_sort_keys(list_id, media_keys)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def snapshot_items(
        self, list_id: int, media_ids: list[int]
    ) -> list[tuple[int, int, str]]:
        return self._lists.items_for_ids(list_id, media_ids)

    def restore_item_rows(
        self, list_id: int, rows: list[tuple[int, int, str]]
    ) -> None:
        if not rows:
            return
        conn = self._project.connection
        try:
            self._lists.insert_item_rows(list_id, rows)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def reorder(self, list_id: int, media_ids_in_order: list[int]) -> None:
        current = self._lists.items_with_sort_keys(list_id)
        new_order = _resolve_order(current, media_ids_in_order)
        self._persist_order(list_id, current, new_order)

    def move_selection(self, list_id: int, media_ids: list[int], delta: int) -> None:
        if not media_ids or delta == 0:
            return
        current = self._lists.items_with_sort_keys(list_id)
        order = [media_id for media_id, _key in current]
        selected_set = set(media_ids)
        selected = [media_id for media_id in order if media_id in selected_set]
        if not selected:
            return
        remaining = [media_id for media_id in order if media_id not in selected_set]
        first_index = order.index(selected[0])
        insert_at = sum(1 for media_id in order[:first_index] if media_id not in selected_set)
        new_insert = min(max(insert_at + delta, 0), len(remaining))
        new_order = remaining[:new_insert] + selected + remaining[new_insert:]
        self._persist_order(list_id, current, new_order)

    def move_to_ends(self, list_id: int, media_ids: list[int], *, end: bool) -> None:
        current = self._lists.items_with_sort_keys(list_id)
        order = [media_id for media_id, _key in current]
        selected_set = set(media_ids)
        selected = [media_id for media_id in order if media_id in selected_set]
        if not selected:
            return
        remaining = [media_id for media_id in order if media_id not in selected_set]
        new_order = remaining + selected if end else selected + remaining
        self._persist_order(list_id, current, new_order)

    def _persist_order(
        self,
        list_id: int,
        current: list[tuple[int, int]],
        new_order: list[int],
    ) -> None:
        existing = {media_id: key for media_id, key in current}
        if new_order == [media_id for media_id, _key in current]:
            return
        keys = _try_assign_keys(new_order, existing)
        if keys is None:
            keys = normalize_list([0] * len(new_order))
        updates = [
            (media_id, key)
            for media_id, key in zip(new_order, keys, strict=True)
            if existing.get(media_id) != key
        ]
        if not updates:
            return
        conn = self._project.connection
        try:
            self._lists.set_sort_keys(list_id, updates)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
