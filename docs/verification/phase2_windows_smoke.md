# Phase 2 Windows Verification Smoke

Date: 2026-09-18
Environment: Windows, Python 3.12.13 project venv, PyInstaller 6.22.3, offscreen Qt.
Branch: `codex/phase2-1`, HEAD `7b8726a`. No real `photos/` used anywhere below;
all fixtures are generated JPEGs under pytest `tmp_path`.

This file separates two evidence kinds. **Automated evidence** (§1–§3) was
machine-captured by the agent. **Manual packaged-EXE evidence** (§4) is a
24-step checklist for a human run of the frozen EXE; boxes stay unchecked
until a human actually clicks through them.

---

## A. Automated evidence (agent, machine-captured)

### A1. Full regression suite

```text
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q
229 passed
```

Covers Phase 1 (ordering, undo, scan progress/cancel, immutability), 2A/2B
(culling, Target List, focus safety), 2C (JSON round-trip, remap, missing /
ambiguous), and 2D (CSV, TXT, three clipboard builders, import confirm /
remap-cancel polish, ambiguous-remap dialog, All-view invariant, Chinese UI).

Fixes landed after the 2D closeout, both covered:

- `fix(library): All view contains all culling states` — the 全部 view now
  returns picked + undecided + rejected (`include_rejected=True` instead of
  the Phase 1 `culling_state != 'rejected'` fallthrough). New test
  `test_all_view_contains_all_culling_states`; four Phase 1-era tests that
  encoded “reject hides from All” were updated to the new semantics
  (`test_session.py`, `test_main_window.py`, `test_phase1_1_smoke.py`).
- `fix(import): match remap roots case-insensitively` — real bug, not a
  flake: source labels derive from normalized (lowercased on Windows) paths,
  so a natural-case remap key missed Level 2 and the relocation test passed
  only on same-second mtimes. Remap keys are lowercased once in `match_list`;
  regression test `test_remap_source_label_matches_case_insensitively` uses
  different file sizes so Level 3 cannot rescue it.

### A2. Performance smokes (existing, unweakened)

```text
python -m pytest tests/test_perf_gui_smoke.py tests/test_perf_smoke.py -q
19 passed
```

1k/10k GUI smoke through the real `MainWindow` plus DB/scheduling helpers.
No new timing SLAs; no meaningful regression.

### A3. Packaged EXE build + launch (machine)

Build (worktree root, HEAD `7b8726a`):

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

Scope: this proves the frozen app starts and exits cleanly. It does **not**
replace the manual walkthrough in §B.

---

## B. Manual packaged-EXE evidence (human, §18 walkthrough)

Run `dist/local_media_curator/local_media_curator.exe`. Use a temp project
and generated JPEGs — never the real `photos/` tree. All 24 steps of
`docs/PHASE2_PLAN.md` §18 were walked by the user on the frozen EXE built
from HEAD `7b8726a` (2026-09-18), with no deviations reported.

Migration and project:

- [x] B1. open an existing Phase 1 project
- [x] B2. schema migration succeeds
- [x] B3. existing lists remain
- [x] B4. existing manual list order remains
- [x] B5. previous rejected items migrate correctly

Keyboard culling:

- [x] B6. P works
- [x] B7. X works
- [x] B8. U works
- [x] B9. Shift+P/X/U work
- [x] B10. Target List works
- [x] B11. B works
- [x] B12. Shift+B works
- [x] B13. Undo / Redo works
- [x] B14. typing in input dialogs does not trigger shortcuts

Filters, counts, lists:

- [x] B15. culling-state filters work
- [x] B16. state counts are correct
- [x] B17. JSON list export works
- [x] B18. JSON list import works
- [x] B19. list-order round-trip is exact
- [x] B20. CSV export works
- [x] B21. TXT export works
- [x] B22. Clipboard export works

Closeout:

- [x] B23. all new user-facing UI is Simplified Chinese
- [x] B24. source-media files remain unchanged

---

## C. Docs updated

- `README.md` — culling workflow plus JSON/CSV/TXT/clipboard export.
- `ARCHITECTURE.md` — portable list, match-then-persist import, CSV/TXT/
  clipboard shapes, import confirm + abort-on-remap-cancel.
- `docs/PHASE2_PLAN.md` §19 — boxes checked for everything verified here.
  `Independent review is complete` stays unchecked: no independent human
  review has happened.

## D. Leftovers (handoff §9, not blockers)

Two §9 items were fixed after the 2D closeout and are no longer leftover:
ambiguous-source remap dialog coverage
(`test_import_ambiguous_source_opens_remap_dialog`) and the always-true
import-refresh condition (now unconditional `self.refresh()`).

Remaining, deliberately untouched:

- `_match_item` `"missing"` / `"ambiguous"` magic strings and raw L3 SQL remain.
- Empty-`source` + basename `relative_path` for media without an owning enabled
  folder remains.
- Native file-dialog buttons stay OS-localized (documented limitation).
