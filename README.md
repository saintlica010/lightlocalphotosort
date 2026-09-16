# Light Local Photo Sort

Lightweight, local-first Windows desktop app for reviewing, rejecting, and independently ordering photos and videos in virtual lists.

This is **not** a general-purpose DAM. Processing stays on the machine. Source media is never moved, renamed, or rewritten during import or classification.

## Status

Repository is initialized. MVP implementation has not started.

Planned stack: Python 3.12+, PySide6, SQLite, Pillow, PyInstaller.

See `AGENTS.md` for product rules, data-safety constraints, and the Phase 1 build order.

## Local reference data (not in Git)

These directories stay on the local machine and must not be committed or uploaded:

- `photos/` — real photos and videos
- `phototakeplan/` — real planning lists
- `lightphotosprt/` — local requirements and agent reference material
