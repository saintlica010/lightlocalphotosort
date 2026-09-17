# Phase 1.1 Pre-Task-6 Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the remaining-fixes queue that must land before plan Task 6 (scan progress): M10 delegate invariant, C1 GUI-thread O(N) reload, I2 selection restore, I1 scan batch-commit / SQLITE_BUSY, and I3 project/source overlap.

**Architecture:** Keep PySide6 / sqlite3. Do not start Task 6 (progress UI), Task 8 (filters), or Task 9/10 (perf/smoke). Do not merge to `main`.

**Tech Stack:** Python 3.12 or 3.13 preferred (`AGENTS.md` §12). This machine may only have 3.14 — use it for focused tests; do not add Pillow `Image.init()` or other 3.14 workarounds if a worker segfaults.

## Status as of `01d9045`

All five tasks in this plan are implemented and task-reviewed on `feat/phase1-mvp`. A whole-queue review found one Important (`_thumb_paths` sticky across scans); that is fixed in `01d9045`. Next work is original plan Task 6 (scan progress), then Task 8 (filters), then I4 docs, then Tasks 9–10. Do not merge to `main` unless asked.

## Global Constraints

- Work on `feat/phase1-mvp` in this clone's existing isolated worktree. Do not merge to `main`.
- Protected trees `photos/`, `phototakeplan/`, `lightphotosprt/` are read-only. Tests use `tmp_path` only. Never `git add .`. Stage explicit paths.
- Git author is already repo-local `lica.liu`. Do not change git config.
- TDD: failing test first, confirm fail, minimal code, confirm pass, covering tests, then commit.
- Qt widgets do not execute SQL. No source-image decode on the GUI thread. No filesystem scans in the GUI thread (`AGENTS.md` §25).
- Source media remains byte-for-byte unchanged.
- Prefer: source safety > correctness > responsiveness > simplicity > extra features.
- Do not implement scan progress, filter UI, perf reports, or Windows smoke in this plan.

---

### Task 1: Arm ThumbnailDelegate paint invariant (M10)

**Files:**
- Test: `tests/test_thumbnail_delegate.py`
- Modify only if the test reveals a real paint() source decode (it should not)

**Interfaces:**
- Consumes: `ThumbnailDelegate._pixmap_for` reads only `MediaListModel.ThumbnailPathRole`
- Produces: a test that paints a row with a real JPEG source path and `thumbnail_path=None` and asserts the source file is never opened

- [ ] **Step 1: Write the failing test**

Create `tests/test_thumbnail_delegate.py`:

```python
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem

from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.thumbnail_delegate import ThumbnailDelegate


def test_delegate_paint_does_not_open_source_image(qtbot, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "A.jpg"
    Image.new("RGB", (40, 40), "red").save(source, "JPEG")
    opened: list[str] = []
    real_open = Path.open

    def tracking_open(self, *args, **kwargs):
        opened.append(str(self))
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    model = MediaListModel(
        [
            {
                "id": 1,
                "file_name": "A.jpg",
                "absolute_path": str(source),
                "thumbnail_path": None,
                "ordinal": 1,
                "rejected": False,
            }
        ]
    )
    delegate = ThumbnailDelegate()
    image = QImage(200, 220, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 176, 196)
    delegate.paint(painter, option, model.index(0))
    painter.end()
    assert str(source) not in opened
    assert not any(path.endswith("A.jpg") for path in opened)
```

Also add a second test: with `thumbnail_path` pointing at a tiny WebP under `tmp_path`, paint() may open that WebP, still must not open the JPEG source.

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_thumbnail_delegate.py -v`

If it **passes** against current `paint()` (source is not opened), that is the desired RED-for-regression: keep the test and commit it as the armed invariant. Do not change production code.

If it **fails** because paint opens the JPEG, fix `_pixmap_for` so it only loads `ThumbnailPathRole` (WebP), then re-run.

- [ ] **Step 3: Commit**

```text
git add tests/test_thumbnail_delegate.py
git commit -m "test(thumbs): guard delegate paint against source decode"
```

---

### Task 2: C1 — no per-row filesystem work in `_reload_grid`

**Files:**
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_library_query.py`

