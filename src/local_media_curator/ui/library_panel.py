from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from local_media_curator.ui.list_panel import ListPanel

_VIEW_NAMES = ("all", "unassigned", "rejected")
_SORT_OPTIONS = (
    ("file_name", "File name"),
    ("captured_at", "Capture time"),
    ("modified_at", "Modified time"),
    ("file_size", "File size"),
    ("imported_at", "Import time"),
)


class LibraryPanel(QWidget):
    view_changed = Signal(str)
    sort_changed = Signal(str)
    filters_changed = Signal()

    _TYPE_OPTIONS = (("all", None), ("image", "image"), ("video", "video"))
    _EXTENSION_OPTIONS = (
        "any",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".tif",
        ".tiff",
        ".mp4",
        ".mov",
    )
    _MISSING_OPTIONS = (("any", None), ("present", False), ("missing", True))

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.views = QListWidget(self)
        self.views.addItem("All")
        self.views.addItem("Unassigned")
        self.views.addItem("Rejected")
        self.views.currentRowChanged.connect(self._emit_view_changed)
        self.views.itemClicked.connect(self._on_view_clicked)
        self.sort_combo = QComboBox(self)
        for value, label in _SORT_OPTIONS:
            self.sort_combo.addItem(label, value)
        self.sort_combo.currentIndexChanged.connect(self._emit_sort_changed)
        self.type_combo = QComboBox(self)
        for _label, value in self._TYPE_OPTIONS:
            self.type_combo.addItem(_label.capitalize(), value)
        self.type_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.extension_combo = QComboBox(self)
        for ext in self._EXTENSION_OPTIONS:
            self.extension_combo.addItem(
                "Any extension" if ext == "any" else ext, None if ext == "any" else ext
            )
        self.extension_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.folder_combo = QComboBox(self)
        self.folder_combo.addItem("Any folder", None)
        self.folder_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.missing_combo = QComboBox(self)
        for label, value in self._MISSING_OPTIONS:
            self.missing_combo.addItem(label.capitalize(), value)
        self.missing_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.list_panel = ListPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Library"))
        layout.addWidget(self.sort_combo)
        filters_layout = QVBoxLayout()
        filters_layout.addWidget(self.type_combo)
        filters_layout.addWidget(self.extension_combo)
        filters_layout.addWidget(self.folder_combo)
        filters_layout.addWidget(self.missing_combo)
        layout.addLayout(filters_layout)
        layout.addWidget(self.views)
        layout.addWidget(self.list_panel, stretch=1)

    def current_filters(self) -> dict[str, object]:
        return {
            "media_type": self.type_combo.currentData(),
            "extension": self.extension_combo.currentData(),
            "source_folder": self.folder_combo.currentData(),
            "missing": self.missing_combo.currentData(),
        }

    def set_source_folders(self, paths: list[str]) -> None:
        current = self.folder_combo.currentData()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("Any folder", None)
        for path in paths:
            self.folder_combo.addItem(path, path)
        if current is not None:
            index = self.folder_combo.findData(current)
            if index >= 0:
                self.folder_combo.setCurrentIndex(index)
        self.folder_combo.blockSignals(False)

    def _emit_filters_changed(self, _index: int) -> None:
        self.filters_changed.emit()

    def _on_view_clicked(self, item: QListWidgetItem) -> None:
        self._emit_view_changed(self.views.row(item))

    def _emit_view_changed(self, row: int) -> None:
        if 0 <= row < len(_VIEW_NAMES):
            self.view_changed.emit(_VIEW_NAMES[row])

    def current_sort(self) -> str:
        value = self.sort_combo.currentData()
        return str(value) if value else "file_name"

    def _emit_sort_changed(self, _index: int) -> None:
        self.sort_changed.emit(self.current_sort())
