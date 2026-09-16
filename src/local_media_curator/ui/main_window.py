from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget

from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.undo_stack: CurationUndoStack | None = None
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.library_panel = LibraryPanel()
        self.media_grid = MediaGrid()
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.media_grid)
        splitter.addWidget(self.preview_panel)
        self.setCentralWidget(splitter)
        self._install_undo_actions()
        self.media_grid.view.selectionModel().currentChanged.connect(
            self._on_media_current_changed
        )

    def set_undo_stack(self, stack: CurationUndoStack | None) -> None:
        self.undo_stack = stack

    def _install_undo_actions(self) -> None:
        undo = QAction("Undo", self)
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.triggered.connect(self._on_undo)
        self.addAction(undo)
        redo = QAction("Redo", self)
        redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo.triggered.connect(self._on_redo)
        self.addAction(redo)

    def _on_undo(self) -> None:
        if self.undo_stack is not None:
            self.undo_stack.undo()

    def _on_redo(self) -> None:
        if self.undo_stack is not None:
            self.undo_stack.redo()

    def _on_media_current_changed(
        self, current: QModelIndex, _previous: QModelIndex
    ) -> None:
        if not current.isValid():
            self.preview_panel.set_media(None)
            return
        self.preview_panel.set_media(self.media_grid.model.row_at(current.row()))
