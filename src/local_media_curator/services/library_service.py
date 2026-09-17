from __future__ import annotations

import os
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

    def scan(
        self,
        cancel_check: Callable[[], bool] | None = None,
        progress_cb: Callable[[int], None] | None = None,
    ) -> ScanResult:
        total = ScanResult()
        processed = 0
        last_reported = -1

        def report(count: int) -> None:
            nonlocal last_reported
            cumulative = processed + count
            if progress_cb is not None and cumulative != last_reported:
                progress_cb(cumulative)
                last_reported = cumulative

        for row in self._source_folders.list_enabled():
            result = scan_source_folder(
                self._project,
                Path(row["path"]),
                recursive=bool(row["recursive"]),
                cancel_check=cancel_check,
                progress_cb=report,
            )
            processed += result.added + result.modified + result.unchanged
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
        culling_state: str | None = None,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
        source_folder: str | None = None,
        missing: bool | None = None,
    ) -> list[Media]:
        rows = self._media.list_media(
            include_rejected=include_rejected,
            rejected_only=rejected_only,
            culling_state=culling_state,
            sort_by=sort_by,
            media_type=media_type,
            extension=extension,
            source_folder=source_folder,
            missing=missing,
        )
        return [Media.from_row(row) for row in rows]

    def list_unassigned(
        self,
        *,
        sort_by: str = "file_name",
        media_type: str | None = None,
        extension: str | None = None,
        source_folder: str | None = None,
        missing: bool | None = None,
        culling_state: str | None = None,
    ) -> list[Media]:
        rows = self._media.list_unassigned(
            sort_by=sort_by,
            media_type=media_type,
            extension=extension,
            source_folder=source_folder,
            missing=missing,
            culling_state=culling_state,
        )
        return [Media.from_row(row) for row in rows]

    def list_media_by_ids(self, media_ids: list[int]) -> list[Media]:
        return [Media.from_row(row) for row in self._media.get_by_ids(media_ids)]

    def filter_media(
        self,
        items: list[Media],
        *,
        media_type: str | None = None,
        extension: str | None = None,
        source_folder: str | None = None,
        missing: bool | None = None,
        culling_state: str | None = None,
    ) -> list[Media]:
        prefix = ""
        if source_folder:
            prefix = source_folder.rstrip("\\/") + os.sep
        ext = extension.lower() if extension else None
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        return [
            media
            for media in items
            if (media_type is None or media.media_type == media_type)
            and (ext is None or (media.extension or "").lower() == ext)
            and (prefix == "" or media.normalized_path.startswith(prefix))
            and (missing is None or media.missing == missing)
            and (culling_state is None or media.culling_state == culling_state)
        ]

    def culling_counts(self) -> dict[str, int]:
        rows = self._project.connection.execute(
            "SELECT culling_state, COUNT(*) FROM media GROUP BY culling_state"
        )
        counts = {"picked": 0, "undecided": 0, "rejected": 0}
        counts.update({str(row[0]): int(row[1]) for row in rows})
        return counts
