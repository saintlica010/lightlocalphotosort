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

## Quick List slots

Phase 3A stores slots `1..9` in the existing `project_settings` table as
`quick_list_slot_1` … `quick_list_slot_9`. Values are `list_id` strings.
Schema version stays 2; no new table. Membership remains ordinary
`list_items`. A list occupies at most one slot. Deleting a bound list clears
that slot in the same transaction as the list delete. Rename does not touch
the setting.

## Lightroom smart collection export

Phase 3C writes `.lrsmcol` as the Lua table Lightroom Classic uses for
Smart Collection settings. The shape follows published files: `type =
"LibrarySmartCollection"`, `criteria = "filename"`, `value2 = ""`, `version = 0`
(gist.github.com/dergachev/6541450). Rules use `operation = "beginsWith"` and
`combine = "union"`, matching a published catalog-to-smart-collection query
(worldofthev1.blogspot.com, 2017). Each JPEG stem becomes `beginsWith "<stem>."`
so the rule can hit the matching RAW without a hard-coded camera extension.
`operation = "any"` in the gist matches a full filename including extension, so
it is not used for the JPEG-to-RAW handoff. The feature stays labeled
experimental until a real Lightroom import is confirmed. The exporter never
writes `.lrcat`, XMP, or source media.

## Phase 3D design system

Visual tokens live in one module, `ui/theme.py`. The QSS is generated from
those tokens. No third-party UI toolkit and no icon font: markers stay the
existing text glyphs. The prototype is a preview only. Filtering, lists, export,
and the grid delegate are unchanged until Phase 3E migrates the real surfaces.

## Phase 3E theme migration

The running window uses `stylesheet()` from `ui/theme.py`. Sidebar, named lists,
filter combos, grid view, preview, menus, status bar, and the dialogs we own
(`QMessageBox`, `QInputDialog`) read those tokens. Native file dialogs stay
OS chrome. The grid is still a `QListView` plus `ThumbnailDelegate`; card,
selection, picked, and rejected colors come from the tokens. Spacing, filters,
list membership, and export are unchanged.

## Phase 3F closeout

The older Linux closeout remains historical. The final Windows evidence is
recorded in `docs/verification/phase3_windows_smoke.md` and supersedes that
run for Windows claims: the complete Python 3.12 suite passed, the populated
quick-list 10k structural regression passed, a clean one-folder EXE built and
started/exited normally, and the packaged output contained no protected data.
The full interactive packaged workflow, packaged `.lrsmcol` export, and real
Lightroom Classic import remain unclaimed; Lightroom import is non-blocking.

## Preview metadata contrast

Preview field labels and values use separate object names so the centralized
dark-theme stylesheet can apply `TOKENS.text_muted` to field names and
high-contrast `TOKENS.text` to values. Picked and rejected state values retain
their distinct state tokens; no source media or metadata is involved.

## Windows packaging ICU isolation

Windows 10/11 packaged builds use the system ICU. The PyInstaller spec filters
only root-level `icuuc.dll` and `icudt*.dll` entries on Windows, because those
can be discovered from an external build environment such as Codex/Poppler and
then override the system ICU at application startup. Nested ICU files inside a
future `PySide6/` package directory are preserved. The fix is build-time
filtering only: it does not add runtime PATH changes, hard-coded machine paths,
or external DLL dependencies.
