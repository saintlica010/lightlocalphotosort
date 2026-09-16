from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

from local_media_curator.domain.models import Project
from local_media_curator.media.thumbnail_schedule import MAX_PENDING, prioritize_jobs
from local_media_curator.media.thumbnail_service import ThumbnailService

MAX_WORKERS = 4


class _JobSignals(QObject):
    finished = Signal(int, str, int)


class _ThumbnailJob(QRunnable):
    def __init__(
        self,
        service: ThumbnailService,
        media_id: int,
        source_path: str,
        signals: _JobSignals,
        generation: int,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._service = service
        self._media_id = media_id
        self._source_path = source_path
        self._signals = signals
        self._generation = generation

    def run(self) -> None:
        path = ""
        try:
            out = self._service.ensure(self._media_id, Path(self._source_path))
            if out.is_file():
                path = str(out)
        except Exception:
            path = ""
        self._signals.finished.emit(self._media_id, path, self._generation)


class ThumbnailPool(QObject):
    ready = Signal(int, str)

    def __init__(self, project: Project, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = ThumbnailService(project)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(MAX_WORKERS)
        self._lock = threading.Lock()
        self._generation = 0
        self._needed: dict[int, str] = {}
        self._pending: OrderedDict[int, str] = OrderedDict()
        self._running: dict[int, int] = {}
        self._signals = _JobSignals(self)
        self._signals.finished.connect(
            self._on_job_finished, Qt.ConnectionType.QueuedConnection
        )

    @property
    def max_workers(self) -> int:
        return self._pool.maxThreadCount()

    def request(self, jobs: list[tuple[int, str]]) -> None:
        self.sync(
            {media_id: path for media_id, path in jobs},
            visible_ids=[media_id for media_id, _path in jobs],
        )

    def sync(
        self, needed: Mapping[int, str], visible_ids: Sequence[int]
    ) -> None:
        with self._lock:
            self._generation += 1
            self._needed = {
                int(media_id): str(path) for media_id, path in needed.items()
            }
            jobs = prioritize_jobs(
                self._needed,
                [int(media_id) for media_id in visible_ids],
                set(self._running),
                max_pending=MAX_PENDING,
            )
            self._pending = OrderedDict(jobs)
        self._pump()

    def pending_ids(self) -> list[int]:
        with self._lock:
            return list(self._pending)

    def inflight_ids(self) -> set[int]:
        with self._lock:
            return {
                media_id
                for media_id, generation in self._running.items()
                if generation == self._generation
            }

    def clear(self) -> None:
        with self._lock:
            self._generation += 1
            self._pending.clear()
            self._needed.clear()
            self._running.clear()
        self._pool.clear()

    def _pump(self) -> None:
        to_start: list[tuple[int, str, int]] = []
        with self._lock:
            while (
                self._pending
                and len(self._running) < MAX_WORKERS
                and self._pool.activeThreadCount() < MAX_WORKERS
            ):
                media_id, path = self._pending.popitem(last=False)
                if media_id in self._running:
                    continue
                generation = self._generation
                self._running[media_id] = generation
                to_start.append((media_id, path, generation))
        for media_id, path, generation in to_start:
            job = _ThumbnailJob(
                self._service,
                media_id,
                path,
                self._signals,
                generation,
            )
            self._pool.start(job)

    @Slot(int, str, int)
    def _on_job_finished(self, media_id: int, path: str, generation: int) -> None:
        if path:
            with self._lock:
                expected = media_id in self._needed
            if expected:
                self.ready.emit(media_id, path)
        with self._lock:
            if self._running.get(media_id) == generation:
                self._running.pop(media_id, None)
        self._pump()
