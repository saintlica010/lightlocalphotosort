# OpenCode handoff — continue Phase 1.1

**This file is the live handoff.** Older docs on the branch are still useful as specs, but several of them are **stale about what is already done**. Follow the read order below.

Written: 2026-09-17
For: OpenCode (or any successor agent)
Repo: `https://github.com/saintlica010/lightlocalphotosort.git`
Branch: `feat/phase1-mvp`
Head at handoff: `c230e37` (`c230e37ec26b4795d7f15a026dfbfec3be059762`)
Do **not** merge to `main` unless the user explicitly asks.

---

## 0. Paste this into OpenCode first

```text
Continue Phase 1.1 of lightlocalphotosort on branch feat/phase1-mvp.

Read docs/OPENCODE_HANDOFF.md first. Then AGENTS.md. Then the Task 6 / Task 8
sections of docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md.

HEAD should be c230e37. If it is not, git fetch and reset/pull that branch
before coding.

Do not re-implement Tasks 1–5 or the pre-Task-6 queue (C1, I1, I2, I3, M10).
Those are already on the branch.

Next work, in this order:
1. Plan Task 6 — scan progress
2. Plan Task 8 — filter UI
3. I4 — update ARCHITECTURE.md / README to match current code
4. Plan Task 9 — 1k/10k perf smoke + docs/verification/phase1_1_performance.md
5. Plan Task 10 — Windows PyInstaller smoke + docs/verification/phase1_1_windows_smoke.md

Python 3.12 or 3.13 only. Not 3.14.
Never modify photos/, phototakeplan/, lightphotosprt/.
Never git add .
Do not merge to main.
Do not start Phase 2 (video thumbs, playback, export, HEIC, installer).
TDD. Tests use tmp_path only.
```

---

## 1. Checkout

```text
git fetch origin
git checkout feat/phase1-mvp
git pull --ff-only origin feat/phase1-mvp
git rev-parse --short HEAD
```

Expected: `c230e37`.

Work wherever the clone is. Do not hard-code another machine's path
(`C:\downloadbook\...` or `H:\2026shbookfair\...`). If a worktree already
exists for this branch, use it; do not create a nested one.

---

## 2. Read order

1. **This file** (`docs/OPENCODE_HANDOFF.md`) — current truth.
2. **`AGENTS.md`** — product rules. Authority over everything else.
3. **`docs/PHASE1_1_REVIEW_FIXES.md`** — original GPT review. Items #8, #9, #11, #12 are still open. Items #3–#7 and #10 are done.
4. **`docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md`** — implementation plan. **Start at Task 6**, then Task 8, then 9, then 10. Tasks 1–5 and Task 7 are done. The banner at the top of that file still says “do not continue at Task 6” because it was written *before* C1/I1/I2/I3 landed; that banner is now stale. C1 is fixed. You **should** do Task 6 next.
5. **`docs/superpowers/plans/2026-09-17-phase1-1-pre-task6.md`** — the queue that was between original Task 5 and Task 6. **Complete.** Do not re-run it.
6. **`docs/PHASE1_1_REMAINING_FIXES.md`** — overnight review. Useful for leftover minors and the “dropped” list. **§0–§3 and the C1/I3 write-ups describe the tree at `4dc8a17` / `7383af3`.** They still claim `paths_overlap` is missing and `_reload_grid` stats every row. That is no longer true. Trust §5’s status update at the top of the queue, and this handoff, over those older sections.

`.superpowers/sdd/` is gitignored scratch from a previous agent. It will not be on a fresh clone. Do not depend on it.

---

## 3. Product (one paragraph)

Local-first Windows PySide6 app for fast manual review of local photos/videos.
Not a DAM. Not TagStudio. SQLite via stdlib `sqlite3`. Virtual lists with
independent sparse `sort_key`. Logical reject/restore. Qt undo stack.
Thumbnails under the project folder, never beside source files.
PyInstaller one-folder packaging.

---

## 4. Non-negotiable rules

- Protected local trees, **read-only**: `photos/`, `phototakeplan/`, `lightphotosprt/`.
  Never modify, rename, move, delete, rewrite EXIF/XMP, write sidecars, or put
  DB/cache/log/test output inside them. Never commit or upload them.
