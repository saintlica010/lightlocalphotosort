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

Implemented as a `QMainWindow` with a horizontal `QSplitter`. Library views are All, Unassigned, and Rejected, plus named virtual lists. The status tip shows `Library (sorted)` versus `List (manual order)`.

## Scanning

`LibraryService.scan()` stays synchronous for tests. The GUI starts `ScanWorker` on a `QThread`. The worker opens its own connection via `open_project`, scans enabled source folders, and emits `finished` or `failed`.

Scans are read-only against source media: enumerate, stat, and open for metadata. They do not rewrite, rename, move, chmod, delete, or write sidecars or caches next to originals.

Supported images: `.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, `.tiff`. Videos `.mp4` and `.mov` are recognized with reduced functionality.

## Thumbnails

`ThumbnailService` writes WebP files under `project.thumbnails_dir`. The cache key includes media id, source mtime, size, profile, and version.

`ThumbnailPool` wraps `QThreadPool` (4 workers). The grid shows placeholders first; `request()` then fills visible rows. Newer visible jobs outrank a large backlog. Corrupt or unreadable sources yield an error placeholder rather than crashing a worker.

## Lists

A media item may belong to multiple lists. Independent order lives on `list_items.sort_key` (sparse integers). Reorder, insert, and gap-fill run in a transaction; a list is normalized only when no integer gap remains.

The grid enables drag while a named list is active. `MediaListModel.dropMimeData` emits `orderChanged`; `MainWindow` persists through `CurationUndoStack.reorder`. Library automatic sorts never rewrite `sort_key`.

## Undo

`CurationUndoStack` wraps Qt's undo stack. Undoable actions: add to list, remove from list, reorder, reject, restore. Undo changes project database state only. It never rewrites source media bytes or metadata.

## Packaging

Windows one-folder PyInstaller build. Spec: `build/local_media_curator.spec`. Entry: `local_media_curator.__main__:main`. Output: `dist/local_media_curator/local_media_curator.exe`.
