# Light Local Photo Sort

Lightweight, local-first Windows desktop app for reviewing, rejecting, and independently ordering photos and videos in virtual lists.

This is **not** a general-purpose DAM. Processing stays on the machine. Source media is never moved, renamed, or rewritten during import or classification.

## Status

Phase 1 MVP is usable locally: create or open a project, add a source folder, scan, maintain virtual lists, reject/restore, and undo.

Stack: Python 3.12+, PySide6, SQLite, Pillow. PyInstaller packaging is not in this pass.

See `AGENTS.md` for product rules, data-safety constraints, and the Phase 1 build order.

## Usage

```text
python -m local_media_curator
```

1. **New Project** or **Open Project** — choose a folder that is not inside `photos/`, `phototakeplan/`, or `lightphotosprt/`.
2. **Add Source Folder**, then **Scan** (F5). Source files are never moved, renamed, or rewritten.
3. Browse All / Unassigned / Rejected, or create named virtual lists.
4. **Add to List** (from All Media, pick a list), reject/restore, reorder a named list with `[` / `]` or Ctrl+Up/Down, and undo.

## Local reference data (not in Git)

These directories stay on the local machine and must not be committed or uploaded:

- `photos/` — real photos and videos
- `phototakeplan/` — real planning lists
- `lightphotosprt/` — local requirements and agent reference material
