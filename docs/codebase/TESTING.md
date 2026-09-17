# Testing Patterns

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: pytest; version is not pinned in `pyproject.toml`.
- Assertion/mocking tools: Python `assert`, pytest fixtures/`raises`/`skipif`, Pillow-generated media, pytest-qt `qtbot`, and targeted monkeypatching.
- Commands:

```text
python -m pytest
python -m pytest tests/test_ordering.py tests/test_lists.py
python -m pytest --cov
```

The third command is a conventional possible command, not a configured repository command: `[TODO]` add `pytest-cov` and a coverage policy if coverage is required.

### 2) Test Layout

- Test file placement pattern: all tests are in the top-level `tests/` folder.
- Naming convention: `test_*.py`, with test functions also named `test_*`.
- Setup files and where they run: `tests/conftest.py` is the repository-level pytest setup file; `pyproject.toml` sets `testpaths = ["tests"]`, `pythonpath = ["src"]`, and `qt_api = "pyside6"`.
- Current suite inventory: 19 test modules cover database, project, scanning, lists, ordering, rejection, undo, Qt UI, thumbnails, previews, and packaging configuration.

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | Yes | `domain/ordering.py`, repository/service behavior, metadata and image loaders | Most fixtures use `tmp_path`; no real protected media is required. |
| Integration | Yes, local-only | Project SQLite plus generated source folders; scan and thumbnail pool | No remote service is involved. `tests/test_scan_immutability.py` verifies source safety. |
| E2E | Partial | `MainWindow`, Qt selection, list flow, scan worker, preview and thumbnail signals | These are Qt behavior tests, not a packaged-executable E2E suite. Windows packaged smoke remains a documented requirement. |

### 4) Mocking and Isolation Strategy

- Main mocking approach: temporary filesystem/SQLite projects with generated Pillow images; monkeypatch only for failure injection and SQL observation.
- Isolation guarantees: pytest `tmp_path` creates disposable roots; project DB/cache/logs are created under those roots; source safety tests capture bytes, mtime, size, and names before/after scanning.
- Common failure mode in this environment: declared GUI/test dependencies are not installed in the checked-in `.venv`; the system `pytest` run failed at collection on missing `PySide6`, and did not execute tests.

### 5) Coverage and Quality Signals

- Coverage tool + threshold: `[TODO]` No coverage plugin or threshold is configured.
- Current reported coverage: `[TODO]` No valid suite run was available in the current dependency state.
- Known gaps/flaky areas: Phase 1.1 calls for regression tests around cooperative scan cancellation, progress signals, generic project/source overlap, complete filter combinations, bounded decoded thumbnail memory, packaged smoke, and 1k/10k performance.

### 6) Evidence

- `pyproject.toml`
- `tests/conftest.py`
- `tests/test_migrations.py`
- `tests/test_ordering.py`
- `tests/test_scan_immutability.py`
- `tests/test_scan_worker.py`
- `tests/test_session.py`
- `tests/test_packaging.py`
- `docs/PHASE1_1_REVIEW_FIXES.md`

