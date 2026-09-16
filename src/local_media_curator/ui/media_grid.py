from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QAbstractItemView, QListView, QVBoxLayout, QWidget

from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.thumbnail_delegate import THUMB_SIZE, ThumbnailDelegate


class MediaGrid(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view = QListView(self)
        self._view.setViewMode(QListView.ViewMode.IconMode)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._view.setResizeMode(QListView.ResizeMode.Adjust)
        self._view.setMovement(QListView.Movement.Static)
        self._view.setUniformItemSizes(True)
        self._view.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self._view.setSpacing(8)
        self._view.setWordWrap(True)
        self._model = MediaListModel(parent=self)
        self._view.setModel(self._model)
        self._view.setItemDelegate(ThumbnailDelegate(self._view))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

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
