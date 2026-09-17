# Live handoff — continue Phase 1.1

**This file is the live handoff.** Other docs on the branch are useful as specs, but several are **stale about what is already done**. Follow the read order below.

Written: 2026-09-17
Repo: `https://github.com/saintlica010/lightlocalphotosort.git`
Branch: `feat/phase1-mvp`
Head at last update: `1ab2423`
Do **not** merge to `main` unless the user explicitly asks.

---

## 0. Paste this into a successor agent first

```text
Continue Phase 1.1 of lightlocalphotosort on branch feat/phase1-mvp.

Read docs/PHASE1_1_FINAL_REVIEW.md FIRST. It is the live requirements document
and it lists what still blocks the merge. Then AGENTS.md (the authority).

HEAD should be 1ab2423 or later. If not, git fetch and pull --ff-only the branch.

Everything in the original implementation plan (Tasks 1-10) is DONE. Do not
redo it. Also done: C1, I1, I2, I3, I4, M10 from the overnight review.

Next work, in this order:
1. docs/PHASE1_1_FINAL_REVIEW.md section 2 - disable reorder in filtered lists
   (MERGE BLOCKER, real correctness bug)
2. section 1 - all user-facing UI must be Simplified Chinese
3. section 3 - packaged-EXE full workflow smoke evidence
4. section 4 - 1k/10k GUI smoke through the real MainWindow

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

Work wherever the clone is. Do not hard-code another machine's path (`C:\downloadbook\...` or `H:\2026shbookfair\...`). If a worktree already exists for this branch, use it; do not create a nested one.

---

## 2. Read order

1. **This file** — current state and rules.
2. **`docs/PHASE1_1_FINAL_REVIEW.md`** — **the live requirements.** Sections 1–4 are the remaining merge blockers. Section 8 is the acceptance gate.
3. **`AGENTS.md`** — product rules. Authority over everything else.
4. **`docs/PHASE1_1_REVIEW_FIXES.md`** — the original review. Items #3–#12 are all done; its §15 gate is superseded by the final review.
5. **`docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md`** — the implementation plan. **Tasks 1–10 are complete.** Its top banner is stale; ignore it.
6. **`docs/PHASE1_1_REMAINING_FIXES.md`** — **historical record of the overnight review at `7383af3`.** Its C1/I1/I2/I3/I4 write-ups are all fixed. Still useful for its **dropped** list and its minor leftovers (§5, §8). Do not read its §0–§3 as current.
7. **`docs/superpowers/plans/2026-09-17-phase1-1-pre-task6.md`** — the queue between original Task 5 and Task 6. **Complete.** Do not re-run.

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
- Python **3.12 or 3.13** (`AGENTS.md` §12). **Not 3.14.** 3.14.3 segfaults ~5% of full-suite runs in Pillow WebP save on a `QThreadPool` worker (`thumbnail_service.py:102`). This is a toolchain defect, not a project defect. Do **not** “fix” it with `Image.init()`.
- Qt widgets do not execute SQL. No source decode on the GUI thread. No filesystem scans on the GUI thread.
- Temporary filter/sort must never rewrite `list_items.sort_key`.
- Do not merge `feat/phase1-mvp` into `main` unless the user says so.
- Do not start Phase 2.

Prefer: source safety > correctness > responsiveness > clarity > extra features.

---

## 5. What is already done (do not redo)

### Original plan Tasks 1–10

| Plan task | Review item | Commit |
|---|---|---|
| 1 bulk list membership | #5 | `4b76373` |
| 2 viewport thumbnail scheduling | #3 queue | `84cf980` |
| 3 bounded pixmap cache | #4 | `fc73670` |
| 4 preview latest-wins | #6 | `b81d984` |
| 5 cooperative scan cancel + off-GUI-thread scan | #7 | `e39bcb3` + `4dc8a17` |
| 7 project/source overlap | #10 | `72795aa` |
| 6 scan progress | #9 | `64f4b0b` |
| 8 library filter UI | #8 | `c9d9894` |
| 9 1k/10k perf smoke + report | #12 | `47cb85d` |
| 10 Windows PyInstaller smoke + report | #11 | `6c97b8d` |

Scan used to run on the GUI thread despite `moveToThread`, because a receiverless lambda used AutoConnection. Fixed with `Qt.ConnectionType.DirectConnection` on `thread.started`. Do not revert that.

### Overnight-review findings (all fixed)

| Finding | What | Commit |
|---|---|---|
| M10 | delegate paint does not open source files | `a210e66` |
| C1 | `_reload_grid` no per-row `is_file` / `cached_path` | `49299a0` |
| C1 follow-up | clear `_thumb_paths` after scan | `01d9045` |
| I2 | restore selection/preview after refresh | `5e6d3cc` |
| I1 | scan batch commit (`SCAN_COMMIT_BATCH = 256`) + busy status | `28c7098` |
| I3 | overlap guard (`paths_overlap` / `reject_overlapping_roots`) | `72795aa` |
| I4 | ARCHITECTURE.md / README refreshed | `bc2178e` |

C1 used to freeze the UI ~19 s at 10k rows (O(N) `stat`/`resolve` on the GUI thread). Reload now uses `self._thumb_paths`, filled by `_on_thumbnail_ready`; after a scan it is cleared so workers re-`ensure()` (the disk cache still wins for unchanged files).

### Final-review sections 1 and 2 (done)

| Review section | What | Commit |
|---|---|---|
| §2 | disable reorder in filtered lists | `15b5e31` |
| §1 | all user-facing UI in Simplified Chinese | `3be72a1` |

§2 was a real correctness bug, not a polish item: a named list could still be dragged while filters hid some members, so dragging moved the hidden photos too (observed `[1,2,3,4]` → `[1,3,4,2]`). Reorder is now gated on `list_mode and not filters_active()`; the four move actions, drag-drop and the status bar follow one value. No filtered-subset reorder algorithm was added, per the review.

§1 translated every visible string. Note `install_chinese_translations` in `app.py`: Qt's own Yes/No/OK/Cancel come from Qt's catalogue, so the translator must be loaded or those buttons stay English inside a Chinese UI. `tests/test_ui_language.py` asserts representative strings and sweeps all visible text for English UI vocabulary.

### Final-review sections 3 and 4

| Review section | What | State |
|---|---|---|
| §3 | packaged-EXE workflow evidence | **partially done** — build, launch, clean close and content checks pass; the user ran it and the two defects it found (English buttons, English error message) are fixed and rebuilt. Steps 3–18 of the walkthrough are **not yet demonstrated**. |
| §4 | 1k/10k GUI smoke through `MainWindow` | **done** — `tests/test_perf_gui_smoke.py`, numbers in `docs/verification/phase1_1_performance.md` |

§4 asserts structure rather than timing: a reload issues 4 filesystem calls whether the
library holds 1,000 rows or 10,000, and at most ceil(n/400) membership statements. Timing
thresholds were avoided deliberately — their absence is why C1 shipped.

Current suite: **169 passed** on Python 3.12.

---

## 6. What to do next

**Sections 3 and 4 of `docs/PHASE1_1_FINAL_REVIEW.md` remain.** Sections 1 and 2 are done — see section 5 above. The subsections below are kept for their detail; 6.1 and 6.2 are complete.

### 6.1 Section 2 — disable reorder while a named list is filtered — **DONE (`15b5e31`)**

A named list can still be dragged/reordered while display filters hide some of its members. Dragging then submits only the visible subset to the full-list reorder path, so **hidden photos move implicitly**. `AGENTS.md` §20 forbids a temporary filter from rewriting manual order.

Confirmed current state: reorder enablement is gated on `list_mode` only — `ui/main_window.py:728` (`set_manual_order_enabled(list_mode)`) and `:729` (`_set_reorder_actions_enabled(list_mode)`). `_current_filters()` is used only for querying, never to gate reorder.

Required: filter active → drag reorder and all four move actions disabled, status shows `名单（已筛选，排序已禁用）`; clearing filters restores them. **Do not build a filtered-subset reorder algorithm** — the review says explicitly not to.

### 6.2 Section 1 — all user-facing UI in Simplified Chinese — **DONE (`3be72a1`)**

Every menu, action, button, label, dialog, warning, status message, view name, filter option, tooltip and empty state. The review carries a full translation table. **Do not translate** filenames, paths, user-created list names, metadata values, or extension strings such as `.jpg`. Source identifiers, tests and developer docs stay English.

Add tests covering representative Chinese strings, per the review.

### 6.3 Section 3 — packaged-EXE workflow evidence

The current `docs/verification/phase1_1_windows_smoke.md` proves build + launch + clean close only. It must additionally prove the **packaged EXE** completes the 18-step workflow (the review lists it), and the report must explicitly distinguish packaged-EXE manual smoke from pytest automated smoke. Synthetic media only.

### 6.4 Section 4 — 1k/10k GUI smoke through the real `MainWindow`

Neither `tests/test_perf_smoke.py` nor `scripts/perf_smoke.py` references `MainWindow` at all — the existing smoke is repository/service level. Add a GUI-level smoke that passes through the real Qt window, model, view and event handling at 1,000 and 10,000 items. Prefer structural assertions (call counts, bounded queues) over timing SLAs.

### 6.5 Then section 5 and 8 — regression and the acceptance gate

Run the full suite on 3.12/3.13, record the exact result, and tick the gate with evidence.

---

## 7. How to run tests

```text
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q
```

On a machine with the default interpreter 3.14.3 and no repo `.venv`, create a 3.12 venv:

```text
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: **127 passed, 1 skipped.** One warning may appear about `.pytest_cache` being undeletable — an environment artifact, not a code issue.

