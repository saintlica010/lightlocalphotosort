from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from local_media_curator.ui.list_panel import ListPanel


class LibraryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.views = QListWidget(self)
        self.views.addItem("All")
        self.views.addItem("Unassigned")
        self.views.addItem("Rejected")
        self.list_panel = ListPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Library"))
        layout.addWidget(self.views)
        layout.addWidget(self.list_panel, stretch=1)
