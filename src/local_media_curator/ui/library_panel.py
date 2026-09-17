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

# Internal view keys stay English; only the displayed labels are Chinese.
_VIEW_NAMES = ("all", "unassigned", "rejected")
_VIEW_LABELS = ("全部", "未分配", "已排除")
_SORT_OPTIONS = (
    ("file_name", "文件名"),
    ("captured_at", "拍摄时间"),
    ("modified_at", "修改时间"),
    ("file_size", "文件大小"),
    ("imported_at", "导入时间"),
)


class LibraryPanel(QWidget):
    view_changed = Signal(str)
    sort_changed = Signal(str)
    filters_changed = Signal()

    _TYPE_OPTIONS = (("全部", None), ("图片", "image"), ("视频", "video"))
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
    _MISSING_OPTIONS = (("任意", None), ("存在", False), ("缺失", True))

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.views = QListWidget(self)
        for label in _VIEW_LABELS:
            self.views.addItem(label)
        self.views.currentRowChanged.connect(self._emit_view_changed)
        self.views.itemClicked.connect(self._on_view_clicked)
        self.sort_combo = QComboBox(self)
        for value, label in _SORT_OPTIONS:
            self.sort_combo.addItem(label, value)
        self.sort_combo.currentIndexChanged.connect(self._emit_sort_changed)
        self.type_combo = QComboBox(self)
        for label, value in self._TYPE_OPTIONS:
            self.type_combo.addItem(label, value)
        self.type_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.extension_combo = QComboBox(self)
        for ext in self._EXTENSION_OPTIONS:
            # Extension values are data and stay verbatim.
            self.extension_combo.addItem(
                "任意扩展名" if ext == "any" else ext, None if ext == "any" else ext
            )
        self.extension_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.folder_combo = QComboBox(self)
        self.folder_combo.addItem("任意文件夹", None)
        self.folder_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.missing_combo = QComboBox(self)
        for label, value in self._MISSING_OPTIONS:
            self.missing_combo.addItem(label, value)
        self.missing_combo.currentIndexChanged.connect(self._emit_filters_changed)
        self.list_panel = ListPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("媒体库"))
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
        self.folder_combo.addItem("任意文件夹", None)
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
