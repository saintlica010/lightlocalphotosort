# Phase 1.1 Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Phase 1 reliably fast, safe, and usable at 1k–10k local photos by applying the blocking and required fixes in `docs/PHASE1_1_REVIEW_FIXES.md` without redesigning the app or starting Phase 2.

**Architecture:** Keep the existing PySide6 / sqlite3 / project-local cache layout. Fix grid reload (bulk list membership), thumbnail scheduling (viewport + bounded pending), decoded pixmap cache (LRU), preview (latest-only slot), scan (cooperative cancel + throttled progress), generic project/source path separation, and compact filter UI. Record sanitized Windows smoke and 1k/10k performance evidence.

**Tech Stack:** Python 3.12 or 3.13, PySide6, stdlib sqlite3, Pillow, pytest/pytest-qt, PyInstaller one-folder.

## Status as of `7383af3` (do not start at Task 1)

Tasks **1–5 are done** on `feat/phase1-mvp` (see commits `4b76373`, `84cf980`, `fc73670`, `b81d984`, `e39bcb3`, `4dc8a17`). Their steps are marked complete below. Do not re-implement them.

**Do not continue this plan linearly at Task 6.** A whole-branch review after Task 5 found defects the original sequence would miss. The live work queue is `docs/PHASE1_1_REMAINING_FIXES.md` §5:

1. **C1** — `_reload_grid` does O(N) filesystem work on the GUI thread (`_thumbnail_path` / `cached_path`). Verify with a filesystem-call-count test, not a timing assertion. Arm the `ThumbnailDelegate` paint invariant (M10) first.
2. **I1** — batch-commit the scan so GUI writes during scan are not dropped (`SQLITE_BUSY`).
3. **I2** — restore selection/preview after non-reorder refresh.
4. **I3 / Task 7** — generic project/source overlap guard (still an `AGENTS.md` safety gap).
5. **Tasks 6 and 8** — scan progress and filter UI (specs below remain valid).
6. **I4** — refresh `ARCHITECTURE.md` (and README if needed) after C1, not before.
7. **Tasks 9 and 10** — 1k/10k perf evidence and Windows smoke. **Do not run these until C1 is fixed**, or the reports will record GUI freezes as baseline.
8. Remaining minors in the handoff, except items it explicitly drops.

Use Python **3.12 or 3.13** (`AGENTS.md` §12). Do not use Python 3.14: it has been measured to segfault ~5% of full-suite runs in Pillow WebP save on a `QThreadPool` worker. That is a toolchain defect, not an app bug.

## Global Constraints

- Work on branch `feat/phase1-mvp` in the existing isolated worktree for this clone. Do not merge to `main`. Do not hard-code another machine's worktree path.
- Do not redesign the app. Do not introduce Electron, a web UI, SQLAlchemy, cloud/network/telemetry, or Phase 2 features (video thumbs, playback, export, HEIC, installer).
- Protected local trees `photos/`, `phototakeplan/`, and `lightphotosprt/` are read-only reference data. Never modify, rename, move, delete, rewrite EXIF/XMP, create sidecars, or write project DB/cache/log/test output inside them. Never commit or upload them.
- Automated tests must use generated files under pytest `tmp_path` only. Do not read or write real `photos/` contents in tests.
- Never `git add .`. Stage explicit paths only. Before every commit, inspect staged paths and reject anything under the protected trees, `dist/`, `build/local_media_curator/`, or user media.
- Git author is already repo-local `lica.liu`. Do not change git config.
- Follow TDD: write the failing test, run it and confirm it fails for the right reason, write minimal production code, confirm the test passes, then run the covering tests before commit.
- Qt widgets do not execute SQL. Services own behavior. Repositories own SQL. Media workers open their own SQLite connections and never reuse the GUI connection.
- Source media remains byte-for-byte unchanged. Thumbnails stay under `project.thumbnails_dir`. Preview EXIF orientation is in-memory only.
- SQLite `IN (...)` lists must be chunked at 400 ids so a 10k library never hits the default 999-variable limit.
- Temporary filter/sort never rewrites `list_items.sort_key`.
- Prefer: source safety > correctness > responsiveness > simplicity > extra features.

## File structure

- Modify: `src/local_media_curator/db/repositories.py` — bulk list names; source-folder and missing filters
- Modify: `src/local_media_curator/services/list_service.py` — bulk list-name wrapper
- Modify: `src/local_media_curator/services/library_service.py` — scan cancel/progress; source overlap check; extra list filters
- Modify: `src/local_media_curator/ui/main_window.py` — bulk membership on reload; viewport thumb scheduling; scan cancel/progress status; filter plumbing; wait for scan thread
- Create: `src/local_media_curator/media/thumbnail_schedule.py` — pure prioritize/bound helper
- Modify: `src/local_media_curator/media/thumbnail_pool.py` — inflight vs pending, `sync()`, bounded pending
- Modify: `src/local_media_curator/ui/media_grid.py` — viewport row range + signal
- Create: `src/local_media_curator/ui/pixmap_cache.py` — bounded LRU pixmap cache
- Modify: `src/local_media_curator/ui/thumbnail_delegate.py` — use bounded cache
- Modify: `src/local_media_curator/media/preview_loader.py` — latest-only pending slot
- Modify: `src/local_media_curator/media/scanner.py` — cancel check, progress callback, rollback on cancel
- Modify: `src/local_media_curator/media/scan_worker.py` — cancel event, progress/cancelled signals
- Modify: `src/local_media_curator/domain/paths.py` — generic overlap helper
- Modify: `src/local_media_curator/services/project_service.py` — keep name-based protected-root checks
- Modify: `src/local_media_curator/ui/library_panel.py` — compact type/extension/folder/missing filters
- Modify: `ARCHITECTURE.md`, `README.md` only if behavior described there changed
- Create: `docs/verification/phase1_1_windows_smoke.md`, `docs/verification/phase1_1_performance.md`
- Create: `scripts/perf_smoke.py` — synthetic 1k/10k timings (tmp dirs only)
- Tests under `tests/` as named in each task

