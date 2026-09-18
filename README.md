# Light Local Photo Sort

Lightweight, local-first Windows desktop app for reviewing, rejecting, and independently ordering photos and videos in virtual lists.

This is **not** a general-purpose DAM. Processing stays on the machine. Source media is never moved, renamed, or rewritten during import or classification.

## Status

Phase 1 MVP plus Phase 2 keyboard-first culling and portable lists on Windows 10/11: create or open a project, add a source folder, scan, cull with P/X/U, assign to a Target List with B, maintain virtual lists, and export lists as `.llplist.json`, CSV, TXT, or clipboard text.

Stack: Python 3.12+, PySide6, SQLite, Pillow. Windows packaging is a one-folder PyInstaller build.

See `AGENTS.md` for product rules, data-safety constraints, and the Phase 1 build order.

## Requirements

- Windows 10/11
- Python 3.12 or newer for source installs

## Install and run from source

```text
python -m pip install -e ".[dev]"
python -m local_media_curator
```

1. **New Project** or **Open Project** — choose a folder that is not inside `photos/`, `phototakeplan/`, or `lightphotosprt/`. A source folder that would overlap the project folder is rejected with a warning.
2. **Add Source Folder**, then **Scan** (F5). The status bar shows `Scanning... {n:,} files processed` while working. Source files are never moved, renamed, or rewritten.
3. Browse All / Unassigned / Picked / Undecided / Rejected, or create named virtual lists. Filter the grid with the four combos (type, extension, source folder, missing/present); filtering never rewrites a list's manual order.
4. Cull keyboard-first: `P` picked, `X` rejected, `U` undecided (`Shift` variants advance); set a Target List and press `B` to toggle membership (`Shift+B` adds and advances). Reorder a named list with `[` / `]` or Ctrl+Up/Down, and undo.
5. Export a list without touching source files: **导出名单...** (`.llplist.json`, exact order round-trip across machines), **导出 CSV...**, **导出 TXT...**, or **复制文件名** / **复制绝对路径** / **复制相对路径**. Import with **导入名单...**; missing and ambiguous items are reported, never silently matched.

## Packaged Windows build

```text
python -m pip install pyinstaller
python -m PyInstaller build/local_media_curator.spec
```

Or:

```text
python -m pip install -e ".[packaging]"
powershell -File scripts/build_windows.ps1
```

Run the packaged app:

```text
dist/local_media_curator/local_media_curator.exe
```

The spec is one-folder (`COLLECT`), not one-file. It does not bundle user media or planning trees.

## Project data and backup

Application state lives in the project folder you create or open, not next to source media:

```text
MyProject/
    project.sqlite3
    thumbnails/
    logs/
```

Backup = copy that project folder. Restoring is opening the copied folder. Original photos and videos stay in their source directories.

## Local reference data (not in Git)

These directories stay on the local machine and must not be committed or uploaded:

- `photos/` — real photos and videos
- `phototakeplan/` — real planning lists
- `lightphotosprt/` — local requirements and agent reference material
