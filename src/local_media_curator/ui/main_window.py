from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget

from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.library_panel = QWidget()
        self.media_grid = MediaGrid()
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.media_grid)
        splitter.addWidget(self.preview_panel)
        self.setCentralWidget(splitter)
        self.media_grid.view.selectionModel().currentChanged.connect(
            self._on_media_current_changed
        )

    def _on_media_current_changed(
        self, current: QModelIndex, _previous: QModelIndex
    ) -> None:
        if not current.isValid():
            self.preview_panel.set_media(None)
            return
        self.preview_panel.set_media(self.media_grid.model.row_at(current.row()))
