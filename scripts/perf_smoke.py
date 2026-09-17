"""Synthetic performance smoke for Phase 1.1.

Run from the worktree root with the project venv:

    python scripts/perf_smoke.py

Everything is generated under a temporary directory. No real photos,
no user paths, no protected trees. Numbers are approximate single-run
timings for regression spotting only, not SLAs.
"""

from __future__ import annotations

import os
import platform
import tempfile
import time
from pathlib import Path

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.media.thumbnail_schedule import (
    MAX_PENDING,
    prioritize_jobs,
)
from local_media_curator.ui.pixmap_cache import PIXMAP_CACHE_LIMIT
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project

IMPORTED_AT = "2026-01-01T00:00:00"


def insert_media(project, count: int) -> list[int]:
    repo = MediaRepository(project.connection)
    ids = []
    for i in range(count):
        ids.append(
            repo.insert(
                absolute_path=f"src/{i}.jpg",
                normalized_path=f"c:/src/{i}.jpg",
                media_type="image",
                file_name=f"{i}.jpg",
                extension=".jpg",
                file_size=1000 + i,
                width=100,
                height=100,
                duration_ms=None,
                captured_at=None,
                modified_at=None,
                imported_at=IMPORTED_AT,
            )
        )
    project.connection.commit()
    return ids


def timed(label: str, func):
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    print(f"{label:<28} {elapsed * 1000:8.1f} ms")
    return result, elapsed


def run(count: int) -> None:
    print(f"\n=== {count:,} synthetic media rows ===")
    with tempfile.TemporaryDirectory() as tmp:
        project = create_project(Path(tmp) / "proj")
        lib = LibraryService(project)
        lists = ListService(project)
        try:
            (ids, insert_s) = timed("insert rows", lambda: insert_media(project, count))
            (media, list_s) = timed("list_media()", lambda: lib.list_media())
            assert len(media) == count
            (mapping, member_s) = timed(
                "list_names_for_media_ids()", lambda: lists.list_names_for_media_ids(ids)
            )
            queries = 0
            conn = project.connection

            class Counting:
                def execute(self, sql, parameters=()):
                    nonlocal queries
                    queries += 1
                    return conn.execute(sql, parameters)

                def __getattr__(self, name):
                    return getattr(conn, name)

            lists._lists._conn = Counting()  # type: ignore[assignment]
            lists.list_names_for_media_ids(ids)
            lists._lists._conn = conn  # type: ignore[assignment]
            print(f"{'membership queries':<28} {queries:8d} (chunk=400)")

            needed = {i: f"p{i}" for i in ids}
            (jobs, sched_s) = timed(
                "prioritize_jobs(10k visible30)",
                lambda: prioritize_jobs(needed, visible_ids=ids[:30], inflight=set()),
            )
            assert len(jobs) <= MAX_PENDING

            (filtered, filter_s) = timed(
                'list_media(media_type="image")',
                lambda: lib.list_media(media_type="image"),
            )
            assert len(filtered) == count

            list_id = lists.create("Perf")
            lists.add_items(list_id, ids[:200])
            (ordered, named_s) = timed(
                "ordered_media_ids(200)", lambda: lists.ordered_media_ids(list_id)
            )
            assert ordered[:200] == ids[:200]

            (rng, reorder_s) = timed(
                "reorder(50 items)",
                lambda: lists.reorder(list_id, ids[98:49:-1]),
            )
            assert lists.ordered_media_ids(list_id)[:49] == [ids[i] for i in range(98, 49, -1)]

        finally:
            project.close()


def main() -> None:
    print(f"Python {platform.python_version()} on {platform.system()}")
    print(f"MAX_PENDING={MAX_PENDING} PIXMAP_CACHE_LIMIT={PIXMAP_CACHE_LIMIT}")
    run(1_000)
    run(10_000)


if __name__ == "__main__":
    main()
