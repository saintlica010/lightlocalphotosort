# Live handoff — implement Phase 2D

**This file is the live handoff for Phase 2D.** Specs below are current. Do not start from the Phase 1.1 handoff (`docs/OPENCODE_HANDOFF.md`); that document is historical and still says “do not start Phase 2.”

Written: 2026-09-18
Repo: `https://github.com/saintlica010/lightlocalphotosort.git`
Branch: `codex/phase2-1`
Required HEAD: **`9fd80e0`** or later (`fix(import): match before persist and remap ambiguous sources`)
Do **not** merge to `main` unless the user explicitly asks.
Do **not** start Phase 3, video work, FFmpeg, or physical media copy/export.

---

## 0. Paste this into a successor agent first

```text
Implement Phase 2D of lightlocalphotosort on branch codex/phase2-1.

Read docs/OPENCODE_HANDOFF_PHASE2D.md FIRST (this file). Then AGENTS.md.
Then docs/PHASE2_PLAN.md sections 9, 15 (Phase 2D), 16, 18, 19.

HEAD must be 9fd80e0 or later. If you are behind that, stop and get the
Phase 2C commits (d21f24e..9fd80e0). Origin may still be at 6243f8c until
those commits are pushed.

2A, 2B, and 2C are DONE. Do not redo culling, Target List, or .llplist.json.

Phase 2D only:
1. CSV export
2. TXT export
3. Clipboard export (filenames / absolute paths / relative paths)
4. Light export/import UI polish (see §8)
5. Regression + 1k/10k + packaged-EXE smoke evidence
6. Docs (README, ARCHITECTURE, PHASE2_PLAN merge-gate checkboxes)

Python 3.12 or 3.13 only. Not 3.14.
Never modify photos/, phototakeplan/, lightphotosprt/.
Never git add .
Do not merge to main.
TDD. Tests use tmp_path only.
Phase 2 export = list/manifest export, never copying source photos.
```

---

## 1. Checkout

```text
git fetch origin
git checkout codex/phase2-1
git pull --ff-only origin codex/phase2-1
git rev-parse --short HEAD
```

**Verify HEAD is `9fd80e0` or a descendant.**

At handoff time the local worktree was **6 commits ahead of `origin/codex/phase2-1`**. Those commits are Phase 2C and this handoff. If `git log -1 --oneline` shows `6243f8c feat(culling): add phase 2 keyboard workflow`, you do **not** have 2C. Stop. Ask the user to push `codex/phase2-1` from the machine that has `9fd80e0`, then fetch again.

Work wherever the clone is. Do not hard-code another machine's path. If a worktree already exists for `codex/phase2-1`, use it; do not create a nested one.

Python: 3.12 or 3.13 venv. `QT_QPA_PLATFORM=offscreen` for pytest.

```text
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM="offscreen"
python -m pytest -q
```

Expected at `9fd80e0` before you change anything: **212 passed, 1 skipped**.

---

## 2. Read order

1. **This file** — current state, 2D scope, and rules.
2. **`AGENTS.md`** — product rules. Authority over everything else. Phase 2 is §31. User instruction to do 2D overrides the “wait for independent 2C review” gate.
3. **`docs/PHASE2_PLAN.md`** — spec. 2D is §9 (CSV/TXT/clipboard), §15 Phase 2D, §16 named tests, §18 packaged EXE smoke, §19 merge gate.
4. **`docs/superpowers/plans/2026-09-18-phase2c-portable-lists.md`** — how 2C was built. Reuse `ExportService` / `PortableList`. Do not invent a second exporter.
5. **`ARCHITECTURE.md`**, **`DECISIONS.md`**, **`README.md`** — update these as part of 2D closeout.

`.superpowers/sdd/` is gitignored scratch. It will not be on a fresh clone. Do not depend on it.

---

## 3. Product (one paragraph)

Local-first Windows PySide6 app for fast manual review of local photos.
Not a DAM. Not TagStudio. SQLite via stdlib `sqlite3`. Virtual lists with
independent sparse `sort_key`. Three-state culling (`undecided` / `picked` /
`rejected`). Keyboard-first Target List. Portable `.llplist.json` lists.
Thumbnails under the project folder, never beside source files.
PyInstaller one-folder packaging. No network, no telemetry, no cloud AI.

---

## 4. Non-negotiable rules

- Protected local trees, **read-only**: `photos/`, `phototakeplan/`, `lightphotosprt/`.
  Never modify, rename, move, delete, rewrite EXIF/XMP, write sidecars, or put
  DB/cache/log/test output inside them. Never commit or upload them.
