from __future__ import annotations

SORT_KEY_GAP = 1024

__all__ = [
    "SORT_KEY_GAP",
    "next_sort_key",
    "sort_key_between",
    "normalize_list",
    "keys_between",
]


def next_sort_key(after: int | None) -> int:
    if after is None:
        return SORT_KEY_GAP
    return after + SORT_KEY_GAP


def sort_key_between(left: int | None, right: int | None) -> int | None:
    if right is None:
        return next_sort_key(left)
    lo = 0 if left is None else left
    if right - lo <= 1:
        return None
    mid = lo + (right - lo) // 2
    if mid <= lo or mid >= right:
        return None
    return mid


def normalize_list(keys: list[int]) -> list[int]:
    return [SORT_KEY_GAP * (index + 1) for index in range(len(keys))]


def keys_between(left: int | None, right: int | None, count: int) -> list[int] | None:
    if count <= 0:
        return []
    if count == 1:
        key = sort_key_between(left, right)
        return None if key is None else [key]
    if right is None:
        keys: list[int] = []
        after = left
        for _ in range(count):
            after = next_sort_key(after)
            keys.append(after)
        return keys
    lo = 0 if left is None else left
    span = right - lo
    if span <= count:
        return None
    keys = []
    prev = lo
    for index in range(count):
        key = lo + ((index + 1) * span) // (count + 1)
        if key <= prev:
            key = prev + 1
        if key >= right:
            return None
        keys.append(key)
        prev = key
    return keys
