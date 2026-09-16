from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class MediaListModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    FileNameRole = Qt.ItemDataRole.UserRole + 2
    OrdinalRole = Qt.ItemDataRole.UserRole + 3
    RejectedRole = Qt.ItemDataRole.UserRole + 4
    ThumbnailPathRole = Qt.ItemDataRole.UserRole + 5

    def __init__(
        self,
        rows: Sequence[Mapping[str, object]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, object]] = [dict(row) for row in rows] if rows else []

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
