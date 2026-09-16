from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from local_media_curator.ui.list_panel import ListPanel

_VIEW_NAMES = ("all", "unassigned", "rejected")


class LibraryPanel(QWidget):
    view_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.views = QListWidget(self)
        self.views.addItem("All")
        self.views.addItem("Unassigned")
        self.views.addItem("Rejected")
        self.views.currentRowChanged.connect(self._emit_view_changed)
        self.views.itemClicked.connect(self._on_view_clicked)
        self.list_panel = ListPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Library"))
        layout.addWidget(self.views)
        layout.addWidget(self.list_panel, stretch=1)

    def _on_view_clicked(self, item: QListWidgetItem) -> None:
        self._emit_view_changed(self.views.row(item))

    def _emit_view_changed(self, row: int) -> None:
        if 0 <= row < len(_VIEW_NAMES):
            self.view_changed.emit(_VIEW_NAMES[row])
