from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView, QListView, QVBoxLayout, QWidget

from local_media_curator.media.thumbnail_schedule import PREFETCH_ROWS
from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.theme import TOKENS
from local_media_curator.ui.thumbnail_delegate import THUMB_SIZE, ThumbnailDelegate


class MediaGrid(QWidget):
    viewportRowsChanged = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view = QListView(self)
        self._view.setViewMode(QListView.ViewMode.IconMode)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._view.setResizeMode(QListView.ResizeMode.Adjust)
        self._view.setMovement(QListView.Movement.Static)
        self._view.setUniformItemSizes(True)
        self._view.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self._view.setObjectName("mediaGrid")
        self._view.setSpacing(TOKENS.thumbnail_spacing)
        self._view.setWordWrap(True)
        self._model = MediaListModel(parent=self)
        self._view.setModel(self._model)
        self._view.setItemDelegate(ThumbnailDelegate(self._view))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._viewport_timer = QTimer(self)
        self._viewport_timer.setSingleShot(True)
        self._viewport_timer.setInterval(16)
        self._viewport_timer.timeout.connect(self._emit_viewport_rows)
        vbar = self._view.verticalScrollBar()
        hbar = self._view.horizontalScrollBar()
        vbar.valueChanged.connect(self._schedule_viewport_signal)
        hbar.valueChanged.connect(self._schedule_viewport_signal)
        vbar.rangeChanged.connect(self._schedule_viewport_signal)
        hbar.rangeChanged.connect(self._schedule_viewport_signal)
        self._model.modelReset.connect(self._schedule_viewport_signal)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_viewport_signal()

    def set_manual_order_enabled(self, enabled: bool) -> None:
        self._model.set_manual_order_enabled(enabled)
        if enabled:
            self._view.setMovement(QListView.Movement.Snap)
            self._view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self._view.setDefaultDropAction(Qt.DropAction.MoveAction)
        else:
            self._view.setMovement(QListView.Movement.Static)
            self._view.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

    @property
    def view(self) -> QListView:
        return self._view

    @property
    def model(self) -> MediaListModel:
        return self._model

    def visible_row_range(self, prefetch: int = PREFETCH_ROWS) -> tuple[int, int]:
        count = self._model.rowCount()
        if count <= 0:
            return (0, -1)
        viewport = self._view.viewport()
        step = max(THUMB_SIZE // 2, 1)
        found: list[int] = []
        width = viewport.width()
        height = viewport.height()
        y = 0
        while y <= height:
            x = 0
            while x <= width:
                index = self._view.indexAt(QPoint(x, y))
                if index.isValid():
                    found.append(index.row())
                x += step
            y += step
        corner = self._view.indexAt(QPoint(max(width - 1, 0), max(height - 1, 0)))
        if corner.isValid():
            found.append(corner.row())
        if not found:
            return (0, min(count - 1, prefetch))
        first = max(0, min(found) - prefetch)
        last = min(count - 1, max(found) + prefetch)
        return (first, last)

    def selected_ids(self) -> list[int]:
        ids: list[int] = []
        seen: set[int] = set()
        selection = self._view.selectionModel()
        indexes = selection.selectedIndexes() if selection is not None else []
        if not indexes:
            current = self._view.currentIndex()
            if current.isValid():
                indexes = [current]
        for index in indexes:
            value = self._model.data(index, MediaListModel.IdRole)
            if value is None:
                continue
            media_id = int(value)
            if media_id in seen:
                continue
            seen.add(media_id)
            ids.append(media_id)
        return ids

    def _schedule_viewport_signal(self, *_args: object) -> None:
        self._viewport_timer.start()

    def _emit_viewport_rows(self) -> None:
        first, last = self.visible_row_range()
        self.viewportRowsChanged.emit(first, last)