- Tests: generated files under pytest `tmp_path` only. Never use real `photos/`.
- Never `git add .`. Stage explicit paths. Inspect staged paths before every commit.
- Do not change git author config (repo-local `lica.liu`; set the same on a new clone if empty).
- Python **3.12 or 3.13** (`AGENTS.md` §12). **Not 3.14.** 3.14.3 segfaults ~5% of full-suite runs in Pillow WebP save on a `QThreadPool` worker. Do **not** “fix” it with `Image.init()`.
- Qt widgets do not execute SQL. Services own behavior.
- Temporary filter/sort must never rewrite `list_items.sort_key`.
- `SCHEMA_VERSION` stays **2**. No new migration unless you discover a blocker; if you do, stop and report.
- Phase 2 export means **list/manifest export**, not copying physical source media.
- Do not implement video thumbnails, playback, FFmpeg, HEIC-as-a-feature, or a Windows installer.
- Do not merge `codex/phase2-1` into `main` unless the user says so.
- User-facing UI is Simplified Chinese. Identifiers stay English.
- `tests/test_ui_language.py` forbids English words including `Import`. New actions must be Chinese (`导出 CSV...`, `复制文件名`, etc.).

Prefer: source safety > correctness > responsiveness > clarity > extra features.

---

## 5. What is already done (do not redo)

### Phase 2A + 2B — `6243f8c`

Culling core and keyboard workflow: schema v2, `culling_state`, P/X/U, Shift+P/X/U, Target List, B / Shift+B, focus safety, overlays, counts. Tests: `tests/test_culling.py`, `tests/test_phase2b.py`.

### Phase 2C — `d21f24e` … `9fd80e0`

| Commit | What |
|---|---|
| `d21f24e` | `docs/PHASE2_PLAN.md` + 2C implementation plan |
| `ac8ea5b` | `PortableList` JSON document |
| `8dd2442` | `ExportService.export_list` → `.llplist.json` |
| `dc1d7ec` | `import_list` + layered matching + `ListService.replace_items` |
| `79975d6` | File menu `导出名单...` / `导入名单...` |
| `9fd80e0` | Match before persist; remap missing **and** ambiguous; `from_json` raises Chinese `ValueError` |

Key APIs to **reuse**, not rewrite:

```text
src/local_media_curator/domain/portable_list.py
  FORMAT = "light-local-photo-list"
  VERSION = 1
  PortableItem(order, source, relative_path, file_name, file_size, modified_at, absolute_path=None)
  PortableList(name, items)
  to_json / from_json

src/local_media_curator/services/export_service.py
  source_labels / relative_to_source / owning_source
  ExportService.export_list(list_id, destination) -> PortableList
  ExportService.match_list(path, remaps=None) -> MatchResult   # no DB writes
  ExportService.import_list(path, remaps=None) -> ImportResult  # match then persist
  ListService.replace_items(list_id, media_ids)

src/local_media_curator/ui/main_window.py
  export_list_action = "导出名单..."
  import_list_action = "导入名单..."
  _on_import_list: match_list → remap dialogs → import_list once
  Full remap-cancel returns without wiping an existing list.
```

JSON `order` is **0-based**. `relative_path` is POSIX (`2026/IMG_0001.jpg`). Absolute paths are not the only identity.

Existing tests you must keep green:

```text
tests/test_portable_list.py
tests/test_manifest_export.py
tests/test_manifest_import.py
tests/test_manifest_ui.py
tests/test_culling.py
tests/test_phase2b.py
tests/test_ui_language.py
tests/test_lists.py
tests/test_scan_immutability.py
```

---

## 6. Phase 2D — implement this

Work TDD. One focused commit per task below. Do not implement 2A–2C again.

### Task 1: CSV export

Spec (`PHASE2_PLAN.md` §9.1):

```csv
order,file_name,relative_path
1,IMG_0001.jpg,2026/IMG_0001.jpg
2,IMG_0038.jpg,2026/IMG_0038.jpg
```

Requirements:

- Export the **current manual list order**.
- CSV `order` is **1-based** (the spec example starts at 1). Do not write `sort_key`. Do not write JSON’s 0-based `order`.
- `relative_path` is the same POSIX path `ExportService` already computes for JSON.
- UTF-8. `utf-8-sig` is allowed if you want Excel to open it; pin it in the test.
- Use stdlib `csv`. Quote fields that need quoting.
- Do not copy source bytes. Do not change source files.
- Raise `ValueError("名单不存在。")` if the list is missing (same as JSON export).

Suggested shape:

```python
ExportService.export_csv(list_id: int, destination: Path) -> Path
```

Build rows from the same data as `export_list` (you may extract a private `_portable_list(list_id) -> PortableList` and have JSON/CSV/TXT all consume it). Do not duplicate source-label logic.

Test file: `tests/test_csv_export.py`  
Required name: `test_csv_export`  
Also assert source SHA unchanged.

UI: File menu `导出 CSV...` (`export_csv_action`). Filter `CSV (*.csv)`. Default name `{list_name}.csv`. Same list-picker rules as JSON export (selected named list, else `ask_item`).

Commit: `feat(export): write CSV list manifests`

### Task 2: TXT export

Spec (§9.2):

```text
IMG_0001.jpg
IMG_0038.jpg
IMG_0082.jpg
```

Requirements:

- One `file_name` per line, current manual order, UTF-8, `\n` or `\r\n` (pin one in the test).
- No extra columns. No header.
- Same list-picker / immutability / missing-list rules as CSV.

```python
ExportService.export_txt(list_id: int, destination: Path) -> Path
```

Test file: `tests/test_txt_export.py`  
Required name: `test_txt_export`

UI: File menu `导出 TXT...` (`export_txt_action`). Filter `文本文件 (*.txt)`. Default `{list_name}.txt`.

Commit: `feat(export): write TXT filename lists`

### Task 3: Clipboard export

Spec (§9.3):

```text
Copy filenames
Copy absolute paths
Copy relative paths
```

Chinese actions (required):

| Attr | Text |
|---|---|
| `copy_file_names_action` | `复制文件名` |
| `copy_absolute_paths_action` | `复制绝对路径` |
| `copy_relative_paths_action` | `复制相对路径` |

Requirements:

- Operate on the **currently selected named list** (same picker as export if none selected).
- One entry per line, current manual order.
- Filenames = `file_name`.
- Absolute paths = `media.absolute_path` as stored (do not rewrite the file).
- Relative paths = POSIX `relative_path` from the owning source folder (same helper as JSON).
- Use `QApplication.clipboard().setText(...)`.
- No file dialog. No source-file writes.
- Enable only when a project is open (`_set_project_actions_enabled`).

Put clipboard **building** in `ExportService` (pure strings) and only the `QClipboard` call in the widget:

```python
ExportService.clipboard_file_names(list_id: int) -> str
ExportService.clipboard_absolute_paths(list_id: int) -> str
ExportService.clipboard_relative_paths(list_id: int) -> str
```

Tests (required names) in `tests/test_clipboard_export.py`:

```text
test_clipboard_file_names
test_clipboard_absolute_paths
test_clipboard_relative_paths
```

Service tests can assert the returned string. One qtbot test may set/read `QApplication.clipboard()` if you wire the actions.

`tests/test_ui_language.py` must stay green. Do not add `Copy` / `Export` / `Clipboard` as user-visible English.

Commit: `feat(export): copy list names and paths to clipboard`

### Task 4: Export/import UI polish

Do these, and **only** these. They came out of the 2C review. Do not redesign the app.

1. **Confirm before replacing a same-named list on import.** If `match_list` finds an existing list with `document.name` and that list already has items, `ask_confirm` (Chinese Yes/No, default No). Title/text e.g. `导入将替换名单「{name}」中的现有项目。继续？` Cancel → no persist.
2. **Partial remap cancel.** Today, if one source is remapped and another dialog is cancelled, import still persists. Either: persist only remapped sources and leave others missing (no wipe of unmatched), **or** abort the whole import if any remap dialog was cancelled. Pick one, test it, document it in the commit message. Do not silently `replace_items` an existing list with a partial match unless the user confirmed (item 1).
3. **Show the import summary even when remap is fully cancelled** — or a one-line status `已取消导入`. Do not fail silently.
4. **Do not** try to Chinese-force native `QFileDialog` buttons unless it is free with existing helpers. Same limitation as `choose_existing_directory`.

Keep match-before-persist. Keep “all remap dialogs cancelled ⇒ do not wipe.”

Tests: extend `tests/test_manifest_ui.py`. Monkeypatch `ask_confirm` / `choose_existing_directory`.

Commit: `fix(ui): confirm list replace and remap cancel`

### Task 5: Regression, performance, packaged EXE, docs

Do not treat this as a feature dump.

