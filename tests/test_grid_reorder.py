from pathlib import Path

from PIL import Image
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView

from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.thumbnail_delegate import ordinal_label


def test_drop_reorders_ids_and_emits(qtbot) -> None:
    model = MediaListModel(
        [
            {"id": 1, "file_name": "A.jpg", "ordinal": 1},
            {"id": 2, "file_name": "B.jpg", "ordinal": 2},
            {"id": 3, "file_name": "C.jpg", "ordinal": 3},
        ]
    )
    model.set_manual_order_enabled(True)
    with qtbot.waitSignal(model.orderChanged, timeout=1000) as blocker:
        parent = QModelIndex()
        mime = model.mimeData([model.index(0, 0)])
        assert model.dropMimeData(mime, Qt.DropAction.MoveAction, 3, 0, parent)
    assert blocker.args[0] == [2, 3, 1]
    assert [model.data(model.index(i), MediaListModel.IdRole) for i in range(3)] == [
        2,
        3,
        1,
    ]


def test_flags_include_drag_drop_when_manual_order_enabled() -> None:
    model = MediaListModel([{"id": 1, "file_name": "A.jpg", "ordinal": 1}])
    index = model.index(0)
    disabled = model.flags(index)
    assert disabled & Qt.ItemFlag.ItemIsEnabled
    assert disabled & Qt.ItemFlag.ItemIsSelectable
    assert not (disabled & Qt.ItemFlag.ItemIsDragEnabled)
    assert not (disabled & Qt.ItemFlag.ItemIsDropEnabled)
    model.set_manual_order_enabled(True)
    enabled = model.flags(index)
    assert enabled & Qt.ItemFlag.ItemIsDragEnabled
    assert enabled & Qt.ItemFlag.ItemIsDropEnabled
    assert enabled & Qt.ItemFlag.ItemIsSelectable
    assert enabled & Qt.ItemFlag.ItemIsEnabled


def test_drop_ignored_when_manual_order_disabled() -> None:
    model = MediaListModel(
        [
            {"id": 1, "file_name": "A.jpg", "ordinal": 1},
            {"id": 2, "file_name": "B.jpg", "ordinal": 2},
        ]
    )
    mime = model.mimeData([model.index(0, 0)])
    assert not model.dropMimeData(
        mime, Qt.DropAction.MoveAction, 2, 0, QModelIndex()
    )
    assert model.data(model.index(0), MediaListModel.IdRole) == 1


def test_ordinal_label_formats_two_digits() -> None:
    assert ordinal_label(1) == "01"
    assert ordinal_label(2) == "02"
    assert ordinal_label(12) == "12"
    assert ordinal_label(None) is None


def test_grid_forwards_manual_order_to_model(qtbot) -> None:
    grid = MediaGrid()
    qtbot.addWidget(grid)
    grid.model.set_rows([{"id": 1, "file_name": "A.jpg", "ordinal": 1}])
    grid.set_manual_order_enabled(True)
    flags = grid.model.flags(grid.model.index(0))
    assert flags & Qt.ItemFlag.ItemIsDragEnabled
    assert flags & Qt.ItemFlag.ItemIsDropEnabled
    grid.set_manual_order_enabled(False)
    flags = grid.model.flags(grid.model.index(0))
    assert not (flags & Qt.ItemFlag.ItemIsDragEnabled)


def _jpeg(path: Path) -> None:
    Image.new("RGB", (20, 20), "red").save(path, "JPEG")


def _open_scanned_window(qtbot, tmp_path: Path, names: tuple[str, ...]):
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
    return window, project


def test_apply_grid_order_persists_named_list(qtbot, tmp_path: Path) -> None:
    window, project = _open_scanned_window(qtbot, tmp_path, ("A.jpg", "B.jpg"))
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(list_id, [ids["A.jpg"], ids["B.jpg"]])
    window.show_list(list_id)
    window.apply_grid_order([ids["B.jpg"], ids["A.jpg"]])
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    model = window.media_grid.model
    assert [
        int(model.data(model.index(i), MediaListModel.IdRole))
        for i in range(model.rowCount())
    ] == [ids["B.jpg"], ids["A.jpg"]]
    project.close()


def test_order_changed_signal_persists_named_list(qtbot, tmp_path: Path) -> None:
    window, project = _open_scanned_window(qtbot, tmp_path, ("A.jpg", "B.jpg"))
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(list_id, [ids["A.jpg"], ids["B.jpg"]])
    window.show_list(list_id)
    window.media_grid.model.orderChanged.emit([ids["B.jpg"], ids["A.jpg"]])
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    project.close()


def test_library_views_keep_drag_disabled(qtbot, tmp_path: Path) -> None:
    window, project = _open_scanned_window(qtbot, tmp_path, ("A.jpg", "B.jpg"))
    window.show_library_view("all")
    assert (
        window.media_grid.view.dragDropMode()
        == QAbstractItemView.DragDropMode.NoDragDrop
    )
    flags = window.media_grid.model.flags(window.media_grid.model.index(0))
    assert not (flags & Qt.ItemFlag.ItemIsDragEnabled)
    assert window.media_grid.model.data(
        window.media_grid.model.index(0), MediaListModel.OrdinalRole
    ) is None
    list_id = window.list_service.create("Promotional")
    media_id = int(window.media_grid.model.row_at(0)["id"])
    window.add_items_to_list(list_id, [media_id])
    window.show_list(list_id)
    assert (
        window.media_grid.view.dragDropMode()
        == QAbstractItemView.DragDropMode.InternalMove
    )
    list_flags = window.media_grid.model.flags(window.media_grid.model.index(0))
    assert list_flags & Qt.ItemFlag.ItemIsDragEnabled
    assert window.media_grid.model.data(
        window.media_grid.model.index(0), MediaListModel.OrdinalRole
    ) == 1
    project.close()
