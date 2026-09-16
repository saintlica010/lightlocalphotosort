# Local Media Curator — Agent Instructions

## 1. Mission

Build a lightweight, local-first Windows desktop application for fast manual review, filtering, rejection, categorization, and independent ordering of local photos and videos.

The product is intentionally **not** a general-purpose Digital Asset Management system.

Primary goals, in order:

1. Fast review of large local photo collections.
2. Fast filtering and sorting.
3. Independent manually ordered virtual lists.
4. Non-destructive operation.
5. Simple Windows packaging and low long-term maintenance cost.
6. Strict protection of the user's real local photos and planning data.

The first usable target is Windows 10/11.

---

## 2. Highest-Priority Data Safety Rule

The local machine contains real user data.

The following directories are **protected local reference directories**:

```text
lightphotosprt/
photos/
phototakeplan/
```

Typical contents:

```text
lightphotosprt/
    SKILL.md
    requirements/reference documents
    other local project instructions

photos/
    real local photos
    real local videos
    real media folders used by the user

phototakeplan/
    real local lists
    planning files
    grouping/order references
```

These directories are **reference inputs only**.

They are not development workspaces.

They are not test-output directories.

They are not application cache directories.

They are not export targets.

They are not Git content.

They are not cloud-transfer sources.

### Absolute rule

Unless the user explicitly gives a separate instruction authorizing a specific operation:

**ONLY READ these directories.**

Never modify their contents.

This rule overrides convenience, test automation, refactoring, cleanup, migration, formatting, and implementation shortcuts.

---

## 3. Protected Directory Policy

For:

```text
photos/
phototakeplan/
```

the agent MAY:

- list files;
- inspect directory structure;
- read file metadata;
- read supported media files for compatibility testing;
- generate thumbnails into a separate application cache;
- read list/planning files;
- use the contents to understand actual user workflows;
- use the contents as realistic local read-only examples;
- measure read performance when necessary.

The agent MUST NOT:

- modify any source file;
- overwrite any source file;
- rename any source file;
- move any source file;
- delete any source file;
- touch file timestamps intentionally;
- rewrite EXIF;
- rewrite XMP;
- change orientation metadata;
- recompress photos;
- transcode videos in place;
- optimize media in place;
- reorganize source folders;
- create sidecar files beside the original media;
- create hidden application files inside these folders;
- create `.TagStudio`, `.cache`, `.thumbs`, `.db`, or similar application directories inside them;
- use them as temporary directories;
- use them as build directories;
- use them as test-output directories.

A failed test must never leave files inside these directories.

---

## 4. `lightphotosprt/` Policy

`lightphotosprt/` contains local project reference material such as:

```text
SKILL.md
requirements
planning notes
reference documents
```

The agent MAY read these files when they are relevant.

Treat them as local source-of-truth/reference documents.

Do not rewrite or reorganize them unless the user explicitly asks for that specific file to be edited.

Do not automatically normalize Markdown, filenames, formatting, or directory layout.

When information from `lightphotosprt/` conflicts with general assumptions, prefer the explicit local project instructions.

---

## 5. No Cloud Upload Rule

Protected local data must remain local.

The agent MUST NOT upload, sync, transmit, publish, paste, attach, or otherwise transfer contents from:

```text
photos/
phototakeplan/
lightphotosprt/
```

to any external service unless the user explicitly authorizes that exact transfer.

This includes, but is not limited to:

- GitHub;
- GitLab;
- Bitbucket;
- cloud storage;
- Google Drive;
- OneDrive;
- Dropbox;
- S3;
- external APIs;
- AI APIs;
- image-recognition APIs;
- telemetry systems;
- crash-reporting services;
- analytics services;
- paste sites;
- external databases;
- remote CI artifacts.

Do not send image bytes, video bytes, filenames, folder structures, list contents, or extracted metadata to remote services.

Do not use cloud AI or remote computer-vision APIs on the protected media.

All media processing must be local.

---

## 6. Git Protection

Real user data must never be committed to Git.

The repository `.gitignore` should include, when these paths are located inside or beneath the working tree:

```gitignore
# Real local user data — never commit
/photos/
/phototakeplan/
/lightphotosprt/

# Local application state
*.sqlite
*.sqlite3
*.db
thumb_cache/
thumbnails/
cache/
exports/
logs/
```

