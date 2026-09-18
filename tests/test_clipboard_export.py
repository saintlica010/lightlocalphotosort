import hashlib
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

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


def test_clipboard_file_names(tmp_path: Path) -> None:
    project, _source, list_id = _setup(tmp_path)
    service = ExportService(project)
    assert service.clipboard_file_names(list_id) == (
        "IMG_0002.jpg\nIMG_0001.jpg\nIMG_0003.jpg"
    )
    project.close()


def test_clipboard_absolute_paths(tmp_path: Path) -> None:
    project, source, list_id = _setup(tmp_path)
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (source / "2026").iterdir()
    }
    service = ExportService(project)
    text = service.clipboard_absolute_paths(list_id)
    assert text.splitlines() == [
        str(source / "2026" / "IMG_0002.jpg"),
        str(source / "2026" / "IMG_0001.jpg"),
        str(source / "2026" / "IMG_0003.jpg"),
    ]
    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (source / "2026").iterdir()
    }
    assert after == before
    project.close()


def test_clipboard_relative_paths(tmp_path: Path) -> None:
    project, _source, list_id = _setup(tmp_path)
    service = ExportService(project)
    assert service.clipboard_relative_paths(list_id) == (
        "2026/IMG_0002.jpg\n2026/IMG_0001.jpg\n2026/IMG_0003.jpg"
    )
    project.close()


def test_clipboard_actions_copy_to_system_clipboard(
    qtbot, tmp_path: Path
) -> None:
    project, _source, _list_id = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    assert window.copy_file_names_action.text() == "复制文件名"
    assert window.copy_absolute_paths_action.text() == "复制绝对路径"
    assert window.copy_relative_paths_action.text() == "复制相对路径"
    window.list_panel.lists_widget.setCurrentRow(0)
    window.copy_file_names_action.trigger()
    assert QApplication.clipboard().text() == (
        "IMG_0002.jpg\nIMG_0001.jpg\nIMG_0003.jpg"
    )
    window.copy_relative_paths_action.trigger()
    assert QApplication.clipboard().text() == (
        "2026/IMG_0002.jpg\n2026/IMG_0001.jpg\n2026/IMG_0003.jpg"
    )
    window.copy_absolute_paths_action.trigger()
    assert QApplication.clipboard().text().splitlines()[0].endswith(
        "IMG_0002.jpg"
    )
    project.close()