---

### Task 1: Bulk-load list memberships

**Files:**
- Modify: `src/local_media_curator/db/repositories.py`
- Modify: `src/local_media_curator/services/list_service.py`
- Modify: `src/local_media_curator/ui/main_window.py` (`_row_from_media` / `_reload_grid`)
- Test: `tests/test_lists.py`
- Test: `tests/test_library_query.py` (query-count regression)

**Interfaces:**
- Consumes: existing `ListRepository.list_names_for_media(media_id: int) -> list[str]`
- Produces: `ListRepository.list_names_for_media_ids(media_ids: list[int]) -> dict[int, list[str]]`; `ListService.list_names_for_media_ids(media_ids: list[int]) -> dict[int, list[str]]`; `_IN_CHUNK = 400`

- [x] **Step 1: Write the failing tests**

Add to `tests/test_lists.py`:

```python
def test_list_names_for_media_ids_bulk(tmp_path: Path) -> None:
    project, lists, ids, _source = _setup(tmp_path, ("A.jpg", "B.jpg", "C.jpg"))
    promo = lists.create("Promotional")
    web = lists.create("Website")
    lists.add_items(promo, [ids["A.jpg"], ids["B.jpg"]])
    lists.add_items(web, [ids["A.jpg"]])
    mapping = lists.list_names_for_media_ids(
        [ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]]
    )
    assert mapping[ids["A.jpg"]] == ["Promotional", "Website"]
    assert mapping[ids["B.jpg"]] == ["Promotional"]
    assert mapping[ids["C.jpg"]] == []
    project.close()
```

Add to `tests/test_library_query.py`:

```python
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
    conn = project.connection
    original = conn.execute
    seen: list[str] = []

    def wrapped(sql, parameters=()):
        text = str(sql)
        if "list_items" in text and "lists" in text:
            seen.append(text)
        return original(sql, parameters)

    conn.execute = wrapped  # type: ignore[method-assign]
    window.show_library_view("all")
    membership_queries = [
        sql for sql in seen if "list_items" in sql and "lists" in sql
    ]
    assert len(membership_queries) <= 1
    assert window.media_grid.model.rowCount() == 3
    project.close()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lists.py::test_list_names_for_media_ids_bulk tests/test_library_query.py::test_grid_reload_does_not_issue_per_item_list_name_queries -v`

Expected: FAIL with `AttributeError: list_names_for_media_ids` and/or too many membership queries (current `_row_from_media` calls `list_names_for_media` per row).

- [x] **Step 3: Write minimal implementation**

In `ListRepository` add `_IN_CHUNK = 400` and:

```python
def list_names_for_media_ids(self, media_ids: list[int]) -> dict[int, list[str]]:
    mapping: dict[int, list[str]] = {int(media_id): [] for media_id in media_ids}
    if not media_ids:
        return mapping
    unique_ids = list(dict.fromkeys(int(media_id) for media_id in media_ids))
    for start in range(0, len(unique_ids), _IN_CHUNK):
        chunk = unique_ids[start : start + _IN_CHUNK]
        placeholders = ",".join("?" * len(chunk))
        rows = self._conn.execute(
            f"""
            SELECT list_items.media_id, lists.name
            FROM list_items
            JOIN lists ON lists.id = list_items.list_id
            WHERE list_items.media_id IN ({placeholders})
            ORDER BY lists.name COLLATE NOCASE, lists.id
            """,
            tuple(chunk),
        )
        for row in rows:
            mapping[int(row[0])].append(str(row[1]))
    return mapping
```

Keep `list_names_for_media` as `return self.list_names_for_media_ids([media_id]).get(media_id, [])`.

`ListService.list_names_for_media_ids` delegates to the repository.

In `MainWindow._reload_grid`, after `items = self._media_for_current_view()`:

```python
media_ids = [item.id for item in items]
names_by_id = (
    self.list_service.list_names_for_media_ids(media_ids)
    if self.list_service is not None
    else {}
)
rows = [
    self._row_from_media(
        item,
        ordinal if list_mode else None,
        names_by_id.get(item.id, []),
    )
    for ordinal, item in enumerate(items, start=1)
]
```

Change `_row_from_media` to take `lists: list[str]` instead of querying.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lists.py tests/test_library_query.py tests/test_main_window.py -v`

Expected: PASS

- [x] **Step 5: Commit**

```text
git add src/local_media_curator/db/repositories.py src/local_media_curator/services/list_service.py src/local_media_curator/ui/main_window.py tests/test_lists.py tests/test_library_query.py
git commit -m "perf(grid): bulk-load list memberships"
```

---

### Task 2: Viewport-driven thumbnail scheduling

**Files:**
- Create: `src/local_media_curator/media/thumbnail_schedule.py`
- Modify: `src/local_media_curator/media/thumbnail_pool.py`
- Modify: `src/local_media_curator/ui/media_grid.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_thumbnail_schedule.py`
- Test: `tests/test_thumbnail_pool.py`

**Interfaces:**
- Consumes: existing `ThumbnailPool.request`, `ThumbnailService.ensure`, `MainWindow._thumbnail_jobs`
- Produces: `MAX_PENDING = 64`; `PREFETCH_ROWS = 24`; `prioritize_jobs(needed: dict[int, str], visible_ids: Sequence[int], inflight: set[int], max_pending: int = MAX_PENDING) -> list[tuple[int, str]]`; `ThumbnailPool.sync(needed: dict[int, str], visible_ids: Sequence[int]) -> None`; `ThumbnailPool.pending_ids() -> list[int]`; `ThumbnailPool.inflight_ids() -> set[int]`; `MediaGrid.viewportRowsChanged = Signal(int, int)`; `MediaGrid.visible_row_range(prefetch: int = PREFETCH_ROWS) -> tuple[int, int]`

- [x] **Step 1: Write the failing tests**

Create `tests/test_thumbnail_schedule.py`:

```python
from local_media_curator.media.thumbnail_schedule import MAX_PENDING, prioritize_jobs


