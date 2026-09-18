from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt, QThread, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTextEdit,
    QWidget,
)

from local_media_curator.domain.lightroom_smart_collection import (
    DUPLICATE_STEM_WARNING,
)
from local_media_curator.domain.models import Media, Project
from local_media_curator.media.scan_worker import ScanWorker
from local_media_curator.media.thumbnail_pool import ThumbnailPool
from local_media_curator.media.thumbnail_service import ThumbnailService
from local_media_curator.services.export_service import ExportService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project
from local_media_curator.services.rejection_service import RejectionService
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.dialogs import (
    ask_confirm,
    choose_existing_directory,
    choose_list_name,
    choose_open_file,
    choose_save_file,
    show_import_summary,
    show_warning,
)

_PORTABLE_LIST_FILTER = "可移植名单 (*.llplist.json)"
_CSV_FILTER = "CSV (*.csv)"
_TXT_FILTER = "文本文件 (*.txt)"
_LRSMCOL_FILTER = "Lightroom 智能收藏夹 (*.lrsmcol)"
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.preview_panel import PreviewPanel
from local_media_curator.ui.theme_prototype import open_theme_prototype

_LIBRARY_VIEW_ROWS = {
    "all": 0,
    "unassigned": 1,
    "picked": 2,
    "undecided": 3,
    "rejected": 4,
}
_SCAN_STOP_TIMEOUT_MS = 30000


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self.library_service: LibraryService | None = None
        self.list_service: ListService | None = None
        self.rejection_service: RejectionService | None = None
        self.thumbnail_service: ThumbnailService | None = None
        self.thumbnail_pool: ThumbnailPool | None = None
        self.undo_stack: CurationUndoStack | None = None
        self.list_name_picker: Callable[[list[str]], str | None] | None = None
        self.confirm_delete: Callable[[str], bool] | None = None
        self._view_mode = "all"
        self._current_list_id: int | None = None
        self._sort_by = "file_name"
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._thumb_needed: dict[int, str] = {}
        self._thumb_paths: dict[int, str] = {}
        self._pending_selection: list[int] = []
        self._target_id: int | None = None
        self.setWindowTitle("本地媒体整理")

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.library_panel = LibraryPanel()
        self.list_panel = self.library_panel.list_panel
        self.confirm_quick_rebind = None
        self.list_panel.bind_slot_requested.connect(self._on_bind_quick_slot)
        self.list_panel.unbind_slot_requested.connect(self._on_clear_quick_slot)
        self.list_panel.lightroom_export_requested.connect(self._on_export_lightroom)
        self.media_grid = MediaGrid()
        self.preview_panel = PreviewPanel()
        self.target_list_label = self.list_panel.target_label
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.media_grid)
        splitter.addWidget(self.preview_panel)
        self.setCentralWidget(splitter)

        self._install_menus()
        self.media_grid.view.selectionModel().currentChanged.connect(
            self._on_media_current_changed
        )
        self.media_grid.viewportRowsChanged.connect(self._on_viewport_rows_changed)
        self.library_panel.view_changed.connect(self._on_library_view_changed)
        self.library_panel.sort_changed.connect(self._on_library_sort_changed)
        self.library_panel.filters_changed.connect(self._on_filters_changed)
        self.library_panel.list_panel.current_list_changed.connect(
            self._on_named_list_changed
        )
        self.library_panel.list_panel.create_requested.connect(self._on_create_list)
        self.library_panel.list_panel.rename_requested.connect(self._on_rename_list)
        self.library_panel.list_panel.delete_requested.connect(self._on_delete_list)
        self.library_panel.list_panel.set_target_requested.connect(
            self._on_set_target_list
        )
        self.media_grid.model.orderChanged.connect(self.apply_grid_order)
        self._set_project_actions_enabled(False)

    def set_undo_stack(self, stack: CurationUndoStack | None) -> None:
        self.undo_stack = stack

    @property
    def target_list_id(self) -> int | None:
        return self._target_id

    def set_project(self, project: Project) -> None:
        self._stop_scan_thread()
        previous = self.project
        self.project = project
        self.library_service = LibraryService(project)
        self.list_service = ListService(project)
        self.rejection_service = RejectionService(project)
        self.thumbnail_service = ThumbnailService(project)
        self._replace_thumbnail_pool(project)
        self.set_undo_stack(CurationUndoStack(project))
        self._view_mode = "all"
        self._current_list_id = None
        self._sort_by = self.library_panel.current_sort()
        self._thumb_paths = {}
        self._pending_selection = []
        if previous is not None and previous is not project:
            previous.close()
        self._set_project_actions_enabled(True)
        views = self.library_panel.views
        views.blockSignals(True)
        views.setCurrentRow(0)
        views.blockSignals(False)
        self.refresh()

    def add_source_folder(self, path: Path) -> None:
        if self.library_service is None:
            return
        self.library_service.add_source_folder(path)

    def remove_source_folder(self, path: Path) -> None:
        if self.library_service is None:
            return
        self.library_service.remove_source_folder(path)

    def scan(self) -> None:
        if self.project is None:
            return
        if self._scan_thread is not None and self._scan_thread.isRunning():
            return
        self._stop_scan_thread()
        db_path = str(self.project.db_path)
        worker = ScanWorker()
        thread = QThread(self)
        worker.moveToThread(thread)
        # Direct: a receiverless lambda is bound to the *sender's* thread
        # affinity (this window), which would queue run() back onto the GUI
        # thread and block it for the whole scan.
        thread.started.connect(
            lambda: worker.run(db_path), Qt.ConnectionType.DirectConnection
        )
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.cancelled.connect(self._on_scan_cancelled)
        worker.progress.connect(self._on_scan_progress, Qt.ConnectionType.QueuedConnection)
        self._scan_worker = worker
        self._scan_thread = thread
        self.statusBar().showMessage("正在扫描…")
        thread.start()

    @Slot(int)
    def _on_scan_progress(self, count: int) -> None:
        if self._scan_worker is None or self.sender() is not self._scan_worker:
            return
        self.statusBar().showMessage(f"正在扫描… 已处理 {count:,} 个文件")

    def _on_scan_finished(self, _result: object) -> None:
        self._stop_scan_thread()
        # Drop cached thumb paths so workers re-ensure() after scan may have
        # refreshed source mtime/size; disk cache still hits off the GUI thread.
        self._thumb_paths.clear()
        self.refresh()

    def _on_scan_cancelled(self) -> None:
        if self._scan_thread is None:
            # Cancellation was requested by _stop_scan_thread(), which already
            # stopped the thread and cleaned up. This delivery is the leftover
            # queued signal, and refreshing here would touch a project the
            # window may not own any more.
            return
        self._stop_scan_thread()
        self._thumb_paths.clear()
        self.refresh()

    def _on_scan_failed(self, message: str) -> None:
        self._stop_scan_thread()
        self._set_order_status()
        show_warning(self, "扫描", message)

    def _stop_scan_thread(self) -> None:
        thread = self._scan_thread
        worker = self._scan_worker
        if thread is None:
            self._scan_worker = None
            return
        if worker is not None:
            for signal, slot in (
                (worker.finished, self._on_scan_finished),
                (worker.failed, self._on_scan_failed),
                (worker.cancelled, self._on_scan_cancelled),
                (worker.progress, self._on_scan_progress),
            ):
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
            worker.cancel()
        if thread.isRunning():
            thread.quit()
            thread.wait(_SCAN_STOP_TIMEOUT_MS)
        if thread.isRunning():
            # Still winding down: keep both references so the live thread is
            # never leaked, and never force it with QThread.terminate().
            return
        self._scan_thread = None
        self._scan_worker = None
        if worker is not None:
            worker.deleteLater()
        thread.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_scan_thread()
        super().closeEvent(event)

    def refresh(self) -> None:
        self._reload_lists()
        if self.library_service is None:
            self.library_panel.set_culling_counts({})
        else:
            self.library_panel.set_culling_counts(
                self.library_service.culling_counts()
            )
        self._reload_grid()

    def _run_curation(self, action: Callable[[], None]) -> bool:
        try:
            action()
            return True
        except sqlite3.OperationalError:
            self.statusBar().showMessage("数据库忙，请重试。")
            return False

    def show_library_view(self, name: str) -> None:
        self._view_mode = name
        self._current_list_id = None
        self._sync_library_selection(name)
        self._reload_grid()

    def show_list(self, list_id: int) -> None:
        self._view_mode = "list"
        self._current_list_id = list_id
        self._sync_named_list_selection(list_id)
        self._reload_grid()

    def add_items_to_list(self, list_id: int, media_ids: list[int]) -> None:
        if self.undo_stack is None or not media_ids:
            return
        if not self._run_curation(
            lambda: self.undo_stack.add_items(list_id, media_ids)
        ):
            return
        self.refresh()

    def add_selection_to_list(self, list_id: int) -> None:
        self.add_items_to_list(list_id, self.media_grid.selected_ids())

    def add_selection_to_quick_slot(self, slot: int) -> None:
        if not self._curation_shortcut_allowed():
            return
        if self.list_service is None or self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        list_id = self.list_service.ensure_quick_slot(slot)
        self.add_items_to_list(list_id, media_ids)

    def add_selection_to_quick_slot_and_advance(self, slot: int) -> None:
        if not self._curation_shortcut_allowed():
            return
        if self.list_service is None or self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        visible_ids = self._visible_media_ids()
        advance_to = self._next_visible_id(visible_ids, media_ids)
        list_id = self.list_service.ensure_quick_slot(slot)
        existing = set(self.list_service.ordered_media_ids(list_id))
        missing = [media_id for media_id in media_ids if media_id not in existing]
        if missing and not self._run_curation(
            lambda: self.undo_stack.add_items(list_id, missing)
        ):
            return
        self._refresh_after_curation(advance_to)

    def _on_bind_quick_slot(self, list_id: int, slot: int) -> None:
        if self.list_service is None:
            return
        current = self.list_service.quick_slot_list_id(slot)
        if current == list_id:
            return
        if current is not None:
            text = (
                f"快捷键 {slot} 当前绑定到：\n"
                f"{self._list_name(current)}\n\n"
                f"是否改为：\n"
                f"{self._list_name(list_id)}"
            )
            confirmed = (
                self.confirm_quick_rebind(text)
                if self.confirm_quick_rebind is not None
                else ask_confirm(self, "绑定快捷键", text)
            )
            if not confirmed:
                return
        self.list_service.bind_quick_slot(slot, list_id)
        self.refresh()

    def _on_clear_quick_slot(self, list_id: int) -> None:
        if self.list_service is None:
            return
        self.list_service.clear_quick_slot_for_list(list_id)
        self.refresh()

    def _list_name(self, list_id: int) -> str:
        if self.list_service is None:
            return ""
        for row in self.list_service.all_lists():
            if int(row["id"]) == list_id:
                return str(row["name"])
        return ""

    def move_selection(self, delta: int) -> None:
        if (
            self.undo_stack is None
            or self._view_mode != "list"
            or self._current_list_id is None
        ):
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        if not self._run_curation(
            lambda: self.undo_stack.move_selection(
                self._current_list_id, media_ids, delta
            )
        ):
            return
        self.refresh()
        self._select_media_ids(media_ids)

    def apply_grid_order(
        self, ids: list[int], moved_ids: list[int] | None = None
    ) -> None:
        if (
            self.undo_stack is None
            or self._view_mode != "list"
            or self._current_list_id is None
            or not ids
        ):
            return
        current = (
            self.list_service.ordered_media_ids(self._current_list_id)
            if self.list_service is not None
            else []
        )
        ordered = [int(media_id) for media_id in ids]
        if ordered == current:
            return
        source_ids = (
            moved_ids
            if moved_ids is not None
            else self.media_grid.selected_ids()
        )
        previously_selected = {int(media_id) for media_id in source_ids}
        to_select = [
            media_id for media_id in ordered if media_id in previously_selected
        ]
        if not self._run_curation(
            lambda: self.undo_stack.reorder(self._current_list_id, ordered)
        ):
            return
        self.refresh()
        self._select_media_ids(to_select)

    def move_to_ends(self, *, end: bool) -> None:
        if (
            self.undo_stack is None
            or self._view_mode != "list"
            or self._current_list_id is None
        ):
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        if not self._run_curation(
            lambda: self.undo_stack.move_to_ends(
                self._current_list_id, media_ids, end=end
            )
        ):
            return
        self.refresh()
        self._select_media_ids(media_ids)

    def remove_selection_from_list(self, list_id: int) -> None:
        if self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        if not self._run_curation(
            lambda: self.undo_stack.remove_items(list_id, media_ids)
        ):
            return
        self.refresh()

    def reject_selection(self) -> None:
        if not self._curation_shortcut_allowed():
            return
        if self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        self.set_culling_state("rejected", media_ids)

    def reject_selection_and_advance(self) -> None:
        if not self._curation_shortcut_allowed():
            return
        self.set_culling_state("rejected", advance=True)

    def pick_selection(self, advance: bool = False) -> None:
        if not self._curation_shortcut_allowed():
            return
        self.set_culling_state("picked", advance=advance)

    def undecide_selection(self, advance: bool = False) -> None:
        if not self._curation_shortcut_allowed():
            return
        self.set_culling_state("undecided", advance=advance)

    def set_culling_state(
        self,
        state: str,
        media_ids: list[int] | None = None,
        *,
        advance: bool = False,
    ) -> None:
        if self.undo_stack is None:
            return
        ids = media_ids if media_ids is not None else self.media_grid.selected_ids()
        if not ids and media_ids is None:
            # A non-advance action can hide the current item (for example X in
            # the default library view). Keep P/X/U able to operate on that
            # pending selection so the next key can restore or reclassify it.
            ids = list(self._pending_selection)
        if not ids:
            return
        visible_ids = self._visible_media_ids() if advance else []
        advance_to = self._next_visible_id(visible_ids, ids) if advance else None
        if state == "rejected":
            operation = lambda: self.undo_stack.reject(ids)
        else:
            operation = lambda: self.undo_stack.set_culling_state(ids, state)
        if not self._run_curation(operation):
            return
        self._refresh_after_curation(advance_to if advance else None)

    def _refresh_after_curation(self, advance_to: int | None) -> None:
        if advance_to is None:
            self.refresh()
            return
        # Do not let _reload_grid restore the just-acted-on selection or leave
        # it in _pending_selection when the action removes it from the view.
        selection = self.media_grid.view.selectionModel()
        if selection is not None:
            selection.clearSelection()
            selection.clearCurrentIndex()
        self._pending_selection = []
        self.refresh()
        if advance_to in self._visible_media_ids():
            self._select_media_ids([advance_to])

    def _visible_media_ids(self) -> list[int]:
        ids: list[int] = []
        model = self.media_grid.model
        for row in range(model.rowCount()):
            value = model.data(model.index(row), MediaListModel.IdRole)
            if value is not None:
                ids.append(int(value))
        return ids

    def _next_visible_id(
        self, visible_ids: list[int], selected_ids: list[int]
    ) -> int | None:
        if not visible_ids:
            return None
        selected_positions = [
            index
            for index, media_id in enumerate(visible_ids)
            if media_id in selected_ids
        ]
        if not selected_positions:
            current = self.media_grid.view.currentIndex()
            anchor = current.row() if current.isValid() else -1
        else:
            # For a multi-selection, continue after the last selected visible
            # item while preserving the view's existing order.
            anchor = max(selected_positions)
        return visible_ids[anchor + 1] if anchor + 1 < len(visible_ids) else None

    def restore_selection(self) -> None:
        self.undecide_selection()

    def _curation_shortcut_allowed(self) -> bool:
        """Keep single-letter curation keys inside text editors harmless."""
        widget = QApplication.focusWidget()
        while widget is not None:
            if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QInputDialog)):
                return False
            if isinstance(widget, QComboBox) and widget.isEditable():
                return False
            widget = widget.parentWidget()
        return True

    def _target_list_from_settings(self) -> int | None:
        if self.list_service is None:
            return None
        return self.list_service.target_list_id()

    def _target_list_name(self, list_id: int | None) -> str | None:
        if list_id is None or self.list_service is None:
            return None
        return next(
            (
                str(row["name"])
                for row in self.list_service.all_lists()
                if int(row["id"]) == list_id
            ),
            None,
        )

    def _refresh_target_indicator(self) -> None:
        target_id = self._target_list_from_settings()
        self._target_id = target_id
        self.library_panel.list_panel.set_target_list(self._target_list_name(target_id))

    def _on_set_target_list(self, list_id: object = None) -> None:
        if self.list_service is None:
            return
        selected_id = int(list_id) if list_id is not None else self._target_list_id()
        if selected_id is None:
            selected_id = self._choose_list_id()
        if selected_id is None:
            return
        try:
            self.list_service.set_target_list(selected_id)
        except ValueError as exc:
            show_warning(self, "设置目标名单", str(exc))
            return
        self._refresh_target_indicator()

    def set_target_list(self, list_id: int) -> None:
        self._on_set_target_list(list_id)

    def toggle_target_selection(self) -> None:
        if not self._curation_shortcut_allowed():
            return
        target_id = self._target_list_from_settings()
        if target_id is None:
            self.statusBar().showMessage("请先设置目标名单。")
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids or self.undo_stack is None:
            return
        existing = set(self.list_service.ordered_media_ids(target_id))
        if set(media_ids).issubset(existing):
            operation = lambda: self.undo_stack.remove_items(target_id, media_ids)
        else:
            missing = [media_id for media_id in media_ids if media_id not in existing]
            operation = lambda: self.undo_stack.add_items(target_id, missing)
        if self._run_curation(operation):
            self.refresh()

    def add_to_target_and_advance(self) -> None:
        if not self._curation_shortcut_allowed():
            return
        target_id = self._target_list_from_settings()
        if target_id is None:
            self.statusBar().showMessage("请先设置目标名单。")
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids or self.undo_stack is None:
            return
        visible_ids = self._visible_media_ids()
        advance_to = self._next_visible_id(visible_ids, media_ids)
        existing = set(self.list_service.ordered_media_ids(target_id))
        missing = [media_id for media_id in media_ids if media_id not in existing]
        if missing and not self._run_curation(
            lambda: self.undo_stack.add_items(target_id, missing)
        ):
            return
        self._refresh_after_curation(advance_to)

    def _install_menus(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        new_project = QAction("新建项目", self)
        new_project.setShortcut(QKeySequence.StandardKey.New)
        new_project.triggered.connect(self._on_new_project)
        open_project_action = QAction("打开项目", self)
        open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        open_project_action.triggered.connect(self._on_open_project)
        self.add_source_action = QAction("添加源文件夹", self)
        self.add_source_action.triggered.connect(self._on_add_source_folder)
        self.remove_source_action = QAction("移除源文件夹", self)
        self.remove_source_action.triggered.connect(self._on_remove_source_folder)
        self.scan_action = QAction("扫描", self)
        self.scan_action.setShortcut(QKeySequence(Qt.Key.Key_F5))
        self.scan_action.triggered.connect(self._on_scan)
        self.open_original_action = QAction("打开原文件", self)
        self.open_original_action.triggered.connect(self._on_open_original)
        self.export_list_action = QAction("导出名单...", self)
        self.export_list_action.triggered.connect(self._on_export_list)
        self.import_list_action = QAction("导入名单...", self)
        self.import_list_action.triggered.connect(self._on_import_list)
        self.export_csv_action = QAction("导出 CSV...", self)
        self.export_csv_action.triggered.connect(self._on_export_csv)
        self.export_txt_action = QAction("导出 TXT...", self)
        self.export_txt_action.triggered.connect(self._on_export_txt)
        self.export_lightroom_action = QAction(
            "导出 Lightroom 智能收藏夹（实验性）...", self
        )
        self.export_lightroom_action.triggered.connect(
            lambda _checked=False: self._on_export_lightroom()
        )
        self.copy_file_names_action = QAction("复制文件名", self)
        self.copy_file_names_action.triggered.connect(self._on_copy_file_names)
        self.copy_absolute_paths_action = QAction("复制绝对路径", self)
        self.copy_absolute_paths_action.triggered.connect(
            self._on_copy_absolute_paths
        )
        self.copy_relative_paths_action = QAction("复制相对路径", self)
        self.copy_relative_paths_action.triggered.connect(
            self._on_copy_relative_paths
        )
        file_menu.addAction(new_project)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(self.add_source_action)
        file_menu.addAction(self.remove_source_action)
        file_menu.addAction(self.scan_action)
        file_menu.addAction(self.open_original_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_list_action)
        file_menu.addAction(self.import_list_action)
        file_menu.addAction(self.export_csv_action)
        file_menu.addAction(self.export_txt_action)
        file_menu.addAction(self.export_lightroom_action)
        file_menu.addSeparator()
        file_menu.addAction(self.copy_file_names_action)
        file_menu.addAction(self.copy_absolute_paths_action)
        file_menu.addAction(self.copy_relative_paths_action)

        undo = QAction("撤销", self)
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.triggered.connect(self._on_undo)
        redo = QAction("重做", self)
        redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo.triggered.connect(self._on_redo)
        reject = QAction("排除", self)
        reject.setShortcut(QKeySequence.StandardKey.Delete)
        reject.triggered.connect(self.reject_selection)
        restore = QAction("恢复", self)
        restore.triggered.connect(self.restore_selection)
        add_to_list = QAction("添加到名单", self)
        add_to_list.triggered.connect(self._on_add_to_current_list)
        remove_from_list = QAction("从名单移除", self)
        remove_from_list.triggered.connect(self._on_remove_from_current_list)
        self.move_up_action = QAction("上移", self)
        self.move_up_action.setShortcuts(
            [QKeySequence("["), QKeySequence("Ctrl+Up")]
        )
        self.move_up_action.triggered.connect(lambda: self.move_selection(-1))
        self.move_down_action = QAction("下移", self)
        self.move_down_action.setShortcuts(
            [QKeySequence("]"), QKeySequence("Ctrl+Down")]
        )
        self.move_down_action.triggered.connect(lambda: self.move_selection(1))
        self.move_start_action = QAction("移到开头", self)
        self.move_start_action.setShortcut(QKeySequence(Qt.Key.Key_Home))
        self.move_start_action.triggered.connect(
            lambda: self.move_to_ends(end=False)
        )
        self.move_end_action = QAction("移到末尾", self)
        self.move_end_action.setShortcut(QKeySequence(Qt.Key.Key_End))
        self.move_end_action.triggered.connect(lambda: self.move_to_ends(end=True))
        self._set_reorder_actions_enabled(False)

        edit_menu = self.menuBar().addMenu("编辑")
        for action in (
            undo,
            redo,
            reject,
            restore,
            add_to_list,
            remove_from_list,
            self.move_up_action,
            self.move_down_action,
            self.move_start_action,
            self.move_end_action,
        ):
            self.addAction(action)
        edit_menu.addAction(undo)
        edit_menu.addAction(redo)
        edit_menu.addSeparator()
        edit_menu.addAction(reject)
        edit_menu.addAction(restore)
        edit_menu.addSeparator()
        edit_menu.addAction(add_to_list)
        edit_menu.addAction(remove_from_list)
        edit_menu.addSeparator()
        edit_menu.addAction(self.move_up_action)
        edit_menu.addAction(self.move_down_action)
        edit_menu.addAction(self.move_start_action)
        edit_menu.addAction(self.move_end_action)
        self.media_grid.view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.ActionsContextMenu
        )
        self.media_grid.view.addAction(reject)
        self.media_grid.view.addAction(restore)
        self.media_grid.view.addAction(add_to_list)
        self.media_grid.view.addAction(remove_from_list)

        self.pick_action = QAction("标记为已选", self)
        self.pick_action.setShortcut(QKeySequence("P"))
        self.pick_action.triggered.connect(self.pick_selection)
        self.culling_reject_action = QAction("标记为已排除", self)
        self.culling_reject_action.setShortcut(QKeySequence("X"))
        self.culling_reject_action.triggered.connect(self.reject_selection)
        self.undecide_action = QAction("标记为未决定", self)
        self.undecide_action.setShortcut(QKeySequence("U"))
        self.undecide_action.triggered.connect(self.undecide_selection)
        self.pick_and_advance_action = QAction("标记为已选并前进", self)
        self.pick_and_advance_action.setShortcut(QKeySequence("Shift+P"))
        self.pick_and_advance_action.triggered.connect(
            lambda _checked=False: self.pick_selection(advance=True)
        )
        self.culling_reject_and_advance_action = QAction(
            "标记为已排除并前进", self
        )
        self.culling_reject_and_advance_action.setShortcut(QKeySequence("Shift+X"))
        self.culling_reject_and_advance_action.triggered.connect(
            lambda _checked=False: self.reject_selection_and_advance()
        )
        self.undecide_and_advance_action = QAction("标记为未决定并前进", self)
        self.undecide_and_advance_action.setShortcut(QKeySequence("Shift+U"))
        self.undecide_and_advance_action.triggered.connect(
            lambda _checked=False: self.undecide_selection(advance=True)
        )
        self.shift_pick_action = self.pick_and_advance_action
        self.shift_reject_action = self.culling_reject_and_advance_action
        self.shift_undecide_action = self.undecide_and_advance_action
        self.set_target_list_action = QAction("设为目标名单", self)
        self.set_target_list_action.triggered.connect(
            lambda _checked=False: self._on_set_target_list()
        )
        self.target_toggle_action = QAction("在目标名单中切换", self)
        self.target_toggle_action.setShortcut(QKeySequence("B"))
        self.target_toggle_action.triggered.connect(
            lambda _checked=False: self.toggle_target_selection()
        )
        self.target_add_and_advance_action = QAction("加入目标名单并前进", self)
        self.target_add_and_advance_action.setShortcut(QKeySequence("Shift+B"))
        self.target_add_and_advance_action.triggered.connect(
            lambda _checked=False: self.add_to_target_and_advance()
        )
        self.set_target_action = self.set_target_list_action
        self.target_add_action = self.target_add_and_advance_action
        self.target_list_toggle_action = self.target_toggle_action
        self.target_list_add_action = self.target_add_and_advance_action
        for action in (
            self.pick_action,
            self.culling_reject_action,
            self.undecide_action,
            self.pick_and_advance_action,
            self.culling_reject_and_advance_action,
            self.undecide_and_advance_action,
            self.set_target_list_action,
            self.target_toggle_action,
            self.target_add_and_advance_action,
        ):
            self.addAction(action)
            edit_menu.addAction(action)
            self.media_grid.view.addAction(action)

        self.quick_slot_actions = []
        self.quick_slot_shift_actions = []
        for slot in range(1, 10):
            action = QAction(f"添加到快捷名单 {slot}", self)
            action.setShortcut(QKeySequence(str(slot)))
            action.triggered.connect(
                lambda _checked=False, slot=slot: self.add_selection_to_quick_slot(slot)
            )
            shift = QAction(f"添加到快捷名单并前进 {slot}", self)
            shift.setShortcut(QKeySequence(f"Shift+{slot}"))
            shift.triggered.connect(
                lambda _checked=False, slot=slot: self.add_selection_to_quick_slot_and_advance(
                    slot
                )
            )
            for item in (action, shift):
                self.addAction(item)
                edit_menu.addAction(item)
            self.quick_slot_actions.append(action)
            self.quick_slot_shift_actions.append(shift)

        self.theme_prototype_action = QAction("设计样板...", self)
        self.theme_prototype_action.triggered.connect(
            lambda _checked=False: open_theme_prototype(self)
        )
        edit_menu.addSeparator()
        edit_menu.addAction(self.theme_prototype_action)

    def _set_project_actions_enabled(self, enabled: bool) -> None:
        self.add_source_action.setEnabled(enabled)
        self.remove_source_action.setEnabled(enabled)
        self.scan_action.setEnabled(enabled)
        self.export_list_action.setEnabled(enabled)
        self.import_list_action.setEnabled(enabled)
        self.export_csv_action.setEnabled(enabled)
        self.export_txt_action.setEnabled(enabled)
        self.export_lightroom_action.setEnabled(enabled)
        self.copy_file_names_action.setEnabled(enabled)
        self.copy_absolute_paths_action.setEnabled(enabled)
        self.copy_relative_paths_action.setEnabled(enabled)
        for action in (
            getattr(self, "pick_action", None),
            getattr(self, "culling_reject_action", None),
            getattr(self, "undecide_action", None),
            getattr(self, "pick_and_advance_action", None),
            getattr(self, "culling_reject_and_advance_action", None),
            getattr(self, "undecide_and_advance_action", None),
            getattr(self, "set_target_list_action", None),
            getattr(self, "target_toggle_action", None),
            getattr(self, "target_add_and_advance_action", None),
        ):
            if action is not None:
                action.setEnabled(enabled)
        for action in getattr(self, "quick_slot_actions", ()):
            action.setEnabled(enabled)
        for action in getattr(self, "quick_slot_shift_actions", ()):
            action.setEnabled(enabled)

    def _set_reorder_actions_enabled(self, enabled: bool) -> None:
        self.move_up_action.setEnabled(enabled)
        self.move_down_action.setEnabled(enabled)
        self.move_start_action.setEnabled(enabled)
        self.move_end_action.setEnabled(enabled)

    def _select_media_ids(self, media_ids: list[int]) -> None:
        selection = self.media_grid.view.selectionModel()
        if selection is None or not media_ids:
            return
        wanted = set(media_ids)
        selection.clearSelection()
        first = None
        indexes = []
        for row in range(self.media_grid.model.rowCount()):
            index = self.media_grid.model.index(row)
            value = self.media_grid.model.data(index, MediaListModel.IdRole)
            if value is None or int(value) not in wanted:
                continue
            if first is None:
                first = index
            indexes.append(index)
        # Select every matching index before setting the current index. Using
        # the view's setCurrentIndex last can apply its default selection
        # command and collapse a multi-selection on some Qt platforms.
        for index in indexes:
            selection.select(index, selection.SelectionFlag.Select)
        if first is not None:
            selection.setCurrentIndex(first, selection.SelectionFlag.NoUpdate)

    def _on_new_project(self) -> None:
        path = choose_existing_directory(self, "新建项目")
        if path is None:
            return
        try:
            self.set_project(create_project(path))
        except ValueError as exc:
            show_warning(self, "新建项目", str(exc))

    def _on_open_project(self) -> None:
        path = choose_existing_directory(self, "打开项目")
        if path is None:
            return
        try:
            self.set_project(open_project(path))
        except FileNotFoundError:
            show_warning(
                self, "打开项目", "该文件夹中没有找到项目。"
            )
        except ValueError as exc:
            show_warning(self, "打开项目", str(exc))

    def _on_add_source_folder(self) -> None:
        if self.library_service is None:
            return
        path = choose_existing_directory(self, "添加源文件夹")
        if path is None:
            return
        try:
            self.add_source_folder(path)
        except ValueError as exc:
            show_warning(self, "添加源文件夹", str(exc))

    def _on_remove_source_folder(self) -> None:
        if self.library_service is None:
            return
        path = choose_existing_directory(self, "移除源文件夹")
        if path is None:
            return
        self.remove_source_folder(path)

    def _on_library_sort_changed(self, sort_by: str) -> None:
        self._sort_by = sort_by
        self._reload_grid()

    def _on_filters_changed(self) -> None:
        self._reload_grid()

    def _current_filters(self) -> dict[str, object]:
        return self.library_panel.current_filters()

    def _on_scan(self) -> None:
        self.scan()

    def _on_open_original(self) -> None:
        self.preview_panel.open_original()

    def _resolve_export_list(
        self, title: str, action: str = "导出"
    ) -> tuple[int, str] | None:
        if self.project is None or self.list_service is None:
            return None
        list_id = self.list_panel.selected_list_id()
        list_name: str | None = None
        if list_id is not None:
            list_name = next(
                (
                    str(row["name"])
                    for row in self.list_service.all_lists()
                    if int(row["id"]) == list_id
                ),
                None,
            )
        if list_id is None or list_name is None:
            rows = self.list_service.all_lists()
            if not rows:
                show_warning(self, f"无法{action}", f"没有可{action}的名单。")
                return None
            chosen = choose_list_name(
                self, [str(row["name"]) for row in rows], title=title
            )
            if not chosen:
                return None
            match = next(
                (row for row in rows if str(row["name"]) == chosen), None
            )
            if match is None:
                return None
            list_id = int(match["id"])
            list_name = str(match["name"])
        return list_id, list_name

    def _on_export_list(self) -> None:
        if self.project is None:
            return
        resolved = self._resolve_export_list("导出名单")
        if resolved is None:
            return
        list_id, list_name = resolved
        destination = choose_save_file(
            self,
            "导出名单",
            _PORTABLE_LIST_FILTER,
            default_name=f"{list_name}.llplist.json",
        )
        if destination is None:
            return
        try:
            ExportService(self.project).export_list(list_id, destination)
        except ValueError as exc:
            show_warning(self, "无法导出", str(exc))

    def _on_export_lightroom(self, list_id: int | None = None) -> None:
        if self.project is None or self.list_service is None:
            return
        if list_id is None:
            resolved = self._resolve_export_list("导出 Lightroom 智能收藏夹（实验性）")
            if resolved is None:
                return
            list_id, list_name = resolved
        else:
            match = next(
                (
                    row
                    for row in self.list_service.all_lists()
                    if int(row["id"]) == int(list_id)
                ),
                None,
            )
            if match is None:
                show_warning(self, "无法导出", "名单不存在。")
                return
            list_name = str(match["name"])
            list_id = int(list_id)
        show_warning(self, "Lightroom 智能收藏夹导出（实验性）", DUPLICATE_STEM_WARNING)
        destination = choose_save_file(
            self,
            "导出 Lightroom 智能收藏夹（实验性）",
            _LRSMCOL_FILTER,
            default_name=f"{list_name}.lrsmcol",
        )
        if destination is None:
            return
        try:
            ExportService(self.project).export_lightroom_smart_collection(
                list_id, destination
            )
        except ValueError as exc:
            show_warning(self, "无法导出", str(exc))

    def _on_export_csv(self) -> None:
        if self.project is None:
            return
        resolved = self._resolve_export_list("导出 CSV")
        if resolved is None:
            return
        list_id, list_name = resolved
        destination = choose_save_file(
            self,
            "导出 CSV",
            _CSV_FILTER,
            default_name=f"{list_name}.csv",
        )
        if destination is None:
            return
        try:
            ExportService(self.project).export_csv(list_id, destination)
        except ValueError as exc:
            show_warning(self, "无法导出", str(exc))

    def _on_export_txt(self) -> None:
        if self.project is None:
            return
        resolved = self._resolve_export_list("导出 TXT")
        if resolved is None:
            return
        list_id, list_name = resolved
        destination = choose_save_file(
            self,
            "导出 TXT",
            _TXT_FILTER,
            default_name=f"{list_name}.txt",
        )
        if destination is None:
            return
        try:
            ExportService(self.project).export_txt(list_id, destination)
        except ValueError as exc:
            show_warning(self, "无法导出", str(exc))

    def _copy_list_text(self, title: str, builder: Callable[[object, int], str]) -> None:
        if self.project is None:
            return
        resolved = self._resolve_export_list(title, action="复制")
        if resolved is None:
            return
        list_id, _name = resolved
        try:
            text = builder(ExportService(self.project), list_id)
        except ValueError as exc:
            show_warning(self, "无法复制", str(exc))
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    def _on_copy_file_names(self) -> None:
        self._copy_list_text("复制文件名", ExportService.clipboard_file_names)

    def _on_copy_absolute_paths(self) -> None:
        self._copy_list_text(
            "复制绝对路径", ExportService.clipboard_absolute_paths
        )

    def _on_copy_relative_paths(self) -> None:
        self._copy_list_text(
            "复制相对路径", ExportService.clipboard_relative_paths
        )

    def _named_list_has_items(self, name: str) -> bool:
        if self.list_service is None:
            return False
        row = next(
            (
                item
                for item in self.list_service.all_lists()
                if str(item["name"]) == name
            ),
            None,
        )
        if row is None:
            return False
        return self.list_service.count(int(row["id"])) > 0

    def _on_import_list(self) -> None:
        if self.project is None:
            return
        path = choose_open_file(self, "导入名单", _PORTABLE_LIST_FILTER)
        if path is None:
            return
        service = ExportService(self.project)
        try:
            match = service.match_list(path)
            if self._named_list_has_items(match.name):
                if not ask_confirm(
                    self,
                    "导入名单",
                    f"导入将替换名单「{match.name}」中的现有项目。继续？",
                ):
                    return
            remaps: dict[str, Path] = {}
            if match.missing or match.ambiguous:
                for source in sorted(
                    {
                        item.source
                        for item in (*match.missing, *match.ambiguous)
                    }
                ):
                    chosen = choose_existing_directory(
                        self, f"为源 {source} 选择新根目录"
                    )
                    if chosen is None:
                        # Any remap dialog cancelled aborts the whole import:
                        # a partial match must never wipe an existing list.
                        self.statusBar().showMessage("已取消导入")
                        return
                    remaps[source] = chosen
            result = service.import_list(path, remaps=remaps or None)
        except ValueError as exc:
            show_warning(self, "无法导入", str(exc))
            return
        show_import_summary(
            self,
            matched=result.matched,
            missing=len(result.missing),
            ambiguous=len(result.ambiguous),
        )
        self.refresh()

    def _on_undo(self) -> None:
        if self.undo_stack is None:
            return
        if not self._run_curation(self.undo_stack.undo):
            return
        self.refresh()

    def _on_redo(self) -> None:
        if self.undo_stack is None:
            return
        if not self._run_curation(self.undo_stack.redo):
            return
        self.refresh()

    def _on_library_view_changed(self, name: str) -> None:
        self.show_library_view(name)

    def _on_named_list_changed(self, list_id: object) -> None:
        if list_id is None:
            return
        self.show_list(int(list_id))

    def _sync_library_selection(self, name: str) -> None:
        views = self.library_panel.views
        views.blockSignals(True)
        views.setCurrentRow(_LIBRARY_VIEW_ROWS[name])
        views.blockSignals(False)
        self._clear_named_list_selection()

    def _sync_named_list_selection(self, list_id: int) -> None:
        views = self.library_panel.views
        views.blockSignals(True)
        views.setCurrentRow(-1)
        views.clearSelection()
        views.blockSignals(False)
        lists_widget = self.library_panel.list_panel.lists_widget
        lists_widget.blockSignals(True)
        for row in range(lists_widget.count()):
            item = lists_widget.item(row)
            if item is not None and int(item.data(Qt.ItemDataRole.UserRole)) == list_id:
                lists_widget.setCurrentItem(item)
                break
        lists_widget.blockSignals(False)

    def _clear_named_list_selection(self) -> None:
        lists_widget = self.library_panel.list_panel.lists_widget
        lists_widget.blockSignals(True)
        lists_widget.setCurrentItem(None)
        lists_widget.clearSelection()
        lists_widget.blockSignals(False)

    def _on_create_list(self, name: str) -> None:
        if self.list_service is None:
            return
        try:
            list_id = self.list_service.create(name)
        except sqlite3.IntegrityError:
            show_warning(
                self, "新建名单", f'已存在名为"{name}"的名单。'
            )
            return
        self._reload_lists()
        self.show_list(list_id)

    def _on_rename_list(self, list_id: int, name: str) -> None:
        if self.list_service is None:
            return
        try:
            self.list_service.rename(list_id, name)
        except sqlite3.IntegrityError:
            show_warning(
                self, "重命名名单", f'已存在名为"{name}"的名单。'
            )
            return
        self._reload_lists()

    def _on_delete_list(self, list_id: int) -> None:
        if self.list_service is None:
            return
        name = next(
            (
                str(row["name"])
                for row in self.list_service.all_lists()
                if int(row["id"]) == list_id
            ),
            None,
        )
        if name is None:
            return
        confirmer = self.confirm_delete
        allowed = (
            confirmer(name)
            if confirmer is not None
            else self._confirm_delete_dialog(name)
        )
        if not allowed:
            return
        self.list_service.delete(list_id)
        if self._current_list_id == list_id:
            self.show_library_view("all")
            return
        self.refresh()

    def _confirm_delete_dialog(self, name: str) -> bool:
        return ask_confirm(
            self,
            "删除名单",
            f'确定删除名单"{name}"吗？原始媒体文件不会被删除。',
        )

    def _target_list_id(self) -> int | None:
        if self._current_list_id is not None:
            return self._current_list_id
        return self.library_panel.list_panel.selected_list_id()

    def _choose_list_id(self) -> int | None:
        if self.list_service is None:
            return None
        rows = self.list_service.all_lists()
        if not rows:
            return None
        names = [str(row["name"]) for row in rows]
        picker = self.list_name_picker
        chosen = picker(names) if picker is not None else choose_list_name(self, names)
        if not chosen:
            return None
        for row in rows:
            if str(row["name"]) == chosen:
                return int(row["id"])
        return None

    def _on_add_to_current_list(self) -> None:
        list_id = self._target_list_id()
        if list_id is None:
            list_id = self._choose_list_id()
        if list_id is None:
            return
        self.add_selection_to_list(list_id)

    def _on_remove_from_current_list(self) -> None:
        list_id = self._target_list_id()
        if list_id is None:
            return
        self.remove_selection_from_list(list_id)

    def _reload_lists(self) -> None:
        lists_widget = self.library_panel.list_panel.lists_widget
        lists_widget.blockSignals(True)
        if self.list_service is None:
            self.library_panel.list_panel.set_lists([])
        else:
            self.library_panel.list_panel.set_lists(self.list_service.all_lists())
        lists_widget.blockSignals(False)
        if self.library_service is not None:
            self.library_panel.set_source_folders(
                [str(row["path"]) for row in self.library_service._source_folders.list_enabled()]
            )
        self._refresh_target_indicator()

    def _reload_grid(self) -> None:
        if self.library_service is None:
            self._thumb_needed = {}
            self._pending_selection = []
            if self.thumbnail_pool is not None:
                self.thumbnail_pool.clear()
            self.media_grid.model.set_rows([])
            self.preview_panel.set_media(None)
            self.media_grid.set_manual_order_enabled(False)
            self._set_reorder_actions_enabled(False)
            self.statusBar().clearMessage()
            return
        selected = self.media_grid.selected_ids()
        current = self.media_grid.view.currentIndex()
        if current.isValid():
            value = self.media_grid.model.data(current, MediaListModel.IdRole)
            if value is not None:
                current_id = int(value)
                if current_id not in selected:
                    selected = [*selected, current_id]
        items = self._media_for_current_view()
        list_mode = self._view_mode == "list"
        media_ids = [item.id for item in items]
        present_ids = set(media_ids)
        names_by_id = (
            self.list_service.list_names_for_media_ids(media_ids)
            if self.list_service is not None
            else {}
        )
        slots_by_id = (
            self.list_service.quick_slots_for_media_ids(media_ids)
            if self.list_service is not None
            else {}
        )
        rows = [
            self._row_from_media(
                item,
                ordinal if list_mode else None,
                names_by_id.get(item.id, []),
                slots_by_id.get(item.id, []),
            )
            for ordinal, item in enumerate(items, start=1)
        ]
        jobs = self._thumbnail_jobs(items, rows)
        self._thumb_needed = {media_id: path for media_id, path in jobs}
        self.media_grid.model.set_rows(rows)
        reorder_enabled = list_mode and not self._filters_active()
        self.media_grid.set_manual_order_enabled(reorder_enabled)
        self._set_reorder_actions_enabled(reorder_enabled)
        self._set_order_status()
        self._sync_thumbnails()
        to_restore = selected if selected else self._pending_selection
        present = [media_id for media_id in to_restore if media_id in present_ids]
        if present:
            self._select_media_ids(present)
            self._pending_selection = []
        else:
            if selected:
                self._pending_selection = selected
            self.preview_panel.set_media(None)

    def _filters_active(self) -> bool:
        """True when any display filter is narrowing the current view.

        A filter can hide members of a manually ordered list, so reordering
        must be locked while one is active: reordering a filtered subset would
        otherwise move the hidden members too (AGENTS.md §20).
        """
        return any(value is not None for value in self._current_filters().values())

    def _set_order_status(self) -> None:
        """Show whether the view is sorted or manually ordered.

        Derives the state itself so a caller cannot pass a stale flag; the
        status must always agree with the reorder controls set alongside it.
        """
        if self._view_mode != "list":
            self.statusBar().showMessage("媒体库（自动排序）")
        elif self._filters_active():
            self.statusBar().showMessage("名单（已筛选，排序已禁用）")
        else:
            self.statusBar().showMessage("名单（手动排序）")

    def _media_for_current_view(self) -> list[Media]:
        assert self.library_service is not None
        filters = self._current_filters()
        media_type = filters["media_type"]
        extension = filters["extension"]
        source_folder = filters["source_folder"]
        missing = filters["missing"]
        if self._view_mode in {"picked", "undecided", "rejected"}:
            return self.library_service.list_media(
                include_rejected=True,
                culling_state=self._view_mode,
                sort_by=self._sort_by,
                media_type=media_type,
                extension=extension,
                source_folder=source_folder,
                missing=missing,
            )
        if self._view_mode == "unassigned":
            return self.library_service.list_unassigned(
                sort_by=self._sort_by,
                media_type=media_type,
                extension=extension,
                source_folder=source_folder,
                missing=missing,
            )
        if (
            self._view_mode == "list"
            and self._current_list_id is not None
            and self.list_service is not None
        ):
            media_ids = self.list_service.ordered_media_ids(self._current_list_id)
            items = self.library_service.list_media_by_ids(media_ids)
            return self.library_service.filter_media(
                items,
                media_type=media_type,
                extension=extension,
                source_folder=source_folder,
                missing=missing,
            )
        # The All view contains every culling state:
        # all = picked + undecided + rejected.
        return self.library_service.list_media(
            include_rejected=True,
            sort_by=self._sort_by,
            media_type=media_type,
            extension=extension,
            source_folder=source_folder,
            missing=missing,
        )

    def _row_from_media(
        self,
        media: Media,
        ordinal: int | None,
        lists: list[str],
        quick_slots: list[int] | None = None,
    ) -> dict[str, object]:
        return {
            "id": media.id,
            "file_name": media.file_name,
            "absolute_path": media.absolute_path,
            "culling_state": media.culling_state,
            "rejected": media.rejected,
            "ordinal": ordinal,
            "thumbnail_path": self._thumb_paths.get(media.id),
            "width": media.width,
            "height": media.height,
            "file_size": media.file_size,
            "captured_at": media.captured_at,
            "modified_at": media.modified_at,
            "lists": lists,
            "quick_slots": list(quick_slots or []),
        }

    def _replace_thumbnail_pool(self, project: Project) -> None:
        previous = self.thumbnail_pool
        if previous is not None:
            previous.ready.disconnect(self._on_thumbnail_ready)
            previous.clear()
            previous.deleteLater()
        pool = ThumbnailPool(project, parent=self)
        pool.ready.connect(self._on_thumbnail_ready)
        self.thumbnail_pool = pool

    def _thumbnail_jobs(
        self, items: list[Media], rows: list[dict[str, object]]
    ) -> list[tuple[int, str]]:
        jobs: list[tuple[int, str]] = []
        for media in items:
            if media.id in self._thumb_paths:
                continue
            if media.media_type != "image" or media.missing:
                continue
            jobs.append((media.id, media.absolute_path))
        return jobs

    def _on_thumbnail_ready(self, media_id: int, path: str) -> None:
        self._thumb_paths[int(media_id)] = path
        self._thumb_needed.pop(int(media_id), None)
        self.media_grid.model.set_thumbnail_path(int(media_id), path)

    def _on_viewport_rows_changed(self, _first: int, _last: int) -> None:
        self._sync_thumbnails()

    def _sync_thumbnails(self) -> None:
        if self.thumbnail_pool is None:
            return
        first, last = self.media_grid.visible_row_range()
        visible_ids: list[int] = []
        model = self.media_grid.model
        for row in range(first, last + 1):
            record = model.row_at(row)
            if record is None or record.get("thumbnail_path"):
                continue
            media_id = record.get("id")
            if media_id is None:
                continue
            visible_ids.append(int(media_id))
        self.thumbnail_pool.sync(self._thumb_needed, visible_ids)

    def _on_media_current_changed(
        self, current: QModelIndex, _previous: QModelIndex
    ) -> None:
        if not current.isValid():
            self.preview_panel.set_media(None)
            return
        self.preview_panel.set_media(self.media_grid.model.row_at(current.row()))
