from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QImage

from local_media_curator.media.image_loader import load_preview_image


def _open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(url))


def open_path(path: Path) -> None:
    _open_url(str(Path(path)))


class _JobSignals(QObject):
    finished = Signal(int, object)


class _PreviewJob(QRunnable):
    def __init__(
        self, path: str, token: int, max_edge: int, signals: _JobSignals
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._path = path
        self._token = token
        self._max_edge = max_edge
        self._signals = signals

    def run(self) -> None:
        try:
            image = load_preview_image(Path(self._path), int(self._max_edge))
            payload: object = None if image.isNull() else image
            self._signals.finished.emit(int(self._token), payload)
        except Exception:
            self._signals.finished.emit(int(self._token), None)


class PreviewLoader(QObject):
    loaded = Signal(int, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._latest_token = 0
        self._signals = _JobSignals(self)
        self._signals.finished.connect(
            self._emit_loaded, Qt.ConnectionType.QueuedConnection
        )

    def load(self, path: str, token: int, max_edge: int) -> None:
        self._latest_token = int(token)
        job = _PreviewJob(str(path), int(token), int(max_edge), self._signals)
        self._pool.start(job)

    @Slot(int, object)
    def _emit_loaded(self, token: int, image: object) -> None:
        if int(token) != self._latest_token:
            return
        self.loaded.emit(int(token), image)
