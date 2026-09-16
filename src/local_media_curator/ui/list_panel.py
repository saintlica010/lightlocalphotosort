from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ListPanel(QWidget):
    create_requested = Signal(str)
    rename_requested = Signal(int, str)
    delete_requested = Signal(int)
    current_list_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lists_widget = QListWidget(self)
        self.new_button = QPushButton("New")
        self.rename_button = QPushButton("Rename")
        self.delete_button = QPushButton("Delete")
        self.new_button.clicked.connect(self._on_new)
        self.rename_button.clicked.connect(self._on_rename)
        self.delete_button.clicked.connect(self._on_delete)
        self.lists_widget.currentItemChanged.connect(self._on_current_changed)
        self.lists_widget.itemClicked.connect(self._on_item_clicked)

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Lists"))
        layout.addWidget(self.lists_widget, stretch=1)
        layout.addLayout(buttons)

    def set_lists(self, rows: Sequence[Mapping[str, object]]) -> None:
        current_id = self.selected_list_id()
        self.lists_widget.clear()
        restore: QListWidgetItem | None = None
        for row in rows:
            item = QListWidgetItem(str(row.get("name") or ""))
            item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
            self.lists_widget.addItem(item)
            if current_id is not None and int(row["id"]) == current_id:
                restore = item
        if restore is not None:
            self.lists_widget.setCurrentItem(restore)

    def selected_list_id(self) -> int | None:
        item = self.lists_widget.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _on_new(self) -> None:
        name, ok = QInputDialog.getText(self, "New list", "Name:")
        if ok and name.strip():
            self.create_requested.emit(name.strip())

    def _on_rename(self) -> None:
        list_id = self.selected_list_id()
        if list_id is None:
            return
        item = self.lists_widget.currentItem()
        current = item.text() if item is not None else ""
        name, ok = QInputDialog.getText(self, "Rename list", "Name:", text=current)
        if ok and name.strip():
            self.rename_requested.emit(list_id, name.strip())

    def _on_delete(self) -> None:
        list_id = self.selected_list_id()
        if list_id is None:
            return
        self.delete_requested.emit(list_id)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self._on_current_changed(item, None)

    def _on_current_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self.current_list_changed.emit(None)
            return
        value = current.data(Qt.ItemDataRole.UserRole)
        self.current_list_changed.emit(int(value) if value is not None else None)