If `lightphotosprt/` contains files intentionally tracked separately by the user, do **not** blindly change its Git state.

Instead, preserve its existing state and treat it as read-only.

Before any Git commit, verify that no protected data is staged.

Recommended check:

```bash
git status --short
git diff --cached --name-only
```

If any path under:

```text
photos/
phototakeplan/
```

appears staged, stop and remove it from the staging area without deleting the local file.

Never use commands such as:

```bash
git add .
```

without first confirming that protected directories are excluded.

Prefer explicit paths:

```bash
git add src tests pyproject.toml README.md AGENTS.md
```

---

## 7. Architecture Decision

The architecture assessment has already been completed.

**Decision: build a new focused PySide6 application. Do not fork TagStudio.**

TagStudio may be inspected as an architectural reference.

Reference baseline:

- Repository: `TagStudioDev/TagStudio`
- Branch: `main`
- Baseline commit observed during review:
  `1f1d86e1c990ac3cef5736c6ed656d41a7f7c77c`
- TagStudio version observed: `9.6.4`

Important reference locations:

- `src/tagstudio/core/library/refresh.py`
  - Reference for responsive directory scanning.
- `src/tagstudio/qt/cache_manager.py`
  - Reference for disk thumbnail caching.
- `src/tagstudio/qt/views/layouts/thumb_grid_layout.py`
  - Reference for visible-window thumbnail reuse and rendering prioritization.
- `src/tagstudio/previews/`
  - Reference for preview/thumbnail renderer separation.
- `src/tagstudio/core/library/alchemy/models.py`
  - Reference only; do not reproduce TagStudio's DAM schema.
- `scripts/tagstudio.spec`
  - Reference for PyInstaller packaging.
- `.github/workflows/build.yml`
  - Reference for Windows build automation.

Do not repeat a full fork-vs-new-build analysis unless new evidence reveals a blocking problem.

If a blocking problem is discovered, document it in `DECISIONS.md` before changing architecture.

---

## 8. Licensing Rule

TagStudio as a whole contains GPL-3.0-only code.

Do **not** copy GPL-licensed TagStudio database, UI, grid, cache, or application code into this project unless the project intentionally adopts the corresponding GPL obligations.

Some individual TagStudio preview files are separately marked MIT.

Any code reuse must be evaluated file-by-file from its SPDX header and dependency chain.

When uncertain:

- reimplement the behavior;
- do not copy the implementation;
- record the decision in `DECISIONS.md`.

Never remove upstream attribution from reused code.

---

## 9. Source of Truth

Read these files before implementation when they exist:

```text
AGENTS.md
lightphotosprt/SKILL.md
lightphotosprt/REQUIREMENTS_SUMMARY.md
REQUIREMENTS_SUMMARY.md
SKILL.md
DECISIONS.md
```

Do not assume every file exists in both locations.

Do not relocate them merely to normalize the project structure.

Priority in case of conflict:

```text
AGENTS.md
→ DECISIONS.md
→ explicit local requirements
→ SKILL.md
```

User instructions in the active task override repository documentation.

---

## 10. Real Data vs Test Data

There are two separate concepts:

### Real usage examples

```text
photos/
phototakeplan/
```

These contain real local user data.

They may be used for **read-only manual verification**.

### Automated test data

Automated tests must create their own disposable fixtures.

Preferred locations:

```text
tests/fixtures/
temporary pytest directories
generated temporary projects
```

Tests should generate small fake images whenever possible.

For example:

```python
from PIL import Image

Image.new("RGB", (100, 100)).save(temp_path / "example.jpg")
```

Do not use `photos/` as the normal pytest fixture directory.

Do not make tests depend on the user's personal media collection.

The application must still work when `photos/` is unavailable.

---

## 11. Non-Negotiable Product Rules

The application must be:

- local-first;
- offline-capable;
- non-destructive;
- free of telemetry;
- free of cloud dependencies;
- free of remote AI processing;
- free of face-recognition features in the MVP.

Never modify the contents of source media.

Never rename or move source media merely because it is imported, classified, rejected, or placed in a virtual list.

Never write classification state into EXIF/XMP during the MVP.

