from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtGui import QKeySequence

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


def _window(qtbot, project) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.refresh()
    return window


def test_quick_slots_default_empty(tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    lists = ListService(project)
    assert [lists.quick_slot_list_id(slot) for slot in range(1, 10)] == [None] * 9
    project.close()


def test_bind_list_to_slot(tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    lists = ListService(project)
    website = lists.create("网站")
    lists.bind_quick_slot(3, website)
    assert lists.quick_slot_list_id(3) == website
    assert lists.quick_slot_list_id(1) is None
    project.close()


def test_slot_binding_persists_after_reopen(tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    lists = ListService(project)
    website = lists.create("网站")
    lists.bind_quick_slot(3, website)
    project.close()

    reopened = open_project(tmp_path / "project")
    assert ListService(reopened).quick_slot_list_id(3) == website
    reopened.close()


def test_rename_preserves_quick_slot(tmp_path: Path) -> None:
    project, _ids = _setup(tmp_path)
    lists = ListService(project)
    list_id = lists.create("快捷名单 4")
    lists.bind_quick_slot(4, list_id)
    lists.rename(list_id, "社交媒体")
    assert lists.quick_slot_list_id(4) == list_id
    names = {int(row["id"]): str(row["name"]) for row in lists.all_lists()}
    assert names[list_id] == "社交媒体"
    project.close()


def test_delete_bound_list_clears_slot(tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    lists = ListService(project)
    list_id = lists.create("快捷名单 4")
    lists.bind_quick_slot(4, list_id)
    lists.add_items(list_id, [ids["A.jpg"]])
    lists.delete(list_id)
    assert lists.quick_slot_list_id(4) is None
    project.close()


def test_ensure_quick_slot_api_removed() -> None:
    assert not hasattr(ListService, "ensure_quick_slot")


def test_named_lists_without_bindings_leave_slots_unbound(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    lists = ListService(project)
    lists.create("宣传")
    lists.create("网站")
    lists.create("活动")

    assert [lists.quick_slot_list_id(slot) for slot in range(1, 10)] == [None] * 9
    names = {str(row["name"]) for row in lists.all_lists()}
    assert names == {"宣传", "网站", "活动"}
    assert not any(name.startswith("快捷名单 ") for name in names)
    project.close()


def test_rebind_moves_slot_without_changing_membership(tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    lists = ListService(project)
    website = lists.create("网站")
    home = lists.create("首页候选")
    lists.add_items(website, [ids["A.jpg"]])
    lists.add_items(home, [ids["B.jpg"], ids["C.jpg"]])
    lists.bind_quick_slot(3, website)
    lists.bind_quick_slot(1, home)
    website_members = lists.ordered_media_ids(website)
    home_members = lists.ordered_media_ids(home)

    lists.bind_quick_slot(3, home)

    assert lists.quick_slot_list_id(3) == home
    assert lists.quick_slot_list_id(1) is None
    assert lists.ordered_media_ids(website) == website_members
    assert lists.ordered_media_ids(home) == home_members
    project.close()


def test_unbound_number_key_does_not_create_list(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_actions[3].trigger()
    assert window.list_service.all_lists() == []
    assert window.list_service.quick_slot_list_id(4) is None
    assert "尚未绑定" in window.statusBar().currentMessage()
    project.close()


def test_unbound_number_key_does_not_change_membership(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg", "B.jpg"))
    window = _window(qtbot, project)
    website = window.list_service.create("网站")
    window.list_service.add_items(website, [ids["A.jpg"]])
    before = window.list_service.ordered_media_ids(website)
    window._select_media_ids([ids["B.jpg"]])
    window.quick_slot_actions[2].trigger()
    assert window.list_service.ordered_media_ids(website) == before
    assert window.list_service.quick_slot_list_id(3) is None
    assert ids["B.jpg"] not in window.list_service.ordered_media_ids(website)
    project.close()


def test_unbound_number_key_shows_status_message(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_actions[4].trigger()
    message = window.statusBar().currentMessage()
    assert "尚未绑定" in message
    assert message == "快捷键 5 尚未绑定。请在左侧名单上右键或点「绑定快捷键」。"
    project.close()


def test_number_key_adds_to_user_bound_list(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    list_id = window.list_service.create("网站")
    window.list_service.bind_quick_slot(4, list_id)
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_actions[3].trigger()
    assert window.list_service.ordered_media_ids(list_id) == [ids["A.jpg"]]
    names = {int(row["id"]): str(row["name"]) for row in window.list_service.all_lists()}
    assert names[list_id] == "网站"
    assert "快捷名单 4" not in names.values()
    project.close()


def test_number_key_is_idempotent(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    list_id = window.list_service.create("网站")
    window.list_service.bind_quick_slot(3, list_id)
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_actions[2].trigger()
    list_id = window.list_service.quick_slot_list_id(3)
    before = window.undo_stack._stack.count()
    window.quick_slot_actions[2].trigger()
    assert window.list_service.ordered_media_ids(list_id) == [ids["A.jpg"]]
    assert window.list_service.count(list_id) == 1
    assert window.undo_stack._stack.count() == before
    project.close()


def test_deleted_quick_list_stays_gone_when_number_pressed(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path, ("A.jpg",))
    window = _window(qtbot, project)
    list_id = window.list_service.create("快捷名单 1")
    window.list_service.bind_quick_slot(1, list_id)
    window.confirm_delete = lambda _name: True
    window._on_delete_list(list_id)
    assert window.list_service.all_lists() == []
    window._select_media_ids([ids["A.jpg"]])
    window.quick_slot_actions[0].trigger()
    assert window.list_service.all_lists() == []
    assert window.list_service.quick_slot_list_id(1) is None
    project.close()


def test_number_key_adds_multi_selection_as_one_undo(qtbot, tmp_path: Path) -> None:
    project, ids = _setup(tmp_path)
    window = _window(qtbot, project)
    list_id = window.list_service.create("网站")
    window.list_service.bind_quick_slot(1, list_id)
    window._select_media_ids([ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]])
    before = window.undo_stack._stack.count()
    window.quick_slot_actions[0].trigger()
    list_id = window.list_service.quick_slot_list_id(1)
    assert window.undo_stack._stack.count() == before + 1
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["A.jpg"],
        ids["B.jpg"],
        ids["C.jpg"],
    ]
    window._on_undo()
    assert window.list_service.count(list_id) == 0
    window._on_redo()
    assert window.list_service.count(list_id) == 3
    project.close()


def test_quick_slot_shortcuts_are_one_through_nine(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert len(window.quick_slot_actions) == 9
    for slot, action in enumerate(window.quick_slot_actions, start=1):
        assert action.shortcut() == QKeySequence(str(slot))
