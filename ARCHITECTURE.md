# Architecture

Local Media Curator is a local-first desktop app. UI, services, persistence, and media processing stay in separate layers.

## Layers

```text
src/local_media_curator/
    ui/          Qt widgets (no SQL)
    services/    application use-cases
    domain/      models and invariants
    db/          sqlite3 connection, migrations, repositories
    media/       scanning, metadata, thumbnails (later)
```

Qt widgets do not execute SQL. Services own behavior. The database layer owns connections and schema.

## Project directory

```text
MyProject/
    project.sqlite3
    thumbnails/
    exports/          (optional, later)
    logs/
```

The project directory is separate from source media such as `photos/`. Thumbnails and logs never live beside original files.

## Main window

Three-panel shell:

```text
+----------------+--------------------------------+------------------+
| Library/Lists  | Media Grid                     | Preview          |
| library_panel  | media_grid                     | preview_panel    |
+----------------+--------------------------------+------------------+
```

Implemented as a `QMainWindow` with a horizontal `QSplitter` of three placeholder widgets. Scanning, thumbnails, lists, reject, and undo are later tasks.