**Interfaces:**
- Consumes: existing `_on_thumbnail_ready`, `_thumb_needed`, `ThumbnailPool.sync`
- Produces: `self._thumb_paths: dict[int, str]` filled only by `_on_thumbnail_ready`, cleared in `set_project`; `_row_from_media` uses `_thumb_paths.get(media.id)` and does **not** call `ThumbnailService.cached_path` or `Path.is_file`; `_thumbnail_jobs` does **not** call `is_file()` — skip only `media_type != "image"` or `media.missing`; `_sync_thumbnails` treats ids absent from `_thumb_paths` as needing work

- [ ] **Step 1: Write the failing test**

Add to `tests/test_library_query.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_library_query.py::test_grid_reload_does_not_stat_each_source_or_cache_path -v`

Expected: FAIL — current `_thumbnail_path` / `_thumbnail_jobs` call `is_file` and `cached_path` per row.

- [ ] **Step 3: Write minimal implementation**

In `MainWindow.__init__` add `self._thumb_paths: dict[int, str] = {}`.

`set_project`: `self._thumb_paths = {}` before `refresh()`.

`_row_from_media`: `"thumbnail_path": self._thumb_paths.get(media.id)`.

Delete `_thumbnail_path` (or stop calling it).

`_thumbnail_jobs`:

```python
def _thumbnail_jobs(self, items: list[Media], rows: list[dict[str, object]]) -> list[tuple[int, str]]:
    jobs: list[tuple[int, str]] = []
    for media in items:
        if media.id in self._thumb_paths:
            continue
        if media.media_type != "image" or media.missing:
            continue
        jobs.append((media.id, media.absolute_path))
    return jobs
```

`_on_thumbnail_ready`:

```python
self._thumb_paths[int(media_id)] = path
self._thumb_needed.pop(int(media_id), None)
self.media_grid.model.set_thumbnail_path(int(media_id), path)
```

Do not call `Path.resolve()` / `Path.stat()` / `cached_path` from `_reload_grid`. Worker `ensure()` still stats on the pool thread.

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_library_query.py tests/test_thumbnail_delegate.py tests/test_thumbnail_pool.py tests/test_main_window.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/ui/main_window.py tests/test_library_query.py
git commit -m "perf(grid): skip filesystem work during grid reload"
```

---

### Task 3: I2 — restore selection and preview after refresh

**Files:**
- Modify: `src/local_media_curator/ui/main_window.py` (`_reload_grid`)
- Test: `tests/test_main_window.py` or `tests/test_undo.py`

**Interfaces:**
- Consumes: existing `_select_media_ids`
- Produces: `_reload_grid` captures selected ids and current id **before** `set_rows`, then re-selects them after (same helper the reorder paths use). Preview follows current index via existing `currentChanged`.

- [ ] **Step 1: Write the failing test**

```python
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
```

Also:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_main_window.py::test_undo_reject_restores_selection_and_preview tests/test_main_window.py::test_library_refresh_keeps_selection -v`

Expected: FAIL — `set_rows` resets the model and `_reload_grid` sets preview to None.

- [ ] **Step 3: Write minimal implementation**

At the start of the loaded-project branch of `_reload_grid`, capture `selected = self.media_grid.selected_ids()` and the current id if valid. After `set_rows` / status / `_sync_thumbnails`, if `selected`: `self._select_media_ids(selected)`. If capture is empty, keep today's "no selection → preview None" behavior.

