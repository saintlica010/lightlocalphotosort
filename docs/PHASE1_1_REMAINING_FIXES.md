# Phase 1.1 — Remaining Work

Status: **`feat/phase1-mvp` is pushed with known open defects. This document is the handoff.**

Written: 2026-09-17
Branch: `feat/phase1-mvp`
Head at handoff: `7383af3` (code complete through Task 5 at `4dc8a17`; this file plus triage landed in `4731062` and `7383af3`)
Governing spec: `AGENTS.md` (read it first — it is the authority)
Source review: `docs/PHASE1_1_REVIEW_FIXES.md`
Implementation plan: `docs/superpowers/plans/2026-09-16-phase1-1-review-fixes.md`

**Whole-branch review verdict on pushing this branch: Yes.** No safety rule is violated — source media is provably untouched, project state is project-local, lists use a relationship entity with independent sparse `sort_key`, rejection is logical, and there is no protected or binary data anywhere in the 68-file diff. The two measured responsiveness defects (C1, I1) are documented below with reproductions and ordered for the next agent. This is a feature branch, not a merge to `main`.

Two limits on the evidence below, stated by the reviewer so they are not over-read:

- This machine's `os.stat` is unusually slow (~135 µs warm vs 5–15 µs typical), so C1's absolute numbers will be smaller elsewhere. The O(N) shape and the GUI-thread violation hold regardless — which is why C1 should be verified by call count, not by timing.
- PySide6 6.11 does not abort on unhandled exceptions in slots or `QRunnable.run()`; it prints and continues. That is why two candidate crash findings are Minor rather than Critical — and it is also why I1's dropped user action is silent.

---

## 0. Read this before running anything

**Use Python 3.12, not 3.14.**

The repo `.venv` is Python 3.12.10 and is correct. If you build your own environment, pin 3.12 (or 3.13, per `AGENTS.md` §12).

Python 3.14.3 was measured to **segfault ~5% of full-suite runs**, always in the same place: a `QThreadPool` worker inside `media/thumbnail_service.py:102` (`rgb.save(tmp, "WEBP", quality=80)`) — i.e. Pillow's `save` on a worker thread. Evidence: identical code, machine, Pillow 12.3.0 and PySide6 6.11.2, sole variable the interpreter — 3.14.3 crashed 5 times in 100 full-suite runs; 3.12.10 crashed 0 times in 100. Were 3.12 carrying the 3.14 rate, zero crashes in 100 runs would occur with probability ~0.6%.

This is a toolchain defect, **not** a defect in this project's code. Do not "fix" it by adding `Image.init()` or similar to `thumbnail_service` — the correct baseline avoids it. If you must run 3.14 and see this crash, it is not your change.

Verification commands:

```bash
QT_QPA_PLATFORM=offscreen "H:/2026shbookfair/.venv/Scripts/python.exe" -m pytest -q
```

Current state: **107 passed, 1 skipped.** The one warning is a `PytestCacheWarning` caused by `.pytest_cache` being undeletable on this machine (WinError 5 on an empty directory — a held Windows handle or an odd ACL, not a code issue). Clearing it needs a reboot or closing the lock holder.

---

## 1. What is done

Tasks 1–5 of the plan are implemented and committed, each with an independent task review that came back clean:

| Task | Review item | Commit |
|---|---|---|
| 1 — bulk list membership | #5 | `4b76373` |
| 2 — viewport thumbnail scheduling | #3 | `84cf980` |
| 3 — bounded pixmap cache | #4 | `fc73670` |
| 4 — preview latest-wins | #6 | `b81d984` |
| 5 — cooperative scan cancellation | #7 | `e39bcb3` + `4dc8a17` |

Task 5 also fixed a defect it uncovered: the scan had been running **on the GUI thread** since `b41099d`, because `thread.started.connect(lambda: worker.run(db_path))` — a receiverless lambda — resolves its AutoConnection context from the sender (the `QThread` object, GUI-thread affinity). `moveToThread` was inert. Fixed with `Qt.ConnectionType.DirectConnection` at `ui/main_window.py:122-124`. **Note the history is misleading:** `b41099d`'s message claims "run library scan off the GUI thread" and it did not.

---

## 2. What is NOT done

**Tasks 6–10 of the plan are absent from the tree.** External review items **#8, #9, #10, #11, #12** are therefore unaddressed, and the §15 acceptance gate in `docs/PHASE1_1_REVIEW_FIXES.md` cannot be signed off. Verified directly:

