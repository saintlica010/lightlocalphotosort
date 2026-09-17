# Light Local Photo Sort

Lightweight, local-first Windows desktop app for reviewing, rejecting, and independently ordering photos and videos in virtual lists.

This is **not** a general-purpose DAM. Processing stays on the machine. Source media is never moved, renamed, or rewritten during import or classification.

## Status

Phase 1 MVP is usable on Windows 10/11: create or open a project, add a source folder, scan, maintain virtual lists, reject/restore, and undo.

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
3. Browse All / Unassigned / Rejected, or create named virtual lists. Filter the grid with the four combos (type, extension, source folder, missing/present); filtering never rewrites a list's manual order.
4. **Add to List** (from All Media, pick a list), reject/restore, reorder a named list with `[` / `]` or Ctrl+Up/Down, and undo.

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
