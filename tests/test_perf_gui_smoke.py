"""1k / 10k GUI smoke through the real MainWindow.

Assertions are structural, not timing SLAs. A timing threshold flakes across
machines, and it is exactly the guard that was missing when C1 shipped an O(N)
filesystem reload that froze the UI for ~19 s at 10k rows on a slow-stat box.
Counting filesystem calls and SQL queries catches the shape of that defect
regardless of how fast the machine is.

Media rows are inserted directly; no JPEGs are generated. Nothing here reads
real media.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

from local_media_curator.db.repositories import _IN_CHUNK, MediaRepository
from local_media_curator.media.thumbnail_schedule import MAX_PENDING
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.pixmap_cache import BoundedPixmapCache, PIXMAP_CACHE_LIMIT

SIZES = (1_000, 10_000)

# Far below one call per row (which is what the defect did) but above whatever
# incidental filesystem work the Qt/SQLite stack does during a reload.
FS_CALL_BUDGET = 50


def _fill(project, count: int) -> list[int]:
    repo = MediaRepository(project.connection)
    stamp = "2026-01-01T00:00:00"
    ids = []
    for i in range(count):
        ids.append(
            repo.insert(
                absolute_path=f"src/{i:06d}.jpg",
                normalized_path=f"c:/src/{i:06d}.jpg",
                media_type="image",
                file_name=f"{i:06d}.jpg",
                extension=".jpg",
                file_size=1000 + i,
                width=100,
                height=100,
                duration_ms=None,
                captured_at=stamp,
                modified_at=stamp,
                imported_at=stamp,
            )
        )
    project.connection.commit()
    return ids


def _count_fs_calls(monkeypatch) -> dict[str, int]:
    calls = {"stat": 0, "is_file": 0}
    real_stat = os.stat
    real_is_file = Path.is_file

    def counting_stat(*args, **kwargs):
        calls["stat"] += 1
        return real_stat(*args, **kwargs)

    def counting_is_file(self):
        calls["is_file"] += 1
        return real_is_file(self)

    monkeypatch.setattr(os, "stat", counting_stat)
    monkeypatch.setattr(Path, "is_file", counting_is_file)
    return calls


def _install_sql_probe(repository, needle: str) -> list[str]:
    """Record statements containing `needle` on a repository's connection.

    sqlite3.Connection.execute is immutable, so the connection is swapped for
    a delegating proxy on the repository that MainWindow actually calls.
    """
    real_conn = repository._conn
    seen: list[str] = []

    class _ExecuteProbe:
        def execute(self, sql, parameters=()):
            text = str(sql)
            if needle in text:
                seen.append(text)
            return real_conn.execute(sql, parameters)

        def __getattr__(self, name: str):
            return getattr(real_conn, name)

    repository._conn = _ExecuteProbe()  # type: ignore[assignment]
    return seen


@pytest.fixture(params=SIZES, ids=[f"{n // 1000}k" for n in SIZES])
def big_window(qtbot, tmp_path: Path, request):
    count = request.param
    project = create_project(tmp_path / f"proj{count}")
    ids = _fill(project, count)
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1400, 900)
    window.set_project(project)
    try:
        yield window, project, ids, count
    finally:
        project.close()


def test_gui_displays_full_library(big_window) -> None:
    window, _project, ids, count = big_window
    assert window.media_grid.model.rowCount() == count
    assert len(ids) == count


def test_reload_does_not_do_per_row_filesystem_work(
    big_window, monkeypatch
) -> None:
    window, project, _ids, count = big_window
    calls = _count_fs_calls(monkeypatch)
    window.refresh()
    total = calls["stat"] + calls["is_file"]
    assert total <= FS_CALL_BUDGET, (
        f"{count} rows caused {total} filesystem calls during reload"
    )


def test_reload_does_not_do_per_row_list_membership_sql(big_window) -> None:
    window, _project, _ids, count = big_window
    queries = _install_sql_probe(window.list_service._lists, "list_items")
    window.refresh()
    # Ids are chunked at 400 per statement, so the count scales as n/400 rather
    # than n. The property under test is the chunking, not a magic constant:
    # 10k rows must not produce 10k statements.
    chunked_bound = math.ceil(count / _IN_CHUNK)
    assert len(queries) <= chunked_bound, (
        f"{count} rows caused {len(queries)} list_items queries, "
        f"above the chunked bound of {chunked_bound}"
    )
    assert len(queries) < count / 10


def test_thumbnail_work_stays_bounded_while_scrolling(big_window) -> None:
    window, _project, _ids, count = big_window
    pool = window.thumbnail_pool
    scrollbar = window.media_grid.view.verticalScrollBar()
    assert scrollbar.maximum() > 0, "library should be scrollable"

    for step in range(12):
        scrollbar.setValue(scrollbar.maximum() * step // 12)
        window.media_grid.view.viewport().repaint()
        pending = len(pool.pending_ids())
        inflight = len(pool.inflight_ids())
        assert pending + inflight <= MAX_PENDING + 8, (
            f"{count} rows: queue grew to {pending + inflight} while scrolling"
        )


def test_newly_visible_rows_are_promoted(big_window) -> None:
    window, _project, _ids, count = big_window
    scrollbar = window.media_grid.view.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    window.media_grid.view.viewport().repaint()
    first, last = window.media_grid.visible_row_range()
    assert last == count - 1
    assert first > 0


def test_pixmap_cache_never_exceeds_its_bound() -> None:
    from PySide6.QtGui import QPixmap

    cache = BoundedPixmapCache(max_items=8)
    for i in range(500):
        cache.put(f"k{i}", QPixmap(1, 1))
        assert len(cache) <= 8
    assert PIXMAP_CACHE_LIMIT == 256


def test_filter_and_sort_change_at_scale(big_window) -> None:
    window, _project, _ids, count = big_window
    window.library_panel.type_combo.setCurrentIndex(
        window.library_panel.type_combo.findData("image")
    )
    assert window.media_grid.model.rowCount() == count
    window.library_panel.type_combo.setCurrentIndex(
        window.library_panel.type_combo.findData("video")
    )
    assert window.media_grid.model.rowCount() == 0
    window.library_panel.type_combo.setCurrentIndex(0)
    window.library_panel.sort_combo.setCurrentIndex(1)
    assert window.media_grid.model.rowCount() == count


def test_named_list_display_and_manual_reorder(big_window) -> None:
    from PySide6.QtCore import Qt

    window, project, ids, count = big_window
    lists = ListService(project)
    list_id = lists.create("Perf")
    lists.add_items(list_id, ids[:50])
    window.show_list(list_id)
    assert window.media_grid.model.rowCount() == 50
    model = window.media_grid.model
    assert model.flags(model.index(0)) & Qt.ItemFlag.ItemIsDragEnabled

    reversed_ids = list(reversed(ids[:50]))
    window.apply_grid_order(reversed_ids)
    assert lists.ordered_media_ids(list_id) == reversed_ids


def test_filtered_named_list_keeps_reorder_disabled_at_scale(
    big_window, qtbot
) -> None:
    from PySide6.QtCore import Qt

    window, project, ids, count = big_window
    lists = ListService(project)
    list_id = lists.create("Perf")
    lists.add_items(list_id, ids[:50])
    window.show_list(list_id)
    window.library_panel.extension_combo.setCurrentIndex(
        window.library_panel.extension_combo.findData(".jpg")
    )
    model = window.media_grid.model
    assert not (model.flags(model.index(0)) & Qt.ItemFlag.ItemIsDragEnabled)
    for action in (
        window.move_up_action,
        window.move_down_action,
        window.move_start_action,
        window.move_end_action,
    ):
        assert not action.isEnabled()
    assert window.statusBar().currentMessage() == "名单（已筛选，排序已禁用）"
