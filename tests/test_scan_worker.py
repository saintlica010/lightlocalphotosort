import threading
import time
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QThread
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


def test_scan_worker_does_not_block_and_persists(qtbot, tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (20, 20)).save(source / "A.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)

    scan_threads: list[threading.Thread] = []
    real_scan = LibraryService.scan

    def recording_scan(self, cancel_check=None):
        scan_threads.append(threading.current_thread())
        return real_scan(self, cancel_check=cancel_check)

    monkeypatch.setattr(LibraryService, "scan", recording_scan)

    worker = ScanWorker()
    thread = QThread()
    worker.moveToThread(thread)
    # Same shape as MainWindow.scan(): a receiverless lambda binds to the
    # *sender's* thread affinity, which would queue run() onto the GUI thread.
    thread.started.connect(
        lambda: worker.run(str(project.db_path)), Qt.ConnectionType.DirectConnection
    )
    with qtbot.waitSignal(worker.finished, timeout=8000):
        thread.start()
    thread.quit()
    thread.wait(2000)

    assert scan_threads
    assert scan_threads[0] is not threading.main_thread()
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


def test_cancel_stops_slow_scan_and_thread(qtbot, tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for i in range(8):
        Image.new("RGB", (12, 12)).save(source / f"{i:02d}.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)

    started = threading.Event()
    from local_media_curator.media import scanner as scanner_mod

    real_read = scanner_mod._read_fields

    def slow_read(path, ext, stat_result):
        started.set()
        time.sleep(0.3)
        return real_read(path, ext, stat_result)

    monkeypatch.setattr(scanner_mod, "_read_fields", slow_read)

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.scan()
    qtbot.waitUntil(lambda: started.is_set(), timeout=8000)
    thread = window._scan_thread
    assert thread is not None and thread.isRunning()
    window.close()
    # deleteLater() is deferred, so a raw QThread wrapper can already be a
    # dangling Python handle by the time we look. Poll the window's own live
    # state, and treat "no QThread child left" as proof the thread stopped:
    # _stop_scan_thread only deletes it after wait() confirmed it exited.
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=15000)
    qtbot.waitUntil(lambda: window.findChildren(QThread) == [], timeout=15000)
    # The scan was cancelled, not merely waited out: the in-progress folder
    # transaction was rolled back, so nothing it read is committed.
    assert project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 0
    # DB remains usable; a new scan can run
    other = create_project(tmp_path / "other")
    window2 = MainWindow()
    qtbot.addWidget(window2)
    window2.set_project(other)
    window2.scan()
    qtbot.waitUntil(lambda: window2._scan_thread is None, timeout=8000)
    other.close()


def test_set_project_cancels_running_scan_thread(qtbot, tmp_path: Path, monkeypatch) -> None:
    first = create_project(tmp_path / "first")
    second = create_project(tmp_path / "second")
    source = tmp_path / "src"
    source.mkdir()
    for i in range(6):
        Image.new("RGB", (12, 12)).save(source / f"{i:02d}.jpg", "JPEG")
    LibraryService(first).add_source_folder(source)
    started = threading.Event()
    from local_media_curator.media import scanner as scanner_mod

    real_read = scanner_mod._read_fields

    def slow_read(path, ext, stat_result):
        started.set()
        time.sleep(0.3)
        return real_read(path, ext, stat_result)

    monkeypatch.setattr(scanner_mod, "_read_fields", slow_read)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(first)
    window.scan()
    qtbot.waitUntil(lambda: started.is_set(), timeout=8000)
    old_thread = window._scan_thread
    assert old_thread is not None and old_thread.isRunning()
    window.set_project(second)
    # See test_cancel_stops_slow_scan_and_thread for why these two polls
    # replace a direct isRunning() call on the (possibly deleted) thread.
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=15000)
    qtbot.waitUntil(lambda: window.findChildren(QThread) == [], timeout=15000)
    assert window.project is second
    second.close()
