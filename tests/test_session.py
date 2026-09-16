from pathlib import Path

from PIL import Image
from PySide6.QtGui import QKeySequence

from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_model import MediaListModel


def _jpeg(path: Path) -> None:
    Image.new("RGB", (40, 30), "red").save(path, "JPEG")


def _open_scanned_window(qtbot, tmp_path: Path, names: tuple[str, ...] = ("A.jpg", "B.jpg")):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for name in names:
        _jpeg(source / name)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(
        lambda: window.media_grid.model.rowCount() == len(names),
        timeout=8000,
    )
    return window, project, source


def test_set_project_scan_populates_grid(qtbot, tmp_path: Path) -> None:
    window, project, source = _open_scanned_window(qtbot, tmp_path)
    model = window.media_grid.model
    assert model.rowCount() == 2
    rows = [model.row_at(i) for i in range(model.rowCount())]
    assert {row["file_name"] for row in rows} == {"A.jpg", "B.jpg"}
    for row in rows:
        assert row["id"]
        assert Path(str(row["absolute_path"])).is_file()
        assert row["rejected"] is False
        assert "ordinal" in row
        thumb = Path(str(row["thumbnail_path"]))
        assert thumb.is_file()
        assert project.thumbnails_dir in thumb.parents
        assert not any(source.rglob("*.webp"))
    project.close()


def test_reject_via_stack_hides_from_default_list_media(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path)
    media_id = int(window.media_grid.model.row_at(0)["id"])
    window.undo_stack.reject([media_id])
    visible = window.library_service.list_media(include_rejected=False)
    assert all(item.id != media_id for item in visible)
    window.refresh()
    remaining = [
        window.media_grid.model.data(
            window.media_grid.model.index(i), MediaListModel.IdRole
        )
        for i in range(window.media_grid.model.rowCount())
    ]
    assert media_id not in remaining
    assert window.media_grid.model.rowCount() == 1
    project.close()


def test_file_menu_has_project_actions(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    titles: list[str] = []
    for action in window.menuBar().actions():
        menu = action.menu()
        if menu is None:
            continue
        titles.extend(
            child.text() for child in menu.actions() if not child.isSeparator()
        )
    assert "New Project" in titles
    assert "Open Project" in titles
    assert "Add Source Folder" in titles
    assert "Scan" in titles


def test_library_views_switch_grid(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path)
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(list_id, [ids["A.jpg"]])
    window.undo_stack.reject([ids["B.jpg"]])
    window.refresh()

    window.show_library_view("all")
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "A.jpg"

    window.show_library_view("unassigned")
    assert window.media_grid.model.rowCount() == 0

    window.show_library_view("rejected")
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "B.jpg"

    window.show_list(list_id)
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "A.jpg"
    project.close()


def test_delete_rejects_selection_via_undo_stack(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path, ("A.jpg",))
    index = window.media_grid.model.index(0)
    window.media_grid.view.setCurrentIndex(index)
    reject = next(
        action
        for action in window.actions()
        if action.shortcut() == QKeySequence(QKeySequence.StandardKey.Delete)
    )
    reject.trigger()
    assert window.library_service.list_media(include_rejected=False) == []
    assert window.media_grid.model.rowCount() == 0
    window.undo_stack.undo()
    window.refresh()
    assert [item.file_name for item in window.library_service.list_media()] == ["A.jpg"]
    assert window.media_grid.model.rowCount() == 1
    project.close()


def test_reselecting_all_media_after_named_list_restores_library(
    qtbot, tmp_path: Path
) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path)
    list_id = window.list_service.create("Promotional")
    window.refresh()
    a_id = next(
        int(window.media_grid.model.row_at(i)["id"])
        for i in range(window.media_grid.model.rowCount())
        if window.media_grid.model.row_at(i)["file_name"] == "A.jpg"
    )
    window.add_items_to_list(list_id, [a_id])

    window._on_named_list_changed(list_id)
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "A.jpg"

    views = window.library_panel.views
    views.setCurrentRow(0)
    all_item = views.item(0)
    assert all_item is not None
    views.itemClicked.emit(all_item)

    names = {
        window.media_grid.model.row_at(i)["file_name"]
        for i in range(window.media_grid.model.rowCount())
    }
    assert names == {"A.jpg", "B.jpg"}
    project.close()


def test_reject_clears_preview_when_grid_empty(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path, ("A.jpg",))
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    assert window.preview_panel.file_name_label.text() == "A.jpg"

    window.reject_selection()

    assert window.media_grid.model.rowCount() == 0
    assert window.preview_panel.file_name_label.text() == ""
    project.close()


def test_add_and_remove_selection_on_virtual_list(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path, ("A.jpg",))
    list_id = window.list_service.create("Promotional")
    window.refresh()
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    window.add_selection_to_list(list_id)
    assert window.list_service.ordered_media_ids(list_id) == [
        int(window.media_grid.model.row_at(0)["id"])
    ]
    window.show_list(list_id)
    assert window.media_grid.model.rowCount() == 1
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    window.remove_selection_from_list(list_id)
    assert window.list_service.ordered_media_ids(list_id) == []
    assert window.media_grid.model.rowCount() == 0
    project.close()


def test_add_to_list_from_all_media_uses_picker(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(qtbot, tmp_path, ("A.jpg",))
    list_id = window.list_service.create("Promotional")
    window.refresh()
    window.show_library_view("all")
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    media_id = int(window.media_grid.model.row_at(0)["id"])
    window.list_name_picker = lambda _names: "Promotional"
    add = next(action for action in window.actions() if action.text() == "Add to List")
    add.trigger()
    assert window.list_service.ordered_media_ids(list_id) == [media_id]
    project.close()


def test_move_selection_on_named_list_persists(qtbot, tmp_path: Path) -> None:
    window, project, _source = _open_scanned_window(
        qtbot, tmp_path, ("A.jpg", "B.jpg")
    )
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(list_id, [ids["A.jpg"], ids["B.jpg"]])
    window.show_list(list_id)
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    window.move_selection(1)
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    root = project.root
    project.close()
    reopened = open_project(root)
    assert ListService(reopened).ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    reopened.close()
