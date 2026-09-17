# Architecture

> **STALE SNAPSHOT — see [README.md](README.md) in this directory.** In
> particular the `_pixmaps` and `MainWindow` line-count claims near the end are
> no longer true. For current architecture read the repository-root
> `ARCHITECTURE.md`.

## Core Sections (Required)

### 1) Architectural Style

- Primary style: layered local desktop application with Qt model/view UI and worker-based media processing.
- Why this classification: the package is explicitly divided into `ui`, `services`, `domain`, `db`, and `media`; `ARCHITECTURE.md` states that UI, services, persistence, and media processing are separate.
- Primary constraints:
  1. Source media remains local and non-destructive; project state is stored separately in SQLite.
  2. GUI work must stay responsive by moving scanning, thumbnail generation, and preview decoding away from the GUI thread.
  3. A media item can be in multiple virtual lists, with ordering stored on the `list_items` relationship.

### 2) System Flow

```text
__main__.py -> app.run() -> MainWindow -> services/repositories -> project.sqlite3
                                      \-> ScanWorker/QThread -> scanner/metadata -> SQLite
                                      \-> ThumbnailPool/PreviewLoader -> project cache/UI
```

1. `__main__.py` calls `app.run()`, which creates a `QApplication` and shows `MainWindow`.
2. New/open project actions call `create_project()` or `open_project()`, which create/open `project.sqlite3`, project thumbnails, logs, and migrations.
3. `MainWindow.scan()` moves `ScanWorker` to a `QThread`; the worker opens its own project connection and invokes `LibraryService.scan()`.
4. `LibraryService` delegates source-folder enumeration to `scanner.py` and image metadata to `metadata.py`; repositories persist media rows and missing state.
5. Grid reloads use `MediaListModel` and `ThumbnailDelegate`; `ThumbnailPool` schedules project-cache WebP generation, prioritizing the visible viewport.
6. Selection starts `PreviewLoader` work, while curation commands flow through `CurationUndoStack` to list/rejection services and SQLite.

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| `ui/main_window.py` and panel/grid modules | Qt shell, menus, view mode, selection, refresh, UI-to-service orchestration | SQL statements or direct source-media mutation | `src/local_media_curator/ui/main_window.py`, `ARCHITECTURE.md` |
| `services/` | Application use cases and transaction-level calls to repositories | Widget painting or full-resolution decoding | `src/local_media_curator/services/*.py` |
| `domain/ordering.py`, `models.py`, `paths.py` | Value models, path normalization, sparse ordering invariants | Project lifecycle or Qt widgets | `src/local_media_curator/domain/*.py` |
| `db/` | Connection pragmas, schema version 1, SQL repositories | Media rendering or user-facing dialogs | `src/local_media_curator/db/*.py` |
| `media/scanner.py` and `metadata.py` | Read-only source discovery and image metadata extraction | Cache writes beside source media | `src/local_media_curator/media/scanner.py`, `metadata.py` |
| `media/thumbnail_*` and `preview_loader.py` | Bounded worker scheduling, project-local WebP cache, off-thread preview decode | GUI-thread source decode or remote processing | `src/local_media_curator/media/thumbnail_pool.py`, `thumbnail_service.py`, `preview_loader.py` |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| Repository | `db/repositories.py` | Encapsulates SQL for source folders, media, lists, membership, ordering, and rejection state. |
| Service layer | `services/*.py` | Keeps project/library/list/rejection workflows above persistence and below Qt widgets. |
| Qt model/view + delegate | `ui/media_model.py`, `media_grid.py`, `thumbnail_delegate.py` | Supports lightweight rows, selection, drag reorder, and placeholder painting without one widget per media item. |
| Worker pool / queued signals | `media/thumbnail_pool.py`, `preview_loader.py` | Keeps image work off the GUI thread and returns results through Qt signals. |
| Command/undo stack | `services/undo_commands.py` | Makes membership, ordering, rejection, and restore operations undoable without database snapshots. |
| Sparse-key ordering | `domain/ordering.py`, `services/list_service.py` | Allows insertion/reordering without rewriting every list row until a gap is exhausted. |

### 5) Known Architectural Risks

- `ScanWorker` has no cooperative cancellation or progress signal; `MainWindow` only requests thread quit and waits, while scanning itself is synchronous inside the worker.
- Project/source separation is currently protected by known directory names, not by generic path-overlap checks for arbitrary source folders.
- `ThumbnailDelegate._pixmaps` is an unbounded in-memory dictionary, so long sessions can grow decoded pixmap memory.
- `PreviewLoader` uses a single-thread pool and token filtering, but obsolete queued jobs are not cancelled and can still consume decode time.
- `MainWindow` is 683 lines and owns session, view, action, reload, scan, and thumbnail orchestration, making it a high-churn coordination point.

### 6) Evidence

- `ARCHITECTURE.md`
- `DECISIONS.md`
- `src/local_media_curator/__main__.py`
- `src/local_media_curator/app.py`
- `src/local_media_curator/ui/main_window.py`
- `src/local_media_curator/services/undo_commands.py`
- `src/local_media_curator/db/migrations.py`
- `src/local_media_curator/media/scan_worker.py`
- `docs/PHASE1_1_REVIEW_FIXES.md`