def test_visible_ids_are_requested_first() -> None:
    needed = {i: f"p{i}" for i in range(100)}
    jobs = prioritize_jobs(needed, visible_ids=[50, 51, 52], inflight=set())
    assert [media_id for media_id, _path in jobs[:3]] == [50, 51, 52]


def test_inflight_ids_are_not_duplicated() -> None:
    needed = {1: "a", 2: "b", 3: "c"}
    jobs = prioritize_jobs(needed, visible_ids=[1, 2], inflight={1})
    assert [media_id for media_id, _path in jobs] == [2, 3]


def test_pending_work_is_bounded_for_10000_items() -> None:
    needed = {i: f"p{i}" for i in range(10_000)}
    jobs = prioritize_jobs(needed, visible_ids=list(range(20)), inflight=set())
    assert len(jobs) <= MAX_PENDING
    assert [media_id for media_id, _path in jobs[:20]] == list(range(20))


def test_repeated_prioritize_does_not_grow() -> None:
    needed = {i: f"p{i}" for i in range(10_000)}
    first = prioritize_jobs(needed, visible_ids=[1, 2], inflight=set())
    second = prioritize_jobs(needed, visible_ids=[3, 4], inflight=set())
    assert len(first) <= MAX_PENDING
    assert len(second) <= MAX_PENDING
    assert [media_id for media_id, _path in second[:2]] == [3, 4]
