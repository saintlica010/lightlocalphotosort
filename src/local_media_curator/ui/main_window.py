from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.library_panel = QWidget()
        self.media_grid = QWidget()
        self.preview_panel = QWidget()
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.media_grid)
        splitter.addWidget(self.preview_panel)
        self.setCentralWidget(splitter)
