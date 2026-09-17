# External Integrations

## Core Sections (Required)

### 1) Integration Inventory

| System | Type (API/DB/Queue/etc) | Purpose | Auth model | Criticality | Evidence |
|--------|---------------------------|---------|------------|-------------|----------|
| Local source folders | Local filesystem | Read-only enumeration, stat, image open, and metadata extraction | OS filesystem permissions; no app credentials | High | `src/local_media_curator/media/scanner.py`, `AGENTS.md` |
| Project SQLite database | Embedded DB | Store media metadata, source folders, virtual lists, membership, ordering, rejection state | None | High | `src/local_media_curator/db/connection.py`, `migrations.py` |
| Project thumbnail/log directories | Local filesystem | Store generated WebP thumbnails and reserved project logs outside source media | OS filesystem permissions; no app credentials | Medium | `src/local_media_curator/services/project_service.py`, `media/thumbnail_service.py` |
| Windows system application | OS service/API | Open the selected original via `QDesktopServices` | OS-level file association | Low | `src/local_media_curator/media/preview_loader.py` |

No HTTP API, cloud database, message queue, remote AI, telemetry, analytics, or crash-reporting integration was found in the application source/configuration.

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| `project.sqlite3` | Durable project metadata and curation state | `connect()`, migrations, repositories, services | Migration safety and project/source path separation | `src/local_media_curator/db/connection.py`, `migrations.py`, `services/project_service.py` |
| `project.thumbnails_dir` (`thumbnails/`) | Derived thumbnail cache | `ThumbnailService` and `ThumbnailPool` | Cache growth and stale files; must stay outside source trees | `src/local_media_curator/media/thumbnail_service.py`, `thumbnail_pool.py` |
| Source media files | User-owned input only; not an application-owned store | `scanner.py`, Pillow loaders | Accidental write/sidecar/cache; current tests cover immutability | `tests/test_scan_immutability.py`, `AGENTS.md` |

### 3) Secrets and Credentials Handling

- Credential sources: none found; the application is local-first and has no configured external service credentials.
- Hardcoding checks: no URLs, access tokens, or credential reads were found in `src`, `tests`, `pyproject.toml`, `build`, or `scripts`.
- Rotation or lifecycle notes: not applicable. `[TODO]` Re-check if any future export, update, or remote integration is added.

### 4) Reliability and Failure Behavior

- Retry/backoff behavior: no external-call retry exists; SQLite uses `PRAGMA busy_timeout = 5000`.
- Timeout policy: SQLite busy timeout is 5 seconds; the main-window scan shutdown wait is 2 seconds.
- Circuit-breaker or fallback behavior: none. Database operations roll back on selected failures; corrupt image/thumbnail/preview inputs fall back to null/error placeholders.
- Scan cancellation: `[TODO]` Cooperative cancellation is explicitly required by `docs/PHASE1_1_REVIEW_FIXES.md` but is not present in `ScanWorker`.

### 5) Observability for Integrations

- Logging around external calls: no external calls; no application logging writer was found.
- Metrics/tracing coverage: none found.
- Missing visibility gaps: scan progress, cancellation status, packaged smoke evidence, and 1k/10k performance reports remain to be supplied per the Phase 1.1 review document.

### 6) Evidence

- `src/local_media_curator/db/connection.py`
- `src/local_media_curator/db/migrations.py`
- `src/local_media_curator/services/project_service.py`
- `src/local_media_curator/media/scanner.py`
- `src/local_media_curator/media/preview_loader.py`
- `tests/test_scan_immutability.py`
- `docs/PHASE1_1_REVIEW_FIXES.md`
- `AGENTS.md`

