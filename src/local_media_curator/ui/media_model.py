from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QMimeData,
    QModelIndex,
    Qt,
    Signal,
)

_MIME_TYPE = "application/x-local-media-curator-media-ids"


class MediaListModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    FileNameRole = Qt.ItemDataRole.UserRole + 2
    OrdinalRole = Qt.ItemDataRole.UserRole + 3
    RejectedRole = Qt.ItemDataRole.UserRole + 4
    ThumbnailPathRole = Qt.ItemDataRole.UserRole + 5
    orderChanged = Signal(list, list)

    def __init__(
        self,
        rows: Sequence[Mapping[str, object]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, object]] = [dict(row) for row in rows] if rows else []
        self._manual_order = False

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, self.FileNameRole):
            return row.get("file_name")
        if role == self.IdRole:
            return row.get("id")
        if role == self.OrdinalRole:
            return row.get("ordinal")
        if role == self.RejectedRole:
            return bool(row.get("rejected", False))
        if role == self.ThumbnailPathRole:
            path = row.get("thumbnail_path")
            return str(path) if path else None
        return None

    def roleNames(self):
        names = super().roleNames()
        names[self.IdRole] = b"id"
        names[self.FileNameRole] = b"file_name"
        names[self.OrdinalRole] = b"ordinal"
        names[self.RejectedRole] = b"rejected"
        return names

    def row_at(self, row: int) -> dict[str, object] | None:
        if 0 <= row < len(self._rows):
            return dict(self._rows[row])
        return None

    def set_rows(self, rows: Sequence[Mapping[str, object]]) -> None:
        self.beginResetModel()
        self._rows = [dict(row) for row in rows]
        self.endResetModel()

    def set_thumbnail_path(self, media_id: int, path: str) -> None:
        wanted = int(media_id)
        for row_index, row in enumerate(self._rows):
            value = row.get("id")
            if value is None or int(value) != wanted:
                continue
            row["thumbnail_path"] = path
            index = self.index(row_index)
            self.dataChanged.emit(index, index, [self.ThumbnailPathRole])
            return

    def set_manual_order_enabled(self, enabled: bool) -> None:
        self._manual_order = bool(enabled)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not self._manual_order:
            if not index.isValid():
                return Qt.ItemFlag.NoItemFlags
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        flags = Qt.ItemFlag.ItemIsDropEnabled
        if index.isValid():
            flags |= (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
        return flags

    def supportedDropActions(self) -> Qt.DropActions:
        if not self._manual_order:
            return Qt.DropAction.IgnoreAction
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return [_MIME_TYPE]

    def mimeData(self, indexes) -> QMimeData:
        mime = QMimeData()
        rows = sorted({index.row() for index in indexes if index.isValid()})
        ids: list[int] = []
        for row in rows:
            if not (0 <= row < len(self._rows)):
                continue
            value = self._rows[row].get("id")
            if value is None:
                continue
            ids.append(int(value))
        payload = ",".join(str(media_id) for media_id in ids).encode()
        mime.setData(_MIME_TYPE, QByteArray(payload))
        return mime

    def dropMimeData(
        self,
        data,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        del column
        if not self._manual_order or action != Qt.DropAction.MoveAction:
            return False
        if data is None or not data.hasFormat(_MIME_TYPE):
            return False
        raw = bytes(data.data(_MIME_TYPE)).decode("utf-8")
        moved_ids = [int(part) for part in raw.split(",") if part]
        if not moved_ids:
            return False
        by_id = {
            int(item["id"]): item
            for item in self._rows
            if item.get("id") is not None
        }
        moved_rows = [by_id[media_id] for media_id in moved_ids if media_id in by_id]
        if not moved_rows:
            return False
        moved_set = {int(item["id"]) for item in moved_rows}
        if parent.isValid() and row < 0:
            row = parent.row()
        if row < 0:
            row = len(self._rows)
        dest = row
        for item in self._rows[: min(row, len(self._rows))]:
            value = item.get("id")
            if value is not None and int(value) in moved_set:
                dest -= 1
        remaining = [item for item in self._rows if int(item["id"]) not in moved_set]
        dest = min(max(dest, 0), len(remaining))
        new_rows = remaining[:dest] + moved_rows + remaining[dest:]
        new_ids = [int(item["id"]) for item in new_rows]
        old_ids = [int(item["id"]) for item in self._rows]
        if new_ids == old_ids:
            return False
        self.beginResetModel()
        for ordinal, item in enumerate(new_rows, start=1):
            item["ordinal"] = ordinal
        self._rows = new_rows
        self.endResetModel()
        self.orderChanged.emit(new_ids, list(moved_ids))
        return True
