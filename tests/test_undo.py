import hashlib
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QKeySequence

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.main_window import MainWindow


def test_reject_undo_redo(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    stack = CurationUndoStack(project)
    stack.reject([media_id])
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 1
    stack.undo()
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 0
    stack.redo()
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 1
    project.close()


def test_reorder_undo_redo(tmp_path: Path) -> None:
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
    lst = lists.create("Promotional")
    lists.add_items(lst, [ids["A.jpg"], ids["B.jpg"]])
    stack = CurationUndoStack(project)
    stack.reorder(lst, [ids["B.jpg"], ids["A.jpg"]])
    assert lists.ordered_media_ids(lst) == [ids["B.jpg"], ids["A.jpg"]]
    stack.undo()
    assert lists.ordered_media_ids(lst) == [ids["A.jpg"], ids["B.jpg"]]
    stack.redo()
    assert lists.ordered_media_ids(lst) == [ids["B.jpg"], ids["A.jpg"]]
    project.close()


def _setup(tmp_path: Path, names: tuple[str, ...] = ("A.jpg", "B.jpg")):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photos: dict[str, Path] = {}
    for name in names:
        path = source / name
        Image.new("RGB", (10, 10)).save(path, "JPEG")
        photos[name] = path
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    ids = {
        row["file_name"]: int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    return project, ListService(project), ids, photos


def _item_keys(project, list_id: int) -> list[tuple[int, int]]:
    return [
        (int(row[0]), int(row[1]))
        for row in project.connection.execute(
            "SELECT media_id, sort_key FROM list_items WHERE list_id = ? ORDER BY media_id",
            (list_id,),
        )
    ]


def _file_fingerprint(path: Path) -> dict[str, object]:
    return {
        "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
        "mtime": path.stat().st_mtime_ns,
        "name": path.name,
    }


def test_reorder_undo_restores_previous_sort_keys(tmp_path: Path) -> None:
    project, lists, ids, _photos = _setup(tmp_path)
    lst = lists.create("Promotional")
    lists.add_items(lst, [ids["A.jpg"], ids["B.jpg"]])
    before = _item_keys(project, lst)
    stack = CurationUndoStack(project)
    stack.reorder(lst, [ids["B.jpg"], ids["A.jpg"]])
    after = _item_keys(project, lst)
    assert after != before
    stack.undo()
    assert _item_keys(project, lst) == before
    stack.redo()
    assert _item_keys(project, lst) == after
    project.close()


def test_add_and_remove_undo_redo(tmp_path: Path) -> None:
    project, lists, ids, _photos = _setup(tmp_path)
    lst = lists.create("Promotional")
    stack = CurationUndoStack(project)
    stack.add_items(lst, [ids["A.jpg"], ids["B.jpg"]])
    assert lists.ordered_media_ids(lst) == [ids["A.jpg"], ids["B.jpg"]]
    keys_after_add = _item_keys(project, lst)
    stack.undo()
    assert lists.ordered_media_ids(lst) == []
    stack.redo()
    assert lists.ordered_media_ids(lst) == [ids["A.jpg"], ids["B.jpg"]]
    assert _item_keys(project, lst) == keys_after_add
    stack.remove_items(lst, [ids["A.jpg"]])
    assert lists.ordered_media_ids(lst) == [ids["B.jpg"]]
    stack.undo()
    assert lists.ordered_media_ids(lst) == [ids["A.jpg"], ids["B.jpg"]]
    assert _item_keys(project, lst) == keys_after_add
    stack.redo()
    assert lists.ordered_media_ids(lst) == [ids["B.jpg"]]
    project.close()


def test_restore_undo_redo(tmp_path: Path) -> None:
    project, _lists, ids, _photos = _setup(tmp_path, ("A.jpg",))
    media_id = ids["A.jpg"]
    stack = CurationUndoStack(project)
    stack.reject([media_id])
    stack.restore([media_id])
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 0
    stack.undo()
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 1
    stack.redo()
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 0
    project.close()


def test_undo_does_not_mutate_source_files(tmp_path: Path) -> None:
    project, lists, ids, photos = _setup(tmp_path)
    before = {name: _file_fingerprint(path) for name, path in photos.items()}
    lst = lists.create("Promotional")
    stack = CurationUndoStack(project)
    stack.add_items(lst, [ids["A.jpg"], ids["B.jpg"]])
    stack.reorder(lst, [ids["B.jpg"], ids["A.jpg"]])
    stack.reject([ids["A.jpg"]])
    stack.undo()
    stack.redo()
    stack.restore([ids["A.jpg"]])
    stack.remove_items(lst, [ids["B.jpg"]])
    stack.undo()
    after = {name: _file_fingerprint(path) for name, path in photos.items()}
    assert after == before
    project.close()


def test_main_window_has_undo_redo_shortcuts(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    shortcuts = {
        action.shortcut().toString()
        for action in window.actions()
        if not action.shortcut().isEmpty()
    }
    undo = QKeySequence(QKeySequence.StandardKey.Undo).toString()
    assert undo in shortcuts
    assert "Ctrl+Shift+Z" in shortcuts
