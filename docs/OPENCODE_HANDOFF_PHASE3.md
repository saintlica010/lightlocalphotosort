# Live handoff — implement Phase 3

**This file is the live handoff for Phase 3.** Do not start from `docs/OPENCODE_HANDOFF.md` or `docs/OPENCODE_HANDOFF_PHASE2D.md`; those are historical and tell you not to start Phase 3.

Written: 2026-09-18
Repo: `https://github.com/saintlica010/lightlocalphotosort.git`
Branch to implement on: **`codex/phase3`** (created from `main` at Phase 2 complete)
Baseline `main`: **`fd88191`** `docs(verify): mark manual packaged-EXE walkthrough complete`
Spec: **`docs/PHASE3_PLAN.md`**
Do **not** merge to `main` unless the user explicitly asks.
Do **not** start video, FFmpeg, XMP write-back, Lightroom catalog writes, or physical media copy.

---

## 0. Paste this into a successor agent first

```text
Implement Phase 3 of lightlocalphotosort on branch codex/phase3.

Read docs/OPENCODE_HANDOFF_PHASE3.md FIRST. Then AGENTS.md.
Then docs/PHASE3_PLAN.md (the live spec).

main is Phase 2 complete at fd88191. Do not redo Phase 1 or 2.

Phase 3 product goals:
1. Quick List slots 1..9 (persistent, not visual-order bindings)
2. Lightroom Classic Smart Collection export (.lrsmcol) — no catalog/XMP/RAW writes
3. Modern PySide6-native UI without regressing workflow, performance, or safety

Implement in gated order: 3A → 3B → 3C → 3D → 3E → 3F.
Do not skip a gate. TDD. Tests use tmp_path only.

Python 3.12 or 3.13 only. Not 3.14.
Never modify photos/, phototakeplan/, lightphotosprt/.
Never git add .
Do not merge to main.
Never write .lrcat, XMP sidecars, or source media.
Lightroom does not need to be installed. User Lightroom import is not a merge gate.
```

---

## 1. Checkout

```text
git fetch origin
git checkout codex/phase3
git pull --ff-only origin codex/phase3
git rev-parse --short HEAD
```

If `codex/phase3` does not exist yet, create it from current `main` (`fd88191` or later) and put this file plus `docs/PHASE3_PLAN.md` on it.

Work wherever the clone is. Do not hard-code another machine's path. If a worktree already exists for this branch, use it; do not nest worktrees.

Python 3.12 or 3.13 venv. `QT_QPA_PLATFORM=offscreen` for pytest.

```text
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM="offscreen"
python -m pytest -q
```

Expected on the Phase 2 baseline before you change anything: **229 passed** (offscreen, 3.12).

---

## 2. Read order

1. **This file** — current state and rules.
2. **`AGENTS.md`** — product rules. Authority over everything else. Source-media immutability and protected directories override convenience.
3. **`docs/PHASE3_PLAN.md`** — **the live spec.** Follow it. Do not invent a second product direction.
4. **`ARCHITECTURE.md`**, **`DECISIONS.md`**, **`README.md`** — update during 3F, not as a first commit.

`.superpowers/sdd/` is gitignored scratch. Do not depend on it.

---

## 3. Product (one paragraph)

Local-first Windows PySide6 curator. Not a DAM. Not TagStudio. SQLite via stdlib `sqlite3`. Virtual lists with independent sparse `sort_key`. Three-state culling. Target List. Portable `.llplist.json` plus CSV/TXT/clipboard. Phase 3 adds persistent `1..9` quick-list slots, a best-effort Lightroom Classic `.lrsmcol` export (JPEG filename stems → RAW names; never writes catalogs or XMP), and a PySide6-native visual modernization. No network, no telemetry, no cloud AI.

---

## 4. Non-negotiable rules

- Protected trees, **read-only**: `photos/`, `phototakeplan/`, `lightphotosprt/`.
- Tests: pytest `tmp_path` fixtures only. Never real `photos/`.
- Never `git add .`. Stage explicit paths.
- Git author: keep repo-local `lica.liu` if already set.
- Python **3.12 or 3.13**. **Not 3.14.** Do not “fix” Pillow/WebP segfaults with `Image.init()`.
- Qt widgets do not execute SQL.
- Filter/sort must never rewrite `list_items.sort_key`.
- Do not bump schema unless the spec requires it for quick-slot persistence; keep the change minimal (`project_settings` or a small table). Record it in `DECISIONS.md`.
- Never modify JPEG/RAW bytes, EXIF, XMP, filenames, or Lightroom `.lrcat`.
- Do not require Lightroom installed. Do not benchmark Lightroom. User import confirmation is **not** a merge blocker (`PHASE3_PLAN.md` §11).
- User-facing UI stays Simplified Chinese. Identifiers stay English.
- Do not merge `codex/phase3` into `main` unless the user says so.

