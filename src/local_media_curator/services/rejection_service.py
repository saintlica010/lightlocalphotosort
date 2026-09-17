from __future__ import annotations

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.domain.models import Project


class RejectionService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._media = MediaRepository(project.connection)

    def set_state(self, media_ids: list[int], state: str) -> None:
        try:
            self._media.set_culling_state(media_ids, state)
            self._project.connection.commit()
        except Exception:
            self._project.connection.rollback()
            raise

    def restore_states(self, states: dict[int, str]) -> None:
        """Restore mixed prior states atomically for one undo operation."""
        try:
            for state, media_ids in _group_state_ids(states).items():
                self._media.set_culling_state(media_ids, state)
            self._project.connection.commit()
        except Exception:
            self._project.connection.rollback()
            raise

    def states(self, media_ids: list[int]) -> dict[int, str]:
        return self._media.culling_states(media_ids)

    def reject(self, media_ids: list[int]) -> None:
        self.set_state(media_ids, "rejected")

    def restore(self, media_ids: list[int]) -> None:
        self.set_state(media_ids, "undecided")


def _group_state_ids(states: dict[int, str]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for media_id, state in states.items():
        grouped.setdefault(state, []).append(media_id)
    return grouped
