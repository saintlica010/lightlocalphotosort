from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from local_media_curator.db.connection import connect
from local_media_curator.media.scan_worker import ScanWorker
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow


def test_connect_enables_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "p.sqlite3")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"
    conn.close()


def test_scan_worker_does_not_block_and_persists(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (20, 20)).save(source / "A.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)

    worker = ScanWorker()
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(lambda: worker.run(str(project.db_path)))
    with qtbot.waitSignal(worker.finished, timeout=8000):
        thread.start()
    thread.quit()
    thread.wait(2000)

    count = project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    assert count == 1
    project.close()


def test_main_window_scan_clears_thread_refs(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (20, 20)).save(source / "A.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)

    for _ in range(2):
        window.scan()
        qtbot.waitUntil(lambda: window._scan_thread is None, timeout=8000)
        QApplication.processEvents()

    assert window._scan_worker is None
    assert window.findChildren(QThread) == []


def test_close_event_stops_scan_thread(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (20, 20)).save(source / "A.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.scan()
    window.close()
    assert window._scan_thread is None
    assert window._scan_worker is None


def test_set_project_stops_scan_before_switching(qtbot, tmp_path: Path) -> None:
    first = create_project(tmp_path / "first")
    second = create_project(tmp_path / "second")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (20, 20)).save(source / "A.jpg", "JPEG")
    LibraryService(first).add_source_folder(source)

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(first)
    window.scan()
    window.set_project(second)
    assert window._scan_thread is None
    assert window._scan_worker is None
    assert window.project is second
    second.close()