Prefer: source safety > correctness > responsiveness > clarity > extra features.

---

## 5. What is already done (do not redo)

Phase 1 + Phase 2 are on `main` at `fd88191`.

Reuse, do not rewrite:

```text
ListService / CurationUndoStack / Target List
ExportService.export_list / import_list / export_csv / export_txt / clipboard_*
culling_state  P/X/U  Shift+P/X/U  B/Shift+B
MainWindow._curation_shortcut_allowed  (extend to 1..9)
tests/test_culling.py  test_phase2b.py  test_manifest_*.py
tests/test_csv_export.py  test_txt_export.py  test_clipboard_export.py
tests/test_ui_language.py  test_perf_gui_smoke.py
```

Number keys must **not** bind to the current visual order of the list panel. Bind to persistent slots (`PHASE3_PLAN.md` §3.1).

---

## 6. Implement in this order

Follow `docs/PHASE3_PLAN.md` §7. One focused commit stream per milestone. TDD.

### 3A — Quick List Core

Persistent slots `1..9`. Service bind/unbind/resolve. Unbound slots require explicit bind (no auto-create / no Nth-list auto-bind). `1..9` idempotent add when bound (multi-select = one undo unit). List delete clears the slot and leaves it unbound. Rename preserves the slot. Reassignment does not change membership.

Gate: slot persistence, unbound key does not create or auto-bind, rename/delete, add when bound, multi-select, idempotent repeat, Phase 1/2 regression.

### 3B — Quick List Keyboard/UI

`Shift+1..9` add-and-advance. Focus safety (same widgets as P/X/U/B: `QLineEdit`, `QTextEdit`, `QPlainTextEdit`, `QInputDialog`, editable `QComboBox`). Binding UI with no silent overwrite. List panel labels `[1]`…`[9]`. Grid membership badges. Shortcuts visible in menus.

### 3C — Lightroom Smart Collection Export

Verified `.lrsmcol` serializer. JPEG filename stem. Duplicate-stem de-dup + warning. Named-list export action. Deterministic output. Structural/golden tests. Source immutability tests. Packaged app can write the file.

**Not required:** Lightroom installed, launched, or timed.

### 3D — Design System

Tokens, type, spacing, dark palette, focus/hover/selection, icon policy, centralized QSS. Prototype before whole-app migration. No large animation system.

### 3E — UI Migration

Sidebar, list panel, filters, grid delegate/cards, preview, menus/dialogs, status. Do not change core behavior just to restyle.

### 3F — Closeout

Full suite, 1k/10k GUI smoke, quick-list smoke, exporter smoke, packaged EXE, Chinese UI, immutability, docs (`README`, `ARCHITECTURE`, `DECISIONS`, merge-gate checkboxes you actually verified).

Then stop. Independent review / merge is the user’s call.

---

## 7. Out of scope

- Video thumbnails / playback / FFmpeg
- Writing XMP or `.lrcat`
- Copying/moving/transcoding source photos
- SQLAlchemy / Alembic / cloud / telemetry
- Binding `1..9` to whatever list currently sits in row N of the sidebar
- Requiring Lightroom on the build machine
- Merging to `main`

---

## 8. Git

```text
feat(lists): add persistent quick-list slots 1-9
feat(ui): add shift-number quick-list advance and badges
feat(export): write Lightroom smart collection files
feat(ui): add design tokens and theme
feat(ui): migrate panels to the phase 3 theme
docs(verify): record phase 3 closeout
```

Before every commit:

```text
git status --short
git diff --cached --name-only
```

If anything under `photos/`, `phototakeplan/`, `lightphotosprt/`, `dist/`, `*.sqlite3`, or source-adjacent `thumbnails/` is staged, unstage it.

Never `git add .`. Do not push unless asked (a cloud bot may push its own branch). Do not merge `main`.

---

## 9. Definition of done (for the implementing agent)

1. 3A–3F from `docs/PHASE3_PLAN.md` §7 are implemented with tests.
2. Source SHA unchanged by quick-list actions and `.lrsmcol` export.
3. Full suite green on 3.12/3.13 offscreen; record the number.
4. 1k/10k GUI smokes still pass.
5. Packaged EXE builds; `datas=[]` has no protected trees.
6. User-facing strings are Simplified Chinese.
7. `main` was not modified.

Report: branch, HEAD SHA, pytest summary, commits, what EXE smoke actually covered, leftover items, explicit “did not merge main.”
