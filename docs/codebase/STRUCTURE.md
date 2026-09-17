# Codebase Structure

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `src/local_media_curator/` | Application package, split into UI, services, domain, database, and media modules | `ARCHITECTURE.md`, package tree, `src/local_media_curator/` |
| `tests/` | Pytest and pytest-qt tests using generated temporary media/projects | `pyproject.toml`, `tests/conftest.py`, `tests/*.py` |
| `build/` | PyInstaller spec for the one-folder Windows build | `build/local_media_curator.spec` |
| `scripts/` | Windows build helper | `scripts/build_windows.ps1` |
| `docs/` | Phase plans, review requirements, and this codebase map | `docs/PHASE1_1_REVIEW_FIXES.md`, `docs/superpowers/plans/` |
| `.github/agents/` | Repository-local Dev, Producer, and QA role instructions | `.github/agents/*.agent.md` |
| `AGENTS.md` | Product, safety, architecture, testing, and packaging instructions | `AGENTS.md` |
| `ARCHITECTURE.md` | Current architectural description | `ARCHITECTURE.md` |
| `DECISIONS.md` | Recorded architecture/persistence/order/storage decisions | `DECISIONS.md` |
| `pyproject.toml` | Package metadata, dependencies, entry point, and pytest configuration | `pyproject.toml` |

The repository also contains local protected reference directories at the parent workspace level (`photos/` and `phototakeplan/`). They are not application source or test fixtures and are read-only by policy. `lightphotosprt/` is not present in the current workspace root.

### 2) Entry Points

- Main runtime entry: `src/local_media_curator/__main__.py`, which calls `local_media_curator.app.run()`.
- Console-script entry: `local-media-curator = local_media_curator.__main__:main` in `pyproject.toml`.
- Secondary entry points: `ScanWorker.run()` is a Qt worker method, not a standalone CLI; `scripts/build_windows.ps1` is a packaging entry point.
- Entry selection: source execution uses `python -m local_media_curator`; installed execution uses the project script; PyInstaller uses `__main__.py` in `build/local_media_curator.spec`.

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `ui/` | Qt widgets, model/view wiring, menus, selection and display orchestration | Direct SQL; source-image decoding in delegate paint code |
| `services/` | Project, library, list, rejection, and undo use cases | Qt painting or raw source-file transformations |
| `domain/` | Data models, path normalization, sparse ordering functions | UI state or database connection ownership |
| `db/` | SQLite connection setup, schema migration, repositories and SQL | Qt widget behavior or source-media writes |
| `media/` | Source enumeration, read-only metadata, thumbnails, preview loading, worker coordination | Sidecars or writes beside original media |
| `tests/` | Disposable generated fixtures and behavioral regression tests | Real `photos/` or `phototakeplan/` as test-output/fixture roots |

### 4) Naming and Organization Rules

- File naming pattern: lowercase `snake_case.py`; examples include `project_service.py`, `thumbnail_pool.py`, and `test_scan_immutability.py`.
- Directory organization pattern: layer-oriented under one package (`ui`, `services`, `domain`, `db`, `media`).
- Python symbols: classes use PascalCase; functions, methods, and private attributes use `snake_case`; constants use uppercase names such as `SCHEMA_VERSION` and `MAX_WORKERS`.
- Import aliasing/path conventions: package imports use absolute `local_media_curator...` paths; no configured path aliases were found.

### 5) Evidence

- `src/local_media_curator/__main__.py`
- `src/local_media_curator/app.py`
- `src/local_media_curator/ui/main_window.py`
- `src/local_media_curator/services/`
- `src/local_media_curator/db/`
- `tests/`
- `pyproject.toml`

