from __future__ import annotations

from PySide6.QtGui import QUndoCommand, QUndoStack

from local_media_curator.domain.models import Project
from local_media_curator.services.list_service import ListService
from local_media_curator.services.rejection_service import RejectionService

__all__ = ["CurationUndoStack"]


class _SetCullingStateCommand(QUndoCommand):
    def __init__(
        self,
        rejection: RejectionService,
        before: dict[int, str],
        after: str,
    ) -> None:
        super().__init__(f"Set culling state: {after}")
        self._rejection = rejection
        self._before = dict(before)
        self._after = after
        self._media_ids = list(before)

    def redo(self) -> None:
        self._rejection.set_state(self._media_ids, self._after)

    def undo(self) -> None:
        self._rejection.restore_states(self._before)


class _ReorderCommand(QUndoCommand):
    def __init__(
        self,
        lists: ListService,
        list_id: int,
        media_ids_in_order: list[int],
    ) -> None:
        super().__init__("Reorder list")
        self._lists = lists
        self._list_id = list_id
        self._media_ids_in_order = list(media_ids_in_order)
        self._before = lists.items_with_sort_keys(list_id)
        self._after: list[tuple[int, int]] | None = None

    def redo(self) -> None:
        if self._after is None:
            self._lists.reorder(self._list_id, self._media_ids_in_order)
            self._after = self._lists.items_with_sort_keys(self._list_id)
            return
        self._lists.restore_sort_keys(self._list_id, self._after)

    def undo(self) -> None:
        self._lists.restore_sort_keys(self._list_id, self._before)


class _MoveSelectionCommand(QUndoCommand):
    def __init__(
        self,
        lists: ListService,
        list_id: int,
        media_ids: list[int],
        delta: int,
    ) -> None:
        super().__init__("Move selection")
        self._lists = lists
        self._list_id = list_id
        self._media_ids = list(media_ids)
        self._delta = delta
        self._before = lists.items_with_sort_keys(list_id)
        self._after: list[tuple[int, int]] | None = None

    def redo(self) -> None:
        if self._after is None:
            self._lists.move_selection(self._list_id, self._media_ids, self._delta)
            self._after = self._lists.items_with_sort_keys(self._list_id)
            return
        self._lists.restore_sort_keys(self._list_id, self._after)

    def undo(self) -> None:
        self._lists.restore_sort_keys(self._list_id, self._before)


class _MoveToEndsCommand(QUndoCommand):
    def __init__(
        self,
        lists: ListService,
        list_id: int,
        media_ids: list[int],
        *,
        end: bool,
    ) -> None:
        super().__init__("Move to end" if end else "Move to start")
        self._lists = lists
        self._list_id = list_id
        self._media_ids = list(media_ids)
        self._end = end
        self._before = lists.items_with_sort_keys(list_id)
        self._after: list[tuple[int, int]] | None = None

    def redo(self) -> None:
        if self._after is None:
            self._lists.move_to_ends(
                self._list_id, self._media_ids, end=self._end
            )
            self._after = self._lists.items_with_sort_keys(self._list_id)
            return
        self._lists.restore_sort_keys(self._list_id, self._after)

    def undo(self) -> None:
        self._lists.restore_sort_keys(self._list_id, self._before)


class _AddItemsCommand(QUndoCommand):
    def __init__(
        self, lists: ListService, list_id: int, media_ids: list[int]
    ) -> None:
        super().__init__("Add to list")
        self._lists = lists
        self._list_id = list_id
        self._new_ids = list(media_ids)
        self._rows: list[tuple[int, int, str]] = []

    def redo(self) -> None:
        if not self._rows:
            self._lists.add_items(self._list_id, self._new_ids)
            self._rows = self._lists.snapshot_items(self._list_id, self._new_ids)
            return
        self._lists.restore_item_rows(self._list_id, self._rows)

    def undo(self) -> None:
        self._lists.remove_items(self._list_id, self._new_ids)


class _RemoveItemsCommand(QUndoCommand):
    def __init__(
        self, lists: ListService, list_id: int, media_ids: list[int]
    ) -> None:
        super().__init__("Remove from list")
        self._lists = lists
        self._list_id = list_id
        self._rows = lists.snapshot_items(list_id, media_ids)
        self._media_ids = [media_id for media_id, _key, _added in self._rows]

    def redo(self) -> None:
        if self._media_ids:
            self._lists.remove_items(self._list_id, self._media_ids)

    def undo(self) -> None:
        if self._rows:
            self._lists.restore_item_rows(self._list_id, self._rows)


class CurationUndoStack:
    def __init__(self, project: Project) -> None:
        self._lists = ListService(project)
        self._rejection = RejectionService(project)
        self._stack = QUndoStack()

    def undo(self) -> None:
        self._stack.undo()

    def redo(self) -> None:
        self._stack.redo()

    def reject(self, media_ids: list[int]) -> None:
        self.set_culling_state(media_ids, "rejected")

    def restore(self, media_ids: list[int]) -> None:
        self.set_culling_state(media_ids, "undecided")

    def set_culling_state(self, media_ids: list[int], state: str) -> None:
        if state not in {"undecided", "picked", "rejected"}:
            raise ValueError(f"Invalid culling state: {state}")
        states = self._rejection.states(list(dict.fromkeys(media_ids)))
        before = {media_id: current for media_id, current in states.items() if current != state}
        if not before:
            return
        # A single command captures all selected rows, so bulk culling is one
        # undo unit even when the selection contains mixed prior states.
        self._stack.push(_SetCullingStateCommand(self._rejection, before, state))

    def reorder(self, list_id: int, media_ids_in_order: list[int]) -> None:
        self._stack.push(
            _ReorderCommand(self._lists, list_id, media_ids_in_order)
        )

    def move_selection(
        self, list_id: int, media_ids: list[int], delta: int
    ) -> None:
        if not media_ids or delta == 0:
            return
        self._stack.push(
            _MoveSelectionCommand(self._lists, list_id, media_ids, delta)
        )

    def move_to_ends(
        self, list_id: int, media_ids: list[int], *, end: bool
    ) -> None:
        if not media_ids:
            return
        self._stack.push(
            _MoveToEndsCommand(self._lists, list_id, media_ids, end=end)
        )

    def add_items(self, list_id: int, media_ids: list[int]) -> None:
        existing = set(self._lists.ordered_media_ids(list_id))
        new_ids = [media_id for media_id in media_ids if media_id not in existing]
        if not new_ids:
            return
        self._stack.push(_AddItemsCommand(self._lists, list_id, new_ids))

    def remove_items(self, list_id: int, media_ids: list[int]) -> None:
        rows = self._lists.snapshot_items(list_id, media_ids)
        if not rows:
            return
        self._stack.push(
            _RemoveItemsCommand(
                self._lists, list_id, [media_id for media_id, _key, _added in rows]
            )
        )
