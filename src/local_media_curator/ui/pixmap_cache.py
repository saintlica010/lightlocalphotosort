from __future__ import annotations

from collections import OrderedDict

from PySide6.QtGui import QPixmap

PIXMAP_CACHE_LIMIT = 256


class BoundedPixmapCache:
    """LRU cache of decoded pixmaps, holding at most ``max_items`` entries."""

    def __init__(self, max_items: int = PIXMAP_CACHE_LIMIT) -> None:
        self._max_items = max_items
        self._items: OrderedDict[str, QPixmap] = OrderedDict()

    def get(self, key: str) -> QPixmap | None:
        pixmap = self._items.get(key)
        if pixmap is None:
            return None
        self._items.move_to_end(key)
        return pixmap

    def put(self, key: str, pixmap: QPixmap) -> None:
        self._items[key] = pixmap
        self._items.move_to_end(key)
        while len(self._items) > self._max_items:
            self._items.popitem(last=False)

    def keys(self) -> list[str]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)
