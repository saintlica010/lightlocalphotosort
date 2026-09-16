from local_media_curator.media.thumbnail_schedule import MAX_PENDING, prioritize_jobs


def test_visible_ids_are_requested_first() -> None:
    needed = {i: f"p{i}" for i in range(100)}
    jobs = prioritize_jobs(needed, visible_ids=[50, 51, 52], inflight=set())
    assert [media_id for media_id, _path in jobs[:3]] == [50, 51, 52]


def test_inflight_ids_are_not_duplicated() -> None:
    needed = {1: "a", 2: "b", 3: "c"}
    jobs = prioritize_jobs(needed, visible_ids=[1, 2], inflight={1})
    assert [media_id for media_id, _path in jobs] == [2, 3]


def test_pending_work_is_bounded_for_10000_items() -> None:
    needed = {i: f"p{i}" for i in range(10_000)}
    jobs = prioritize_jobs(needed, visible_ids=list(range(20)), inflight=set())
    assert len(jobs) <= MAX_PENDING
    assert [media_id for media_id, _path in jobs[:20]] == list(range(20))


def test_repeated_prioritize_does_not_grow() -> None:
    needed = {i: f"p{i}" for i in range(10_000)}
    first = prioritize_jobs(needed, visible_ids=[1, 2], inflight=set())
    second = prioritize_jobs(needed, visible_ids=[3, 4], inflight=set())
    assert len(first) <= MAX_PENDING
    assert len(second) <= MAX_PENDING
    assert [media_id for media_id, _path in second[:2]] == [3, 4]
