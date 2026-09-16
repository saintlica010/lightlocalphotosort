from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QAbstractItemView, QListView

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.media_grid import MediaGrid


def _setup(tmp_path: Path):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    ids = {
        row["file_name"]: row["id"]
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    return project, lists, ids


def test_lists_have_independent_order(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    photo_a, photo_b = ids["A.jpg"], ids["B.jpg"]
    promotional = lists.create("Promotional")
    website = lists.create("Website")
    lists.add_items(promotional, [photo_a, photo_b])
    lists.add_items(website, [photo_b, photo_a])
    assert lists.ordered_media_ids(promotional) == [photo_a, photo_b]
    assert lists.ordered_media_ids(website) == [photo_b, photo_a]
    project.close()


def test_reorder_first_middle_last(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    Image.new("RGB", (10, 10)).save(tmp_path / "src" / "C.jpg", "JPEG")
    LibraryService(project).scan()
    ids = {
        row["file_name"]: row["id"]
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lst = lists.create("Promotional")
    a, b, c = ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]
    lists.add_items(lst, [a, b, c])
    lists.reorder(lst, [c, a, b])
    assert lists.ordered_media_ids(lst) == [c, a, b]
    lists.reorder(lst, [c, b, a])
    assert lists.ordered_media_ids(lst) == [c, b, a]
    lists.reorder(lst, [a, b, c])
    assert lists.ordered_media_ids(lst) == [a, b, c]
    project.close()


def test_sort_key_normalization(tmp_path: Path) -> None:
    from local_media_curator.domain.ordering import normalize_list

    assert normalize_list([1, 2, 3]) == [1024, 2048, 3072]


def test_reorder_multiple_selection(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    Image.new("RGB", (10, 10)).save(tmp_path / "src" / "C.jpg", "JPEG")
    LibraryService(project).scan()
    ids = {
        row["file_name"]: row["id"]
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lst = lists.create("Promotional")
    a, b, c = ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]
    lists.add_items(lst, [a, b, c])
    lists.move_to_ends(lst, [a, b], end=True)
    assert lists.ordered_media_ids(lst) == [c, a, b]
    project.close()


def _sort_keys(project, list_id: int) -> list[int]:
    return [
        int(row[0])
        for row in project.connection.execute(
            "SELECT sort_key FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (list_id,),
        )
    ]


def test_next_sort_key_and_sort_key_between() -> None:
    from local_media_curator.domain.ordering import (
        SORT_KEY_GAP,
        next_sort_key,
        sort_key_between,
    )

    assert next_sort_key(None) == SORT_KEY_GAP
    assert next_sort_key(1024) == 2048
    assert sort_key_between(1024, 2048) == 1536
    assert sort_key_between(1024, 1025) is None
    assert sort_key_between(None, 1024) == 512
    assert sort_key_between(3072, None) == 4096
    assert sort_key_between(None, None) == SORT_KEY_GAP


def test_reorder_one_list_does_not_change_another(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    photo_a, photo_b = ids["A.jpg"], ids["B.jpg"]
    promotional = lists.create("Promotional")
    website = lists.create("Website")
    lists.add_items(promotional, [photo_a, photo_b])
    lists.add_items(website, [photo_b, photo_a])
    website_before = list(
        project.connection.execute(
            "SELECT media_id, sort_key FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (website,),
        )
    )
    lists.reorder(promotional, [photo_b, photo_a])
    assert lists.ordered_media_ids(promotional) == [photo_b, photo_a]
    assert lists.ordered_media_ids(website) == [photo_b, photo_a]
    website_after = list(
        project.connection.execute(
            "SELECT media_id, sort_key FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (website,),
        )
    )
    assert [(int(r[0]), int(r[1])) for r in website_after] == [
        (int(r[0]), int(r[1])) for r in website_before
    ]
    project.close()


def test_move_selection_and_move_to_beginning(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    Image.new("RGB", (10, 10)).save(tmp_path / "src" / "C.jpg", "JPEG")
    LibraryService(project).scan()
    ids = {
        row["file_name"]: row["id"]
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lst = lists.create("Promotional")
    a, b, c = ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]
    lists.add_items(lst, [a, b, c])
    lists.move_selection(lst, [a], 1)
    assert lists.ordered_media_ids(lst) == [b, a, c]
    lists.move_selection(lst, [a], -1)
    assert lists.ordered_media_ids(lst) == [a, b, c]
    lists.move_to_ends(lst, [c], end=False)
    assert lists.ordered_media_ids(lst) == [c, a, b]
    project.close()


def test_normalize_when_no_integer_gap(tmp_path: Path) -> None:
    project, lists, ids = _setup(tmp_path)
    Image.new("RGB", (10, 10)).save(tmp_path / "src" / "C.jpg", "JPEG")
    LibraryService(project).scan()
    ids = {
        row["file_name"]: row["id"]
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lst = lists.create("Promotional")
    a, b, c = ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]
    lists.add_items(lst, [a, b, c])
    project.connection.execute(
        "UPDATE list_items SET sort_key = 1 WHERE list_id = ? AND media_id = ?",
        (lst, a),
    )
    project.connection.execute(
        "UPDATE list_items SET sort_key = 2 WHERE list_id = ? AND media_id = ?",
        (lst, b),
    )
    project.connection.execute(
        "UPDATE list_items SET sort_key = 0 WHERE list_id = ? AND media_id = ?",
        (lst, c),
    )
    project.connection.commit()
    lists.reorder(lst, [a, c, b])
    assert lists.ordered_media_ids(lst) == [a, c, b]
    assert _sort_keys(project, lst) == [1024, 2048, 3072]
    project.close()


def test_media_grid_enables_manual_reorder(qtbot) -> None:
    grid = MediaGrid()
    qtbot.addWidget(grid)
    assert grid.view.movement() == QListView.Movement.Static
    grid.set_manual_order_enabled(True)
    assert grid.view.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
    assert grid.view.movement() == QListView.Movement.Snap
    grid.set_manual_order_enabled(False)
    assert grid.view.dragDropMode() == QAbstractItemView.DragDropMode.NoDragDrop
    assert grid.view.movement() == QListView.Movement.Static
