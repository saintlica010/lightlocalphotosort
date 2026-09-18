import hashlib
from pathlib import Path

import pytest
from PIL import Image

from local_media_curator.services.export_service import ExportService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow


def _setup(tmp_path: Path):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    nested = source / "2026"
    nested.mkdir(parents=True)
    for name in ("IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg"):
        Image.new("RGB", (12, 12), "red").save(nested / name, "JPEG")
    library = LibraryService(project)
    library.add_source_folder(source)
    library.scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website Final")
    lists.add_items(
        list_id, [ids["IMG_0002.jpg"], ids["IMG_0001.jpg"], ids["IMG_0003.jpg"]]
    )
    return project, source, list_id


def test_txt_export(tmp_path: Path) -> None:
    project, source, list_id = _setup(tmp_path)
    destination = tmp_path / "Website Final.txt"
    photos = list((source / "2026").glob("*.jpg"))
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos}
    result = ExportService(project).export_txt(list_id, destination)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos}
    assert after == before
    assert result == destination
    raw = destination.read_bytes()
    assert raw == "IMG_0002.jpg\nIMG_0001.jpg\nIMG_0003.jpg\n".encode("utf-8")
    project.close()


def test_txt_export_missing_list_raises(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    with pytest.raises(ValueError, match="名单不存在"):
        ExportService(project).export_txt(9999, tmp_path / "nope.txt")
    project.close()


def test_export_txt_action_writes_file(qtbot, tmp_path: Path, monkeypatch) -> None:
    project, _source, list_id = _setup(tmp_path)
    dest = tmp_path / "Website Final.txt"
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    assert window.export_txt_action.text() == "导出 TXT..."
    window.list_panel.lists_widget.setCurrentRow(0)
    before_ids = ListService(project).ordered_media_ids(list_id)
    calls: dict[str, object] = {}

    def fake_save(parent, title, named_filter, default_name=""):
        calls["title"] = title
        calls["filter"] = named_filter
        calls["default"] = default_name
        return dest

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_save_file", fake_save
    )
    window.export_txt_action.trigger()
    assert dest.is_file()
    assert calls["filter"] == "文本文件 (*.txt)"
    assert calls["default"] == "Website Final.txt"
    assert dest.read_text(encoding="utf-8").splitlines() == [
        "IMG_0002.jpg",
        "IMG_0001.jpg",
        "IMG_0003.jpg",
    ]
    assert ListService(project).ordered_media_ids(list_id) == before_ids
    project.close()
