from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from local_media_curator.ui.dialogs import ask_item, ask_text


class ListPanel(QWidget):
    create_requested = Signal(str)
    rename_requested = Signal(int, str)
    delete_requested = Signal(int)
    current_list_changed = Signal(object)
    set_target_requested = Signal(int)
    bind_slot_requested = Signal(int, int)
    unbind_slot_requested = Signal(int)
    lightroom_export_requested = Signal(int)
    NameRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lists_widget = QListWidget(self)
        self.lists_widget.setObjectName("namedLists")
        self.new_button = QPushButton("新建")
        self.rename_button = QPushButton("重命名")
        self.delete_button = QPushButton("删除")
        self.set_target_button = QPushButton("设为目标名单")
        self.bind_button = QPushButton("绑定快捷键")
        self._list_rows: list[Mapping[str, object]] = []
        self.new_button.clicked.connect(self._on_new)
        self.rename_button.clicked.connect(self._on_rename)
        self.delete_button.clicked.connect(self._on_delete)
        self.set_target_button.clicked.connect(self._on_set_target)
        self.bind_button.clicked.connect(self._on_bind_button)
        self.lists_widget.currentItemChanged.connect(self._on_current_changed)
        self.lists_widget.itemClicked.connect(self._on_item_clicked)
        self.lists_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lists_widget.customContextMenuRequested.connect(self._show_context_menu)

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("名单"))
        self.target_label = QLabel("目标名单：未设置")
        self.target_label.setObjectName("targetListLabel")
        layout.addWidget(self.target_label)
        layout.addWidget(self.lists_widget, stretch=1)
        layout.addLayout(buttons)
        layout.addWidget(self.bind_button)
        layout.addWidget(self.set_target_button)

    def set_target_list(self, name: str | None) -> None:
        if name:
            self.target_label.setText(f"目标名单：★ {name}")
        else:
            self.target_label.setText("目标名单：未设置")

    def set_lists(self, rows: Sequence[Mapping[str, object]]) -> None:
        current_id = self.selected_list_id()
        self._list_rows = [dict(row) for row in rows]
        self.lists_widget.clear()
        restore: QListWidgetItem | None = None
        for row in rows:
            name = str(row.get("name") or "")
            slot = row.get("quick_slot")
            label = f"[{int(slot)}] {name}" if slot else name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
            item.setData(self.NameRole, name)
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
        name = ask_text(self, "新建名单", "名称：")
        if name and name.strip():
            self.create_requested.emit(name.strip())

    def _on_rename(self) -> None:
        list_id = self.selected_list_id()
        if list_id is None:
            return
        item = self.lists_widget.currentItem()
        stored = item.data(self.NameRole) if item is not None else None
        current = str(stored) if stored else (item.text() if item is not None else "")
        name = ask_text(self, "重命名名单", "名称：", text=current)
        if name and name.strip():
            self.rename_requested.emit(list_id, name.strip())

    def _on_delete(self) -> None:
        list_id = self.selected_list_id()
        if list_id is None:
            return
        self.delete_requested.emit(list_id)

    def _on_set_target(self) -> None:
        list_id = self.selected_list_id()
        if list_id is not None:
            self.set_target_requested.emit(list_id)

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

    def slot_choice_labels(self) -> list[str]:
        return [self._slot_label(slot) for slot in range(1, 10)]

    def _slot_label(self, slot: int) -> str:
        occupant = next(
            (
                str(row.get("name") or "")
                for row in self._list_rows
                if row.get("quick_slot") == slot
            ),
            None,
        )
        return f"{slot}  {occupant}" if occupant else f"{slot}  未绑定"

    def _on_bind_button(self) -> None:
        list_id = self.selected_list_id()
        if list_id is None:
            return
        labels = self.slot_choice_labels()
        chosen = ask_item(self, "绑定快捷键", "快捷键：", labels)
        if not chosen:
            return
        slot = int(str(chosen).split()[0])
        self.bind_slot_requested.emit(list_id, slot)

    def context_menu_for(self, list_id: int) -> QMenu:
        menu = QMenu(self)
        bind_menu = menu.addMenu("绑定快捷键")
        current_slot = next(
            (
                row.get("quick_slot")
                for row in self._list_rows
                if int(row["id"]) == list_id
            ),
            None,
        )
        for slot in range(1, 10):
            action = QAction(self._slot_label(slot), bind_menu)
            action.setCheckable(True)
            action.setChecked(current_slot == slot)
            action.triggered.connect(
                lambda _checked=False, slot=slot, list_id=list_id: self.bind_slot_requested.emit(
                    list_id, slot
                )
            )
            bind_menu.addAction(action)
        clear = QAction("取消快捷键", menu)
        clear.triggered.connect(
            lambda _checked=False, list_id=list_id: self.unbind_slot_requested.emit(list_id)
        )
        menu.addAction(clear)
        delete = QAction("删除名单", menu)
        delete.triggered.connect(
            lambda _checked=False, list_id=list_id: self.delete_requested.emit(list_id)
        )
        menu.addAction(delete)
        export = QAction("导出 Lightroom 智能收藏夹（实验性）...", menu)
        export.triggered.connect(
            lambda _checked=False, list_id=list_id: self.lightroom_export_requested.emit(list_id)
        )
        menu.addAction(export)
        return menu

    def _show_context_menu(self, pos) -> None:
        item = self.lists_widget.itemAt(pos)
        if item is None:
            return
        value = item.data(Qt.ItemDataRole.UserRole)
        if value is None:
            return
        self.context_menu_for(int(value)).exec(self.lists_widget.mapToGlobal(pos))

