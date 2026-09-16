from __future__ import annotations

from datetime import datetime

from local_media_curator.db.repositories import SORT_KEY_GAP, ListRepository
from local_media_curator.domain.models import Project

__all__ = ["SORT_KEY_GAP", "ListService"]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ListService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._lists = ListRepository(project.connection)

    def create(self, name: str, description: str | None = None) -> int:
        now = _now_iso()
        list_id = self._lists.insert(
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self._project.connection.commit()
        return list_id

    def rename(self, list_id: int, name: str) -> None:
        self._lists.rename(list_id, name, _now_iso())
        self._project.connection.commit()

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