If a GUI-scan test hangs: prefer `LibraryService.scan()` plus `window.refresh()` for unit tests; `window.scan()` needs the DirectConnection worker and `qtbot.waitUntil` with a finite timeout. Always set `QT_QPA_PLATFORM=offscreen`.

---

## 8. Known leftovers (do not treat as the next epic)

Do these only when already in the file, or after the section 1–4 work:

| Id | Note |
|---|---|
| Overlap UI | `MainWindow._on_add_source_folder` does not catch the `ValueError` the overlap guard raises; no warning dialog |
| M1 | `ThumbnailPool` `finished.emit` outside `try`; can emit into a deleted QObject after `deleteLater` |
| M2 | `worker.cancelled` not disconnected in `_stop_scan_thread` |
| M3 | `set_thumbnail_path` linear scan per ready signal |
| M4 | `pixmap.scaled(SmoothTransformation)` on every repaint |
| M6 | `ListService.create` swallows duplicate names; the MainWindow warning path is dead code |
| M7 | Home/End bound to move-to-start/end, stealing grid navigation |
| M8 | `closeEvent` does not close the project connection |
| Unused | `MainWindow.thumbnail_service` leftover after the C1 fix |
| `_pending_selection` | shadowed if a live selection exists after reject |

**Dropped — do not spend time:** M9 `keys()` (delete rather than test if you touch the cache), M5 IN-clause chunking for ≤10k, `.pytest_cache` warnings, rewriting `b41099d` history.