- Tests: generated files under pytest `tmp_path` only. Never use real `photos/`.
- Never `git add .`. Stage explicit paths. Inspect staged paths before every commit.
- Do not change git author config (repo-local `lica.liu` is already set on the original clone; set the same on a new clone if empty).
- Python **3.12 or 3.13** (`AGENTS.md` §12). **Not 3.14.** 3.14.3 segfaults ~5% of full-suite runs in Pillow WebP save on a `QThreadPool` worker (`thumbnail_service.py`). Do not “fix” that with `Image.init()`.
- Qt widgets do not execute SQL. No source decode on the GUI thread. No filesystem scans on the GUI thread.
- Temporary filter/sort must never rewrite `list_items.sort_key`.
- Do not merge `feat/phase1-mvp` into `main` unless the user says so.
- Do not start Phase 2.

Prefer: source safety > correctness > responsiveness > simplicity > extra features.

---

## 5. What is already done (do not redo)

### Original plan Tasks 1–5 and 7

| Plan task | Review item | Commit |
|---|---|---|
| 1 bulk list membership | #5 | `4b76373` |
| 2 viewport thumbnail scheduling | #3 queue | `84cf980` |
| 3 bounded pixmap cache | #4 | `fc73670` |
| 4 preview latest-wins | #6 | `b81d984` |
| 5 cooperative scan cancel + off-GUI-thread scan | #7 | `e39bcb3` + `4dc8a17` |
| 7 project/source overlap | #10 | `72795aa` |

Scan used to run on the GUI thread despite `moveToThread`, because a receiverless lambda used AutoConnection. Fixed with `Qt.ConnectionType.DirectConnection` on `thread.started`. Do not revert that.

### Pre-Task-6 remaining-fixes queue (done after the overnight review)

| Finding | Commit |
|---|---|
| M10 delegate paint does not open source JPEGs | `a210e66` |
| C1 `_reload_grid` no per-row `is_file` / `cached_path` | `49299a0` |
| I2 restore selection/preview after refresh | `5e6d3cc` |
| I1 scan batch commit (`SCAN_COMMIT_BATCH = 256`) + busy status | `28c7098` |
| I3 overlap guard (`paths_overlap` / `reject_overlapping_roots`) | `72795aa` |
| C1 follow-up: clear `_thumb_paths` after scan | `01d9045` |

C1 used to freeze the UI ~19 s at 10k rows on a slow-stat machine (O(N) `stat`/`resolve` on the GUI thread). The shape is fixed: reload uses `self._thumb_paths` filled by `_on_thumbnail_ready`. After a scan, `_thumb_paths` is cleared so workers re-`ensure()` (disk cache still wins for unchanged files).

---

## 6. What to do next

### 6.1 Task 6 — scan progress (review item #9)

Spec: `docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md` → **Task 6**.
Review text: `docs/PHASE1_1_REVIEW_FIXES.md` §9.

Required behavior:

- `progress_cb: Callable[[int], None] | None` on the scan path
- `ScanWorker.progress = Signal(int)`
- Status: `Scanning... {n:,} files processed`
- Throttle: `PROGRESS_EVERY = 25` (do not emit every file)
- Queued connection onto the GUI thread; do not block the GUI
- Exact total count is optional (no expensive pre-scan)

Files: `scanner.py`, `library_service.py`, `scan_worker.py`, `main_window.py`, `tests/test_scan_worker.py`.

Keep cooperative cancel and batch commits. After finished/cancelled, restore the existing `Library (sorted)` / `List (manual order)` status tip.

Suggested commit: `feat(scan): report scan progress`

### 6.2 Task 8 — filter UI (review item #8)

Spec: same plan → **Task 8**.
Review text: `docs/PHASE1_1_REVIEW_FIXES.md` §8.

Required UI (compact, four combos under the sort combo, not heavy):

- media type: all / image / video
- extension
- source folder
- missing / present / all

Do **not** add a second Rejected control. All / Unassigned / Rejected views already exist.

`source_folder` and `missing: bool | None` must land on `MediaRepository.list_media` / `list_unassigned` and `LibraryService`. Named-list view filters in memory and **must not** write `sort_key`.

Suggested commit: `feat(filters): complete phase1 library filters`

Cheap extra while in `MainWindow._on_add_source_folder`: catch `ValueError` from the overlap guard and show a warning dialog, same pattern as New/Open Project. Currently the service raises and the UI does not catch it.

### 6.3 I4 — docs

`ARCHITECTURE.md` still describes old scan signals (`finished`/`failed` only) and old thumbs (`request()` filling visible rows). Update after Tasks 6 and 8 so you only refresh once:

