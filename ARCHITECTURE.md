# Architecture

Local Media Curator is a local-first desktop app. UI, services, persistence, and media processing stay in separate layers.

## Layers

```text
src/local_media_curator/
    ui/          Qt widgets (no SQL)
    services/    application use-cases
    domain/      models and invariants
    db/          sqlite3 connection, migrations, repositories
    media/       scanning, metadata, thumbnails, preview decode
```

Qt widgets do not execute SQL. Services own behavior. The database layer owns connections and schema. Media workers open their own SQLite connections (WAL) and never reuse the GUI connection.

## Project directory

```text
MyProject/
    project.sqlite3
    thumbnails/
    exports/          (optional, later)
    logs/
```

The project directory is separate from source media such as `photos/`. Thumbnails and logs never live beside original files. Backup is a copy of this folder.

## Main window

Three-panel shell:

```text
+----------------+--------------------------------+------------------+
| Library/Lists  | Media Grid                     | Preview          |
| library_panel  | media_grid                     | preview_panel    |
+----------------+--------------------------------+------------------+
```

Implemented as a `QMainWindow` with a horizontal `QSplitter`. Library views are All, Unassigned, Picked, Undecided, and Rejected, plus named virtual lists. Live counters summarize the three culling states. The status tip shows `Library (sorted)` versus `List (manual order)`.

## Scanning

`LibraryService.scan()` stays synchronous for tests. The GUI starts `ScanWorker` on a `QThread`. The worker opens its own connection via `open_project`, scans enabled source folders, and emits `finished`, `failed`, `cancelled`, or `progress`.

- `thread.started` uses `Qt.ConnectionType.DirectConnection` so `run()` executes on the worker thread; a receiverless lambda would otherwise queue onto the GUI thread.
- Cancellation is cooperative: `ScanWorker.cancel()` sets a `threading.Event`; `scan_source_folder` checks it before each file, rolls back the in-progress folder transaction, and raises `ScanCancelled`. `MainWindow._stop_scan_thread` cancels, quits, and waits up to 30 s; it never calls `QThread.terminate()` and never drops a still-running thread.
- Progress is throttled: `scan_source_folder` counts processed files (including unchanged rows) and reports the first file, every `PROGRESS_EVERY = 25`, and the folder total. `LibraryService.scan` accumulates a cumulative count across folders; `ScanWorker.progress = Signal(int)` reaches the GUI through a queued connection and sets status `Scanning... {n:,} files processed`. Stale worker signals are dropped after thread stop; finished/cancelled/failed restore the `Library (sorted)` / `List (manual order)` status.
- Scan work commits in `SCAN_COMMIT_BATCH = 256` batches so concurrent GUI writes are not dropped (`SQLITE_BUSY`).

`LibraryService.add_source_folder` rejects project/source overlap generically via `paths_overlap` / `reject_overlapping_roots` (normalized, case-insensitive on Windows): project inside source, source inside project, or equal roots raise `ValueError`; `MainWindow` catches it and shows a warning dialog.

Scans are read-only against source media: enumerate, stat, and open for metadata. They do not rewrite, rename, move, chmod, delete, or write sidecars or caches next to originals.

