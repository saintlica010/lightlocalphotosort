from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.pixmap_cache import BoundedPixmapCache

THUMB_SIZE = 160


def ordinal_label(value: object) -> str | None:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return f"{number:02d}"


def culling_marker(value: object) -> str | None:
    return {"picked": "✓", "rejected": "×"}.get(str(value))


class ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmaps = BoundedPixmapCache()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.fillRect(option.rect, option.palette.highlight() if selected else QColor("#2b2b2b"))

        thumb_rect = QRect(
            option.rect.left() + 8,
            option.rect.top() + 8,
            THUMB_SIZE,
            THUMB_SIZE,
        )
        pixmap = self._pixmap_for(index)
        if pixmap is None or pixmap.isNull():
            painter.fillRect(thumb_rect, QColor("#3a3a3a"))
        else:
            scaled = pixmap.scaled(
                thumb_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = thumb_rect.x() + (thumb_rect.width() - scaled.width()) // 2
            y = thumb_rect.y() + (thumb_rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        label = ordinal_label(index.data(MediaListModel.OrdinalRole))
        if label:
            text_width = painter.fontMetrics().horizontalAdvance(label)
            badge = QRect(
                thumb_rect.left() + 4,
                thumb_rect.top() + 4,
                max(24, text_width + 8),
                18,
            )
            painter.fillRect(badge, QColor(0, 0, 0, 160))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), label)

        state = index.data(MediaListModel.CullingStateRole)
        marker = culling_marker(state)
        if marker:
            marker_rect = QRect(
                thumb_rect.right() - 28,
                thumb_rect.top() + 4,
                24,
                24,
            )
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.setPen(QColor("#ffffff"))
            painter.drawEllipse(marker_rect)
            painter.drawText(
                marker_rect,
                int(Qt.AlignmentFlag.AlignCenter),
                marker,
            )

        name = index.data(MediaListModel.FileNameRole)
        if name:
            text_rect = QRect(
                option.rect.left() + 4,
                thumb_rect.bottom() + 4,
                option.rect.width() - 8,
                max(option.rect.bottom() - thumb_rect.bottom() - 4, 16),
            )
            painter.setPen(
                option.palette.highlightedText().color() if selected else QColor("#dddddd")
            )
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap),
                str(name),
            )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(THUMB_SIZE + 16, THUMB_SIZE + 36)

    def _pixmap_for(self, index) -> QPixmap | None:
        # Disk-cached WebP only — never decode the source image in paint().
        path = index.data(MediaListModel.ThumbnailPathRole)
        if not path:
            return None
        key = str(path)
        cached = self._pixmaps.get(key)
        if cached is not None:
            return cached
        pix = QPixmap(key)
        if pix.isNull():
            return None
        self._pixmaps.put(key, pix)
        return pix
