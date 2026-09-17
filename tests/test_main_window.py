from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt

from local_media_curator.services.project_service import create_project
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_model import MediaListModel


def test_main_window_has_three_panels(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert isinstance(window.library_panel, LibraryPanel)
    assert window.library_panel.list_panel is not None
    assert window.media_grid is not None
    assert window.preview_panel is not None


def test_undo_reject_restores_selection_and_preview(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    target = window.media_grid.model.index(1)
    window.media_grid.view.setCurrentIndex(target)
    media_id = int(window.media_grid.model.data(target, MediaListModel.IdRole))
    file_name = window.media_grid.model.row_at(1)["file_name"]
    window.reject_selection()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    window._on_undo()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    current = window.media_grid.view.currentIndex()
    assert current.isValid()
    assert int(window.media_grid.model.data(current, MediaListModel.IdRole)) == media_id
    assert window.preview_panel.file_name_label.text() == file_name
    project.close()


def test_library_refresh_keeps_selection(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(source / "B.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(1))
    media_id = int(
        window.media_grid.model.data(
            window.media_grid.view.currentIndex(), MediaListModel.IdRole
        )
    )
    window.show_library_view("all")
    current = window.media_grid.view.currentIndex()
    assert current.isValid()
    assert int(window.media_grid.model.data(current, MediaListModel.IdRole)) == media_id
    project.close()


def test_scan_finished_invalidates_thumb_paths_for_reensure(
    qtbot, tmp_path: Path
) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    media_id = int(window.media_grid.model.row_at(0)["id"])
    window._thumb_paths[media_id] = str(tmp_path / "stale.webp")
    items = window._media_for_current_view()
    skipped = {job_id for job_id, _path in window._thumbnail_jobs(items, [])}
    assert media_id not in skipped
    window._on_scan_finished(None)
    items = window._media_for_current_view()
    requested = {job_id for job_id, _path in window._thumbnail_jobs(items, [])}
    assert media_id in requested
    assert media_id not in window._thumb_paths
    project.close()


def _filtered_list_window(qtbot, tmp_path: Path):
    """Named list holding four items that filters can hide.

    src1: A.jpg, B.jpg   src2: C.png, D.mp4 (fake bytes; only the name matters)
    """
    project = create_project(tmp_path / "proj")
    src1 = tmp_path / "src1"
    src2 = tmp_path / "src2"
    src1.mkdir()
    src2.mkdir()
    Image.new("RGB", (10, 10)).save(src1 / "A.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(src1 / "B.jpg", "JPEG")
    Image.new("RGB", (10, 10)).save(src2 / "C.png", "PNG")
    (src2 / "D.mp4").write_bytes(b"not a real video")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(src1)
    window.add_source_folder(src2)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    ids = {
        window.media_grid.model.row_at(i)["file_name"]: int(
            window.media_grid.model.row_at(i)["id"]
        )
        for i in range(window.media_grid.model.rowCount())
    }
    list_id = window.list_service.create("Promotional")
    window.add_items_to_list(
        list_id, [ids["A.jpg"], ids["B.jpg"], ids["C.png"], ids["D.mp4"]]
    )
    window.show_list(list_id)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    return project, window, list_id, ids, src1, src2


def _drag_enabled(window) -> bool:
    model = window.media_grid.model
    return bool(model.flags(model.index(0)) & Qt.ItemFlag.ItemIsDragEnabled)


def _reorder_actions(window) -> tuple:
    return (
        window.move_up_action,
        window.move_down_action,
        window.move_start_action,
        window.move_end_action,
    )


def test_named_list_reorder_enabled_when_unfiltered(qtbot, tmp_path: Path) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    assert _drag_enabled(window)
    assert all(action.isEnabled() for action in _reorder_actions(window))
    project.close()


def test_extension_filter_disables_reorder_in_named_list(
    qtbot, tmp_path: Path
) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    assert not _drag_enabled(window)
    assert not any(action.isEnabled() for action in _reorder_actions(window))
    assert window.statusBar().currentMessage() == "名单（已筛选，排序已禁用）"
    project.close()


def test_type_filter_disables_reorder_in_named_list(qtbot, tmp_path: Path) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    combo = window.library_panel.type_combo
    combo.setCurrentIndex(combo.findData("image"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 3, timeout=8000)
    assert not _drag_enabled(window)
    assert not any(action.isEnabled() for action in _reorder_actions(window))
    project.close()


def test_folder_filter_disables_reorder_in_named_list(qtbot, tmp_path: Path) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    from local_media_curator.domain.paths import normalize_path

    combo = window.library_panel.folder_combo
    combo.setCurrentIndex(combo.findData(normalize_path(_src1)))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    assert not _drag_enabled(window)
    assert not any(action.isEnabled() for action in _reorder_actions(window))
    project.close()


def test_present_filter_disables_reorder_in_named_list(qtbot, tmp_path: Path) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    combo = window.library_panel.missing_combo
    combo.setCurrentIndex(combo.findData(False))
    # rowCount stays 4 here, so it cannot prove the filter engaged; assert it directly.
    assert combo.currentData() is False
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    assert not _drag_enabled(window)
    assert not any(action.isEnabled() for action in _reorder_actions(window))
    project.close()


def test_missing_filter_disables_reorder_in_named_list(qtbot, tmp_path: Path) -> None:
    project, window, list_id, ids, src1, _src2 = _filtered_list_window(qtbot, tmp_path)
    (src1 / "B.jpg").unlink()
    window.scan()
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=8000)
    combo = window.library_panel.missing_combo
    combo.setCurrentIndex(combo.findData(True))
    assert combo.currentData() is True
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    assert window.media_grid.model.row_at(0)["id"] == ids["B.jpg"]
    assert not _drag_enabled(window)
    assert not any(action.isEnabled() for action in _reorder_actions(window))
    project.close()


def test_clearing_filters_restores_reorder(qtbot, tmp_path: Path) -> None:
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    assert not _drag_enabled(window)
    combo.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    assert _drag_enabled(window)
    assert all(action.isEnabled() for action in _reorder_actions(window))
    assert window.statusBar().currentMessage() == "List (manual order)"
    project.close()


def test_filter_toggle_never_rewrites_stored_sort_keys(
    qtbot, tmp_path: Path
) -> None:
    project, window, list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    before = window.list_service.items_with_sort_keys(list_id)
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    combo.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    assert window.list_service.items_with_sort_keys(list_id) == before
    project.close()


def test_hidden_members_keep_positions_across_filter_toggle(
    qtbot, tmp_path: Path
) -> None:
    project, window, list_id, ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    expected = [ids["A.jpg"], ids["B.jpg"], ids["C.png"], ids["D.mp4"]]
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    assert window.list_service.ordered_media_ids(list_id) == expected
    combo.setCurrentIndex(0)
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 4, timeout=8000)
    assert window.list_service.ordered_media_ids(list_id) == expected
    project.close()


def test_keyboard_reorder_while_filtered_cannot_change_order(
    qtbot, tmp_path: Path
) -> None:
    project, window, list_id, ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    expected = [ids["A.jpg"], ids["B.jpg"], ids["C.png"], ids["D.mp4"]]
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(1))
    for action in _reorder_actions(window):
        action.trigger()
    assert window.list_service.ordered_media_ids(list_id) == expected
    project.close()


def test_scan_failure_restores_order_status(qtbot, tmp_path: Path, monkeypatch) -> None:
    """The failure path also resets the status bar, so it must agree with the locks."""
    project, window, _list_id, _ids, _src1, _src2 = _filtered_list_window(
        qtbot, tmp_path
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.QMessageBox.warning",
        lambda *args, **kwargs: None,
    )
    window._on_scan_failed("boom")
    assert window.statusBar().currentMessage() == "List (manual order)"
    combo = window.library_panel.extension_combo
    combo.setCurrentIndex(combo.findData(".jpg"))
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 2, timeout=8000)
    window._on_scan_failed("boom")
    assert window.statusBar().currentMessage() == "名单（已筛选，排序已禁用）"
    project.close()
