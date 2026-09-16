# Phase 1.1 Review Fixes

Status: **Required before merging `feat/phase1-mvp` into `main` and before starting Phase 2**

Reviewed branch: `feat/phase1-mvp`

Reviewed head at time of audit: `c4de042c3f0263da541273f7954f310b2134ff09`

Reviewer intent: independent verification of Phase 1 implementation against `AGENTS.md`, with emphasis on fast local photo curation, non-destructive behavior, independent virtual-list ordering, responsiveness, and Windows packaging.

---

## 1. Do not redesign the application

The current architecture is acceptable and should be preserved:

- Python 3.12+
- PySide6
- SQLite via `sqlite3`
- project-local SQLite database
- project-local thumbnail cache
- virtual lists backed by `list_items`
- independent sparse integer `sort_key`
- logical reject/restore
- Qt undo stack
- PyInstaller one-folder packaging

Do **not** restart fork-vs-new-app research.

Do **not** migrate to Electron, web UI, cloud services, SQLAlchemy, remote AI, or a server architecture.

This task is a focused Phase 1.1 closeout.

---

## 2. Highest-priority safety rule

The following directories are real local user data/reference data:

```text
photos/
phototakeplan/
lightphotosprt/
```

Treat them as **read-only local examples**.

The implementation and all tests must obey these rules:

- never modify source photos/videos;
- never rename source photos/videos;
- never move source photos/videos;
- never delete source photos/videos;
- never rewrite EXIF/XMP;
- never create sidecars beside source media;
- never create project DB/cache/log files inside those protected trees;
- never use those trees as test-output directories;
- never commit them to Git;
- never upload them to GitHub, cloud storage, APIs, telemetry, AI services, CI artifacts, or other remote services;
- automated tests must use generated temporary files via `tmp_path` or equivalent;
- real data may be used only for local read-only manual verification.

Before every commit, inspect staged paths explicitly. Do not rely on `git add .`.

---

# Blocking fixes

The following items are release-blocking for Phase 1.1.

## 3. Make thumbnail scheduling viewport-driven

### Current problem

The current grid reload builds thumbnail jobs for essentially the whole current result set. This does not scale to the intended 1,000-10,000 image workload.

A photo that has already entered the low-priority queued set also cannot be meaningfully promoted when it becomes visible.

The product goal is fast manual curation, so visible photos must win over backlog work.

### Required behavior

Implement viewport-aware thumbnail scheduling.

Priority order:

1. currently visible rows;
2. a small prefetch buffer before/after the viewport;
3. optional background warming only when worker capacity is available.

Do not enqueue the entire 10,000-photo library at once.

Use a bounded pending-work strategy.

A newly visible item must not wait behind thousands of old off-screen jobs.

Suggested design direction:

```text
QListView viewport
    -> visible row range
    -> visible IDs + small row buffer
    -> thumbnail scheduler
    -> bounded worker queue
    -> disk WebP cache
    -> model row update
```

The exact implementation may differ, but the user-visible behavior must satisfy the acceptance tests below.

### Required tests

Add tests that demonstrate at least:

- current viewport rows are requested first;
- off-screen backlog does not block a newly visible row indefinitely;
- duplicate jobs are not generated unnecessarily;
- pending work remains bounded for a 10,000-item model;
- scrolling repeatedly does not produce unbounded queue growth.

Do not make tests depend on real `photos/` contents.

---

## 4. Bound the in-memory thumbnail pixmap cache

### Current problem

`ThumbnailDelegate` keeps decoded pixmaps in a dictionary without an eviction limit.

A long browsing session through thousands of photos can therefore cause memory usage to grow continuously.

### Required behavior

Replace the unbounded pixmap dictionary with a bounded cache.

Acceptable approaches include:

- `QCache`;
- LRU cache;
- a fixed-count cache;
- a cache limited by approximate byte size.

The cache must evict old entries.

Keep the existing disk thumbnail cache; this task is about decoded in-memory pixmaps.

### Required tests

Prove that inserting more than the configured capacity evicts older entries and does not allow unlimited growth.

---

## 5. Remove N+1 list-membership queries during grid reload

### Current problem

Building rows currently asks for list names per media item individually.

At 10,000 items this can create roughly 10,000 extra SQL queries during a refresh.

### Required behavior

Fetch list membership in bulk.

Preferred shape:

```text
media_ids -> one/few SQL queries -> mapping:
media_id -> [list_name, ...]
```

Then build grid rows from that mapping.

Do not execute one membership SQL query per visible/library item.

### Required tests

Add repository/service tests for bulk membership retrieval.

If practical, add a query-count test or instrumentation-based regression test proving grid reload does not issue O(N) list-membership queries.

---

## 6. Make preview loading "latest selection wins"

### Current problem

Preview results use tokens to ignore stale output, but stale decode work can still execute sequentially.

During rapid keyboard browsing, old selections may consume time before the latest selected image is decoded.

### Required behavior

When the user quickly selects A -> B -> C -> D, the system should not fully process B and C after they are already obsolete.

