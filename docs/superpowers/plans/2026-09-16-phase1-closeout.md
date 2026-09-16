# Phase 1 Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish AGENTS.md Phase 1 so a user can run a packaged Windows app, scan without freezing the UI, persist drag-reorder, sort/filter the library, and keep source folders read-only.

**Architecture:** Keep `LibraryService.scan()` synchronous for existing tests. GUI uses QThread / QThreadPool workers that open their own SQLite connections (WAL). Widgets never write SQL. Thumbnails stay under `project.thumbnails_dir`.

**Tech Stack:** Python 3.12+, PySide6, sqlite3, Pillow, pytest, pytest-qt, PyInstaller.

## Global Constraints

- Package `local_media_curator` under `src/`. Author `lica.liu`. Never `git add .`.
- Never modify/rename/move/delete source media; never write EXIF/XMP; never cache inside source folders.
- Protected dirs never committed or used as test output: `photos/`, `phototakeplan/`, `lightphotosprt/`.
- Tests use pytest `tmp_path` generated images. `QT_QPA_PLATFORM=offscreen`.
- Existing 55 tests must remain green.
- No SQLAlchemy, no cloud, no AI, no TagStudio GPL copy.
- `list_items.sort_key INTEGER` unchanged.
- Do not implement Phase 2 export, video playback, or a Windows installer (one-folder PyInstaller is enough).

---

### Task 1: WAL and asynchronous scanner

**Files:**
- Modify: `src/local_media_curator/db/connection.py`
- Create: `src/local_media_curator/media/scan_worker.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Create: `tests/test_scan_worker.py`

**Interfaces:**
- Consumes: `LibraryService.scan()`, `connect(db_path)`, `Project.db_path`
- Produces:
  - `connect()` also runs `PRAGMA journal_mode=WAL`
  - `ScanWorker(QObject)` with signals `finished(object)`, `failed(str)`
  - `ScanWorker.run(db_path: str)` opens its **own** connection via `connect(Path(db_path))`, constructs a temporary `Project` using that connection (or calls scan with a dedicated connection), never uses `Project.connection` from the GUI thread
  - `MainWindow.scan()` starts a `QThread`, returns immediately, and on `finished` calls `_ensure_thumbnails` / `refresh` on the GUI thread
  - Existing `LibraryService.scan()` remains synchronous for tests

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scan_worker.py
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThread

from local_media_curator.db.connection import connect
from local_media_curator.media.scan_worker import ScanWorker
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scan_worker.py -v`
Expected: FAIL, `ScanWorker` missing and WAL not set.

- [ ] **Step 3: Minimal implementation**

`ScanWorker.run` must `try/except` and `failed.emit` on error. Close its private connection in `finally`. `MainWindow.scan` must not call `library_service.scan()` on the GUI thread.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_scan_worker.py tests/test_library.py tests/test_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/db/connection.py src/local_media_curator/media/scan_worker.py src/local_media_curator/ui/main_window.py tests/test_scan_worker.py
git commit -m "feat(scan): run library scan off the GUI thread"
```

---

### Task 2: Thumbnail worker pool

**Files:**
- Create: `src/local_media_curator/media/thumbnail_pool.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Modify: `src/local_media_curator/ui/media_model.py` if needed to update one row's `thumbnail_path`
- Create: `tests/test_thumbnail_pool.py`

**Interfaces:**
- Consumes: `ThumbnailService.ensure` (filesystem only; safe in workers)
- Produces:
  - `ThumbnailPool` wrapping `QThreadPool` with `max_workers=4`
  - `request(jobs: list[tuple[int, str]])` where each job is `(media_id, source_path)`
  - Signal `ready(int, str)` = media_id, thumbnail path
  - Newer visible requests run before a large backlog (use `QRunnable` with priority or a deque that workers pop from the left for high priority)
  - `MainWindow` after scan/reload: fill grid with placeholders first, then `request()` jobs; on `ready`, set that row's `thumbnail_path`
  - Remove synchronous `_ensure_thumbnails()` of the entire library on the GUI thread

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication

from local_media_curator.media.thumbnail_pool import ThumbnailPool
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


