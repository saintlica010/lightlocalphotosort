from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import open_project


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self, db_path: str) -> None:
        project = None
        try:
            project = open_project(Path(db_path).parent)
            result = LibraryService(project).scan()
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if project is not None:
                project.close()
