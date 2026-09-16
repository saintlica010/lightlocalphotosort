from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMessageBox, QSplitter, QWidget

from local_media_curator.domain.models import Media, Project
from local_media_curator.media.thumbnail_service import ThumbnailService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project
from local_media_curator.services.rejection_service import RejectionService
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.dialogs import choose_existing_directory, choose_list_name
from local_media_curator.ui.library_panel import LibraryPanel
from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.preview_panel import PreviewPanel

_LIBRARY_VIEW_ROWS = {"all": 0, "unassigned": 1, "rejected": 2}


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self.library_service: LibraryService | None = None
        self.list_service: ListService | None = None
        self.rejection_service: RejectionService | None = None
        self.thumbnail_service: ThumbnailService | None = None
        self.undo_stack: CurationUndoStack | None = None
        self.list_name_picker: Callable[[list[str]], str | None] | None = None
        self._view_mode = "all"
        self._current_list_id: int | None = None

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.library_panel = LibraryPanel()
        self.media_grid = MediaGrid()
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.media_grid)
        splitter.addWidget(self.preview_panel)
        self.setCentralWidget(splitter)

        self._install_menus()
        self.media_grid.view.selectionModel().currentChanged.connect(
            self._on_media_current_changed
        )
        self.library_panel.view_changed.connect(self._on_library_view_changed)
        self.library_panel.list_panel.current_list_changed.connect(
            self._on_named_list_changed
        )
        self.library_panel.list_panel.create_requested.connect(self._on_create_list)
        self.library_panel.list_panel.rename_requested.connect(self._on_rename_list)
        self.library_panel.list_panel.delete_requested.connect(self._on_delete_list)
        self._set_project_actions_enabled(False)

    def set_undo_stack(self, stack: CurationUndoStack | None) -> None:
        self.undo_stack = stack

    def set_project(self, project: Project) -> None:
        previous = self.project
        self.project = project
        self.library_service = LibraryService(project)
        self.list_service = ListService(project)
        self.rejection_service = RejectionService(project)
        self.thumbnail_service = ThumbnailService(project)
        self.set_undo_stack(CurationUndoStack(project))
        self._view_mode = "all"
        self._current_list_id = None
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

    def scan(self) -> None:
        if self.library_service is None:
            return
        self.library_service.scan()
        self._ensure_thumbnails()
        self.refresh()

    def refresh(self) -> None:
        self._reload_lists()
        self._reload_grid()

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
        self.undo_stack.add_items(list_id, media_ids)
        self.refresh()

    def add_selection_to_list(self, list_id: int) -> None:
        self.add_items_to_list(list_id, self.media_grid.selected_ids())

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
        self.undo_stack.move_selection(self._current_list_id, media_ids, delta)
        self.refresh()
        self._select_media_ids(media_ids)

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
        self.undo_stack.move_to_ends(self._current_list_id, media_ids, end=end)
        self.refresh()
        self._select_media_ids(media_ids)

    def remove_selection_from_list(self, list_id: int) -> None:
        if self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        self.undo_stack.remove_items(list_id, media_ids)
        self.refresh()

    def reject_selection(self) -> None:
        if self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        self.undo_stack.reject(media_ids)
        self.refresh()

    def restore_selection(self) -> None:
        if self.undo_stack is None:
            return
        media_ids = self.media_grid.selected_ids()
        if not media_ids:
            return
        self.undo_stack.restore(media_ids)
        self.refresh()

    def _install_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        new_project = QAction("New Project", self)
        new_project.setShortcut(QKeySequence.StandardKey.New)
        new_project.triggered.connect(self._on_new_project)
        open_project_action = QAction("Open Project", self)
        open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        open_project_action.triggered.connect(self._on_open_project)
        self.add_source_action = QAction("Add Source Folder", self)
        self.add_source_action.triggered.connect(self._on_add_source_folder)
        self.scan_action = QAction("Scan", self)
        self.scan_action.setShortcut(QKeySequence(Qt.Key.Key_F5))
        self.scan_action.triggered.connect(self._on_scan)
        file_menu.addAction(new_project)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(self.add_source_action)
        file_menu.addAction(self.scan_action)

        undo = QAction("Undo", self)
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.triggered.connect(self._on_undo)
        redo = QAction("Redo", self)
        redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo.triggered.connect(self._on_redo)
        reject = QAction("Reject", self)
        reject.setShortcut(QKeySequence.StandardKey.Delete)
        reject.triggered.connect(self.reject_selection)
        restore = QAction("Restore", self)
        restore.triggered.connect(self.restore_selection)
        add_to_list = QAction("Add to List", self)
        add_to_list.triggered.connect(self._on_add_to_current_list)
        remove_from_list = QAction("Remove from List", self)
        remove_from_list.triggered.connect(self._on_remove_from_current_list)
        self.move_up_action = QAction("Move Up", self)
        self.move_up_action.setShortcuts(
            [QKeySequence("["), QKeySequence("Ctrl+Up")]
        )
        self.move_up_action.triggered.connect(lambda: self.move_selection(-1))
        self.move_down_action = QAction("Move Down", self)
        self.move_down_action.setShortcuts(
            [QKeySequence("]"), QKeySequence("Ctrl+Down")]
        )
        self.move_down_action.triggered.connect(lambda: self.move_selection(1))
        self.move_start_action = QAction("Move to Start", self)
        self.move_start_action.setShortcut(QKeySequence(Qt.Key.Key_Home))
        self.move_start_action.triggered.connect(
            lambda: self.move_to_ends(end=False)
        )
        self.move_end_action = QAction("Move to End", self)
        self.move_end_action.setShortcut(QKeySequence(Qt.Key.Key_End))
        self.move_end_action.triggered.connect(lambda: self.move_to_ends(end=True))
        self._set_reorder_actions_enabled(False)

        edit_menu = self.menuBar().addMenu("Edit")
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

    def _set_project_actions_enabled(self, enabled: bool) -> None:
        self.add_source_action.setEnabled(enabled)
        self.scan_action.setEnabled(enabled)

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
        for row in range(self.media_grid.model.rowCount()):
            index = self.media_grid.model.index(row)
            value = self.media_grid.model.data(index, MediaListModel.IdRole)
            if value is None or int(value) not in wanted:
                continue
            if first is None:
                first = index
                selection.select(index, selection.SelectionFlag.ClearAndSelect)
            else:
                selection.select(index, selection.SelectionFlag.Select)
        if first is not None:
            self.media_grid.view.setCurrentIndex(first)

    def _on_new_project(self) -> None:
        path = choose_existing_directory(self, "New Project")
        if path is None:
            return
        try:
            self.set_project(create_project(path))
        except ValueError as exc:
            QMessageBox.warning(self, "New Project", str(exc))

    def _on_open_project(self) -> None:
        path = choose_existing_directory(self, "Open Project")
        if path is None:
            return
        try:
            self.set_project(open_project(path))
        except FileNotFoundError:
            QMessageBox.warning(
                self, "Open Project", "No project found in that folder."
            )

    def _on_add_source_folder(self) -> None:
        if self.library_service is None:
            return
        path = choose_existing_directory(self, "Add Source Folder")
        if path is None:
            return
        self.add_source_folder(path)

    def _on_scan(self) -> None:
        self.scan()

    def _on_undo(self) -> None:
        if self.undo_stack is not None:
            self.undo_stack.undo()
            self.refresh()

    def _on_redo(self) -> None:
        if self.undo_stack is not None:
            self.undo_stack.redo()
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
            QMessageBox.warning(
                self, "New list", f'A list named "{name}" already exists.'
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
            QMessageBox.warning(
                self, "Rename list", f'A list named "{name}" already exists.'
            )
            return
        self._reload_lists()

    def _on_delete_list(self, list_id: int) -> None:
        if self.list_service is None:
            return
        self.list_service.delete(list_id)
        if self._current_list_id == list_id:
            self.show_library_view("all")
            return
        self.refresh()

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

    def _reload_grid(self) -> None:
        if self.library_service is None:
            self.media_grid.model.set_rows([])
            self.preview_panel.set_media(None)
            self.media_grid.set_manual_order_enabled(False)
            self._set_reorder_actions_enabled(False)
            return
        items = self._media_for_current_view()
        rows = [
            self._row_from_media(item, ordinal)
            for ordinal, item in enumerate(items, start=1)
        ]
        self.media_grid.model.set_rows(rows)
        list_mode = self._view_mode == "list"
        self.media_grid.set_manual_order_enabled(list_mode)
        self._set_reorder_actions_enabled(list_mode)
        current = self.media_grid.view.currentIndex()
        if current.isValid():
            self.preview_panel.set_media(self.media_grid.model.row_at(current.row()))
        else:
            self.preview_panel.set_media(None)

    def _media_for_current_view(self) -> list[Media]:
        assert self.library_service is not None
        if self._view_mode == "rejected":
            return self.library_service.list_media(
                include_rejected=True, rejected_only=True
            )
        if self._view_mode == "unassigned":
            return self.library_service.list_unassigned()
        if (
            self._view_mode == "list"
            and self._current_list_id is not None
            and self.list_service is not None
        ):
            media_ids = self.list_service.ordered_media_ids(self._current_list_id)
            return self.library_service.list_media_by_ids(media_ids)
        return self.library_service.list_media(include_rejected=False)

    def _row_from_media(self, media: Media, ordinal: int) -> dict[str, object]:
        lists = (
            self.list_service.list_names_for_media(media.id)
            if self.list_service is not None
            else []
        )
        return {
            "id": media.id,
            "file_name": media.file_name,
            "absolute_path": media.absolute_path,
            "rejected": media.rejected,
            "ordinal": ordinal,
            "thumbnail_path": self._thumbnail_path(media),
            "width": media.width,
            "height": media.height,
            "file_size": media.file_size,
            "captured_at": media.captured_at,
            "modified_at": media.modified_at,
            "lists": lists,
        }

    def _ensure_thumbnails(self) -> None:
        if self.library_service is None:
            return
        for media in self.library_service.list_media(include_rejected=True):
            self._thumbnail_path(media)

    def _thumbnail_path(self, media: Media) -> str | None:
        if self.thumbnail_service is None:
            return None
        if media.media_type != "image" or media.missing:
            return None
        path = Path(media.absolute_path)
        if not path.is_file():
            return None
        return str(self.thumbnail_service.ensure(media.id, path))

    def _on_media_current_changed(
        self, current: QModelIndex, _previous: QModelIndex
    ) -> None:
        if not current.isValid():
            self.preview_panel.set_media(None)
            return
        self.preview_panel.set_media(self.media_grid.model.row_at(current.row()))
