# Decisions

## Application shape

Build a new focused PySide6 application. Do not fork TagStudio.

TagStudio may be inspected as an architectural reference. Its GPL-3.0-only code is not copied into this project.

## Persistence

Use the Python standard-library `sqlite3` module.

Do not introduce SQLAlchemy or Alembic for the MVP.

Schema versioning uses SQLite `PRAGMA user_version`. Current schema version is 2.

Schema v2 adds one authoritative `media.culling_state` value: `undecided`, `picked`, or `rejected`. The Phase 1 `rejected` column remains only as a synchronized compatibility projection while older call sites are retired; it is not a second domain state. Migration is in-place so list membership and sparse manual order remain unchanged.

## List ordering

Manual order lives on the `list_items` relationship, not on `media`.

The column is `sort_key INTEGER` (sparse integers such as 1024, 2048, 3072). Do not use a `position` column.

## Project data location

A project stores `project.sqlite3`, `thumbnails/`, and `logs/` inside the project directory.

Project data is never stored inside `photos/`, `phototakeplan/`, or other source-media trees.

## Target List

Phase 2B stores the active target list ID in `project_settings` as the
`target_list_id` key. The table is additive and created with an idempotent
`CREATE TABLE IF NOT EXISTS`, including for projects that already report
schema version 2. Target membership remains ordinary `list_items` membership;
the target designation does not create a second relationship or ordering
system. Deleting the selected list clears the setting atomically.

Advance-after-action uses the pre-action visible row order and selects the
first row after the last selected row. At the end of a view it preserves a
still-visible selection or leaves selection empty when the action removed the
last item. Single-letter actions are ignored while a text-editing widget has
focus.
