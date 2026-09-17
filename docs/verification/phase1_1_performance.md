# Phase 1.1 Performance Smoke (synthetic)

Date: 2026-09-17
Machine summary: Windows, Python 3.12, local SSD. No personal identifiers; all data synthetic.
Method: `scripts/perf_smoke.py` (repo worktree, project venv). Rows are inserted directly via
`MediaRepository.insert` into a temporary SQLite project; no real photos are read and no
JPEGs are generated for the query/scheduling measurements.

Constants under test: `MAX_PENDING = 64`, `PIXMAP_CACHE_LIMIT = 256`, membership `IN` chunk = 400.

## Results

| Measurement | 1,000 rows | 10,000 rows |
|---|---|---|
| insert rows (bulk-ish loop) | 9.0 ms | 75.0 ms |
| `list_media()` | 9.0 ms | 98.1 ms |
| `list_names_for_media_ids()` | 1.0 ms | 3.4 ms |
| membership query count | 3 | 25 (ceil(n/400)) |
| `prioritize_jobs(needed 10k, visible 30)` | ~0 ms | ~0 ms (bounded <= 64 jobs) |
| `list_media(media_type="image")` filter change | 9.8 ms | 90.8 ms |
| `ordered_media_ids(200)` named-list display | 0.7 ms | 0.3 ms |
| `reorder(50 items)` on a 200-item list | 2.3 ms | 2.2 ms |

pytest coverage for the same helpers: `tests/test_perf_smoke.py` (1k and 10k parametrized,
asserts finite timings, bounded schedule output, and membership query chunking without
writing 10k JPEGs per run).

## Behavior notes

- Membership lookup scales as chunked `IN` queries (n/400), not O(N) per-row queries.
- Thumbnail scheduling stays bounded regardless of library size: at most `MAX_PENDING`
  jobs exist in pending+inflight; visible rows are promoted over backlog.
- Filter change is one SQL query with `WHERE` clauses; named-list filtering happens in
  memory on already-ordered ids and never rewrites `sort_key`.
- Reorder of 50 items costs a handful of `UPDATE`s inside one transaction.

## Remaining known bottlenecks (out of scope for Phase 1.1)

- No HEIC decode, no video thumbnails, no embedded playback.
- Grid is delegate-painted but not widget-virtualized beyond `QListView` internals.
- `list_media` sorts in SQL at O(N log N); fine at 10k, revisit if libraries reach 100k.
- Single-machine timings are indicative only; CI-style assertions cover call counts and
  bounded queues, not wall-clock SLAs.
