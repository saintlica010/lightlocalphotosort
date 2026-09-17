import sqlite3
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


def test_scan_progress_is_cumulative_and_counts_unchanged(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    library = LibraryService(project)
    for name in ("one", "two"):
        source = tmp_path / name
        source.mkdir()
        for i in range(30):
            Image.new("RGB", (8, 8)).save(source / f"{i}.jpg")
        library.add_source_folder(source)
    try:
        for _ in range(2):
            counts = []
            library.scan(progress_cb=counts.append)
            assert counts == [1, 25, 30, 31, 55, 60]
    finally:
        project.close()


def test_scan_emits_throttled_progress_on_gui_thread(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for i in range(30):
        Image.new("RGB", (8, 8)).save(source / f"{i}.jpg")
    LibraryService(project).add_source_folder(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    messages = []
    threads = []

    def record(message):
        if "已处理" in message:
            messages.append(message)
            threads.append(QThread.currentThread() is window.thread())

    window.statusBar().messageChanged.connect(record)
    window.scan()
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=15000)
    assert messages[-1] == "正在扫描… 已处理 30 个文件"
    assert len(messages) <= 4
    assert all(threads)
    assert window.statusBar().currentMessage() == "媒体库（自动排序）"
    window.close()
    project.close()


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

    def recording_scan(self, cancel_check=None, **kwargs):
        scan_threads.append(threading.current_thread())
        return real_scan(self, cancel_check=cancel_check, **kwargs)

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


def test_scan_commits_in_batches_so_other_connection_can_write(
    tmp_path: Path, monkeypatch
) -> None:
    from local_media_curator.db.connection import connect
    from local_media_curator.media import scanner as scanner_mod

    monkeypatch.setattr(scanner_mod, "SCAN_COMMIT_BATCH", 2)
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for i in range(8):
        Image.new("RGB", (8, 8)).save(source / f"{i:02d}.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)
    started = threading.Event()
    real_read = scanner_mod._read_fields

    def slow_read(path, ext, stat_result):
        started.set()
        time.sleep(0.05)
        return real_read(path, ext, stat_result)

    monkeypatch.setattr(scanner_mod, "_read_fields", slow_read)
    errors: list[str] = []

    def writer():
        started.wait(timeout=5)
        time.sleep(0.12)
        other = connect(project.db_path)
        other.execute("PRAGMA busy_timeout = 0")
        try:
            try:
                other.execute(
                    "UPDATE media SET rejected = 1 WHERE id = (SELECT id FROM media LIMIT 1)"
                )
                other.commit()
            except sqlite3.OperationalError as exc:
                errors.append(str(exc))
        finally:
            other.close()

    thread = threading.Thread(target=writer)
    thread.start()
    LibraryService(project).scan()
    thread.join(timeout=10)
    assert errors == []
    project.close()


def test_reject_during_locked_db_shows_status_not_raise(qtbot, tmp_path: Path) -> None:
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
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))

    def boom(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    window.undo_stack.reject = boom  # type: ignore[method-assign]
    window.reject_selection()
    assert "忙" in window.statusBar().currentMessage()
    project.close()
