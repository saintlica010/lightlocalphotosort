import hashlib
from pathlib import Path

from PIL import Image

from local_media_curator.services.export_service import ExportService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow


def _fill(folder: Path, names: tuple[str, ...]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        Image.new("RGB", (12, 12), "red").save(folder / name, "JPEG")


def test_export_and_import_actions_are_chinese(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.export_list_action.text() == "导出名单..."
    assert window.import_list_action.text() == "导入名单..."


def test_export_then_import_round_trip_via_actions(qtbot, tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    source.mkdir()
    Image.new("RGB", (12, 12), "red").save(source / "A.jpg", "JPEG")
    Image.new("RGB", (12, 12), "red").save(source / "B.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    dest = tmp_path / "Website.llplist.json"

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.list_panel.lists_widget.setCurrentRow(0)

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_save_file",
        lambda *args, **kwargs: dest,
    )
    window.export_list_action.trigger()
    assert dest.is_file()

    lists.replace_items(list_id, [])
    window.refresh()
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: None,
    )
    window.import_list_action.trigger()
    assert ListService(project).ordered_media_ids(list_id) == [ids["B.jpg"], ids["A.jpg"]]
    project.close()


def test_import_ui_relocates_source_root(qtbot, tmp_path: Path, monkeypatch) -> None:
    old_project = create_project(tmp_path / "old")
    old_root = tmp_path / "D-Photos"
    _fill(old_root / "2026", ("A.jpg", "B.jpg"))
    LibraryService(old_project).add_source_folder(old_root)
    LibraryService(old_project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in old_project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(old_project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    dest = tmp_path / "Website.llplist.json"
    ExportService(old_project).export_list(list_id, dest)
    old_project.close()

    new_root = tmp_path / "E-Photos"
    _fill(new_root / "2026", ("A.jpg", "B.jpg"))
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (new_root / "2026").iterdir()
    }
    new_project = create_project(tmp_path / "new")
    LibraryService(new_project).add_source_folder(new_root)
    LibraryService(new_project).scan()

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(new_project)
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_existing_directory",
        lambda *args, **kwargs: new_root,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: None,
    )
    window.import_list_action.trigger()

    website = next(
        row for row in ListService(new_project).all_lists() if row["name"] == "Website"
    )
    names = [
        row["file_name"]
        for row in new_project.connection.execute(
            """
            SELECT media.file_name FROM list_items
            JOIN media ON media.id = list_items.media_id
            WHERE list_items.list_id = ?
            ORDER BY list_items.sort_key
            """,
            (int(website["id"]),),
        )
    ]
    assert names == ["B.jpg", "A.jpg"]
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (new_root / "2026").iterdir()
    }
    assert after == before
    new_project.close()


def test_import_ambiguous_source_opens_remap_dialog(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    import os

    project = create_project(tmp_path / "proj")
    folder_a = tmp_path / "folder-a"
    folder_b = tmp_path / "folder-b"
    _fill(folder_a / "2026", ("DUP.jpg",))
    _fill(folder_b / "2026", ("DUP.jpg",))
    fixed_mtime = 1788000000.0
    os.utime(folder_a / "2026" / "DUP.jpg", (fixed_mtime, fixed_mtime))
    os.utime(folder_b / "2026" / "DUP.jpg", (fixed_mtime, fixed_mtime))
    library = LibraryService(project)
    library.add_source_folder(folder_a)
    library.add_source_folder(folder_b)
    library.scan()
    size = (folder_a / "2026" / "DUP.jpg").stat().st_size
    modified = project.connection.execute(
        "SELECT modified_at FROM media LIMIT 1"
    ).fetchone()[0]
    dest = tmp_path / "Dup.llplist.json"
    dest.write_text(
        "{\n"
        '  "format": "light-local-photo-list",\n'
        '  "version": 1,\n'
        '  "list": {"name": "Dup"},\n'
        '  "items": [{\n'
        '    "order": 0,\n'
        '    "source": "old-drive",\n'
        '    "relative_path": "2026/DUP.jpg",\n'
        '    "file_name": "DUP.jpg",\n'
        f'    "file_size": {size},\n'
        f'    "modified_at": "{modified}"\n'
        "  }]\n"
        "}\n",
        encoding="utf-8",
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    asked_sources: list[str] = []
    summaries: list[dict] = []

    def fake_choose_dir(parent, title):
        asked_sources.append(title)
        return folder_a

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_existing_directory",
        fake_choose_dir,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: summaries.append(kwargs),
    )
    window.import_list_action.trigger()
    assert asked_sources == ["为源 old-drive 选择新根目录"]
    assert summaries == [{"matched": 1, "missing": 0, "ambiguous": 0}]
    dup = next(
        row for row in ListService(project).all_lists() if row["name"] == "Dup"
    )
    imported = ListService(project).ordered_media_ids(int(dup["id"]))
    expected = [
        int(row["id"])
        for row in project.connection.execute(
            "SELECT id FROM media WHERE absolute_path LIKE '%folder-a%'"
        )
    ]
    assert imported == expected
    project.close()


def test_import_ui_cancel_remap_preserves_existing_list(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    _fill(source, ("A.jpg", "B.jpg"))
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    original = lists.ordered_media_ids(list_id)

    dest = tmp_path / "Website.llplist.json"
    dest.write_text(
        "{\n"
        '  "format": "light-local-photo-list",\n'
        '  "version": 1,\n'
        '  "list": {"name": "Website"},\n'
        '  "items": [{\n'
        '    "order": 0,\n'
        '    "source": "other-drive",\n'
        '    "relative_path": "GONE.jpg",\n'
        '    "file_name": "GONE.jpg",\n'
        '    "file_size": 12,\n'
        '    "modified_at": "2026-01-01T00:00:00"\n'
        "  }]\n"
        "}\n",
        encoding="utf-8",
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.ask_confirm",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_existing_directory",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: None,
    )
    window.import_list_action.trigger()
    assert ListService(project).ordered_media_ids(list_id) == original
    assert window.statusBar().currentMessage() == "已取消导入"
    project.close()


def _same_name_manifest(tmp_path: Path, order: tuple[str, ...]) -> Path:
    dest = tmp_path / "Website.llplist.json"
    lines = [
        "{",
        '  "format": "light-local-photo-list",',
        '  "version": 1,',
        '  "list": {"name": "Website"},',
        '  "items": [',
    ]
    entries = []
    for position, name in enumerate(order):
        entries.append(
            "    {\n"
            f'      "order": {position},\n'
            '      "source": "camera-a",\n'
            f'      "relative_path": "{name}",\n'
            f'      "file_name": "{name}",\n'
            '      "file_size": 12,\n'
            '      "modified_at": "2026-01-01T00:00:00"\n'
            "    }"
        )
    lines.append(",\n".join(entries))
    lines.extend(["  ]", "}"])
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def test_import_declined_replace_keeps_existing_list(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    _fill(source, ("A.jpg", "B.jpg"))
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    original = lists.ordered_media_ids(list_id)
    dest = _same_name_manifest(tmp_path, ("A.jpg", "B.jpg"))

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    asked: list[tuple] = []
    summaries: list[tuple] = []
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.ask_confirm",
        lambda parent, title, text: asked.append((title, text)) or False,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: summaries.append(args),
    )
    window.import_list_action.trigger()
    assert len(asked) == 1
    assert asked[0][0] == "导入名单"
    assert "Website" in asked[0][1]
    assert summaries == []
    assert ListService(project).ordered_media_ids(list_id) == original
    project.close()


def test_import_confirmed_replace_persists_new_order(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    _fill(source, ("A.jpg", "B.jpg"))
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    dest = _same_name_manifest(tmp_path, ("A.jpg", "B.jpg"))

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    asked: list[tuple] = []
    summaries: list[dict] = []
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.ask_confirm",
        lambda parent, title, text: asked.append((title, text)) or True,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: summaries.append(kwargs),
    )
    window.import_list_action.trigger()
    assert len(asked) == 1
    assert asked[0][0] == "导入名单"
    assert ListService(project).ordered_media_ids(list_id) == [
        ids["A.jpg"],
        ids["B.jpg"],
    ]
    assert summaries == [{"matched": 2, "missing": 0, "ambiguous": 0}]
    project.close()


def test_import_partial_remap_cancel_aborts_without_persist(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    _fill(source, ("A.jpg", "B.jpg"))
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    before_lists = [
        str(row["name"]) for row in ListService(project).all_lists()
    ]
    dest = tmp_path / "Relocated.llplist.json"
    dest.write_text(
        "{\n"
        '  "format": "light-local-photo-list",\n'
        '  "version": 1,\n'
        '  "list": {"name": "Relocated"},\n'
        '  "items": [{\n'
        '    "order": 0,\n'
        '    "source": "drive-a",\n'
        '    "relative_path": "GONE-A.jpg",\n'
        '    "file_name": "GONE-A.jpg",\n'
        '    "file_size": 12,\n'
        '    "modified_at": "2026-01-01T00:00:00"\n'
        "  }, {\n"
        '    "order": 1,\n'
        '    "source": "drive-b",\n'
        '    "relative_path": "GONE-B.jpg",\n'
        '    "file_name": "GONE-B.jpg",\n'
        '    "file_size": 12,\n'
        '    "modified_at": "2026-01-01T00:00:00"\n'
        "  }]\n"
        "}\n",
        encoding="utf-8",
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    answers = iter([tmp_path / "remap-a", None])
    summaries: list[tuple] = []
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_existing_directory",
        lambda *args, **kwargs: next(answers),
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: summaries.append(args),
    )
    window.import_list_action.trigger()
    assert [
        str(row["name"]) for row in ListService(project).all_lists()
    ] == before_lists
    assert summaries == []
    assert window.statusBar().currentMessage() == "已取消导入"
    project.close()