`docs/codebase/` is an untracked leftover that exists on one machine only and is not on GitHub. If you see it: refresh or delete; do not “fix in place.”

---

## 9. Suggested process

1. One task at a time. TDD: failing test, confirm fail, minimal code, confirm pass, covering tests, commit.
2. After section 2: run `tests/test_lists.py`, `tests/test_main_window.py`, `tests/test_library_query.py`, then the full suite.
3. After section 1: full suite; confirm no non-Chinese user-facing string remains.
4. Push `feat/phase1-mvp` when a task group is done so the user can review on GitHub. Do not open a merge to `main` unless asked.

Suggested commits (from the final review's §10):

```text
fix(ui): disable reorder in filtered lists
feat(i18n): use Chinese user-facing UI strings
test(ui): cover Chinese strings and filtered reorder lock
test(perf): add 1k and 10k MainWindow GUI smoke
docs(verify): update packaged exe and gui performance evidence
```

---

## 10. Handoff back to the user

Provide: branch name; final HEAD SHA; `main...feat/phase1-mvp` diff/PR link; exact full pytest summary; commits added; updated packaged-EXE smoke report; updated 1k/10k GUI performance report; explicit confirmation that all user-facing UI is Simplified Chinese; known limitations deferred to Phase 2.

Do not ask the user to infer success from plans.