Never permanently delete media as part of a normal rejection action.

Physical file operations must be explicit user actions.

Application state belongs in the project database, not in source media folders.

---

## 12. Technology Baseline

Preferred stack:

- Python 3.12 or 3.13
- PySide6
- SQLite
- standard `sqlite3` or a deliberately thin persistence layer
- Pillow
- `pillow-heif` only when HEIC support is enabled
- FFmpeg/ffprobe for video functionality when Phase 2 begins
- pytest
- pytest-qt
- PyInstaller

Avoid adding dependencies without a demonstrated requirement.

Do not introduce:

- web frontends;
- Electron;
- server processes;
- cloud databases;
- REST backends;
- embedded browsers;
- remote inference services;
- analytics SDKs.

Do not introduce SQLAlchemy merely for architectural elegance if plain SQLite repositories remain simpler.

A migration framework such as Alembic is not required for the MVP.

A small versioned migration system using `PRAGMA user_version` or a schema-version table is sufficient.

---

## 13. Required Application Structure

Keep UI, application logic, persistence, and media processing separated.

Recommended package structure:

```text
src/local_media_curator/
    __main__.py
    app.py

    domain/
        models.py
        ordering.py

    db/
        connection.py
        migrations.py
        repositories.py

    media/
        scanner.py
        metadata.py
        thumbnail_service.py
        image_loader.py
        video.py

    services/
        project_service.py
        library_service.py
        list_service.py
        rejection_service.py
        export_service.py
        undo_commands.py

    ui/
        main_window.py
        library_panel.py
        media_grid.py
        media_model.py
        thumbnail_delegate.py
        preview_panel.py
        list_panel.py
        dialogs.py

tests/
```

Do not place database operations directly inside Qt widgets.

Do not place large-image decoding directly inside thumbnail paint methods.

---

## 14. Project Storage

A project owns its metadata but never owns the user's original media files.

Recommended project layout:

```text
MyProject/
    project.sqlite3
    thumbnails/
    exports/
    logs/
```

The project directory must be separate from:

```text
photos/
phototakeplan/
```

Never create the application project database inside a user's real source-media directory by default.

Never place thumbnail caches next to the original photos.

Never place application logs inside the photo source tree.

`exports/` is optional.

Exports must occur only after an explicit user action.

---

## 15. Core Data Model

The central invariant is:

**A media item may belong to multiple lists, and each list must maintain its own independent order.**

Do not implement ordered lists as tags.

Do not put manual list ordering on the `media` row.

Use a relationship entity.

Minimum schema direction:

```sql
CREATE TABLE media (
    id INTEGER PRIMARY KEY,
    absolute_path TEXT NOT NULL UNIQUE,
    normalized_path TEXT NOT NULL UNIQUE,

    media_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    extension TEXT,

    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    duration_ms INTEGER,

    captured_at TEXT,
    modified_at TEXT,
    imported_at TEXT NOT NULL,

    rejected INTEGER NOT NULL DEFAULT 0,
    missing INTEGER NOT NULL DEFAULT 0,

    fingerprint TEXT
);

CREATE TABLE lists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE list_items (
    list_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,

    sort_key INTEGER NOT NULL,
    added_at TEXT NOT NULL,

    PRIMARY KEY (list_id, media_id),

    FOREIGN KEY (list_id)
        REFERENCES lists(id)
        ON DELETE CASCADE,

    FOREIGN KEY (media_id)
        REFERENCES media(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_list_items_order
ON list_items(list_id, sort_key);

CREATE TABLE source_folders (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    recursive INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1
);
```

Enable SQLite foreign keys.

Use transactions for multi-row reorder operations.

---

## 16. Manual Ordering

Manual ordering applies only while viewing a virtual list.

Use sparse integer sort keys.

Example:

```text
1024
2048
3072
4096
```

Insertion between `1024` and `2048` may use:

```text
1536
```

Do not rewrite every list row after every drag.

If there is no integer gap between adjacent keys, normalize the affected list in a transaction.

Required operations:

- drag item to another position;
- drag multiple selected items;
- move one step backward;
- move one step forward;
- move selection to beginning;
- move selection to end;
- undo reorder;
- redo reorder.

Reordering one list must never change ordering in any other list.

