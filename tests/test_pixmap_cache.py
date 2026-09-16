from PySide6.QtGui import QPixmap

from local_media_curator.ui.pixmap_cache import PIXMAP_CACHE_LIMIT, BoundedPixmapCache


def test_pixmap_cache_evicts_oldest_beyond_capacity(qapp) -> None:
    cache = BoundedPixmapCache(max_items=3)
    cache.put("a", QPixmap(1, 1))
    cache.put("b", QPixmap(1, 1))
    cache.put("c", QPixmap(1, 1))
    cache.put("d", QPixmap(1, 1))
    assert len(cache) == 3
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("d") is not None


def test_pixmap_cache_get_refreshes_lru_order(qapp) -> None:
    cache = BoundedPixmapCache(max_items=2)
    cache.put("a", QPixmap(1, 1))
    cache.put("b", QPixmap(1, 1))
    assert cache.get("a") is not None
    cache.put("c", QPixmap(1, 1))
    assert cache.get("b") is None
    assert cache.get("a") is not None


def test_default_limit_is_bounded(qapp) -> None:
    assert PIXMAP_CACHE_LIMIT == 256
    cache = BoundedPixmapCache()
    for i in range(300):
        cache.put(str(i), QPixmap(1, 1))
    assert len(cache) == 256
    assert cache.get("0") is None
    assert cache.get("299") is not None