1. Full pytest, offscreen, 3.12/3.13: record the exact summary in `docs/verification/phase2_windows_smoke.md` (create it).
2. Re-run existing 1k/10k GUI smoke (`tests/test_perf_gui_smoke.py`, `tests/test_perf_smoke.py`). No new timing SLAs. If they fail, fix the regression; do not weaken the tests.
3. Packaged EXE:
   - `python -m pip install -e ".[packaging]"`
   - `python -m PyInstaller build/local_media_curator.spec --noconfirm`
   - Confirm `datas=[]` still has no `photos/` / `phototakeplan/` / `lightphotosprt/`.
   - Launch `dist/local_media_curator/local_media_curator.exe`, prove it stays up and exits 0. Walk `docs/PHASE2_PLAN.md` §18 as far as you can **without** using real `photos/`. Use a temp project + generated JPEGs. Honest about what was machine-captured vs not. Follow the tone of `docs/verification/phase1_1_windows_smoke.md` (do not claim a GUI walkthrough you did not do).
   - `dist/` stays untracked.
4. Docs:
   - `README.md` — CSV/TXT/clipboard and `.llplist.json` in the workflow.
   - `ARCHITECTURE.md` — portable list + CSV/TXT/clipboard; import is match-then-persist.
   - `docs/PHASE2_PLAN.md` §19 — check boxes that 2D actually verified. Leave unchecked anything you did not verify (especially independent human review and any EXE step you did not run).
   - Do not rewrite `AGENTS.md` Phase 1 history.

Commit: `docs(verify): record phase 2D closeout`

Then stop. Independent review / merge to `main` is the user’s call.

---

## 7. Suggested UI labels (all Chinese)

File menu additions next to the existing JSON actions:

```text
导出名单...
导入名单...
导出 CSV...
导出 TXT...
复制文件名
复制绝对路径
复制相对路径
```

Dialog titles: `导出 CSV` / `导出 TXT`. Warnings: `无法导出` / `无法导入` (already used).

---

## 8. Out of scope (stop if you start these)

- Copying/moving/transcoding source photos or videos
- Video thumbnails, playback, FFmpeg
- Schema v3 / SQLAlchemy / Alembic
- Cloud, telemetry, network
- Full visual redesign, dark mode, Fluent
- HEIC as a new product feature
- Windows installer (one-folder PyInstaller is enough)
- Merging to `main`
- Re-implementing 2A/2B/2C

---

## 9. Known leftovers (optional inside Task 4, not blockers)

From the 2C review. Fix if cheap during polish; otherwise leave and mention in the closeout doc:

- No UI test that an **ambiguous** source actually opens the remap dialog (relocation test can Level-3-match identical JPEGs and skip remaps). If you touch that test, force distinct mtimes or a unique `relative_path` so Level 2 is what fires.
- `if result.matched > 0 or result.list_id` is always true after a successful import (`main_window.py`).
- `_match_item` returns `"missing"` / `"ambiguous"` magic strings; L3 uses raw SQL in `ExportService`.
- Empty `source` + basename `relative_path` when a media row has no owning enabled folder.
- Native file-dialog buttons are OS-localized.

---

## 10. Commit and git discipline

```text
feat(export): write CSV list manifests
feat(export): write TXT filename lists
feat(export): copy list names and paths to clipboard
fix(ui): confirm list replace and remap cancel
docs(verify): record phase 2D closeout
```

Before every commit:

```text
git status --short
git diff --cached --name-only
```

If any path under `photos/`, `phototakeplan/`, `lightphotosprt/`, `dist/`, `*.sqlite3`, or `thumbnails/` is staged, unstage it. Do not delete the local file.

Never `git add .`.
Do not push unless the user asks.
Do not merge `main`.

---

## 11. Definition of 2D done (for you)

A successor agent is done when:

1. CSV, TXT, and three clipboard exports exist, with the named tests passing.
2. Source files’ SHA are unchanged by those exports.
3. Import confirm/cancel polish is tested.
4. Full suite is green on 3.12/3.13 offscreen (record the number).
5. 1k/10k GUI smokes still pass.
6. Packaged EXE was built, `datas=[]` inspected, launch/exit recorded honestly.
7. README + ARCHITECTURE mention portable lists and CSV/TXT/clipboard.
8. `main` was not modified.

Report back: branch, HEAD SHA, `origin/main...HEAD` (do not open a PR unless asked), pytest summary, commits added, what the EXE smoke actually covered, leftover §9 items.

---

## 12. If you get stuck

Stop and report if:

- an operation may modify real source media;
- a test would touch `photos/` / `phototakeplan/` / `lightphotosprt/`;
- you think you need a schema change;
- independent list order would be rewritten by export;
- you are about to copy GPL TagStudio code;
- `HEAD` is still `6243f8c` and 2C is missing.
