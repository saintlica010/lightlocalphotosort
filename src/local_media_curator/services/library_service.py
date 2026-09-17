from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from local_media_curator.db.repositories import MediaRepository, SourceFolderRepository
from local_media_curator.domain.models import Media, Project, ScanResult
from local_media_curator.domain.paths import reject_overlapping_roots
from local_media_curator.media.scanner import scan_source_folder


class LibraryService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._source_folders = SourceFolderRepository(project.connection)
        self._media = MediaRepository(project.connection)

    def add_source_folder(self, path: Path, *, recursive: bool = True) -> None:
        reject_overlapping_roots(self._project.root, path)
        self._source_folders.add(path, recursive=recursive)

    def remove_source_folder(self, path: Path) -> None:
        self._source_folders.remove(path)

    def scan(self, cancel_check: Callable[[], bool] | None = None) -> ScanResult:
        total = ScanResult()
        for row in self._source_folders.list_enabled():
            result = scan_source_folder(
                self._project,
                Path(row["path"]),
                recursive=bool(row["recursive"]),
                cancel_check=cancel_check,
            )
            total.added += result.added
            total.missing += result.missing
            total.unchanged += result.unchanged
            total.modified += result.modified
        return total

    def list_media(
        self,
        *,
        include_rejected: bool = False,
        rejected_only: bool = False,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
    ) -> list[Media]:
        rows = self._media.list_media(
            include_rejected=include_rejected,
            rejected_only=rejected_only,
            sort_by=sort_by,
            media_type=media_type,
            extension=extension,
        )
        return [Media.from_row(row) for row in rows]

    def list_unassigned(
        self,
        *,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
    ) -> list[Media]:
        rows = self._media.list_unassigned(
            sort_by=sort_by,
            media_type=media_type,
            extension=extension,
        )
        return [Media.from_row(row) for row in rows]

    def list_media_by_ids(self, media_ids: list[int]) -> list[Media]:
        return [Media.from_row(row) for row in self._media.get_by_ids(media_ids)]