Persist a successful reorder immediately.

---

## 17. Media Scanning

A source-folder scan must be read-only with respect to source media.

This is especially important when scanning:

```text
photos/
```

Allowed scan operations:

- enumerate;
- stat;
- open read-only;
- decode;
- extract metadata into the project database.

Forbidden scan operations:

- rewrite;
- rename;
- move;
- chmod;
- delete;
- create sidecars;
- create cache files beside sources.

MVP supported image formats:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.tif`
- `.tiff`

Enable HEIC/HEIF when decoder support is available.

Recognize at least:

- `.mp4`
- `.mov`

Video may have reduced functionality until Phase 2.

Scanning must run outside the GUI thread.

For each scan:

- find new files;
- detect missing files;
- refresh modified metadata when required;
- avoid reprocessing unchanged items;
- report progress without freezing the UI.

Do not hash entire multi-gigabyte files during every scan.

---

## 18. Thumbnail Architecture

Never load every full-resolution image into memory.

Generate thumbnails asynchronously.

Use a bounded worker pool.

Use a disk cache located inside the application/project data area.

Never cache thumbnails into:

```text
photos/
```

A cache key must change when at least one of the following changes:

- normalized source path or media identity;
- source modification time;
- source file size;
- requested thumbnail profile/version.

Preferred cache format:

- WebP; or
- JPEG for opaque thumbnails if measurements show it is faster.

The grid must immediately show placeholders.

Prioritize:

1. currently visible cells;
2. cells shortly before/after the viewport;
3. background cache warming.

A large backlog must not prevent newly visible items from being rendered quickly.

Corrupt files must produce an error placeholder rather than crash the worker.

---

## 19. Grid Implementation

Prefer Qt model/view architecture:

- `QListView`
- `QAbstractListModel`
- `QStyledItemDelegate`
- IconMode
- ExtendedSelection

Use lightweight rows containing IDs and metadata.

Do not create one heavyweight custom widget per media item when a delegate can paint it.

The grid must support at least 10,000 items without loading their full images.

Required interactions:

- single selection;
- multi-selection;
- Shift/Ctrl selection;
- keyboard navigation;
- drag reorder while inside a manually ordered list;
- context actions;
- ordinal overlay when showing a manual list.

Automatic sorting and manual ordering are different modes.

---

## 20. Sorting and Filtering

Automatic sort modes:

- file name;
- capture time;
- modification time;
- file size;
- import time.

Filters:

- image/video type;
- extension;
- source folder;
- virtual list;
- unassigned;
- rejected;
- not rejected;
- missing/not missing.

The UI must make it clear whether the user is seeing:

- an automatically sorted library view; or
- a manually ordered list.

Do not overwrite manual list order when the user temporarily changes a display filter.

---

## 21. Preview

The preview panel must not eagerly decode every selected source image.

For images:

- load on selection;
- obey EXIF orientation in memory;
- do not rewrite EXIF orientation;
- downsample according to display requirements;
- support zoom;
- support pan;
- permit opening the original in the system application.

Display:

- file name;
- path;
- dimensions;
- size;
- captured time;
- modified time;
- list membership;
- rejection state.

Opening the original must not cause the application itself to modify it.

---

## 22. Rejection

Rejecting a media item means setting logical project state.

It does not delete the source file.

Default library views should hide rejected media.

Provide a dedicated Rejected view.

Support restore.

Reject and restore must participate in Undo/Redo.

No physical delete command is required for the MVP.

If one is introduced later, it must be separately designed and explicitly approved.

---

## 23. Undo/Redo

Use Qt's undo framework when practical.

MVP undoable actions:

- add to list;
- remove from list;
- reorder;
- reject;
- restore.

Undo operates on application/database state.

It must never undo by changing the user's original photo bytes or metadata.

Do not implement undo by taking complete database snapshots.

---

## 24. UI

Target a minimal three-panel UI:

```text
+----------------+--------------------------------+------------------+
| Library/Lists  | Media Grid                     | Preview          |
|                |                                |                  |
| All Media      | [01] [02] [03] [04]           | Large Preview    |
| Unassigned     | [05] [06] [07] [08]           |                  |
| Rejected       |                                | Metadata         |
|                |                                |                  |
| Lists          |                                | Lists            |
| Promotional    |                                | Actions          |
| Website        |                                |                  |
+----------------+--------------------------------+------------------+
```

Optimize for number of actions per photo.

Do not add dashboards.

Do not add maps.

Do not add AI controls.

Do not add large configuration screens during MVP.

Keyboard-first review is a core requirement.

---

## 25. Performance Rules

Always profile before replacing simple code with complex optimization.

Minimum targets:

- 1,000 media items;
- 10,000 media items.

The UI must remain responsive during:

- scanning;
- thumbnail generation;
- filtering;
- sorting;
- scrolling.

Real data under `photos/` may be used for manual read-only performance validation.

Automated performance tests should preferably use generated datasets.

Do not execute filesystem scans, image decoding, or video probing in the GUI thread.

Do not preload full-resolution images.

Use bounded queues and cancellation/version tokens.

---

## 26. Phase 1 — Build Now

Do not perform another long architecture phase.

Implement the MVP in this order:

### 26.1 Skeleton

Create:

- package structure;
- project create/open flow;
- SQLite initialization;
- schema migration mechanism;
- main window shell.

Run tests.

### 26.2 Media Library

Implement:

- source-folder CRUD;
- asynchronous scanner;
- media persistence;
- missing-file detection;
- basic metadata extraction.

Use generated fixture data first.

After automated tests pass, `photos/` may be used for read-only manual validation.

### 26.3 Thumbnail Grid

Implement:

- `QAbstractListModel`;
- `QListView` icon grid;
- placeholder thumbnails;
- thumbnail worker pool;
- disk cache;
- selection.

Cache files must remain outside `photos/`.

### 26.4 Preview

Implement image preview and metadata panel.

Do not block the GUI thread.

Do not alter source media.

### 26.5 Virtual Lists

Implement:

- list create;
- rename;
- delete;
- add media;
- remove media;
- item count.

Then implement independent ordering.

Ordering tests are mandatory.

### 26.6 Rejection

Implement logical reject and restore.

### 26.7 Undo/Redo

Cover:

- list membership;
- reorder;
- reject;
- restore.

### 26.8 Packaging

Produce a Windows PyInstaller one-folder build first.

---

## 27. Phase 1 Acceptance Tests

At minimum automate:

```python
def test_one_media_can_exist_in_multiple_lists():
    ...