Supported images: `.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, `.tiff`. Videos `.mp4` and `.mov` are recognized with reduced functionality.

## Filters

`LibraryPanel` hosts four compact combos (type, extension, source folder, missing/present). `MediaRepository.list_media` / `list_unassigned` accept `source_folder` (exact `normalized_path` prefix match, no `LIKE` wildcards) and `missing: bool | None`. The named-list view filters ordered media in memory via `LibraryService.filter_media`, preserving input order, and never writes `sort_key`. All/Unassigned/Rejected views push the same filters into SQL.

## Thumbnails

`ThumbnailService` writes WebP files under `project.thumbnails_dir`. The cache key includes media id, source mtime, size, profile, and version.

`ThumbnailPool` wraps `QThreadPool` (4 workers). Only in-flight jobs live on the pool; a lock-guarded bounded pending queue (`MAX_PENDING = 64`) is rebuilt by `sync(needed, visible_ids)`, which prioritizes currently visible rows and promotes newly visible ids over backlog. `MediaGrid.visible_row_range()` samples the viewport plus `PREFETCH_ROWS` rows and emits a debounced `viewportRowsChanged`; `MainWindow` stores `_thumb_needed` from reload and calls `_sync_thumbnails()` instead of enqueuing whole libraries. After a scan, `_thumb_paths` is cleared so workers re-`ensure()` (unchanged files still hit the disk cache). The grid shows placeholders first. `ThumbnailDelegate` paints only disk-cache WebP paths through a bounded LRU `BoundedPixmapCache` (`PIXMAP_CACHE_LIMIT = 256`); it never opens source images. Corrupt or unreadable sources yield an error placeholder rather than crashing a worker.

Grid reload is bulk: `_reload_grid` fetches list membership with `list_names_for_media_ids` (chunked `IN` queries, 400 ids per chunk) instead of one query per row, and does no filesystem work on the GUI thread.

## Lists

A media item may belong to multiple lists. Independent order lives on `list_items.sort_key` (sparse integers). Reorder, insert, and gap-fill run in a transaction; a list is normalized only when no integer gap remains.

The grid enables drag while a named list is active. `MediaListModel.dropMimeData` emits `orderChanged`; `MainWindow` persists through `CurationUndoStack.reorder`. Library automatic sorts never rewrite `sort_key`.

The active Target List is a project preference stored in the lightweight
`project_settings` key/value table under `target_list_id`. Target membership
uses the same `list_items` relationship and the same `CurationUndoStack` as
any other named list, so adding or removing target members never changes
another list's order. Deleting a list clears a matching target preference in
the same database transaction.

Keyboard curation actions are visible in the Edit menu: `P`/`X`/`U` set
culling state, `Shift+P`/`Shift+X`/`Shift+U` set state and advance to the next
visible row, `B` applies the target-list all-or-toggle selection rule, and
`Shift+B` adds without toggling and advances. Advance snapshots the current
view order before refresh and restores only the next still-visible media ID.
Text-editor and editable combo-box focus suppresses all single-letter curation
actions.

## Portable lists and interop export

Phase 2 export means list/manifest export. Source photo bytes are never copied, moved, or rewritten by any export path.

- `domain/portable_list.py` is the pure document: `FORMAT = "light-local-photo-list"`, `VERSION = 1`, `PortableItem(order, source, relative_path, file_name, file_size, modified_at)` with 0-based `order` and POSIX `relative_path`. `to_json` / `from_json` round-trip it; `from_json` raises Chinese `ValueError` on bad format/version/fields.
- `ExportService` builds every export from one private `_portable_list(list_id)` (current manual order, unique source labels, owning-source prefix match), so JSON/CSV/TXT/clipboard cannot disagree about identity. Missing lists raise `ValueError("名单不存在。")`.
- `.llplist.json` (`export_list`) keeps the 0-based `order`. Import is match-then-persist: `match_list` layers exact source+relative path, user remap root, then file_name+size+mtime candidates (zero → missing, two or more → ambiguous, never auto-picked), and only then does `import_list` create/replace the named list via `ListService.replace_items`.
- CSV (`export_csv`) writes 1-based `order,file_name,relative_path` with stdlib `csv`, UTF-8 with BOM for Excel. TXT (`export_txt`) writes one `file_name` per line (`\n`, UTF-8, no header).
- Clipboard builders (`clipboard_file_names` / `clipboard_absolute_paths` / `clipboard_relative_paths`) return plain `\n`-joined strings in manual order; only the widget touches `QApplication.clipboard()`.
- Import UI confirms before replacing a same-named non-empty list (`ask_confirm`, default No) and aborts the whole import — with a `已取消导入` status line — if any source-remap dialog is cancelled, so partial matches never wipe a list.

## Undo

`CurationUndoStack` wraps Qt's undo stack. Undoable actions: add to list, remove from list, reorder, and single/bulk culling-state changes. A bulk state change is one undo command, and restoring mixed prior states is transactional. Undo changes project database state only. It never rewrites source media bytes or metadata.

## Packaging

Windows one-folder PyInstaller build. Spec: `build/local_media_curator.spec`. Entry: `local_media_curator.__main__:main`. Output: `dist/local_media_curator/local_media_curator.exe`.
