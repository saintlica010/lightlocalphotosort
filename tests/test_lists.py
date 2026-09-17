import hashlib
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import SORT_KEY_GAP, ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.list_panel import ListPanel
from local_media_curator.ui.main_window import MainWindow


def test_one_media_can_exist_in_multiple_lists(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    lists = ListService(project)
    promo = lists.create("Promotional")
    web = lists.create("Website")
    lists.add_items(promo, [media_id])
    lists.add_items(web, [media_id])
    assert lists.count(promo) == 1
    assert lists.count(web) == 1
    project.close()


def test_remove_from_one_list_does_not_affect_other_lists(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    lists = ListService(project)
    promo = lists.create("Promotional")
    web = lists.create("Website")
    lists.add_items(promo, [media_id])
    lists.add_items(web, [media_id])
    lists.remove_items(promo, [media_id])
    assert lists.count(promo) == 0
    assert lists.count(web) == 1
    project.close()


def _setup(tmp_path: Path, names: tuple[str, ...] = ("A.jpg",)):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for name in names:
        Image.new("RGB", (10, 10)).save(source / name, "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    ids = {
        row["file_name"]: int(row["id"])
        for row in project.connection.execute(
            "SELECT id, file_name FROM media ORDER BY file_name"
        )
    }
    return project, ListService(project), ids, source


def test_create_duplicate_list_name_does_not_raise(tmp_path: Path) -> None:
    project, lists, _ids, _source = _setup(tmp_path)
    first = lists.create("A")
    second = lists.create("A")
    assert first == second
    names = [row["name"] for row in lists.all_lists()]
    assert names == ["A"]
    project.close()


def test_rename_duplicate_list_name_raises_and_keeps_original(tmp_path: Path) -> None:
    project, lists, _ids, _source = _setup(tmp_path)
    lists.create("A")
    b_id = lists.create("B")
    with pytest.raises(sqlite3.IntegrityError):
        lists.rename(b_id, "A")
    name = project.connection.execute(
        "SELECT name FROM lists WHERE id = ?",
        (b_id,),
    ).fetchone()[0]
    assert name == "B"
    project.close()


def test_rename_duplicate_list_shows_warning(qtbot, tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.list_service.create("A")
    b_id = window.list_service.create("B")
    shown: list[str] = []

    def fake_warning(_parent, title, text):
        shown.append(f"{title}: {text}")
        return 0

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.QMessageBox.warning",
        fake_warning,
    )
    window._on_rename_list(b_id, "A")
    assert shown
    assert "已存在" in shown[0]
    names = {int(row["id"]): str(row["name"]) for row in window.list_service.all_lists()}
    assert names[b_id] == "B"
    project.close()


def test_delete_list_requires_confirmation(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    list_id = window.list_service.create("Promotional")
    window.confirm_delete = lambda _name: False
    window._on_delete_list(list_id)
    assert [row["name"] for row in window.list_service.all_lists()] == ["Promotional"]
    window.confirm_delete = lambda name: name == "Promotional"
    window._on_delete_list(list_id)
    assert window.list_service.all_lists() == []
    project.close()


def test_create_rename_and_delete_list(tmp_path: Path) -> None:
    project, lists, _ids, _source = _setup(tmp_path)
    list_id = lists.create("Draft", "temporary")
    row = project.connection.execute(
        "SELECT name, description FROM lists WHERE id = ?",
        (list_id,),
    ).fetchone()
    assert row["name"] == "Draft"
    assert row["description"] == "temporary"
    lists.rename(list_id, "Promotional")
    name = project.connection.execute(
        "SELECT name FROM lists WHERE id = ?",
        (list_id,),
    ).fetchone()[0]
    assert name == "Promotional"
    lists.delete(list_id)
    remaining = project.connection.execute("SELECT COUNT(*) FROM lists").fetchone()[0]
    assert remaining == 0
    project.close()


def test_delete_list_does_not_delete_media_files(tmp_path: Path) -> None:
    project, lists, ids, source = _setup(tmp_path)
    photo = source / "A.jpg"
    before = {
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
    }
    media_id = ids["A.jpg"]
    promo = lists.create("Promotional")
    web = lists.create("Website")
    lists.add_items(promo, [media_id])
    lists.add_items(web, [media_id])
    lists.delete(promo)
    after = {
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
    }
    assert after == before
    assert lists.count(promo) == 0
    assert lists.count(web) == 1
    media_count = project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    assert media_count == 1
    leftover = project.connection.execute(
        "SELECT COUNT(*) FROM list_items WHERE list_id = ?",
        (promo,),
    ).fetchone()[0]
    assert leftover == 0
    project.close()


def test_add_items_appends_sparse_sort_keys(tmp_path: Path) -> None:
    project, lists, ids, _source = _setup(tmp_path, ("A.jpg", "B.jpg", "C.jpg"))
    lst = lists.create("Promotional")
    lists.add_items(lst, [ids["A.jpg"], ids["B.jpg"]])
    lists.add_items(lst, [ids["C.jpg"]])
    keys = [
        int(row[0])
        for row in project.connection.execute(
            "SELECT sort_key FROM list_items WHERE list_id = ? ORDER BY sort_key",
            (lst,),
        )
    ]
    assert keys == [SORT_KEY_GAP, SORT_KEY_GAP * 2, SORT_KEY_GAP * 3]
    assert lists.ordered_media_ids(lst) == [ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]]
    project.close()


def test_add_items_preserves_independent_append_order(tmp_path: Path) -> None:
    project, lists, ids, _source = _setup(tmp_path, ("A.jpg", "B.jpg"))
    promotional = lists.create("Promotional")
    website = lists.create("Website")
    lists.add_items(promotional, [ids["A.jpg"], ids["B.jpg"]])
    lists.add_items(website, [ids["B.jpg"], ids["A.jpg"]])
    assert lists.ordered_media_ids(promotional) == [ids["A.jpg"], ids["B.jpg"]]
    assert lists.ordered_media_ids(website) == [ids["B.jpg"], ids["A.jpg"]]
    assert lists.list_names_for_media(ids["A.jpg"]) == ["Promotional", "Website"]
    project.close()


def test_list_names_for_media_ids_bulk(tmp_path: Path) -> None:
    project, lists, ids, _source = _setup(tmp_path, ("A.jpg", "B.jpg", "C.jpg"))
    promo = lists.create("Promotional")
    web = lists.create("Website")
    lists.add_items(promo, [ids["A.jpg"], ids["B.jpg"]])
    lists.add_items(web, [ids["A.jpg"]])
    mapping = lists.list_names_for_media_ids(
        [ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]]
    )
    assert mapping[ids["A.jpg"]] == ["Promotional", "Website"]
    assert mapping[ids["B.jpg"]] == ["Promotional"]
    assert mapping[ids["C.jpg"]] == []
    project.close()


def test_main_window_library_panel_hosts_list_panel(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert isinstance(window.library_panel, LibraryPanel)
    assert isinstance(window.library_panel.list_panel, ListPanel)
    window.library_panel.list_panel.set_lists(
        [{"id": 1, "name": "Promotional"}, {"id": 2, "name": "Website"}]
    )
    assert window.library_panel.list_panel.lists_widget.count() == 2
    assert window.library_panel.list_panel.lists_widget.item(0).text() == "Promotional"
