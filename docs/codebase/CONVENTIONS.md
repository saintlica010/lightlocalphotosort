# Coding Conventions

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Files | lowercase `snake_case.py`; tests use `test_*.py` | `list_service.py`, `test_ordering.py` | `src/local_media_curator/`, `tests/` |
| Functions/methods | lowercase `snake_case`; private helpers/attributes use a leading underscore | `normalize_path()`, `_reload_grid()` | `src/local_media_curator/domain/paths.py`, `ui/main_window.py` |
| Types/interfaces | PascalCase classes; dataclasses for persisted/domain-shaped values | `Project`, `Media`, `ScanResult`, `ThumbnailPool` | `src/local_media_curator/domain/models.py`, `media/thumbnail_pool.py` |
| Constants/env vars | module constants use uppercase with underscores; no environment-variable convention is present | `SCHEMA_VERSION`, `MAX_PENDING`, `DEFAULT_PROFILE` | `src/local_media_curator/db/migrations.py`, `media/thumbnail_schedule.py`, `media/thumbnail_service.py` |

### 2) Formatting and Linting

- Formatter: `[TODO]` No formatter configuration was found.
- Linter: `[TODO]` No linter configuration was found.
- Most relevant enforced rules: type annotations and `from __future__ import annotations` are common in production modules, but no external enforcement is configured.
- Run commands: `python -m pytest`; no lint/format command is defined in `pyproject.toml`.

### 3) Import and Module Conventions

- Import grouping/order: observed order is standard library, third-party packages, then local `local_media_curator` imports.
- Alias vs relative import policy: production code uses absolute package imports; no path aliases or relative-import policy is configured.
- Public exports/barrel policy: packages are mostly empty `__init__.py` files; selected modules define `__all__` for public ordering/list APIs and the undo stack.

### 4) Error and Logging Conventions

- Error strategy by layer: repositories/services let database errors propagate or roll back; UI catches expected `ValueError`, `FileNotFoundError`, and `sqlite3.IntegrityError` to show `QMessageBox`; worker boundaries convert exceptions to a `failed` signal.
- Media failure behavior: unreadable/corrupt image metadata is represented with fallback metadata; thumbnail failures render an error placeholder; preview failures return a null `QImage`.
- Logging style and required context fields: no use of Python `logging`, metrics, or tracing was found. A project `logs/` directory is created, but no current writer was identified.
- Sensitive-data redaction rules: `AGENTS.md` requires avoiding unnecessary filenames, EXIF, complete inventories, hashes, and automatic transmission; source media and planning data must remain local.

### 5) Testing Conventions

- Test file naming/location rule: `tests/test_*.py`, with `tmp_path` for disposable projects and generated Pillow images.
- Mocking strategy norm: use direct temporary SQLite/filesystem fixtures; targeted monkeypatching appears in `tests/test_scan_immutability.py` and query-probe wrapping appears in `tests/test_library_query.py`.
- Coverage expectation: `[TODO]` No coverage tool or threshold is configured.

### 6) Evidence

- `pyproject.toml`
- `src/local_media_curator/domain/models.py`
- `src/local_media_curator/domain/ordering.py`
- `src/local_media_curator/ui/main_window.py`
- `src/local_media_curator/media/scanner.py`
- `tests/test_scan_immutability.py`
- `tests/test_library_query.py`
- `AGENTS.md`

