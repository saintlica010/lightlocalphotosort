from __future__ import annotations

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.domain.models import Project


class RejectionService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._media = MediaRepository(project.connection)

    def reject(self, media_ids: list[int]) -> None:
        self._media.set_rejected(media_ids, True)
        self._project.connection.commit()

    def restore(self, media_ids: list[int]) -> None:
        self._media.set_rejected(media_ids, False)
        self._project.connection.commit()

    def states(self, media_ids: list[int]) -> dict[int, bool]:
        return self._media.rejection_states(media_ids)
