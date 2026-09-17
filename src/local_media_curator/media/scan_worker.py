from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from local_media_curator.media.scanner import ScanCancelled
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import open_project


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self, db_path: str) -> None:
        project = None
        try:
            project = open_project(Path(db_path).parent)
            result = LibraryService(project).scan(
                cancel_check=self._cancel.is_set, progress_cb=self.progress.emit
            )
            self.finished.emit(result)
        except ScanCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if project is not None:
                project.close()