Desired behavior:

```text
A starts decoding
B requested
C requested
D requested
A completes
skip obsolete pending B/C
load D next
```

Implement one of:

- a latest-only pending slot;
- cancelable jobs where safe;
- queue clearing/replacement;
- equivalent behavior.

Do not block the GUI thread.

### Required tests

Add a deterministic test demonstrating that rapid selection changes do not force every obsolete queued preview to complete before the latest request.

Retain token validation so stale results can never overwrite the current preview.

---

## 7. Add cooperative scan cancellation and safe thread shutdown

### Current problem

The current window shutdown/project-switch code can request `thread.quit()` while the synchronous scan is still running. After a timeout, references may be cleared even if the worker thread has not actually finished.

This is unsafe for large folders.

### Required behavior

Implement cooperative cancellation.

Recommended pattern:

```text
MainWindow requests cancel
    -> worker cancellation flag/event
    -> scanner checks flag periodically
    -> scan exits safely
    -> transaction ends consistently
    -> worker emits completion/cancel state
    -> thread quits
    -> thread actually finishes
    -> QObject cleanup occurs
```

Requirements:

- closing the app during a long scan must not leave a running orphan QThread;
- switching projects during scan must not allow the old worker to continue using the old project unexpectedly;
- cancellation must not leave partial inconsistent DB state;
- source media must remain untouched;
- no `QThread.terminate()` unless there is an exceptional documented reason; prefer cooperative cancellation.

### Required tests

Add tests that simulate a deliberately slow scan and verify:

- close requests cancellation;
- project switch requests cancellation;
- the thread actually stops, not merely that references become `None`;
- DB state remains valid;
- a new scan can start afterward.

---

# Required functional completion

## 8. Finish the Phase 1 filter UI

Repository/service support already exists for some filters, but the user-facing Phase 1 filter set is incomplete.

Add practical UI controls for:

- media type: image / video;
- extension;
- source folder;
- missing / not missing;
- rejected / not rejected where consistent with existing All/Rejected views.

Do not make the UI visually heavy. Keep it optimized for photo review.

Temporary filtering must never rewrite manual list ordering.

### Required tests

Verify combinations such as:

- image-only;
- video-only;
- `.jpg` only;
- one source folder only;
- missing-only;
- filter while viewing a manually ordered list does not change stored `sort_key` values.

---

## 9. Add scan progress reporting

Long scans need visible progress so the user can distinguish working from frozen.

Add progress signals/status text.

At minimum expose processed-file count, e.g.:

```text
Scanning... 1,284 files processed
```

Exact total-file count is optional if obtaining it would require an expensive pre-scan.

Do not update the GUI for every single file if that causes excessive signal traffic. Throttle progress updates appropriately.

### Required tests

Verify progress signals are emitted during a multi-file scan and are handled on the GUI thread without blocking.

---

## 10. Enforce project/source path separation generically

### Current problem

Current protected-project checks rely partly on directory names such as `photos`, `phototakeplan`, and `lightphotosprt`.

That protects the known local layout but does not fully protect arbitrary user source folders such as `Pictures` or `Wedding2026`.

### Required behavior

Enforce generic path-relationship safety.

A project root and a source-media root must not overlap in a way that causes project DB/cache/log output to live inside the source-media tree.

Reject at least these cases:

```text
Project root is inside source folder
Source folder is inside project root
```

Unless a future explicit design provides a safe exception, prefer rejecting both relationships.

Use normalized/resolved paths and Windows-aware case handling.

### Required tests

Cover:

- project inside source;
- source inside project;
- sibling project/source directories allowed;
- Windows case-insensitive equivalent paths where applicable.

---

# Packaging and performance verification

## 11. Run a real Windows PyInstaller smoke test

The current spec structure is acceptable, but Phase 1.1 must produce evidence that the packaged executable actually launches and performs the essential flow.

Build:

```text
python -m PyInstaller build/local_media_curator.spec
```

Then locally test the produced executable on Windows:

```text
dist/local_media_curator/local_media_curator.exe
```

Manual smoke flow:

1. launch EXE;
2. create project in a non-protected directory;
3. add a local read-only source folder;
4. scan;
5. thumbnails appear;
6. preview a photo;
7. create two lists;
8. add the same photo to both lists;
9. drag to different orders in each list;
10. verify orders stay independent;
11. reject and restore;
12. undo and redo;
13. close app;
14. reopen project;
15. verify list membership/order/rejection persisted;
16. confirm source photos did not change.

Record the result in a short Markdown execution report, for example:

```text
docs/verification/phase1_1_windows_smoke.md
```

Do not include personal filenames, user paths, image metadata, screenshots containing private photos, or other protected local data in the committed report.

Use synthetic or sanitized names in committed documentation.

---

## 12. Run 1k and 10k performance smoke tests

The app's central product requirement is fast screening.

Use **generated synthetic test data** for reproducible performance checks where possible.

At minimum test:

