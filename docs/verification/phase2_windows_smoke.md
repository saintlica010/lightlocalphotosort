# Phase 2D Windows Verification Smoke

Date: 2026-09-18
Environment: Windows, Python 3.12.13 project venv, PyInstaller 6.22.3, offscreen Qt.
Branch: `codex/phase2-1`. No real `photos/` used anywhere below; all fixtures are
generated JPEGs under pytest `tmp_path`.

## 1. Full regression suite

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q
225 passed, 1 skipped
```

Covers Phase 1 (ordering, undo, scan progress/cancel, immutability), 2A/2B
(culling, Target List, focus safety), 2C (JSON round-trip, remap, missing /
ambiguous), and 2D (CSV, TXT, three clipboard builders, import confirm /
remap-cancel polish, Chinese UI).

Real bug found by this test during development (not a flake):
`test_manifest_import_after_source_root_change` failed ~2/6 full-suite runs with
`matched == 0`. Root cause: source labels derive from normalized source paths,
which are lowercased on Windows (`d-photos`), while the test's remap dict used
the natural-case folder name (`D-Photos`). The Level 2 lookup was
case-sensitive, so it missed; the test then passed only when old and new JPEG
batches happened to share a wall-clock second (Level 3 mtime rescue).
Fixed in `fix(import): match remap roots case-insensitively` — `match_list`
lowercases remap keys once, Level 2 compares `item.source.lower()` — plus a
deterministic regression test
(`test_remap_source_label_matches_case_insensitively`, different file sizes so
Level 3 cannot rescue). Full suite green 4+ consecutive runs after the fix.

## 2. Performance smokes (existing, unweakened)

```text
python -m pytest tests/test_perf_gui_smoke.py tests/test_perf_smoke.py -q
19 passed
```

1k/10k GUI smoke through the real `MainWindow` plus DB/scheduling helpers.
No new timing SLAs; no meaningful regression.

## 3. Packaged EXE

Build (worktree root):

```text
python -m pip install -e ".[packaging]"
python -m PyInstaller build/local_media_curator.spec --noconfirm
```

Result: build succeeded (`Building COLLECT ... completed successfully`).
EXE: `dist/local_media_curator/local_media_curator.exe`.

Checks:

- `build/local_media_curator.spec` still has `datas=[]` (one-folder `COLLECT`).
- No `photos/` / `phototakeplan/` / `lightphotosprt/` references in the spec.
- `dist/local_media_curator/` top-level holds only the exe and runtime files.
- `dist/` stays untracked (gitignored).

Launch check:

- Started detached; alive after 8 s: yes.
- Closed via `CloseMainWindow()`: yes; exit code 0.
- stdout/stderr: empty, no traceback.

Honest scope: this proves the frozen app starts and exits cleanly. It is not
a full 24-step GUI walkthrough of `docs/PHASE2_PLAN.md` §18 (P/X/U, B,
JSON/CSV/TXT/clipboard, remap dialogs) — those paths are covered by the
automated UI tests above, not by a human clicking the EXE.

## 4. Docs updated in this closeout

- `README.md` — culling workflow plus JSON/CSV/TXT/clipboard export.
- `ARCHITECTURE.md` — portable list, match-then-persist import, CSV/TXT/
  clipboard shapes, import confirm + abort-on-remap-cancel.
- `docs/PHASE2_PLAN.md` §19 — boxes checked for everything verified here.
  `Independent review is complete` stays unchecked: no independent human
  review has happened.

## 5. Leftovers (handoff §9, not blockers)

- No UI test forces the ambiguous-source remap dialog via Level 2 (relocation
  fixtures can Level-3-match identical JPEGs and skip remaps). Left as is.
- `if result.matched > 0 or result.list_id` in `_on_import_list` is always true
  after a successful import. Left as is (refresh is harmless).
- `_match_item` `"missing"` / `"ambiguous"` magic strings and raw L3 SQL remain.
- Empty-`source` + basename `relative_path` for media without an owning enabled
  folder remains.
- Native file-dialog buttons stay OS-localized (documented limitation).
