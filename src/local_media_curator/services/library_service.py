from __future__ import annotations

from pathlib import Path

from local_media_curator.db.repositories import SourceFolderRepository
from local_media_curator.domain.models import Project, ScanResult
from local_media_curator.media.scanner import scan_source_folder


class LibraryService:
    def __init__(self, project: Project) -> None:
        self._project = project
        self._source_folders = SourceFolderRepository(project.connection)

    def add_source_folder(self, path: Path, *, recursive: bool = True) -> None:
        self._source_folders.add(path, recursive=recursive)

    def scan(self) -> ScanResult:
        total = ScanResult()
        for row in self._source_folders.list_enabled():
            result = scan_source_folder(
                self._project,
                Path(row["path"]),
                recursive=bool(row["recursive"]),
            )
            total.added += result.added
            total.missing += result.missing
            total.unchanged += result.unchanged
            total.modified += result.modified
        return total