```

Add to `tests/test_thumbnail_pool.py`:

```python
def test_pool_sync_bounds_pending_and_promotes_visible(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    pool = ThumbnailPool(project)
    needed = {i: str(tmp_path / f"{i}.jpg") for i in range(10_000)}
    pool.sync(needed, visible_ids=list(range(10)))
    assert len(pool.pending_ids()) + len(pool.inflight_ids()) <= 64
    first_pending = pool.pending_ids()
    assert 9999 not in first_pending
    pool.sync(needed, visible_ids=[9999])
    ordered = list(pool.inflight_ids()) + pool.pending_ids()
    assert 9999 in ordered
    assert ordered[0] == 9999 or 9999 in pool.inflight_ids()
    assert len(pool.pending_ids()) + len(pool.inflight_ids()) <= 64
    pool.clear()
    project.close()
```

Keep existing `request()` tests working: `request(jobs)` should call `sync({id: path for id, path in jobs}, visible_ids=[id for id, _ in jobs])`.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_thumbnail_schedule.py tests/test_thumbnail_pool.py::test_pool_sync_bounds_pending_and_promotes_visible -v`

Expected: FAIL (module/attribute missing).

- [x] **Step 3: Write minimal implementation**

`thumbnail_schedule.py`:

```python
from collections.abc import Mapping, Sequence

MAX_PENDING = 64
PREFETCH_ROWS = 24


def prioritize_jobs(
    needed: Mapping[int, str],
    visible_ids: Sequence[int],
    inflight: set[int],
    max_pending: int = MAX_PENDING,
) -> list[tuple[int, str]]:
    ordered: list[tuple[int, str]] = []
    seen = set(inflight)
    for media_id in visible_ids:
        if media_id in seen:
            continue
        path = needed.get(media_id)
        if path is None:
            continue
        seen.add(media_id)
        ordered.append((media_id, path))
        if len(ordered) >= max_pending:
            return ordered
    for media_id, path in needed.items():
        if media_id in seen:
            continue
        seen.add(media_id)
        ordered.append((media_id, path))
        if len(ordered) >= max_pending:
            break
    return ordered
```

Change `ThumbnailPool` so QThreadPool only holds in-flight jobs (`<= MAX_WORKERS`). Keep a lock-guarded `OrderedDict` pending queue rebuilt by `sync()`. `clear()` drops pending and calls `self._pool.clear()`; in-flight jobs may finish and must no-op if the media id is no longer expected (generation counter or discarded set).

`MediaGrid.visible_row_range`: sample `indexAt` across the viewport (step `THUMB_SIZE // 2`), take min/max valid rows, expand by `prefetch`, clamp to `[0, rowCount-1]`. Emit `viewportRowsChanged` (debounced ~16ms) on scrollbar changes, resize, and model reset.

`MainWindow._reload_grid` must **not** `request()` the entire missing-thumb set. Store `_thumb_needed: dict[int, str]` from `_thumbnail_jobs`, connect `viewportRowsChanged` once, and call `_sync_thumbnails()` which:

1. reads `first, last = self.media_grid.visible_row_range()`
2. builds `visible_ids` from those model rows (skip rows that already have `thumbnail_path`)
3. `self.thumbnail_pool.sync(self._thumb_needed, visible_ids)`

Do not enqueue 10k jobs into `QThreadPool`.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_thumbnail_schedule.py tests/test_thumbnail_pool.py tests/test_main_window.py -v`

Expected: PASS

- [x] **Step 5: Commit**

```text
git add src/local_media_curator/media/thumbnail_schedule.py src/local_media_curator/media/thumbnail_pool.py src/local_media_curator/ui/media_grid.py src/local_media_curator/ui/main_window.py tests/test_thumbnail_schedule.py tests/test_thumbnail_pool.py
git commit -m "perf(thumbs): schedule thumbnails from viewport"
```

---

### Task 3: Bound decoded thumbnail pixmap cache

**Files:**
- Create: `src/local_media_curator/ui/pixmap_cache.py`
- Modify: `src/local_media_curator/ui/thumbnail_delegate.py`
- Test: `tests/test_pixmap_cache.py`

**Interfaces:**
- Consumes: `ThumbnailDelegate._pixmap_for`
- Produces: `PIXMAP_CACHE_LIMIT = 256`; `BoundedPixmapCache(max_items: int)` with `get(key) -> QPixmap | None`, `put(key, pixmap)`, `len()`, `keys()`

- [x] **Step 1: Write the failing test**

```python
from PySide6.QtGui import QPixmap
from local_media_curator.ui.pixmap_cache import PIXMAP_CACHE_LIMIT, BoundedPixmapCache


def test_pixmap_cache_evicts_oldest_beyond_capacity() -> None:
    cache = BoundedPixmapCache(max_items=3)
    cache.put("a", QPixmap(1, 1))
    cache.put("b", QPixmap(1, 1))
    cache.put("c", QPixmap(1, 1))
    cache.put("d", QPixmap(1, 1))
    assert len(cache) == 3
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("d") is not None


def test_pixmap_cache_get_refreshes_lru_order() -> None:
    cache = BoundedPixmapCache(max_items=2)
    cache.put("a", QPixmap(1, 1))
    cache.put("b", QPixmap(1, 1))
    assert cache.get("a") is not None
    cache.put("c", QPixmap(1, 1))
    assert cache.get("b") is None
    assert cache.get("a") is not None


def test_default_limit_is_bounded() -> None:
    assert PIXMAP_CACHE_LIMIT == 256
    cache = BoundedPixmapCache()
    for i in range(300):
        cache.put(str(i), QPixmap(1, 1))
    assert len(cache) == 256
    assert cache.get("0") is None
    assert cache.get("299") is not None
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pixmap_cache.py -v`

Expected: FAIL (import error).

- [x] **Step 3: Write minimal implementation**

`BoundedPixmapCache` uses `collections.OrderedDict`. `get` moves the key to the end. `put` inserts/updates and `popitem(last=False)` while `len > max_items`. `ThumbnailDelegate` stores `self._pixmaps = BoundedPixmapCache()` instead of a dict. Keep disk WebP loading in `_pixmap_for`; do not decode source images in `paint()`.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pixmap_cache.py tests/test_thumbnail_pool.py -v`

Expected: PASS

- [x] **Step 5: Commit**

```text
git add src/local_media_curator/ui/pixmap_cache.py src/local_media_curator/ui/thumbnail_delegate.py tests/test_pixmap_cache.py
git commit -m "perf(thumbs): bound decoded pixmap cache"
```

---

### Task 4: Preview latest-wins scheduling

**Files:**
- Modify: `src/local_media_curator/media/preview_loader.py`
- Test: `tests/test_preview_loader.py`

**Interfaces:**
- Consumes: existing `PreviewLoader.load(path, token, max_edge)` and token filtering in `PreviewPanel`
- Produces: a single pending slot; at most one queued-not-started job besides the in-flight decode; obsolete B/C must not fully decode when A→B→C→D is requested rapidly

- [x] **Step 1: Write the failing test**

Add to `tests/test_preview_loader.py`:

```python
import threading
import time
from pathlib import Path

from PIL import Image


def test_rapid_loads_skip_obsolete_queued_work(qtbot, tmp_path: Path, monkeypatch) -> None:
    paths = []
    for name in ("A.jpg", "B.jpg", "C.jpg", "D.jpg"):
        path = tmp_path / name
        Image.new("RGB", (80, 80), "white").save(path, "JPEG")
        paths.append(path)

    started: list[str] = []
    decoded: list[str] = []
    gate = threading.Event()
    release_a = threading.Event()

    from local_media_curator.media import preview_loader as module
    real = module.load_preview_image

    def slow_load(path: Path, max_edge: int):
        name = Path(path).name
        started.append(name)
        if name == "A.jpg":
            gate.set()
            release_a.wait(timeout=5)
        decoded.append(name)
        return real(path, max_edge)

    monkeypatch.setattr(module, "load_preview_image", slow_load)
    loader = module.PreviewLoader()
    loaded_tokens: list[int] = []
    loader.loaded.connect(lambda token, _image: loaded_tokens.append(int(token)))
    loader.load(str(paths[0]), 1, 400)
    qtbot.waitUntil(lambda: gate.is_set(), timeout=8000)
    loader.load(str(paths[1]), 2, 400)
    loader.load(str(paths[2]), 3, 400)
    loader.load(str(paths[3]), 4, 400)
    release_a.set()
    qtbot.waitUntil(lambda: 4 in loaded_tokens, timeout=8000)
    assert 2 not in loaded_tokens
    assert 3 not in loaded_tokens
    assert loaded_tokens[-1] == 4
    assert "B.jpg" not in decoded
    assert "C.jpg" not in decoded
```

Retain `test_preview_loader_emits_downsampled_image` (token validation still required).

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_preview_loader.py::test_rapid_loads_skip_obsolete_queued_work -v`

Expected: FAIL because B and C are fully decoded (current code starts a QRunnable per `load()`).

- [x] **Step 3: Write minimal implementation**

Replace per-call `QThreadPool.start` with:

- `_latest_token`, `_latest_path`, `_latest_max_edge`
- `_busy: bool`
- `load()` updates latest fields; if not busy, start one job for the latest snapshot
- job `run()` re-reads latest token at start; if its snapshot token != latest, emit finished with `None` without decoding
- `_emit_loaded`: if token != latest, start a new job for the latest snapshot and do not emit `loaded`; if token == latest, emit `loaded` and clear busy (or start latest if it changed during emit)

Keep `QThreadPool` max thread count at 1. Do not decode on the GUI thread. Keep token checks in `PreviewPanel._on_preview_loaded`.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_preview_loader.py tests/test_preview.py -v`

Expected: PASS

- [x] **Step 5: Commit**

```text
git add src/local_media_curator/media/preview_loader.py tests/test_preview_loader.py
git commit -m "perf(preview): prefer latest preview request"
```

---

### Task 5: Cooperative scan cancellation

**Files:**
- Modify: `src/local_media_curator/media/scanner.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Modify: `src/local_media_curator/media/scan_worker.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_scan_worker.py`

**Interfaces:**
- Consumes: `LibraryService.scan()`, `ScanWorker.run(db_path)`, `MainWindow._stop_scan_thread`
- Produces: `class ScanCancelled(Exception)` in `scanner.py`; `scan_source_folder(..., cancel_check: Callable[[], bool] | None = None)`; `LibraryService.scan(cancel_check=None)`; `ScanWorker.cancel()`; `ScanWorker.cancelled = Signal()`; `_stop_scan_thread` requests cancel and waits until the QThread is actually finished (timeout 30s). No `QThread.terminate()`.

- [x] **Step 1: Write the failing tests**

Add to `tests/test_scan_worker.py`:

```python
import threading
import time


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
    qtbot.waitUntil(
        lambda: thread is not None and not thread.isRunning(),
        timeout=15000,
    )
    assert window.findChildren(QThread) == []
    project.connection.execute("SELECT COUNT(*) FROM media").fetchone()
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
    window.set_project(second)
    qtbot.waitUntil(
        lambda: old_thread is not None and not old_thread.isRunning(),
        timeout=15000,
    )
    assert window.project is second
    second.close()
```

On cancel, `scan_source_folder` must `rollback()` the in-progress folder transaction so the DB is not left mid-statement. Previously completed folders (already committed) may remain. Source files must still exist unchanged.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scan_worker.py::test_cancel_stops_slow_scan_and_thread tests/test_scan_worker.py::test_set_project_cancels_running_scan_thread -v`

Expected: FAIL or hang until timeout — current `_stop_scan_thread` calls `quit()`/`wait(2000)` and drops refs while the synchronous scan is still running; scanner has no cancel check.

- [x] **Step 3: Write minimal implementation**

```python
class ScanCancelled(Exception):
    pass
```

In the per-file loop of `scan_source_folder`, before `stat`/`insert`:

```python
if cancel_check is not None and cancel_check():
    conn.rollback()
    raise ScanCancelled()
```

`LibraryService.scan(cancel_check=None)` passes it through. `ScanWorker` holds `threading.Event`; `cancel()` sets it; `run()` uses `cancel_check=self._cancel.is_set`. Catch `ScanCancelled` and emit `cancelled` (not `failed`). `MainWindow._stop_scan_thread` calls `worker.cancel()` then `thread.quit(); thread.wait(30000)`. If still running, **do not** drop refs or `deleteLater`. Never call `QThread.terminate()`. Connect `cancelled` to the same UI cleanup as `finished` (stop thread, refresh).

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scan_worker.py tests/test_scan_immutability.py -v`

Expected: PASS

- [x] **Step 5: Commit**

```text
git add src/local_media_curator/media/scanner.py src/local_media_curator/services/library_service.py src/local_media_curator/media/scan_worker.py src/local_media_curator/ui/main_window.py tests/test_scan_worker.py
git commit -m "fix(scan): add cooperative cancellation"
```

---

### Task 6: Scan progress reporting

**Files:**
- Modify: `src/local_media_curator/media/scanner.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Modify: `src/local_media_curator/media/scan_worker.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_scan_worker.py`

**Interfaces:**
- Consumes: Task 5 cancel_check plumbing
- Produces: `progress_cb: Callable[[int], None] | None` on scan; `ScanWorker.progress = Signal(int)`; status text `Scanning... {n:,} files processed`; throttle so GUI is not updated on every file (`PROGRESS_EVERY = 25` files)

- [ ] **Step 1: Write the failing test**

```python
def test_scan_emits_throttled_progress_on_gui_thread(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    for i in range(30):
        Image.new("RGB", (8, 8)).save(source / f"{i:02d}.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    counts: list[int] = []
    threads: list[int] = []

    def on_progress(count: int) -> None:
        from PySide6.QtCore import QThread
        counts.append(int(count))
        threads.append(int(QThread.currentThread() is window.thread()))

    window._scan_progress_hook = on_progress  # or connect to worker.progress after scan() starts
    window.scan()
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=15000)
    assert counts
    assert counts[-1] >= 30
    assert all(threads)
    assert "Scanning..." in window.statusBar().currentMessage() or window.statusBar().currentMessage() in {
        "Library (sorted)",
        "List (manual order)",
    }
    project.close()
```

Prefer connecting `ScanWorker.progress` from `MainWindow.scan()` rather than a test-only hook. The test can subclass or connect after replacing scan wiring if the worker is stored on the window (`window._scan_worker.progress.connect(...)`) **before** `thread.start()` — connect in the test by patching `ScanWorker` if needed. Simplest: the test constructs nothing extra; after `window.scan()` the worker exists immediately, so:

```python
window.scan()
assert window._scan_worker is not None
window._scan_worker.progress.connect(on_progress)
```

If the worker may finish too fast, keep 30 files and connect inside a `ScanWorker` subclass only if necessary. Production code must emit `progress` from the worker thread via Qt queued connection to the GUI slot.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scan_worker.py::test_scan_emits_throttled_progress_on_gui_thread -v`

Expected: FAIL (no `progress` signal).

- [ ] **Step 3: Write minimal implementation**

Count processed files in `scan_source_folder`. Call `progress_cb(n)` when `n == 1`, every `PROGRESS_EVERY` files, and at folder end. `ScanWorker` emits `progress` from that callback. `MainWindow` connects `progress` with `QueuedConnection` to a slot that `statusBar().showMessage(f"Scanning... {count:,} files processed")`. After finished/cancelled, restore the existing library/list status tip. Do not emit on every file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scan_worker.py tests/test_library_query.py::test_status_tip_distinguishes_library_and_list -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/media/scanner.py src/local_media_curator/services/library_service.py src/local_media_curator/media/scan_worker.py src/local_media_curator/ui/main_window.py tests/test_scan_worker.py
git commit -m "feat(scan): report scan progress"
```

---

### Task 7: Generic project/source overlap protection

**Files:**
- Modify: `src/local_media_curator/domain/paths.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Modify: `src/local_media_curator/services/project_service.py` (keep existing protected-name checks)
- Test: `tests/test_project_service.py`
- Test: `tests/test_library_query.py`

**Interfaces:**
- Consumes: `normalize_path`
- Produces: `paths_overlap(a: Path, b: Path) -> bool`; `reject_overlapping_roots(project_root: Path, source_root: Path) -> None` raises `ValueError`; `LibraryService.add_source_folder` calls it against `project.root`

- [ ] **Step 1: Write the failing tests**

```python
from local_media_curator.domain.paths import paths_overlap, reject_overlapping_roots


def test_paths_overlap_project_inside_source(tmp_path: Path) -> None:
    source = tmp_path / "Wedding2026"
    project = source / "curator-project"
    source.mkdir()
    project.mkdir()
    assert paths_overlap(project, source) is True
    with pytest.raises(ValueError, match="overlap"):
        reject_overlapping_roots(project, source)


def test_paths_overlap_source_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "MyProject"
    source = project / "inbox"
    project.mkdir()
    source.mkdir()
    assert paths_overlap(project, source) is True
    with pytest.raises(ValueError, match="overlap"):
        reject_overlapping_roots(project, source)


def test_sibling_project_and_source_allowed(tmp_path: Path) -> None:
    project = tmp_path / "MyProject"
    source = tmp_path / "Pictures"
    project.mkdir()
    source.mkdir()
    assert paths_overlap(project, source) is False
    reject_overlapping_roots(project, source)


def test_windows_case_insensitive_overlap(tmp_path: Path) -> None:
    source = tmp_path / "Pictures"
    project = source / "Proj"
    source.mkdir()
    project.mkdir()
    assert paths_overlap(project, Path(str(source).swapcase())) is True


def test_add_source_folder_rejects_overlap(tmp_path: Path) -> None:
    project = create_project(tmp_path / "MyProject")
    inside = project.root / "media"
    inside.mkdir()
    with pytest.raises(ValueError, match="overlap"):
        LibraryService(project).add_source_folder(inside)
    parent = tmp_path
    with pytest.raises(ValueError, match="overlap"):
        LibraryService(project).add_source_folder(parent)
    sibling = tmp_path / "Pictures"
    sibling.mkdir()
    LibraryService(project).add_source_folder(sibling)
    project.close()
```

Keep existing `test_create_project_refuses_photos_tree` / `test_open_project_refuses_photos_tree`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_project_service.py tests/test_library_query.py::test_add_source_folder_rejects_overlap -v`

Expected: FAIL (`paths_overlap` missing; `add_source_folder` currently allows overlap).

- [ ] **Step 3: Write minimal implementation**

```python
def paths_overlap(left: Path, right: Path) -> bool:
    a = normalize_path(left)
    b = normalize_path(right)
    if a == b:
        return True
    sep = os.sep
    return a.startswith(b + sep) or b.startswith(a + sep)


def reject_overlapping_roots(project_root: Path, source_root: Path) -> None:
    if paths_overlap(project_root, source_root):
        raise ValueError(
            f"Project and source folders overlap: {project_root} vs {source_root}"
        )
```

Call `reject_overlapping_roots(self._project.root, path)` at the start of `LibraryService.add_source_folder`. Use `normalize_path` so Windows case-insensitive equivalents collide. Keep the existing `_PROTECTED_DIR_NAMES` checks on create/open.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_project_service.py tests/test_library_query.py tests/test_scan_immutability.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/domain/paths.py src/local_media_curator/services/library_service.py tests/test_project_service.py tests/test_library_query.py
git commit -m "fix(paths): prevent project-source overlap"
```

---

### Task 8: Complete Phase 1 filter UI

**Files:**
- Modify: `src/local_media_curator/db/repositories.py`
- Modify: `src/local_media_curator/services/library_service.py`
- Modify: `src/local_media_curator/ui/library_panel.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Test: `tests/test_library_query.py`
- Test: `tests/test_lists.py` (sort_key unchanged under list + filter)

**Interfaces:**
- Consumes: existing `list_media(media_type=, extension=)`
- Produces: additional `source_folder: str | None` and `missing: bool | None` on `MediaRepository.list_media` / `list_unassigned` / `LibraryService.list_media` / `list_unassigned`; compact combos on `LibraryPanel` (type, extension, source folder, missing); `LibraryPanel.filters_changed = Signal()`; MainWindow applies filters on reload; named-list view filters in memory and does **not** write `sort_key`

Do not add a second Rejected control (All/Unassigned/Rejected views already exist). Keep the panel visually light: four `QComboBox` widgets under the sort combo.

- [ ] **Step 1: Write the failing tests**

```python
def test_list_media_filters_folder_and_missing(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    one = tmp_path / "cam1"
    two = tmp_path / "cam2"
    one.mkdir()
    two.mkdir()
    Image.new("RGB", (10, 10)).save(one / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(two / "B.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(one)
    lib.add_source_folder(two)
    lib.scan()
    from local_media_curator.domain.paths import normalize_path
    only_one = [m.file_name for m in lib.list_media(source_folder=normalize_path(one))]
    assert only_one == ["A.jpg"]
    (one / "A.jpg").unlink()
    lib.scan()
    missing = [m.file_name for m in lib.list_media(include_rejected=True, missing=True)]
    present = [m.file_name for m in lib.list_media(missing=False)]
    assert missing == ["A.jpg"]
    assert present == ["B.jpg"]
    project.close()


def test_filter_ui_image_video_jpg_folder_missing(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    one = tmp_path / "cam1"
    two = tmp_path / "cam2"
    one.mkdir()
    two.mkdir()
    Image.new("RGB", (10, 10)).save(one / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(one / "C.png", "PNG")
    (two / "D.mp4").write_bytes(b"not a real video")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(one)
    window.add_source_folder(two)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 3, timeout=8000)
    panel = window.library_panel
    panel.type_combo.setCurrentIndex(panel.type_combo.findData("image"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    panel.type_combo.setCurrentIndex(panel.type_combo.findData("video"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    panel.type_combo.setCurrentIndex(0)
    panel.extension_combo.setCurrentIndex(panel.extension_combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    assert window.media_grid.model.row_at(0)["file_name"] == "A.jpg"
    panel.extension_combo.setCurrentIndex(0)
    from local_media_curator.domain.paths import normalize_path
    folder_index = panel.folder_combo.findData(normalize_path(two))
    panel.folder_combo.setCurrentIndex(folder_index)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    assert window.media_grid.model.row_at(0)["file_name"] == "D.mp4"
    project.close()


def test_list_filter_does_not_change_sort_keys(qtbot, tmp_path: Path) -> None:
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
    window.library_panel.extension_combo.setCurrentIndex(
        window.library_panel.extension_combo.findData(".jpg")
    )
    after = window.list_service.items_with_sort_keys(list_id)
    assert after == before
    assert window.list_service.ordered_media_ids(list_id) == [
        ids["B.jpg"],
        ids["A.jpg"],
    ]
    project.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_library_query.py::test_list_media_filters_folder_and_missing tests/test_library_query.py::test_filter_ui_image_video_jpg_folder_missing tests/test_library_query.py::test_list_filter_does_not_change_sort_keys -v`

Expected: FAIL (kwargs/`type_combo` missing).

- [ ] **Step 3: Write minimal implementation**

Extend `_append_type_filters` into `_append_filters` adding:

- `source_folder`: prefix match via `substr(normalized_path, 1, ?) = ?` (same style as `list_under_folder`, no LIKE wildcards)
- `missing is True` → `missing = 1`; `missing is False` → `missing = 0`; `None` → no clause

`LibraryPanel` combo data:

- type: `None`, `"image"`, `"video"`
- extension: `None`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, `.tiff`, `.mp4`, `.mov`
- folder: `None` plus `set_source_folders(paths: list[str])`
- missing: `None`, `False` (Present), `True` (Missing)

`MainWindow._media_for_current_view` passes these into `list_media` / `list_unassigned`. For named-list view, fetch ordered media then filter in `LibraryService.filter_media(items, ...)` preserving input order. Call `set_source_folders` when reloading. Filtering must not call `ListService.reorder` / `set_sort_keys`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_library_query.py tests/test_lists.py tests/test_main_window.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add src/local_media_curator/db/repositories.py src/local_media_curator/services/library_service.py src/local_media_curator/ui/library_panel.py src/local_media_curator/ui/main_window.py tests/test_library_query.py
git commit -m "feat(filters): complete phase1 library filters"
```

---

### Task 9: 1k and 10k performance smoke

**Files:**
- Create: `scripts/perf_smoke.py`
- Create: `docs/verification/phase1_1_performance.md`
- Test: `tests/test_thumbnail_schedule.py` already covers 10k bounded queue; add `tests/test_perf_smoke.py` that runs the helper functions on 1k/10k **in-memory/sqlite tmp** rows without writing 10k JPEGs on every pytest invocation

**Interfaces:**
- Consumes: `prioritize_jobs`, `list_names_for_media_ids`, `list_media`, `create_project`
- Produces: sanitized report at `docs/verification/phase1_1_performance.md` with dataset size, OS/machine summary without personal identifiers, approximate timings, queue/cache behavior, remaining bottlenecks

- [ ] **Step 1: Write the failing test**

`tests/test_perf_smoke.py` inserts 1_000 then 10_000 media rows via `MediaRepository.insert` into a tmp project (no real photos), then:

- times `list_media()`
- times `list_names_for_media_ids(all_ids)` and asserts query count `<= ceil(n / 400)`
- times `prioritize_jobs` for 10k needed + 30 visible and asserts `len(jobs) <= 64`
- times a fake drag reorder of 50 items on a named list (`ListService.reorder`)

Assert each timed step is finite and membership is not O(N) queries. Do not read `photos/`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_perf_smoke.py -v`

Expected: FAIL if helper/report path missing; otherwise implement script first after seeing the test fail on import.

- [ ] **Step 3: Write `scripts/perf_smoke.py` and the report**

The script uses `tempfile.TemporaryDirectory`, creates a project **outside** protected trees, optionally writes a small number of tiny JPEGs (not 10k) for thumbnail timing, and inserts the rest as DB rows. Measure:

- project open
- `list_media` 1k and 10k
- bulk membership
- `prioritize_jobs` / `ThumbnailPool.sync` pending size
- filter change (`media_type="image"`)
- sort change
- named-list `ordered_media_ids`
- `reorder` of 20 ids

Write `docs/verification/phase1_1_performance.md` with sanitized names (`src/`, `proj/`). Include OS (`Windows`), Python version, approximate timings, `MAX_PENDING`/`PIXMAP_CACHE_LIMIT`, and remaining bottlenecks (no HEIC, no video thumbs, no viewport virtualization of widgets). Do not include user paths, real filenames, or photo metadata.

Run: `python scripts/perf_smoke.py` from the worktree and paste sanitized numbers into the report.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_perf_smoke.py tests/test_thumbnail_schedule.py tests/test_lists.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```text
git add scripts/perf_smoke.py tests/test_perf_smoke.py docs/verification/phase1_1_performance.md
git commit -m "test(perf): add 1k and 10k smoke coverage"
```

---

### Task 10: Windows PyInstaller smoke, docs, and verification report

**Files:**
- Create: `docs/verification/phase1_1_windows_smoke.md`
- Modify: `ARCHITECTURE.md` (viewport thumbs, bulk membership, cancel/progress, filters, overlap)
- Modify: `README.md` (filters, scan progress, project/source overlap)
- Test: existing `tests/test_packaging.py` plus a synthetic end-to-end pytest in `tests/test_phase1_1_smoke.py` covering the 16-step flow with tmp files

**Interfaces:**
- Consumes: `scripts/build_windows.ps1`, `dist/local_media_curator/local_media_curator.exe`
- Produces: sanitized smoke report; EXE launch evidence; confirmation that protected dirs are not bundled

- [ ] **Step 1: Write the failing synthetic smoke test**

`tests/test_phase1_1_smoke.py` using `tmp_path` + `MainWindow`:

1. create project in tmp
2. add sibling source folder with two tiny JPEGs
3. scan
4. create two lists, add the same photo to both
5. reorder each list differently via `apply_grid_order` / `ListService.reorder`
6. reject and restore
7. undo/redo
8. close project connection, `open_project` again
9. assert membership, orders, rejection persisted
10. hash source files before/after and assert equal

This is the automated stand-in for GUI steps 1–16. It must not touch `photos/`.

- [ ] **Step 2: Run test to verify it fails if the flow regresses; then implement any glue needed**

Run: `python -m pytest tests/test_phase1_1_smoke.py -v`

Expected: PASS against current behavior plus Tasks 1–8; if it fails, fix only smoke-test glue, not new features.

- [ ] **Step 3: Build and launch the Windows EXE**

From the worktree:

```text
python -m pip install -e ".[packaging]"
python -m PyInstaller build/local_media_curator.spec
```

Then start `dist/local_media_curator/local_media_curator.exe`, confirm the process starts, then stop it. Do not use protected directories as the project or source. Record:

- build succeeded (yes/no)
- EXE path as `dist/local_media_curator/local_media_curator.exe` (relative)
- process started (yes/no)
- pytest smoke result
- source hashes unchanged
- spec still has `datas=[]` and no protected dir names

Do not commit `dist/` or `build/local_media_curator/`. Do not put personal paths or real photo names in the report.

Update `ARCHITECTURE.md` scanning/thumbnails sections: cooperative cancel, progress, viewport scheduling, bounded pixmap cache, bulk list names, generic overlap, filter combos.

Update `README.md` status/install steps: filters, scan progress, reject overlapping project/source.

- [ ] **Step 4: Run the full suite**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q`

Expected: all previous Phase 1 tests plus new ones PASS, output pristine.

- [ ] **Step 5: Commit**

```text
git add tests/test_phase1_1_smoke.py docs/verification/phase1_1_windows_smoke.md ARCHITECTURE.md README.md docs/PHASE1_1_REVIEW_FIXES.md
git commit -m "docs(verify): record phase1.1 windows smoke"
```

If `docs/PHASE1_1_REVIEW_FIXES.md` is already committed, omit it.

---

## Self-review

**Spec coverage:** Blocking items 3–7 map to Tasks 2, 3, 1, 4, 5. Required items 8–12 map to Tasks 8, 6, 7, 10, 9. Preserve-behavior item 13 is enforced by running the existing suite each task. Item 1 (no redesign) and item 2 (protected data) are Global Constraints. Item 16 handoff is produced after SDD finishes.

**Placeholder scan:** No TBD/TODO steps. Each task has concrete tests, code, commands, and commit paths.

**Type consistency:** `list_names_for_media_ids` returns `dict[int, list[str]]`. `prioritize_jobs` / `sync` use `dict[int, str]` needed maps and `Sequence[int]` visible ids. `cancel_check` is `Callable[[], bool]`. `missing` filter is `bool | None`. `ScanWorker.progress` emits `int`.
