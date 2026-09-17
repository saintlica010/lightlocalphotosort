from pathlib import Path

from PIL import Image

from local_media_curator.services.project_service import create_project
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_model import MediaListModel


def test_main_window_has_three_panels(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert isinstance(window.library_panel, LibraryPanel)
    assert window.library_panel.list_panel is not None
    assert window.media_grid is not None
    assert window.preview_panel is not None


def test_undo_reject_restores_selection_and_preview(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    target = window.media_grid.model.index(1)
    window.media_grid.view.setCurrentIndex(target)
    media_id = int(window.media_grid.model.data(target, MediaListModel.IdRole))
    file_name = window.media_grid.model.row_at(1)["file_name"]
    window.reject_selection()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    window._on_undo()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    current = window.media_grid.view.currentIndex()
    assert current.isValid()
    assert int(window.media_grid.model.data(current, MediaListModel.IdRole)) == media_id
    assert window.preview_panel.file_name_label.text() == file_name
    project.close()


def test_library_refresh_keeps_selection(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(1))
    media_id = int(
        window.media_grid.model.data(
            window.media_grid.view.currentIndex(), MediaListModel.IdRole
        )
    )
    window.show_library_view("all")
    current = window.media_grid.view.currentIndex()
    assert current.isValid()
    assert int(window.media_grid.model.data(current, MediaListModel.IdRole)) == media_id
    project.close()