Do not write `sort_key`. Do not skip `_sync_thumbnails`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_main_window.py tests/test_undo.py tests/test_grid_reorder.py tests/test_library_query.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/ui/main_window.py tests/test_main_window.py
git commit -m "fix(ui): restore selection after grid reload"
```

---

### Task 4: I1 — batch-commit scan and surface SQLITE_BUSY

**Files:**
- Modify: `src/local_media_curator/media/scanner.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_scan_worker.py`
- Test: `tests/test_library_query.py` or `tests/test_scan_immutability.py`

**Interfaces:**
- Consumes: existing `cancel_check`, `conn.commit()` at folder end
- Produces: `SCAN_COMMIT_BATCH = 256`; commit every 256 processed files **and** at folder end; on `ScanCancelled` rollback only the uncommitted tail; `cancel_check` also in the missing-marking loop; GUI curation methods catch `sqlite3.OperationalError` and `statusBar().showMessage("Database is busy. Try again.")` without dropping the process

- [ ] **Step 1: Write the failing tests**

```python
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
    other = connect(project.db_path)
    errors: list[str] = []

    def writer():
        started.wait(timeout=5)
        time.sleep(0.12)
        try:
            other.execute("UPDATE media SET rejected = 1 WHERE id = (SELECT id FROM media LIMIT 1)")
            other.commit()
        except sqlite3.OperationalError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=writer)
    thread.start()
    LibraryService(project).scan()
    thread.join(timeout=10)
    other.close()
    assert errors == []
    project.close()
```

```python
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
    assert "busy" in window.statusBar().currentMessage().lower()
    project.close()
```

Keep existing cancel tests passing (`COUNT(*) == 0` for a cancelled short scan still holds because 8 < 256, so the tail rolls back).

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_scan_worker.py::test_scan_commits_in_batches_so_other_connection_can_write tests/test_scan_worker.py::test_reject_during_locked_db_shows_status_not_raise -v`

Expected: FAIL (no `SCAN_COMMIT_BATCH`; reject raises).

- [ ] **Step 3: Write minimal implementation**

In `scanner.py`:

```python
SCAN_COMMIT_BATCH = 256
```

Count processed files in the per-file loop. After each insert/update/unchanged, if `processed % SCAN_COMMIT_BATCH == 0`: `conn.commit()`. In the missing-marking loop, call `cancel_check` each row and rollback+`ScanCancelled` if set. Final `conn.commit()` remains. `except ScanCancelled: conn.rollback(); raise`. Other exceptions still rollback.

In `MainWindow`, wrap `undo_stack.reject` / `restore` / `add_items` / `remove_items` / `reorder` / `move_*` / `undo` / `redo` call sites so `sqlite3.OperationalError` becomes a status message and does **not** call `refresh()` after a failed mutation.

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_scan_worker.py tests/test_scan_immutability.py tests/test_undo.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/media/scanner.py src/local_media_curator/ui/main_window.py tests/test_scan_worker.py
git commit -m "fix(scan): commit in batches and surface database busy"
```

---

### Task 5: I3 — generic project/source overlap protection

**Files:**
- Modify: `src/local_media_curator/domain/paths.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Test: `tests/test_project_service.py`
- Test: `tests/test_library_query.py`

**Interfaces:**
- Consumes: `normalize_path`
- Produces: `paths_overlap(a: Path, b: Path) -> bool`; `reject_overlapping_roots(project_root: Path, source_root: Path) -> None` raises `ValueError` matching `"overlap"`; `LibraryService.add_source_folder` calls it against `project.root`

Use the tests and implementation already written in `docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md` Task 7 (copy verbatim). Keep `_PROTECTED_DIR_NAMES` checks. Sibling directories allowed. Windows case-insensitive overlap via `normalize_path`.

- [ ] **Step 1: Write the failing tests** (verbatim from the Phase 1.1 plan Task 7)

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_project_service.py tests/test_library_query.py::test_add_source_folder_rejects_overlap -v`

- [ ] **Step 3: Write minimal implementation** (verbatim `paths_overlap` / `reject_overlapping_roots` from that plan)

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_project_service.py tests/test_library_query.py tests/test_scan_immutability.py -v`

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/domain/paths.py src/local_media_curator/services/library_service.py tests/test_project_service.py tests/test_library_query.py
git commit -m "fix(paths): prevent project-source overlap"
```
