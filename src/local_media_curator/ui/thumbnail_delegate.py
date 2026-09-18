from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.theme import TOKENS
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


def quick_slot_badge(value: object) -> str | None:
    """Visual projection of quick-slot membership, e.g. '1 3 7'."""
    if value is None:
        return None
    numbers: list[int] = []
    raw = value.split() if isinstance(value, str) else value
    try:
        items = list(raw)
    except TypeError:
        return None
    for item in items:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 9 and number not in numbers:
            numbers.append(number)
    if not numbers:
        return None
    return " ".join(str(number) for number in sorted(numbers))



def card_color(selected: bool) -> QColor:
    return QColor(TOKENS.selection if selected else TOKENS.surface_3)


def placeholder_color() -> QColor:
    return QColor(TOKENS.border)


def marker_color(state: object) -> QColor | None:
    if state == "picked":
        return QColor(TOKENS.picked)
    if state == "rejected":
        return QColor(TOKENS.rejected)
    return None


def slot_badge_color() -> QColor:
    return QColor(TOKENS.accent)


def filename_color() -> QColor:
    return QColor(TOKENS.text)


class ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmaps = BoundedPixmapCache()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.fillRect(option.rect, card_color(selected))

        thumb_rect = QRect(
            option.rect.left() + 8,
            option.rect.top() + 8,
            THUMB_SIZE,
            THUMB_SIZE,
        )
        pixmap = self._pixmap_for(index)
        if pixmap is None or pixmap.isNull():
            painter.fillRect(thumb_rect, placeholder_color())
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
            painter.setPen(marker_color(state) or filename_color())
            painter.drawEllipse(marker_rect)
            painter.drawText(
                marker_rect,
                int(Qt.AlignmentFlag.AlignCenter),
                marker,
            )

        name = index.data(MediaListModel.FileNameRole)
        badge = quick_slot_badge(index.data(MediaListModel.QuickSlotsRole))
        if name or badge:
            text_rect = QRect(
                option.rect.left() + 4,
                thumb_rect.bottom() + 4,
                option.rect.width() - 8,
                max(option.rect.bottom() - thumb_rect.bottom() - 4, 16),
            )
            if badge:
                badge_width = painter.fontMetrics().horizontalAdvance(badge) + 4
                badge_rect = QRect(
                    text_rect.right() - badge_width + 1,
                    text_rect.top(),
                    badge_width,
                    min(18, text_rect.height()),
                )
                painter.setPen(slot_badge_color())
                painter.drawText(
                    badge_rect,
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                    badge,
                )
                text_rect.setWidth(max(0, text_rect.width() - badge_width - 4))
            if name:
                painter.setPen(filename_color())
                painter.drawText(
                    text_rect,
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap),
                    str(name),
                )
        if option.state & QStyle.StateFlag.State_HasFocus:
            pen = QPen(QColor(TOKENS.focus))
            pen.setWidth(TOKENS.border_width)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(option.rect.adjusted(1, 1, -2, -2))
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
