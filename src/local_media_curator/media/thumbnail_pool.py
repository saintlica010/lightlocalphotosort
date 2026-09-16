from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

from local_media_curator.domain.models import Project
from local_media_curator.media.thumbnail_service import ThumbnailService

MAX_WORKERS = 4


class _JobSignals(QObject):
    finished = Signal(int, str)


class _ThumbnailJob(QRunnable):
    def __init__(
        self,
        service: ThumbnailService,
        media_id: int,
        source_path: str,
        signals: _JobSignals,
        lock: threading.Lock,
        queued: set[int],
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._service = service
        self._media_id = media_id
        self._source_path = source_path
        self._signals = signals
        self._lock = lock
        self._queued = queued

    def run(self) -> None:
        try:
            out = self._service.ensure(self._media_id, Path(self._source_path))
            if out.is_file():
                self._signals.finished.emit(self._media_id, str(out))
        except Exception:
            return
        finally:
            with self._lock:
                self._queued.discard(self._media_id)


class ThumbnailPool(QObject):
    ready = Signal(int, str)

    def __init__(self, project: Project, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = ThumbnailService(project)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(MAX_WORKERS)
        self._priority = 0
        self._lock = threading.Lock()
        self._queued: set[int] = set()
        self._signals = _JobSignals(self)
        self._signals.finished.connect(
            self._emit_ready, Qt.ConnectionType.QueuedConnection
        )

    @property
    def max_workers(self) -> int:
        return self._pool.maxThreadCount()

    def request(self, jobs: list[tuple[int, str]]) -> None:
        # Newer batches outrank a large backlog already sitting in the pool.
        self._priority += 1
        priority = self._priority
        for media_id, source_path in jobs:
            with self._lock:
                if media_id in self._queued:
                    continue
                self._queued.add(media_id)
            job = _ThumbnailJob(
                self._service,
                int(media_id),
                str(source_path),
                self._signals,
                self._lock,
                self._queued,
            )
            self._pool.start(job, priority)

    def clear(self) -> None:
        self._pool.clear()
        with self._lock:
            self._queued.clear()

    @Slot(int, str)
    def _emit_ready(self, media_id: int, path: str) -> None:
        self.ready.emit(media_id, path)
