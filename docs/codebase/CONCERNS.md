# Codebase Concerns

> **STALE SNAPSHOT — see [README.md](README.md) in this directory.** Every
> "high" risk below has since been fixed, and the Medium/Performance entries on
> the pixmap cache and preview queue are fixed too. Kept as a record of the
> pre-fix state, not as a live risk register.

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| high | Scan has no cooperative cancellation or progress reporting | `src/local_media_curator/media/scan_worker.py`, `src/local_media_curator/ui/main_window.py`, `docs/PHASE1_1_REVIEW_FIXES.md` | Closing or switching projects during a long scan may leave shutdown behavior uncertain, and users cannot distinguish work from a freeze | Add a cancellation event, progress signal, atomic/consistent commit boundaries, and tests for close/switch/restart. |
| high | Project/source separation is not generic | `src/local_media_curator/services/project_service.py`, `docs/PHASE1_1_REVIEW_FIXES.md` | A project under an arbitrary source folder, or a source under a project folder, could place DB/cache/log output in the source tree | Validate normalized/resolved ancestor relationships when creating/opening projects and adding source folders. |
| high | User-facing filter UI is incomplete | `src/local_media_curator/ui/library_panel.py`, `src/local_media_curator/db/repositories.py`, `docs/PHASE1_1_REVIEW_FIXES.md` | Required type, extension, source-folder, missing, and rejection combinations are not available from the UI | Add lightweight filter controls and regression tests that preserve list sort keys. |
| medium | Decoded thumbnail pixmaps are cached in an unbounded dictionary | `src/local_media_curator/ui/thumbnail_delegate.py` | Long sessions or large libraries can retain too many decoded pixmaps | Use a bounded LRU/cache budget and invalidate entries safely on project changes. |
| medium | Preview latest-token filtering does not cancel obsolete work | `src/local_media_curator/media/preview_loader.py`, `ui/preview_panel.py` | Rapid navigation can leave stale decode jobs consuming the single worker and delay the current selection | Add cancellation/coalescing or a latest-only queue while retaining token validation. |
| medium | Main window is a high-churn coordination module | `src/local_media_curator/ui/main_window.py`, repository git history | Changes to session, refresh, scanning, thumbnails, selection, and menus converge in one 683-line file | Keep changes incremental; extract only after a measured responsibility boundary appears. |
| low | Build/test tool versions and quality gates are not pinned | `pyproject.toml`, scan result, `docs/codebase/STACK.md` | Reproducibility and review confidence vary by machine | Decide supported package version ranges, add a lock strategy if needed, and document lint/coverage gates. |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|----------------|---------------|
| Schema migration currently only defines version 1 | MVP has one schema version and a minimal `PRAGMA user_version` path | `src/local_media_curator/db/migrations.py` | Future changes need careful forward-only migration handling to avoid project-state loss | Add explicit version steps and migration tests before changing tables. |
| Source-folder removal removes the folder registration but retains media rows | This preserves non-destructive media history and is covered by tests | `src/local_media_curator/db/repositories.py`, `tests/test_library_query.py` | Re-adding or reconciling old rows may require clearer ownership semantics | Document intended lifecycle and add reconciliation behavior only with a product decision. |
| Project logs directory exists without an active logging policy | Storage layout reserves logs while code does not write them | `src/local_media_curator/services/project_service.py`, `AGENTS.md` | Future diagnostics could accidentally log private paths/metadata | Define local-only redaction rules before adding logging. |

### 3) Security Concerns

| Risk | OWASP category (if applicable) | Evidence | Current mitigation | Gap |
|------|-------------------------------|----------|--------------------|-----|
| Project/cache/log output can overlap an arbitrary source tree | N/A (local data isolation) | `services/project_service.py`, `docs/PHASE1_1_REVIEW_FIXES.md` | Blocks roots containing the known names `photos`, `phototakeplan`, and `lightphotosprt`; tests cover known `photos` paths | Generic ancestor/descendant checks are still missing. |
| Accidental mutation of source media | N/A (data integrity) | `media/scanner.py`, `media/thumbnail_service.py`, `tests/test_scan_immutability.py` | Scanner opens/stat/enumerates; derived thumbnails target project cache; tests compare source content and metadata | Continue extending safety tests for all future media workflows. |
| Unnecessary private-data logging or transmission | N/A (privacy) | `AGENTS.md`, `README.md` | No network/telemetry code or logging writer found; repository rules prohibit upload | `[TODO]` Re-audit whenever exports, diagnostics, or dependencies change. |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| Synchronous scan body, limited shutdown control | `services/library_service.py`, `media/scanner.py`, `media/scan_worker.py` | Work is off the GUI thread but has no progress/cancellation checkpoints | Large source trees can make close/switch slow or ambiguous | Add cooperative cancellation and throttled progress. |
| Unbounded decoded pixmap cache | `ui/thumbnail_delegate.py` | One `QPixmap` is retained per distinct cache path seen by the delegate | 10k-item/long-session memory growth | Bound by count/bytes and evict least-recently-used entries. |
| Preview queue is latest-token filtered, not latest-job cancelled | `media/preview_loader.py` | Obsolete results are dropped only after decode completes | Rapid selection can waste serial decode time | Coalesce queued jobs or cancel safe jobs. |
| Grid reload materializes the current view and list membership map | `ui/main_window.py`, `db/repositories.py` | Current result rows are loaded into Python before model reset | Large result sets increase reload latency/memory | Preserve visible-window thumbnail scheduling and measure before introducing pagination. |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|--------------|----------------------|
| `src/local_media_curator/ui/main_window.py` | Owns project lifecycle, views, menus, scan shutdown, refresh, selection, and thumbnail coordination | Highest recent file churn in the repository scan/history | Keep changes focused, add behavior tests first, and avoid broad UI rewrites. |
| `src/local_media_curator/db/repositories.py` | Central SQL boundary for media/list state and query behavior | Second-highest recent churn | Preserve parameterized queries and transaction behavior; add focused repository tests. |
| `src/local_media_curator/services/list_service.py` | Encodes the release-blocking independent-order invariant | High recent churn and ordering dependency | Change through domain/order tests and verify another list's keys remain unchanged. |
| `tests/test_session.py` and `tests/test_lists.py` | Broad Qt/database behavioral coverage | Among the largest test files and repeatedly changed | Keep fixtures disposable and update only the affected acceptance scenario. |

### 6) `[ASK USER]` Questions

1. [ASK USER] Should the next implementation pass focus on the documented Phase 1.1 closeout fixes on `feat/phase1-mvp` before any merge toward `main`?
2. [ASK USER] Do you authorize installing the missing development dependencies into the worktree environment so the full pytest and Windows packaging checks can run?

### 7) Evidence

- `AGENTS.md`
- `README.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `src/local_media_curator/ui/main_window.py`
- `src/local_media_curator/ui/thumbnail_delegate.py`
- `src/local_media_curator/media/scan_worker.py`
- `src/local_media_curator/media/preview_loader.py`
- `src/local_media_curator/services/project_service.py`
- `src/local_media_curator/services/list_service.py`
- `src/local_media_curator/db/repositories.py`
- `docs/PHASE1_1_REVIEW_FIXES.md`

