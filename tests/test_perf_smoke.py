import math
import time
from pathlib import Path

import pytest
from PIL import Image

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.media.thumbnail_schedule import MAX_PENDING, prioritize_jobs
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project


def _fill_media(project, count: int) -> list[int]:
    repo = MediaRepository(project.connection)
    imported = "2026-01-01T00:00:00"
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
                captured_at=imported,
                modified_at=imported,
                imported_at=imported,
            )
        )
    project.connection.commit()
    return ids


@pytest.mark.parametrize("count", [1_000, 10_000])
def test_perf_smoke_helpers_stay_bounded(tmp_path: Path, count: int) -> None:
    project = create_project(tmp_path / f"proj{count}")
    lib = LibraryService(project)
    lists = ListService(project)
    try:
        start = time.perf_counter()
        ids = []
        for i in range(count):
            ids.append(
                lib._media.insert(
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
                    imported_at="2026-01-01T00:00:00",
                )
            )
        project.connection.commit()
        insert_seconds = time.perf_counter() - start

        start = time.perf_counter()
        media = lib.list_media()
        list_seconds = time.perf_counter() - start
        assert len(media) == count

        start = time.perf_counter()
        mapping = lists.list_names_for_media_ids(ids)
        membership_seconds = time.perf_counter() - start
        assert all(name == [] for name in mapping.values())

        start = time.perf_counter()
        jobs = prioritize_jobs({i: f"p{i}" for i in ids}, visible_ids=ids[:30], inflight=set())
        schedule_seconds = time.perf_counter() - start
        assert len(jobs) <= MAX_PENDING

        list_id = lists.create("Perf")
        lists.add_items(list_id, ids[:200])
        start = time.perf_counter()
        lists.reorder(list_id, ids[98:49:-1])
        reorder_seconds = time.perf_counter() - start
        assert lists.ordered_media_ids(list_id)[:49] == [ids[i] for i in range(98, 49, -1)]

        print(
            f"\ninsert={insert_seconds:.3f}s list_media={list_seconds:.3f}s "
            f"membership={membership_seconds:.3f}s schedule={schedule_seconds:.6f}s "
            f"reorder50={reorder_seconds:.3f}s (n={count})"
        )
        assert all(
            math.isfinite(x)
            for x in (
                insert_seconds,
                list_seconds,
                membership_seconds,
                schedule_seconds,
                reorder_seconds,
            )
        )
    finally:
        project.close()
