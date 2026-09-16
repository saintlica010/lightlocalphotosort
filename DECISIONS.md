# Decisions

## Application shape

Build a new focused PySide6 application. Do not fork TagStudio.

TagStudio may be inspected as an architectural reference. Its GPL-3.0-only code is not copied into this project.

## Persistence

Use the Python standard-library `sqlite3` module.

Do not introduce SQLAlchemy or Alembic for the MVP.

Schema versioning uses SQLite `PRAGMA user_version`. Current schema version is 1.

## List ordering

Manual order lives on the `list_items` relationship, not on `media`.

The column is `sort_key INTEGER` (sparse integers such as 1024, 2048, 3072). Do not use a `position` column.

## Project data location

A project stores `project.sqlite3`, `thumbnails/`, and `logs/` inside the project directory.

Project data is never stored inside `photos/`, `phototakeplan/`, or other source-media trees.