- cooperative cancel, progress, DirectConnection
- viewport `sync()`, `MAX_PENDING=64`, bounded pixmap cache
- bulk list membership
- generic overlap
- filter combos
- `_thumb_paths` / no FS work in `_reload_grid`

Update `README.md` only if user-visible steps changed.

`docs/codebase/` was an untracked leftover on one machine. If you see it: refresh or delete; do not “fix in place.” It is not on GitHub.

### 6.4 Task 9 — 1k / 10k perf (review item #12)

Spec: plan Task 9. Sanitized report: `docs/verification/phase1_1_performance.md`.
Synthetic data only. No real `photos/` inventory in the commit.

C1 is already fixed, so it is now valid to measure. Still: assert call counts / bounded queues, not a single-machine timing SLA.

### 6.5 Task 10 — Windows PyInstaller smoke (review item #11)

Spec: plan Task 10. Report: `docs/verification/phase1_1_windows_smoke.md`.
Build: `python -m PyInstaller build/local_media_curator.spec`
EXE: `dist/local_media_curator/local_media_curator.exe`
Do not commit `dist/` or `build/local_media_curator/`. No personal paths or real photo names in the report.

Phase 1.1 is complete only when `docs/PHASE1_1_REVIEW_FIXES.md` §15 checkboxes can be ticked with evidence.

---

## 7. How to run tests

```text
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q
```

On the last Grok machine the default interpreter was 3.14.3 and there was no repo `.venv`. Create a 3.12 venv if needed:

```text
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

Overnight review at `4dc8a17` reported **107 passed, 1 skipped**. This handoff HEAD has more tests (delegate, reload call-count, selection restore, batch scan, overlap, thumb invalidation). Re-run the full suite after Task 6 and after Task 8.

If a GUI-scan test hangs: prefer `LibraryService.scan()` plus `window.refresh()` for unit tests; `window.scan()` needs the DirectConnection worker and `qtbot.waitUntil` with a finite timeout. Always set `QT_QPA_PLATFORM=offscreen`.

---

## 8. Known leftovers (do not treat as the next epic)

Do these only when already in the file, or after Task 10:

| Id | Note |
|---|---|
| Overlap UI | `MainWindow._on_add_source_folder` does not catch `ValueError` |
| M1 | `ThumbnailPool` `finished.emit` outside `try`; emit into deleted QObject after `deleteLater` |
| M2 | `worker.cancelled` not disconnected in `_stop_scan_thread` |
| M3 | `set_thumbnail_path` linear scan per ready signal |
| M4 | `pixmap.scaled(SmoothTransformation)` every repaint |
| M6 | `ListService.create` swallows duplicate names; MainWindow warning is dead |
| M7 | Home/End bound to move-to-start/end, steal grid nav |
| M8 | `closeEvent` does not close the project connection |
| Unused | `MainWindow.thumbnail_service` leftover after C1 |
| `_pending_selection` | shadowed if a live selection exists after reject |

**Dropped — do not spend time:** M9 `keys()` (delete rather than test if you touch the cache), M5 IN-clause chunking for ≤10k, `.pytest_cache` warnings, rewriting `b41099d` history.

---

## 9. Suggested OpenCode process

1. One task at a time. TDD: failing test, confirm fail, minimal code, confirm pass, covering tests, commit.
2. After Task 6: `pytest tests/test_scan_worker.py tests/test_scan_immutability.py tests/test_library_query.py -q`
3. After Task 8: add `tests/test_lists.py tests/test_main_window.py` and a full `pytest -q`
4. Do not implement Task 9/10 until 6 and 8 are green.
5. Push `feat/phase1-mvp` when a task group is done so the user can review on GitHub. Do not open a merge to `main` unless asked.

Suggested commits (from the original plan):

```text
feat(scan): report scan progress
feat(filters): complete phase1 library filters
docs: refresh architecture after phase 1.1 responsiveness fixes
test(perf): add 1k and 10k smoke coverage
docs(verify): record phase1.1 windows smoke
```

---

## 10. Handoff back to the user

When Tasks 6 and 8 (and ideally 9–10) are done, give:

1. branch name and HEAD SHA
2. `main...feat/phase1-mvp` link
3. full pytest summary
4. new/changed files
5. remaining Phase 2 items (video thumbs, optional playback, list export, JSON/CSV manifest, cancellation already exists, moved-file reconciliation, shortcuts, installer)

Do not ask the user to infer success from plans.
