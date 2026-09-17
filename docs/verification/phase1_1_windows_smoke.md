# Phase 1.1 Windows PyInstaller Smoke

Date: 2026-09-17
Environment: Windows, Python 3.12 venv (project `.venv`), PyInstaller 6.22.3.

## Build

Command (worktree root):

```text
python -m PyInstaller build/local_media_curator.spec --noconfirm
```

Result: build succeeded (`Building COLLECT ... completed successfully`).
EXE produced: `dist/local_media_curator/local_media_curator.exe`.

## Launch check

- Started `dist/local_media_curator/local_media_curator.exe` detached.
- Process alive after 8 s: yes.
- Closed via `CloseMainWindow()` (graceful): yes; exit code 0.
- stdout/stderr: empty (no traceback, no warnings).

## Contents check (protected data must not ship)

- `build/local_media_curator.spec` still has `datas=[]` and `COLLECT` (one-folder).
- No `photos/`, `phototakeplan/`, or `lightphotosprt/` references in the spec.
- `dist/local_media_curator/` top-level contains only the exe and PySide6 runtime files;
  no directory names matching the protected trees.
- `dist/` and `build/local_media_curator/` are not committed (gitignored).

## Automated end-to-end smoke

`tests/test_phase1_1_smoke.py` exercises the 16-step manual flow synthetically on
`tmp_path` only (project create, add sibling source folder, scan, two lists sharing
the same photo, independent reorder, reject/restore, undo/redo, close/reopen,
membership + order + rejection persistence, and source SHA-256 unchanged).

Result: **128 passed, 1 skipped** (full suite, `QT_QPA_PLATFORM=offscreen`).
