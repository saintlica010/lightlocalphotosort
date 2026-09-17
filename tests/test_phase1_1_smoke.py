import hashlib
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project
from local_media_curator.ui.main_window import MainWindow


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase1_1_end_to_end_smoke(qtbot, tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    source = tmp_path / "src"
    source.mkdir()
    photo_paths = []
    for name in ("A.jpg", "B.jpg"):
        path = source / name
        Image.new("RGB", (16, 16)).save(path, "JPEG")
        photo_paths.append(path)
    before = {path: _sha256(path) for path in photo_paths}

    project = create_project(project_root)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=15000)

    lists = ListService(project)
    first = lists.create("Promotional")
    second = lists.create("Website")
    ids = [
        int(window.media_grid.model.row_at(i)["id"])
        for i in range(window.media_grid.model.rowCount())
    ]
    window.add_items_to_list(first, ids)
    window.add_items_to_list(second, ids)
    lists.reorder(first, ids[::-1])
    window.show_list(first)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    window.move_selection(1)

    window.show_library_view("all")
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))
    window.reject_selection()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    window.show_library_view("rejected")
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    window.restore_selection()
    window.show_library_view("all")
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)

    window._on_undo()
    window._on_redo()

    promo = lists.ordered_media_ids(first)
    web = lists.ordered_media_ids(second)
    project.close()
    reopened = open_project(project_root)
    try:
        assert promo != web
        assert len(promo) == 2 and len(web) == 2
        states = {
            row["id"]: row["rejected"]
            for row in reopened.connection.execute("SELECT id, rejected FROM media")
        }
        assert set(states.values()) == {0}
        QApplication.processEvents()
    finally:
        reopened.close()

    after = {path: _sha256(path) for path in photo_paths}
    assert after == before