def test_thumbnail_pool_emits_ready(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (80, 80), "red").save(photo, "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    pool = ThumbnailPool(project)
    with qtbot.waitSignal(pool.ready, timeout=8000) as blocker:
        pool.request([(int(media_id), str(photo))])
    assert blocker.args[0] == media_id
    out = Path(blocker.args[1])
    assert out.is_file()
    assert project.thumbnails_dir in out.parents
    project.close()
```

- [ ] **Step 2: Run test, expect fail** (`ThumbnailPool` missing)

- [ ] **Step 3: Implement pool + wire MainWindow**

Corrupt/missing sources must emit nothing or a safe skip, never crash the pool.

- [ ] **Step 4: pytest tests/test_thumbnail_pool.py tests/test_thumbnails.py tests/test_session.py -v**

- [ ] **Step 5: Commit** `feat(thumbs): generate thumbnails on a worker pool`

---

### Task 3: Asynchronous preview and open-original

**Files:**
- Create: `src/local_media_curator/media/preview_loader.py`
- Modify: `src/local_media_curator/ui/preview_panel.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Create: `tests/test_preview_loader.py`
- Modify: `tests/test_preview.py` if selection-load tests assume sync decode

**Interfaces:**
- Consumes: `load_preview_image`
- Produces:
  - `PreviewLoader.load(path: str, token: int, max_edge: int)` on a worker
  - Signal `loaded(int, object)` token + QImage (or None)
  - Ignore stale tokens when selection changed
  - `PreviewPanel.open_original()` uses `QDesktopServices.openUrl` (extract a helper `open_path(path: Path)` for tests to monkeypatch)
  - GUI thread only assigns the QImage to the view

- [ ] **Step 1: Failing tests**

```python
from pathlib import Path

from PIL import Image

from local_media_curator.media.preview_loader import PreviewLoader


def test_preview_loader_emits_downsampled_image(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "big.jpg"
    Image.new("RGB", (1200, 800), "white").save(path, "JPEG")
    loader = PreviewLoader()
    with qtbot.waitSignal(loader.loaded, timeout=8000) as blocker:
        loader.load(str(path), token=7, max_edge=400)
    token, image = blocker.args
    assert token == 7
    assert max(image.width(), image.height()) <= 400


def test_open_path_helper(monkeypatch, tmp_path: Path) -> None:
    from local_media_curator.media.preview_loader import open_path

    seen: list[str] = []
    monkeypatch.setattr(
        "local_media_curator.media.preview_loader._open_url",
        lambda url: seen.append(url),
    )
    photo = tmp_path / "A.jpg"
    photo.write_bytes(b"x")
    open_path(photo)
    assert seen and seen[0].endswith("A.jpg")
```

- [ ] **Step 2: Fail then implement**

- [ ] **Step 3: Wire PreviewPanel.set_media to loader; add menu/action Open Original**

- [ ] **Step 4: pytest tests/test_preview_loader.py tests/test_preview.py -v**

- [ ] **Step 5: Commit** `feat(preview): load previews off the GUI thread`

---

### Task 4: Persist drag-reorder and paint ordinals

**Files:**
- Modify: `src/local_media_curator/ui/media_model.py`
- Modify: `src/local_media_curator/ui/media_grid.py`
- Modify: `src/local_media_curator/ui/thumbnail_delegate.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Create: `tests/test_grid_reorder.py`

**Interfaces:**
- Consumes: `CurationUndoStack.reorder`, `ListService.ordered_media_ids`
- Produces:
  - When manual order is enabled, `MediaListModel.flags` include `ItemIsDragEnabled | ItemIsDropEnabled | ItemIsSelectable | ItemIsEnabled`
  - `mimeTypes` / `mimeData` / `dropMimeData` reorder `_rows` and emit `orderChanged(list[int])` with media ids in new order
  - `MainWindow` connects `orderChanged` to `undo_stack.reorder(current_list_id, ids)` then refresh
  - `ThumbnailDelegate.paint` draws the ordinal (01, 02, …) when `OrdinalRole` is not None
  - Library views keep drag disabled

- [ ] **Step 1: Failing tests**

```python
from PySide6.QtCore import QModelIndex, Qt

from local_media_curator.ui.media_model import MediaListModel


def test_drop_reorders_ids_and_emits(qtbot) -> None:
    model = MediaListModel(
        [
            {"id": 1, "file_name": "A.jpg", "ordinal": 1},
            {"id": 2, "file_name": "B.jpg", "ordinal": 2},
            {"id": 3, "file_name": "C.jpg", "ordinal": 3},
        ]
    )
    model.set_manual_order_enabled(True)
    with qtbot.waitSignal(model.orderChanged, timeout=1000) as blocker:
        parent = QModelIndex()
        mime = model.mimeData([model.index(0, 0)])
        assert model.dropMimeData(mime, Qt.DropAction.MoveAction, 3, 0, parent)
    assert blocker.args[0] == [2, 3, 1]
```

Also add a session-level test: show a named list, simulate `orderChanged` / public `apply_grid_order(ids)`, assert `ordered_media_ids` persisted.

Delegate ordinal: a small test can instantiate the delegate and check `OrdinalRole` is read; if paint is hard to unit test, assert a helper `ordinal_label(value) -> "01"`.

- [ ] **Step 2: Fail then implement**

- [ ] **Step 3: pytest tests/test_grid_reorder.py tests/test_ordering.py tests/test_session.py -v**

- [ ] **Step 4: Commit** `feat(grid): persist drag reorder and paint list ordinals`

---

### Task 5: Source-folder remove, library sort/filter, read-only sources

**Files:**
- Modify: `src/local_media_curator/db/repositories.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Modify: `src/local_media_curator/ui/library_panel.py` if adding sort combo
- Create: `tests/test_library_query.py`
- Modify: `tests/test_scan_immutability.py` or create `tests/test_readonly_source.py`

**Interfaces:**
- Consumes: `source_folders` table, `LibraryService.list_media`
- Produces:
  - `LibraryService.remove_source_folder(path: Path)` deletes the `source_folders` row only (does not delete media files or media rows)
  - File menu: Remove Source Folder (picker or last-added is OK if tests call the method)
  - `list_media(..., sort_by: str = "file_name")` supporting `file_name`, `captured_at`, `modified_at`, `file_size`, `imported_at`
  - `list_media(..., media_type: str | None = None, extension: str | None = None)`
  - Library UI makes automatic-sort vs manual-list order obvious (window status tip or label `Library (sorted)` vs `List (manual order)`)
  - Sort combo does not rewrite `list_items.sort_key`

- [ ] **Step 1: Failing tests**

```python
from pathlib import Path
import os
import stat

from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


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


def test_scan_read_only_source_directory(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (10, 10)).save(photo, "JPEG")
    os.chmod(source, stat.S_IREAD | stat.S_IEXEC)
    try:
        lib = LibraryService(project)
        lib.add_source_folder(source)
        lib.scan()
        assert project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 1
        assert photo.is_file()
    finally:
        os.chmod(source, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        project.close()
```

Windows may need `stat.S_IREAD` only on the file, not the directory. If directory chmod is unreliable on Windows, make the **file** read-only (`os.chmod(photo, stat.S_IREAD)`) and assert scan still inserts a row without modifying bytes.

- [ ] **Step 2: Implement**

- [ ] **Step 3: pytest the new tests + tests/test_library.py tests/test_scan_immutability.py**

- [ ] **Step 4: Commit** `feat(library): remove source folders, sort, and read-only scan`

---

### Task 6: PyInstaller one-folder packaging and docs

**Files:**
- Create: `build/local_media_curator.spec`
- Create: `scripts/build_windows.ps1`
- Modify: `pyproject.toml` (optional extra `packaging = ["pyinstaller"]`)
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Create: `tests/test_packaging.py`

**Interfaces:**
- Consumes: `local_media_curator.__main__:main`
- Produces:
  - PyInstaller **one-folder** spec (`COLLECT`, not one-file)
  - `datas` / `binaries` must **not** include `photos/`, `phototakeplan/`, `lightphotosprt/`
  - `scripts/build_windows.ps1` runs `python -m PyInstaller build/local_media_curator.spec`
  - README: Windows 10/11, install, `python -m local_media_curator`, packaged run path `dist/local_media_curator/local_media_curator.exe`, data location (`project.sqlite3` in chosen project dir), backup = copy project folder
  - ARCHITECTURE.md updated so scanning/thumbs/lists/undo are no longer “later”

- [ ] **Step 1: Failing test**

```python
from pathlib import Path

SPEC = Path("build/local_media_curator.spec")


def test_spec_is_one_folder_and_excludes_protected_dirs() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "COLLECT" in text
    assert "EXE(" in text
    for banned in ("photos/", "phototakeplan/", "lightphotosprt/"):
        assert banned not in text.replace("\\", "/")
```

If PyInstaller is installed, the script may run a build; do **not** fail the unit suite if PyInstaller is missing. Optional: skip a live build test unless `importlib.util.find_spec("PyInstaller")`.

- [ ] **Step 2: Write spec + script + docs**

- [ ] **Step 3: Try `python -m pip install pyinstaller` and run the spec once if network allows; store the command in README even if the live build is skipped**

- [ ] **Step 4: Commit** `build(win): add PyInstaller one-folder spec`