- `grep -rn "paths_overlap\|reject_overlapping"` → nothing (item #10)
- `scripts/` contains only `build_windows.ps1` — no `perf_smoke.py` (item #12)
- no `docs/verification/` — no smoke or performance reports (items #11, #12)
- `LibraryPanel` has no `type_combo` / `extension_combo` / `folder_combo` (item #8)
- `scanner.py` has no `progress_cb` (item #9)

Tasks 6, 7, 8 and 9 in the plan are written in full, with tests, and can be executed as-is. **Task 7 (item #10) is a real safety gap, not just a missing feature — see I3 below.**

---

## 3. Open findings, in the order to fix them

### C1 — CRITICAL: `_reload_grid` does O(N) filesystem work on the GUI thread

**Measured: 2.00 s at 1,000 rows, 19.31 s at 10,000 rows.**

- Where: `src/local_media_curator/ui/main_window.py:733-741` (`_thumbnail_path`), `:690` (`_row_from_media`), `:718-731` (`_thumbnail_jobs`), `:622` (`_reload_grid`); the cost lives in `src/local_media_curator/media/thumbnail_service.py:19-35` (`cached_path`).
- What: per image row, `_thumbnail_path` calls `Path.is_file()`, then `cached_path` → `_source_mtime_size` (stat) → `_assert_inside_cache` (**two** `resolve()` calls) → `out.is_file()` → `out.stat()`. That is ~2 realpath walks + 3–4 stats per row, plus a second `is_file()` in `_thumbnail_jobs`. All synchronous on the GUI thread.
- Breakdown: `cached_path` = 1.84 ms/row, of which the two `resolve()` calls are 1.10 ms (~60%).
- Why it matters: `_reload_grid` runs on every `refresh()`, every view switch and every sort change. At 10k the UI freezes ~19 s on every reject, restore, undo, redo, add/remove, reorder, view switch and scan completion. Violates `AGENTS.md` §25 ("Do not execute filesystem scans … in the GUI thread") and the §15 gate ("1k and 10k smoke tests show no obvious UI freeze").
- Provenance: pre-existing from `d5a6178`. `84cf980` bounded the thumbnail **queue** but left the O(N) **reload**; Task 9 — the perf smoke that would have caught it — was never implemented.
- **Machine caveat:** this box's `os.stat` is slow (~135 µs warm vs 5–15 µs typical). On a fast SSD expect ~1–2 s rather than 19 s. The O(N) shape and the GUI-thread violation hold regardless.
- Reproduction script: `C:\Users\saintlica\AppData\Local\Temp\lmc_review\reload_cost.py` (may not survive; rebuild it by timing a real `MainWindow._reload_grid` over a synthetic project with 1k/10k rows).
- **Fix:** stop resolving thumbnails during reload. Keep `self._thumb_paths: dict[int, str]` on the window, filled by `_on_thumbnail_ready`, cleared in `set_project`; set `"thumbnail_path": self._thumb_paths.get(media.id)`; make `_sync_thumbnails` treat "id not in `_thumb_paths`" as needing work; delete the `is_file()` from `_thumbnail_jobs` (the pool's `ensure()` already returns a cached path without re-rendering, and stats on the worker). Reload becomes ~50–100 ms of dict/SQL work at 10k, and the one-frame placeholder is exactly what `AGENTS.md` §18 asks for. If any per-row path work remains, memoize the resolved cache root and use `os.path.normcase(os.path.abspath(...))` instead of `Path.resolve()`.

### I1 — GUI writes during a scan freeze 5 s, then silently do nothing

- Where: `src/local_media_curator/media/scanner.py:158` commits once per folder, holding one write transaction for the whole enumeration. SQLite/WAL allows one writer, so a concurrent reject/undo/add hits `SQLITE_BUSY`.
- Measured (real `db/connection.py`): `GUI reject FAILED after 5.031s: database is locked`. A probe confirmed PySide6 6.11.2 prints the traceback and continues (no abort), so the user's action is **dropped with no message**.
- Provenance: new failure mode from `b41099d` (async scan); `e39bcb3` did not address it.
- **Fix:** commit in bounded batches (~256 rows) inside the folder loop, rolling back only the current batch on cancel (the 8-file cancel test still passes); also catch `sqlite3.OperationalError` in the GUI mutation paths and surface a status message.

### I2 — Selection and preview are cleared by every non-reordering refresh

- Where: `main_window.py:642` (`set_rows` = full model reset → current index invalid), then `:646-650` sets preview to None. Only `move_selection` / `apply_grid_order` / `move_to_ends` re-select.
- Effect: undo of a reject brings the photo back with no selection and no preview — one extra keystroke on every curation step, against `AGENTS.md` §24 (keyboard-first).
- **Fix:** capture the current/selected media ids before reload and call `_select_media_ids` after, as the reorder paths already do.

### I3 — Item #10 is an open `AGENTS.md` gap, not merely a missing feature

- Where: `services/library_service.py:18` (`add_source_folder` has no guard) and `domain/paths.py` (no `paths_overlap`).
- Effect: project creation blocks only the three known directory *names* (`project_service.py:11`), so a project at `D:\Pictures\curator` with source `D:\Pictures` is **accepted**, putting `project.sqlite3`, `thumbnails/` and `logs/` **inside the source tree**. Violates `AGENTS.md` §14, §17, §37.
- **Fix:** the plan's Task 7 is small and already contains implementation plus tests — run it.

### I4 — Committed `ARCHITECTURE.md` describes behaviour the branch removed

- `ARCHITECTURE.md:45` ("emits `finished` or `failed`" — now also `cancelled`, plus cooperative cancel) and `:55` ("`request()` then fills visible rows" — now viewport-driven `sync()` with bounded `MAX_PENDING=64`, plus a bounded pixmap cache).
- `AGENTS.md` §33 requires maintaining it; a stale doc is how the next reviewer misses C1.
- **Fix:** update those two sections.

### Minor findings

| # | Where | Issue |
|---|---|---|
| M1 | `media/thumbnail_pool.py:47` | Final `finished.emit` is outside the `try`; after a project switch the old pool is `deleteLater`'d with up to 4 jobs mid-decode, so it can emit into a deleted QObject. Reproduced as a printed `RuntimeError: Signal source has been deleted`; process survives. One-line fix: move the emit inside the `try`, or `waitForDone()` before `deleteLater`. |
| M2 | `ui/main_window.py:169-176` | `worker.cancelled` is not disconnected in `_stop_scan_thread`, making the `_scan_thread is None` guard at `:137-142` load-bearing. Near-unreachable; disconnecting costs one line. |
| M3 | `ui/media_model.py:118-127` | `set_thumbnail_path` is a linear scan per `ready` signal (~0.1 s total at 10k rows). A media-id → row-index dict makes it O(1). |
| M4 | `ui/thumbnail_delegate.py:44-48` | `pixmap.scaled(SmoothTransformation)` re-scales the same 256 px WebP on every repaint of every visible cell. Cache the scaled result. |
| M5 | `db/repositories.py:269-322` | `get_by_ids` / `set_rejected` / `rejection_states` / `items_for_ids` / `remove_items` build one unchunked `IN (...)`, contradicting the plan's `_IN_CHUNK = 400`. Harmless: SQLite 3.49.1 allows 32,766 variables, so ≤10k is safe. Worth a comment, not a change. |
| M6 | `services/list_service.py:52-67` | `create()` swallows `IntegrityError` and returns the existing id, making the `except sqlite3.IntegrityError` at `main_window.py:521-526` dead code: "New list" with a duplicate name silently switches to the existing list instead of warning. The two layers disagree. |
| M7 | `ui/main_window.py:236,240` | `Home` / `End` are bound to "Move to Start/End", overriding grid navigation. Consider scoping them to list mode. |
| M8 | `ui/main_window.py:1070` | `closeEvent` stops the scan thread but never closes the project connection (process exit covers it). |
| M9 | `ui/pixmap_cache.py:30,13` | `keys()` has no test and no caller; `max_items` is unvalidated (`0` degrades safely but silently re-decodes every repaint). |
| M10 | tests | No test constructs a `ThumbnailDelegate`, so its call-site wiring and the "no source decode in `paint()`" invariant are unguarded. |

---

## 4. Two other things left in the worktree

- **`docs/codebase/` is untracked.** Seven markdown files that appeared during this work, not part of any brief or commit. They may belong to another session; they were deliberately left in place. **They contain a stale claim** — `docs/codebase/ARCHITECTURE.md:55` still calls `_pixmaps` an unbounded dict, which `fc73670` fixed. Verified to contain no real filenames, no user absolute paths, and no protected-tree contents. Decide whether to commit, correct, or delete them.
- **A stash entry** `stash@{0}: On feat/phase1-mvp: task4-verify-1577` is leftover baseline-comparison residue from Task 4, identical to what is committed. It was left because the stash stack is shared across the main checkout and all worktrees, and a peer's request to drop it was refused as permission laundering. Drop it yourself if you want it gone — but check the stack first.

---

## 5. The queue, in order

This ordering comes from the final whole-branch review's triage, not from the author of this document. Nothing on the deferred list blocks the push that already happened; this is the next agent's work queue.

1. **C1.** It is what review item #3 was actually about, and it is the difference between "usable at 10k" and "19 s freeze per action".
   - **Verify it with a filesystem-call-count assertion, not a timing test.** A timing assertion will flake across machines; a call-count assertion is exactly the guard whose absence let C1 through. Copy the pattern already in `tests/test_library_query.py::test_grid_reload_does_not_issue_per_item_list_name_queries`.
   - **Arm the delegate test (M10) first.** The delegate is load-bearing for C1's fix, so its "no source decode in `paint()`" invariant must be armed before that refactor touches the code path.
2. **I1** — batch-commit the scan. This also closes two deferred items as side effects: the orphan-QThread-on-30 s-stall risk, and the missing cancel check in the missing-marking pass (both become near-impossible once cancel latency is bounded).
3. **I2** — re-select after reload, so undo of a reject keeps the photo selected and previewed.
4. **I3 / plan Task 7** — the overlap guard. This is the one remaining `AGENTS.md` gap; its tests are already written in the plan.
5. **Plan Tasks 6 and 8** (items #9, #8) — scan progress and the filter UI, to finish the phase properly.
6. **I4 and the `docs/codebase/` refresh together** — so the docs match what C1's fix changes, rather than being refreshed twice.
7. **Plan Tasks 9 and 10** (items #12, #11) — the 1k/10k perf evidence and the Windows smoke, and the §15 gate.
8. M2, M3, M4, M5, M6, M7, M8, M9, M1/M12 (fold these two together — the `thumbnail_pool` emit hardening) — opportunistic, while already in those files.

**Dropped — do not spend time on these.** The triage explicitly closes them:

- **M9 (`keys()` has no test and no caller)** — delete the method rather than testing dead code. That also removes the undocumented-ordering question entirely.
- **M5's chunking concern** — SQLite 3.49.1 allows 32,766 variables, so ≤10k items are safe; a comment, not a change.
- **The `.pytest_cache` warning** — environment artifact, no code implication.
- **Report line counts off by one** — immaterial.
- **`_current_token()` unlocked read** — worst case one wasted decode; it is the only cross-thread read.
- **The scan test passing against a no-op cancel** — already resolved at HEAD; the amended `COUNT(*) == 0` assertion genuinely distinguishes cancellation from waiting the scan out.
- **Mixed `Co-Authored-By` trailers** — expected under current session guidance, not a defect.
- **`b41099d`'s inaccurate message** — state it in the PR body; do not rewrite pushed history.
- **The scan test proving mechanism rather than responsiveness** — a prior reviewer judged the deterministic trade correct and asked that it not be re-litigated. Cover the consequence with a filesystem-call-count test instead.
- **`docs/codebase/`** — refresh or delete it; do not try to "fix" it in place. Note it is stale in three of its five listed risks and is wrong about `MainWindow`'s size.

Process note: Tasks 3–5 were done under subagent-driven development — one implementer per task, an independent reviewer after each with separate spec and quality verdicts, a bounded fix loop, and a final whole-branch review. The record of that (rulings, deferred minors, review packages) lives in `.superpowers/sdd/2026-09-16-phase1-1-review-fixes/`, which is **git-ignored scratch** and not on the remote. Everything that matters from it is reproduced in this document.

## 6. Data-safety rules that are not negotiable

`photos/`, `phototakeplan/`, `lightphotosprt/` are real user data. Read-only. Never modify, rename, move, or create sidecars in them; never put project DBs, caches, logs, or test output inside them; never commit or upload them. Tests use generated `tmp_path` fixtures only. Stage explicit paths — never `git add .`. This branch was verified to contain zero protected paths and zero binary artifacts; keep it that way.