def test_lists_have_independent_order():
    ...

def test_reorder_first_middle_last():
    ...

def test_reorder_multiple_selection():
    ...

def test_sort_key_normalization():
    ...

def test_remove_from_one_list_does_not_affect_other_lists():
    ...

def test_reject_and_restore():
    ...

def test_reject_undo_redo():
    ...

def test_reorder_undo_redo():
    ...

def test_duplicate_absolute_path_rejected():
    ...

def test_missing_media_detected_without_deleting_database_row():
    ...

def test_database_migration():
    ...

def test_scan_does_not_modify_source_files():
    ...
```

The independent-order test is release-blocking.

The source-file immutability test is also release-blocking.

---

## 28. Source Immutability Verification

Tests involving source media should verify that the application does not alter it.

For temporary fixture media, capture before/after values such as:

```text
file size
content hash
filename
relative path
```

For real data under `photos/`, avoid expensive full hashing of the entire library.

During manual smoke testing, treat the directory as read-only.

The application's normal workflow must not require write permission to source folders.

This is an important design requirement:

**The application should still browse and classify media when the source directory itself is read-only.**

---

## 29. `phototakeplan/` Usage

`phototakeplan/` contains real local planning/list examples.

Use it to understand how real lists are named or organized.

Do not treat these files as the application's writable database.

Do not rewrite them to synchronize application state.

Do not automatically import and then overwrite them.

If import support is later added:

1. parse the source read-only;
2. copy interpreted state into the local project database;
3. leave the original planning file unchanged.

Export back to these files requires a separate explicit user command.

---

## 30. Test Media Safety

Never run destructive tests against:

```text
photos/
phototakeplan/
lightphotosprt/
```

Generate disposable test data.

Use pytest temporary directories.

Tests must never rename, move, modify, or delete media outside their temporary fixture directories.

---

## 31. Phase 2

Only after the image-first MVP is stable, add:

- video thumbnails;
- optional video playback;
- list export;
- JSON/CSV export manifest;
- duplicate output name handling;
- cancellation;
- stronger moved-file reconciliation.

Default file export operation is Copy.

Export destinations must never silently overwrite originals.

Never default to Move.

---

## 32. Packaging

Start with PyInstaller one-folder builds.

Reasons:

- easier dependency debugging;
- faster startup;
- easier FFmpeg integration later;
- easier inspection during development.

A one-file build may be evaluated later.

The packaged application must not contain:

- files copied from `photos/`;
- files copied from `phototakeplan/`;
- private planning documents;
- local absolute-path inventories;
- real generated thumbnails unless deliberately packaged as synthetic demo data.

Before release packaging, inspect the build contents.

---

## 33. Required Repository Documentation

Maintain:

```text
README.md
AGENTS.md
ARCHITECTURE.md
DECISIONS.md
pyproject.toml
src/
tests/
build/
```

Existing local reference files may remain in:

```text
lightphotosprt/
```

Do not move them merely for aesthetic consistency.

---

## 34. Logs and Privacy

Logs must not contain unnecessary personal information.

Avoid logging:

- full lists of photo filenames;
- complete directory inventories;
- image EXIF text;
- planning-list contents;
- hashes of every source file.

When a path is necessary for debugging, prefer minimal scoped logging.

Do not transmit logs automatically.

Crash reporting must remain local unless the user explicitly chooses otherwise in a future version.

---

## 35. Network Policy

The finished application should require **no network access for normal usage**.

Core functionality must work with the network disabled.

No background update checks during MVP.

No telemetry.

No analytics.

No remote thumbnails.

No remote metadata lookup.

No cloud classification.

No hidden network requests.

Development tools such as package managers or Git may use the network for obtaining source code and dependencies, but must never include protected local user data in those requests.

---

## 36. Commit Discipline

Keep changes small and testable.

Prefer commits such as:

```text
feat(db): add initial project schema
feat(scan): add asynchronous source scanner
feat(grid): add media list model
feat(thumbs): add disk thumbnail cache
feat(lists): add virtual list persistence
feat(order): add sparse manual ordering
feat(reject): add logical rejection workflow
test(order): cover independent list ordering
test(safety): verify source files remain unchanged
build(win): add PyInstaller build
```

Before every commit:

1. inspect `git status`;
2. confirm no real photos are staged;
3. confirm no planning data is staged;
4. confirm no generated thumbnail cache is staged;
5. confirm no project database containing user paths is staged.

---

## 37. Stop and Escalate Conditions

Stop implementing and report the issue if:

- an operation may modify real source media unexpectedly;
- code requires write permission to `photos/`;
- an automated test touches real user files destructively;
- a database migration could destroy existing project state;
- independent list ordering cannot be preserved;
- protected local data is about to be uploaded;
- protected local data is accidentally staged in Git;
- a dependency introduces telemetry/cloud behavior;
- a copied dependency has unresolved licensing terms;
- a design requires converting virtual lists into tags.

For ordinary implementation decisions, choose the simplest maintainable solution and continue.

---

## 38. Definition of MVP Done

The MVP is done when a user can:

1. launch a packaged Windows application;
2. create/open a project;
3. add local source folders such as `photos/`;
4. browse them without modifying their contents;
5. browse thumbnails without source files being copied or moved;
6. rapidly navigate and select media;
7. create multiple virtual lists;
8. put one image in several lists;
9. manually maintain a different order in each list;
10. reject and restore images logically;
11. undo required curation operations;
12. close and reopen the project without losing state;
13. use the application while the source photo directory is read-only;
14. complete all of the above without uploading media or planning data to the cloud.

Performance, correctness, privacy, and non-destructive behavior take priority over additional features.

---

## 39. Final Safety Principle

Treat:

```text
photos/
phototakeplan/
```

as the user's real personal working data.

Treat:

```text
lightphotosprt/
```

as local project/reference material.

They exist so the application can be designed and validated against realistic local usage.

They do **not** exist for the agent to clean up, migrate, reorganize, publish, upload, commit, or modify.

When in doubt:

**read only, create test data elsewhere, and leave the original local files untouched.**