- project open;
- initial library display;
- scrolling;
- thumbnail generation scheduling;
- filter change;
- sort change;
- named-list display;
- drag reorder;
- rapid preview navigation.

Data sizes:

```text
1,000 media items
10,000 media items
```

The purpose is not to chase a specific benchmark number yet. The purpose is to detect obvious UI stalls, unbounded memory/queue growth, and O(N) per-item database behavior.

Record:

- dataset size;
- machine/OS summary without personal identifiers;
- approximate timings;
- peak/observed memory if available;
- queue/cache behavior;
- any remaining bottleneck.

Commit a sanitized report such as:

```text
docs/verification/phase1_1_performance.md
```

Real `photos/` may be used locally for read-only manual confirmation, but no real photo, filename inventory, path list, or derived private metadata may be committed or uploaded.

---

# Preserve currently correct behavior

## 13. Do not regress these Phase 1 capabilities

The following behavior is already directionally correct and must remain green:

- one media item can exist in multiple virtual lists;
- each virtual list has independent ordering;
- removing from one list does not affect another;
- sparse integer sort keys are used;
- list normalization occurs when needed;
- drag reorder persists to SQLite;
- library automatic sorting does not rewrite list order;
- reject/restore only changes project state;
- undo/redo works for required curation actions;
- source-media scan is read-only;
- thumbnail files are stored under project cache, not source folders;
- preview applies EXIF orientation in memory only;
- project database is separate from source media;
- `.gitignore` excludes protected local data;
- PyInstaller does not bundle protected directories.

Run the entire existing test suite after every major fix group.

---

# Suggested implementation order

## 14. Recommended sequence

Use this order to reduce rework:

1. bulk list-membership query;
2. viewport-driven thumbnail scheduling;
3. bounded thumbnail memory cache;
4. preview latest-wins scheduling;
5. scan cooperative cancellation;
6. scan progress;
7. generic project/source overlap protection;
8. filter UI completion;
9. full test suite;
10. 1k performance smoke;
11. 10k performance smoke;
12. Windows PyInstaller build and executable smoke test;
13. update README/ARCHITECTURE only if implementation details changed;
14. write sanitized verification reports.

Keep commits small and focused.

Suggested commit names:

```text
perf(thumbs): schedule thumbnails from viewport
perf(grid): bulk-load list memberships
perf(thumbs): bound decoded pixmap cache
perf(preview): prefer latest preview request
fix(scan): add cooperative cancellation
feat(scan): report scan progress
fix(paths): prevent project-source overlap
feat(filters): complete phase1 library filters
test(perf): add 1k and 10k smoke coverage
docs(verify): record phase1.1 windows smoke
```

---

# Acceptance gate

## 15. Phase 1.1 is complete only when all of the following are true

### Safety

- [ ] source files remain byte-for-byte unchanged during normal curation workflows;
- [ ] source folder may be read-only;
- [ ] project/cache/log output never goes into a source tree;
- [ ] protected local directories are not committed or uploaded;
- [ ] no new network/cloud/telemetry dependency is introduced.

### Ordering and curation

- [ ] drag reorder persists;
- [ ] multi-selection reorder persists;
- [ ] two lists retain different orders for the same photos;
- [ ] reject/restore persists;
- [ ] undo/redo remains correct;
- [ ] temporary sort/filter operations do not rewrite manual list order.

### Responsiveness

- [ ] thumbnail queue is bounded;
- [ ] visible images are prioritized;
- [ ] decoded thumbnail memory cache is bounded;
- [ ] grid reload does not use per-item list-membership SQL queries;
- [ ] rapid preview navigation skips obsolete queued work;
- [ ] long scans can be cancelled safely;
- [ ] scan progress is visible;
- [ ] 1k and 10k smoke tests show no obvious UI freeze/unbounded growth.

### Packaging

- [ ] PyInstaller one-folder build succeeds on Windows;
- [ ] packaged EXE launches;
- [ ] full synthetic smoke flow succeeds;
- [ ] close/reopen preserves project state;
- [ ] packaged app does not include real user media/reference data.

### Tests

- [ ] all previous Phase 1 tests remain green;
- [ ] new regression tests for every blocking fix are added;
- [ ] tests use generated temporary media rather than real protected data.

---

# Handoff back for review

## 16. What to provide after implementation

When Phase 1.1 fixes are finished, provide the reviewer with:

1. final branch name;
2. final commit SHA;
3. `main...branch` diff/PR link;
4. full pytest summary;
5. list of new/changed files;
6. Windows PyInstaller build result;
7. sanitized Windows smoke-test report;
8. sanitized 1k/10k performance report;
9. known limitations that remain intentionally deferred to Phase 2.

Do not ask the reviewer to infer success only from plans or documentation. Provide executable/test evidence.

---

## Final instruction to the implementing agent

Do not broaden scope into Phase 2 features while completing this document.

The goal is not more features. The goal is to make Phase 1 reliably fast, safe, testable, and genuinely usable with large local photo collections.

When a choice exists, prefer:

```text
source safety
> correctness
> responsiveness
> simplicity
> extra features
```
