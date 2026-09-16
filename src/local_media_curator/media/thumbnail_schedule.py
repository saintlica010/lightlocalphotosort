from collections.abc import Mapping, Sequence

MAX_PENDING = 64
PREFETCH_ROWS = 24


def prioritize_jobs(
    needed: Mapping[int, str],
    visible_ids: Sequence[int],
    inflight: set[int],
    max_pending: int = MAX_PENDING,
) -> list[tuple[int, str]]:
    ordered: list[tuple[int, str]] = []
    seen = set(inflight)
    for media_id in visible_ids:
        if media_id in seen:
            continue
        path = needed.get(media_id)
        if path is None:
            continue
        seen.add(media_id)
        ordered.append((media_id, path))
        if len(ordered) >= max_pending:
            return ordered
    for media_id, path in needed.items():
        if media_id in seen:
            continue
        seen.add(media_id)
        ordered.append((media_id, path))
        if len(ordered) >= max_pending:
            break
    return ordered
