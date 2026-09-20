from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QComboBox, QInputDialog, QLineEdit, QPlainTextEdit, QTextEdit

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.thumbnail_delegate import quick_slot_badge


def _setup(tmp_path: Path, names: tuple[str, ...] = ("A.jpg", "B.jpg", "C.jpg")):
    project = create_project(tmp_path / "project")
    source = tmp_path / "source"
    source.mkdir()
    for name in names:
        Image.new("RGB", (12, 12), "red").save(source / name, "JPEG")
    library = LibraryService(project)
    library.add_source_folder(source)
    library.scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    return project, ids


def _window(qtbot, project) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.refresh()
    return window


def _visible_id(window: MainWindow, row: int) -> int:
    index = window.media_grid.model.index(row)
    return int(window.media_grid.model.data(index, MediaListModel.IdRole))


def _current_id(window: MainWindow) -> int | None:
    index = window.media_grid.view.currentIndex()
    if not index.isValid():
        return None
    value = window.media_grid.model.data(index, MediaListModel.IdRole)
    return int(value) if value is not None else None


def test_shift_number_adds_and_advances(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    window = _window(qtbot, project)
    first = _visible_id(window, 0)
    second = _visible_id(window, 1)
    window._select_media_ids([first])
    list_id = window.list_service.create("网站")
    window.list_service.bind_quick_slot(7, list_id)
    window.quick_slot_shift_actions[6].trigger()
    list_id = window.list_service.quick_slot_list_id(7)
    assert list_id is not None
    assert window.list_service.ordered_media_ids(list_id) == [first]
    assert _current_id(window) == second
    assert window.quick_slot_shift_actions[6].shortcut() == QKeySequence("Shift+7")
    project.close()


def test_unbound_shift_number_does_not_create_list(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg", "B.jpg"))
    window = _window(qtbot, project)
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_shift_actions[0].trigger()
    assert window.list_service.all_lists() == []
    assert window.list_service.quick_slot_list_id(1) is None
    assert "尚未绑定" in window.statusBar().currentMessage()
    project.close()


def test_unbound_shift_number_does_not_advance(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    window = _window(qtbot, project)
    first = _visible_id(window, 0)
    window._select_media_ids([first])
    assert _current_id(window) == first
    window.quick_slot_shift_actions[2].trigger()
    assert window.list_service.all_lists() == []
    assert window.list_service.quick_slot_list_id(3) is None
    assert _current_id(window) == first
    project.close()


def test_shift_number_advances_when_already_member(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    window = _window(qtbot, project)
    first = _visible_id(window, 0)
    second = _visible_id(window, 1)
    window._select_media_ids([first])
    list_id = window.list_service.create("网站")
    window.list_service.bind_quick_slot(1, list_id)
    window.quick_slot_actions[0].trigger()
    list_id = window.list_service.quick_slot_list_id(1)
    window._select_media_ids([first])
    window.quick_slot_shift_actions[0].trigger()
    assert window.list_service.ordered_media_ids(list_id) == [first]
    assert _current_id(window) == second
    project.close()


@pytest.mark.parametrize(
    "editor_factory",
    [QLineEdit, QTextEdit, QPlainTextEdit, QInputDialog],
)
def test_number_shortcuts_ignored_in_text_editors(
    qtbot, tmp_path: Path, editor_factory
) -> None:
    project, ids = _setup(tmp_path, ("A.jpg", "B.jpg"))
    window = _window(qtbot, project)
    window.show()
    qtbot.wait(10)
    slot_one = window.list_service.create("网站")
    slot_two = window.list_service.create("首页候选")
    window.list_service.bind_quick_slot(1, slot_one)
    window.list_service.bind_quick_slot(2, slot_two)
    window.refresh()
    window._select_media_ids([ids["A.jpg"]])
    editor = editor_factory(window)
    qtbot.addWidget(editor)
    editor.show()
    focus_target = editor
    if isinstance(editor, QInputDialog):
        editor.setInputMode(QInputDialog.InputMode.TextInput)
        focus_target = editor.findChild(QLineEdit)
    assert focus_target is not None
    focus_target.setFocus()
    qtbot.waitUntil(lambda: focus_target.hasFocus())

    window.quick_slot_actions[0].trigger()
    window.quick_slot_shift_actions[1].trigger()
    assert window.list_service.ordered_media_ids(slot_one) == []
    assert window.list_service.ordered_media_ids(slot_two) == []
    assert window.media_grid.selected_ids() == [ids["A.jpg"]]
    assert _current_id(window) == ids["A.jpg"]
    project.close()


def test_number_shortcuts_ignored_in_editable_combobox(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg", "B.jpg"))
    window = _window(qtbot, project)
    window.show()
    qtbot.wait(10)
    slot_three = window.list_service.create("网站")
    window.list_service.bind_quick_slot(3, slot_three)
    window.refresh()
    window._select_media_ids([ids["A.jpg"]])
    combo = QComboBox(window)
    combo.setEditable(True)
    combo.addItem("输入")
    qtbot.addWidget(combo)
    combo.show()
    combo.lineEdit().setFocus()
    qtbot.waitUntil(lambda: combo.lineEdit().hasFocus())

    window.quick_slot_actions[2].trigger()
    window.quick_slot_shift_actions[2].trigger()
    assert window.list_service.ordered_media_ids(slot_three) == []
    assert window.media_grid.selected_ids() == [ids["A.jpg"]]
    assert _current_id(window) == ids["A.jpg"]
    project.close()


def test_rebind_occupied_slot_requires_confirmation(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg", "B.jpg"))
    window = _window(qtbot, project)
    lists = window.list_service
    website = lists.create("网站")
    home = lists.create("首页候选")
    lists.add_items(website, [ids["A.jpg"]])
    lists.add_items(home, [ids["B.jpg"]])
    lists.bind_quick_slot(3, website)
    lists.bind_quick_slot(1, home)
    prompts: list[str] = []

    def deny(text: str) -> bool:
        prompts.append(text)
        return False

    window.confirm_quick_rebind = deny
    window._on_bind_quick_slot(home, 3)
    assert prompts
    assert "快捷键 3" in prompts[0]
    assert "网站" in prompts[0]
    assert "首页候选" in prompts[0]
    assert lists.quick_slot_list_id(3) == website
    assert lists.ordered_media_ids(website) == [ids["A.jpg"]]
    assert lists.ordered_media_ids(home) == [ids["B.jpg"]]

    window.confirm_quick_rebind = lambda _text: True
    window._on_bind_quick_slot(home, 3)
    assert lists.quick_slot_list_id(3) == home
    assert lists.quick_slot_list_id(1) is None
    assert lists.ordered_media_ids(website) == [ids["A.jpg"]]
    assert lists.ordered_media_ids(home) == [ids["B.jpg"]]
    project.close()


def test_empty_slot_bind_skips_confirmation(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    home = window.list_service.create("首页候选")
    called: list[str] = []
    window.confirm_quick_rebind = lambda text: called.append(text) or False
    window._on_bind_quick_slot(home, 5)
    assert called == []
    assert window.list_service.quick_slot_list_id(5) == home
    project.close()


def test_list_context_menu_offers_bind_and_clear(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    list_id = window.list_service.create("备用")
    window.list_service.bind_quick_slot(2, list_id)
    window.refresh()
    menu = window.list_panel.context_menu_for(list_id)
    titles = [action.text() for action in menu.actions()]
    assert "绑定快捷键" in titles
    assert "取消快捷键" in titles
    assert "删除名单" in titles
    bind = next(action.menu() for action in menu.actions() if action.text() == "绑定快捷键")
    labels = [action.text() for action in bind.actions()]
    assert labels[0] == "1  未绑定"
    assert labels[1] == "2  备用"
    assert bind.actions()[1].isChecked()
    project.close()


def test_list_panel_displays_slot_number(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    picked = window.list_service.create("精选")
    spare = window.list_service.create("备用")
    window.list_service.bind_quick_slot(1, picked)
    window.refresh()
    texts = [
        window.list_panel.lists_widget.item(i).text()
        for i in range(window.list_panel.lists_widget.count())
    ]
    assert "[1] 精选" in texts
    assert "备用" in texts
    assert "[1] 备用" not in texts
    project.close()


def test_grid_displays_quick_slot_membership(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    lists = window.list_service
    first = lists.create("精选")
    third = lists.create("网站")
    lists.bind_quick_slot(1, first)
    lists.bind_quick_slot(3, third)
    lists.add_items(first, [ids["A.jpg"]])
    lists.add_items(third, [ids["A.jpg"]])
    window.refresh()
    index = window.media_grid.model.index(0)
    slots = window.media_grid.model.data(index, MediaListModel.QuickSlotsRole)
    assert slots == [1, 3]
    assert quick_slot_badge(slots) == "1 3"
    project.close()


def test_quick_slot_shortcuts_are_in_edit_menu(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    edit = next(
        action.menu()
        for action in window.menuBar().actions()
        if action.text() == "编辑"
    )
    shortcuts = {action.shortcut(): action.text() for action in edit.actions()}
    assert shortcuts[QKeySequence("1")] == "添加到快捷名单 1"
    assert shortcuts[QKeySequence("Shift+9")] == "添加到快捷名单并前进 9"
