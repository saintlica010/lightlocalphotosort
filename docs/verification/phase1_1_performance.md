# Phase 1.1 Performance Smoke (synthetic)

Date: 2026-09-17
Machine summary: Windows, Python 3.12.10, local disk. No personal identifiers; all data synthetic.
Method: `scripts/perf_smoke.py` (worktree root, project venv). Rows are inserted directly via
`MediaRepository.insert` into a temporary SQLite project; no real photos are read and no
JPEGs are generated.

Constants under test: `MAX_PENDING = 64`, `PIXMAP_CACHE_LIMIT = 256`, membership `IN` chunk = 400.

> **Read the structural numbers, not the timings.** Single-machine wall-clock varies by an
> order of magnitude between disks, and a timing threshold is what let C1 ship. The
> assertions in `tests/test_perf_gui_smoke.py` count filesystem calls and SQL statements
> instead, so they hold on any machine.

## 1. Repository / service level

| Measurement | 1,000 rows | 10,000 rows |
|---|---|---|
| insert rows | 5.1 ms | 52.6 ms |
| `list_media()` | 7.7 ms | 76.7 ms |
| `list_names_for_media_ids()` | 0.5 ms | 3.0 ms |
| membership query count | 3 | 25 (ceil(n/400)) |
| `prioritize_jobs(10k needed, 30 visible)` | ~0 ms | ~0 ms (bounded ≤ 64 jobs) |
| `list_media(media_type="image")` | 7.4 ms | 75.8 ms |
| `ordered_media_ids(200)` | 0.2 ms | 0.2 ms |
| `reorder(50 items)` on a 200-item list | 1.1 ms | 1.1 ms |

## 2. GUI level — real `MainWindow`, model and view (offscreen)

This is the layer the previous report did not cover, and the layer C1 lived in.

| Measurement | 1,000 rows | 10,000 rows |
|---|---|---|
| `set_project` (grid reload + model reset) | 22.9 ms | 116.5 ms |
| **filesystem calls per reload** | **4** | **4** |
| filter change | 11.3 ms | 119.7 ms |
| sort change | 11.3 ms | 120.4 ms |
| named-list display (200 items) | 3.1 ms | 5.0 ms |
| 12 viewport scroll steps | 4.3 ms | 9.4 ms |
| thumbnail pending / inflight after scrolling | 32 / 4 | 24 / 4 |

The filesystem count is the headline: **4 calls whether the library holds 1,000 rows or
10,000**. It does not scale with the library, which is the property that matters.

## 3. Why that number is the one to watch

Before this branch, `_reload_grid` resolved and stat'ed a thumbnail path per row. Measured
on this machine at the time: **2.00 s at 1,000 rows and 19.31 s at 10,000**, all of it on the
GUI thread, re-run on every reject, undo, reorder and view switch. About 60% of the cost was
two `Path.resolve()` walks per row.

It was found by review, not by a test. The repo had no assertion on the *shape* of a reload —
only timings, which nobody ran at scale. `tests/test_perf_gui_smoke.py` now asserts:

- reload issues ≤ 50 filesystem calls regardless of row count (measured: 4);
- reload issues ≤ ceil(n/400) `list_items` statements (measured: 25 at 10k, not 10,000);
- pending + inflight stays within `MAX_PENDING` across repeated scrolling;
- the decoded pixmap cache never exceeds its bound;
- viewport changes promote newly visible rows;
- a filtered named list keeps drag reorder and all four move actions disabled.

These are structural, so they fail on a fast machine too.

## 4. Behavior notes

- Membership lookup scales as chunked `IN` queries (n/400), not one query per row.
- Thumbnail scheduling is viewport-driven and bounded: pending + inflight ≤ `MAX_PENDING`
  plus the in-flight workers, at any library size. Visible rows are promoted over backlog.
- Filter change is one SQL query with `WHERE` clauses; named-list filtering happens in memory
  on already-ordered ids and never rewrites `sort_key`.
- Reorder of 50 items costs a handful of `UPDATE`s inside one transaction.
- Scan work runs off the GUI thread (it did not, before `e39bcb3`).

## 5. Remaining known bottlenecks (deferred, out of Phase 1.1 scope)

- No HEIC decode (28 HEIC files in a typical local library are skipped), no video thumbnails,
  no embedded playback. `pillow-heif` would be needed for the former.
- `list_media` sorts in SQL at O(N log N); fine at 10k, revisit around 100k.
- The grid is delegate-painted but not widget-virtualised beyond `QListView` internals.
- The pixmap cache is bounded by entry count, not bytes; a future profile could size it by
  memory instead.
- Single-machine timings are indicative only; CI-style assertions cover call counts and
  bounded queues, not wall-clock SLAs.
