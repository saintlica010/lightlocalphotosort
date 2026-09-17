from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QComboBox, QInputDialog, QLineEdit, QPlainTextEdit, QTextEdit

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project
from local_media_curator.ui.main_window import MainWindow


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


def _current_id(window: MainWindow) -> int | None:
    index = window.media_grid.view.currentIndex()
    if not index.isValid():
        return None
    value = window.media_grid.model.data(index, window.media_grid.model.IdRole)
    return int(value) if value is not None else None


def test_shift_p_x_u_advances(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.show()
    qtbot.wait(10)

    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    window.pick_and_advance_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "picked"
    assert _current_id(window) == ids["B.jpg"]

    window.culling_reject_and_advance_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["B.jpg"],)
    ).fetchone()[0] == "rejected"
    assert _current_id(window) == ids["C.jpg"]

    window.undecide_and_advance_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["C.jpg"],)
    ).fetchone()[0] == "undecided"
    # At the end there is no next row, so the current row remains stable.
    assert _current_id(window) == ids["C.jpg"]
    project.close()


def test_phase2b_shortcuts_are_exposed_in_actions(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.pick_and_advance_action.shortcut() == QKeySequence("Shift+P")
    assert window.culling_reject_and_advance_action.shortcut() == QKeySequence("Shift+X")
    assert window.undecide_and_advance_action.shortcut() == QKeySequence("Shift+U")
    assert window.target_toggle_action.shortcut() == QKeySequence("B")
    assert window.target_add_and_advance_action.shortcut() == QKeySequence("Shift+B")


def test_target_list_persists(tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    lists = ListService(project)
    target_id = lists.create("Website")
    lists.set_target_list(target_id)
    project.close()

    reopened = open_project(tmp_path / "project")
    assert ListService(reopened).target_list_id() == target_id
    reopened.close()


def test_b_adds_and_removes_with_multi_selection(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.show()
    qtbot.wait(10)
    target_id = window.list_service.create("Website")
    other_id = window.list_service.create("Other")
    window.list_service.add_items(other_id, [ids["C.jpg"], ids["A.jpg"]])
    other_order = window.list_service.items_with_sort_keys(other_id)
    window.list_service.set_target_list(target_id)
    window.refresh()

    window._select_media_ids([ids["A.jpg"], ids["B.jpg"]])
    window.target_toggle_action.trigger()
    assert window.list_service.ordered_media_ids(target_id) == [ids["A.jpg"], ids["B.jpg"]]
    assert window.list_service.items_with_sort_keys(other_id) == other_order

    window._select_media_ids([ids["A.jpg"], ids["B.jpg"]])
    window.target_toggle_action.trigger()
    assert window.list_service.ordered_media_ids(target_id) == []
    assert window.list_service.items_with_sort_keys(other_id) == other_order
    project.close()


def test_shift_b_advances_and_is_not_toggle(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    target_id = window.list_service.create("Website")
    window.list_service.set_target_list(target_id)
    window.refresh()
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))

    window.target_add_and_advance_action.trigger()
    assert window.list_service.ordered_media_ids(target_id) == [ids["A.jpg"]]
    assert _current_id(window) == ids["B.jpg"]

    window._select_media_ids([ids["A.jpg"]])
    window.target_add_and_advance_action.trigger()
    assert window.list_service.ordered_media_ids(target_id) == [ids["A.jpg"]]
    project.close()


def test_target_membership_undo_redo_is_one_operation(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    target_id = window.list_service.create("Website")
    window.list_service.set_target_list(target_id)
    window.refresh()
    window._select_media_ids([ids["A.jpg"], ids["B.jpg"]])

    before = window.undo_stack._stack.count()
    window.target_toggle_action.trigger()
    assert window.undo_stack._stack.count() == before + 1
    assert window.list_service.count(target_id) == 2
    window._on_undo()
    assert window.list_service.count(target_id) == 0
    window._on_redo()
    assert window.list_service.count(target_id) == 2
    project.close()


@pytest.mark.parametrize(
    "editor_factory",
    [QLineEdit, QTextEdit, QPlainTextEdit, QInputDialog],
)
def test_shortcuts_ignored_when_editing_text(qtbot, tmp_path: Path, editor_factory) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.show()
    qtbot.wait(10)
    target_id = window.list_service.create("Website")
    window.list_service.set_target_list(target_id)
    window.refresh()
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

    window.pick_action.trigger()
    window.target_toggle_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "undecided"
    assert window.list_service.count(target_id) == 0
    project.close()


def test_shortcuts_ignored_when_editing_combo(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.show()
    qtbot.wait(10)
    target_id = window.list_service.create("Website")
    window.list_service.set_target_list(target_id)
    window.refresh()
    combo = QComboBox(window)
    combo.setEditable(True)
    combo.addItem("输入")
    qtbot.addWidget(combo)
    combo.show()
    combo.lineEdit().setFocus()
    qtbot.waitUntil(lambda: combo.lineEdit().hasFocus())

    window.culling_reject_action.trigger()
    window.target_toggle_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "undecided"
    assert window.list_service.count(target_id) == 0
    project.close()


def test_deleting_target_list_clears_setting_and_indicator(qtbot, tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    target_id = window.list_service.create("Website")
    window.list_service.set_target_list(target_id)
    window.refresh()
    assert window.target_list_id == target_id

    window.confirm_delete = lambda _name: True
    window._on_delete_list(target_id)
    assert window.list_service.target_list_id() is None
    assert window.target_list_label.text() == "目标名单：未设置"
    project.close()
