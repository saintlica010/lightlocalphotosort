from pathlib import Path

import pytest
from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.main_window import MainWindow


def test_folder_missing_filters_and_list_order(qtbot, tmp_path: Path) -> None:
    from local_media_curator.domain.paths import normalize_path

    project = create_project(tmp_path / "proj")
    lib = LibraryService(project)
    one = tmp_path / "cam_%"
    two = tmp_path / "cam_%extra"
    one.mkdir()
    two.mkdir()
    Image.new("RGB", (10, 10)).save(one / "A.jpg")
    Image.new("RGB", (10, 10)).save(one / "B.png")
    (two / "C.mp4").write_bytes(b"synthetic")
    lib.add_source_folder(one)
    lib.add_source_folder(two)
    lib.scan()
    (one / "A.jpg").unlink()
    lib.scan()
    assert [m.file_name for m in lib.list_media(source_folder=normalize_path(one))] == ["A.jpg", "B.png"]
    assert [m.file_name for m in lib.list_unassigned(missing=True)] == ["A.jpg"]
    assert [m.file_name for m in lib.list_media(missing=False)] == ["B.png", "C.mp4"]
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    panel = window.library_panel
    ids = [m.id for m in lib.list_media()]
    list_id = window.list_service.create("First")
    other_id = window.list_service.create("Second")
    window.add_items_to_list(list_id, ids[::-1])
    window.add_items_to_list(other_id, ids)
    before = window.list_service.items_with_sort_keys(list_id)
    other_before = window.list_service.items_with_sort_keys(other_id)

    def names():
        return [window.media_grid.model.row_at(i)["file_name"] for i in range(window.media_grid.model.rowCount())]

    for view in ("all", "list"):
        if view == "list":
            window.show_list(list_id)
        else:
            window.show_library_view(view)
        panel.type_combo.setCurrentIndex(panel.type_combo.findData("video"))
        assert names() == ["C.mp4"]
        panel.type_combo.setCurrentIndex(0)
        panel.folder_combo.setCurrentIndex(panel.folder_combo.findData(normalize_path(one)))
        panel.extension_combo.setCurrentIndex(panel.extension_combo.findData(".jpg"))
        assert names() == ["A.jpg"]
        panel.missing_combo.setCurrentIndex(panel.missing_combo.findData(False))
        assert names() == []
        panel.missing_combo.setCurrentIndex(panel.missing_combo.findData(True))
        assert names() == ["A.jpg"]
        panel.extension_combo.setCurrentIndex(0)
        panel.folder_combo.setCurrentIndex(0)
        panel.missing_combo.setCurrentIndex(0)
    assert names() == ["C.mp4", "B.png", "A.jpg"]
    assert window.list_service.items_with_sort_keys(list_id) == before
    assert window.list_service.items_with_sort_keys(other_id) == other_before
    window.close()
    project.close()


def test_add_source_overlap_dialog(qtbot, tmp_path: Path, monkeypatch) -> None:
    from local_media_curator.ui import main_window as module

    project = create_project(tmp_path / "proj")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    monkeypatch.setattr(module, "choose_existing_directory", lambda *_: tmp_path)
    warnings = []
    monkeypatch.setattr(module, "show_warning", lambda *args: warnings.append(args))
    window._on_add_source_folder()
    assert len(warnings) == 1
    assert "重叠" in warnings[0][2]
    window.close()
    project.close()


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


def test_add_source_folder_rejects_overlap(tmp_path: Path) -> None:
    project = create_project(tmp_path / "MyProject")
    inside = project.root / "media"
    inside.mkdir()
    # Match the message, not "overlap": pytest's tmp_path embeds the test name
    # (truncated), and that path appears in the message.
    with pytest.raises(ValueError, match="不能重叠"):
        LibraryService(project).add_source_folder(inside)
    parent = tmp_path
    with pytest.raises(ValueError, match="不能重叠"):
        LibraryService(project).add_source_folder(parent)
    sibling = tmp_path / "Pictures"
    sibling.mkdir()
    LibraryService(project).add_source_folder(sibling)
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
    assert "移除源文件夹" in titles


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
    assert window.statusBar().currentMessage() == "媒体库（自动排序）"
    list_id = window.list_service.create("Promotional")
    window.show_list(list_id)
    assert window.statusBar().currentMessage() == "名单（手动排序）"
    window.show_library_view("all")
    assert window.statusBar().currentMessage() == "媒体库（自动排序）"
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


def test_grid_reload_does_not_stat_each_source_or_cache_path(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    from local_media_curator.db.repositories import MediaRepository
    from local_media_curator.domain.paths import normalize_path
    from local_media_curator.media.thumbnail_service import ThumbnailService

    project = create_project(tmp_path / "proj")
    repo = MediaRepository(project.connection)
    for i in range(40):
        path = tmp_path / "src" / f"{i:02d}.jpg"
        repo.insert(
            absolute_path=str(path),
            normalized_path=normalize_path(path),
            media_type="image",
            file_name=path.name,
            extension=".jpg",
            file_size=10,
            width=10,
            height=10,
            duration_ms=None,
            captured_at="2026-01-01T00:00:00",
            modified_at="2026-01-01T00:00:00",
            imported_at="2026-01-01T00:00:00",
        )
    project.connection.commit()
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    cached_calls: list[int] = []
    is_file_calls: list[str] = []
    real_cached = ThumbnailService.cached_path
    real_is_file = Path.is_file

    def counting_cached(self, media_id, source_path, *args, **kwargs):
        cached_calls.append(int(media_id))
        return real_cached(self, media_id, source_path, *args, **kwargs)

    def counting_is_file(self):
        is_file_calls.append(str(self))
        return real_is_file(self)

    monkeypatch.setattr(ThumbnailService, "cached_path", counting_cached)
    monkeypatch.setattr(Path, "is_file", counting_is_file)
    cached_calls.clear()
    is_file_calls.clear()
    window.show_library_view("all")
    assert window.media_grid.model.rowCount() == 40
    assert cached_calls == []
    assert is_file_calls == []
    project.close()
