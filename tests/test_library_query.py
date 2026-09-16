from pathlib import Path

from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.main_window import MainWindow


def test_remove_source_folder_keeps_media_and_files(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (10, 10)).save(photo, "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    lib.remove_source_folder(source)
    folders = project.connection.execute("SELECT COUNT(*) FROM source_folders").fetchone()[0]
    media = project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    assert folders == 0
    assert media == 1
    assert photo.is_file()
    project.close()


def test_list_media_sort_by_name(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    names = [m.file_name for m in lib.list_media(sort_by="file_name")]
    assert names == ["A.jpg", "B.jpg"]
    project.close()


def test_list_media_sort_by_file_size(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (8, 8), "red").save(source / "small.jpg", "JPEG")
    Image.new("RGB", (200, 200), "blue").save(source / "large.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    names = [m.file_name for m in lib.list_media(sort_by="file_size")]
    assert names == ["small.jpg", "large.jpg"]
    default_names = [m.file_name for m in lib.list_media()]
    assert default_names == ["large.jpg", "small.jpg"]
    project.close()


def test_list_media_filters_media_type_and_extension(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.png", "PNG")
    (source / "C.mp4").write_bytes(b"not a real video")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    images = [m.file_name for m in lib.list_media(media_type="image")]
    videos = [m.file_name for m in lib.list_media(media_type="video")]
    jpgs = [m.file_name for m in lib.list_media(extension=".jpg")]
    pngs = [m.file_name for m in lib.list_media(extension="png")]
    assert images == ["A.jpg", "B.png"]
    assert videos == ["C.mp4"]
    assert jpgs == ["A.jpg"]
    assert pngs == ["B.png"]
    all_items = lib.list_media(include_rejected=False)
    assert [m.file_name for m in all_items] == ["A.jpg", "B.png", "C.mp4"]
    project.close()


def test_file_menu_has_remove_source_folder(qtbot) -> None:
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
    assert "Remove Source Folder" in titles


def test_library_sort_combo_does_not_rewrite_list_sort_keys(
    qtbot, tmp_path: Path
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(list_id, [ids["B.jpg"], ids["A.jpg"]])
    window.show_list(list_id)
    before = window.list_service.items_with_sort_keys(list_id)
    assert [media_id for media_id, _key in before] == [ids["B.jpg"], ids["A.jpg"]]
    combo = window.library_panel.sort_combo
    next_index = 0 if combo.currentIndex() != 0 else 1
    combo.setCurrentIndex(next_index)
    after = window.list_service.items_with_sort_keys(list_id)
    assert after == before
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    project.close()


def test_status_tip_distinguishes_library_and_list(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    assert window.statusBar().currentMessage() == "Library (sorted)"
    list_id = window.list_service.create("Promotional")
    window.show_list(list_id)
    assert window.statusBar().currentMessage() == "List (manual order)"
    window.show_library_view("all")
    assert window.statusBar().currentMessage() == "Library (sorted)"
    project.close()


def test_library_panel_exposes_sort_combo(qtbot) -> None:
    panel = LibraryPanel()
    qtbot.addWidget(panel)
    values = [
        panel.sort_combo.itemData(i) for i in range(panel.sort_combo.count())
    ]
    assert values == [
        "file_name",
        "captured_at",
        "modified_at",
        "file_size",
        "imported_at",
    ]


def test_grid_reload_does_not_issue_per_item_list_name_queries(
    qtbot, tmp_path: Path
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for name in ("A.jpg", "B.jpg", "C.jpg"):
        Image.new("RGB", (10, 10)).save(source / name, "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 3, timeout=8000)
    list_id = window.list_service.create("Promotional")
    ids = [
        int(window.media_grid.model.row_at(i)["id"])
        for i in range(window.media_grid.model.rowCount())
    ]
    window.add_items_to_list(list_id, ids[:2])
    # Python 3.14: sqlite3.Connection.execute is immutable; wrap the repo connection.
    real_conn = window.list_service._lists._conn
    seen: list[str] = []

    class _ExecuteProbe:
        def execute(self, sql, parameters=()):
            text = str(sql)
            if "list_items" in text and "lists" in text:
                seen.append(text)
            return real_conn.execute(sql, parameters)

        def __getattr__(self, name: str):
            return getattr(real_conn, name)

    window.list_service._lists._conn = _ExecuteProbe()  # type: ignore[assignment]
    window.show_library_view("all")
    membership_queries = [
        sql for sql in seen if "list_items" in sql and "lists" in sql
    ]
    assert len(membership_queries) <= 1
    assert window.media_grid.model.rowCount() == 3
    project.close()
