from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QFormLayout,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from local_media_curator.media.image_loader import DEFAULT_PREVIEW_MAX_EDGE
from local_media_curator.media.preview_loader import PreviewLoader, open_path


class ImageView(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._item: QGraphicsPixmapItem | None = None
        self._image = QImage()
        self._fit = True
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def image(self) -> QImage:
        return self._image

    def set_image(self, image: QImage | None) -> None:
        self._scene.clear()
        self.resetTransform()
        self._item = None
        self._fit = True
        if image is None or image.isNull():
            self._image = QImage()
            return
        self._image = QImage(image)
        self._item = self._scene.addPixmap(QPixmap.fromImage(self._image))
        self._scene.setSceneRect(self._item.boundingRect())
        self._fit_image()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._item is None:
            return
        self._fit = False
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit:
            self._fit_image()

    def _fit_image(self) -> None:
        if self._item is None:
            return
        self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)


class PreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._token = 0
        self._current_path: Path | None = None
        self.loader = PreviewLoader(self)
        self.loader.loaded.connect(self._on_preview_loaded)
        self.image_view = ImageView(self)
        self.file_name_label = QLabel()
        self.path_label = QLabel()
        self.dimensions_label = QLabel()
        self.size_label = QLabel()
        self.captured_at_label = QLabel()
        self.modified_at_label = QLabel()
        self.lists_label = QLabel()
        self.culling_state_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form = QFormLayout()
        form.addRow("文件名", self.file_name_label)
        form.addRow("路径", self.path_label)
        form.addRow("尺寸", self.dimensions_label)
        form.addRow("大小", self.size_label)
        form.addRow("拍摄时间", self.captured_at_label)
        form.addRow("修改时间", self.modified_at_label)
        form.addRow("名单", self.lists_label)
        form.addRow("整理状态", self.culling_state_label)
        layout = QVBoxLayout(self)
        layout.addWidget(self.image_view, stretch=1)
        layout.addLayout(form)
        self.set_media(None)

    def set_media(self, media: Mapping[str, object] | None) -> None:
        if not media:
            self._clear()
            return
        path_value = media.get("absolute_path") or media.get("path")
        path_text = str(path_value) if path_value else ""
        self._current_path = Path(path_text) if path_text else None
        width = media.get("width")
        height = media.get("height")
        size = media.get("file_size")
        if size is None:
            size = media.get("size")
        lists = media.get("lists")
        state = str(media.get("culling_state") or (
            "rejected" if media.get("rejected", False) else "undecided"
        ))
        state_label = {"picked": "已选", "undecided": "未决定", "rejected": "已排除"}.get(
            state, "未决定"
        )
        self.file_name_label.setText(str(media.get("file_name") or ""))
        self.path_label.setText(path_text)
        self.dimensions_label.setText(
            f"{width} × {height}" if width is not None and height is not None else ""
        )
        self.size_label.setText(f"{size} 字节" if size is not None else "")
        self.captured_at_label.setText(str(media.get("captured_at") or ""))
        self.modified_at_label.setText(str(media.get("modified_at") or ""))
        self.lists_label.setText(_format_lists(lists))
        self.culling_state_label.setText(state_label)
        self._load_preview(path_value)

    def open_original(self) -> None:
        if self._current_path is None:
            return
        open_path(self._current_path)

    def _clear(self) -> None:
        self._token += 1
        self._current_path = None
        self.file_name_label.clear()
        self.path_label.clear()
        self.dimensions_label.clear()
        self.size_label.clear()
        self.captured_at_label.clear()
        self.modified_at_label.clear()
        self.lists_label.clear()
        self.culling_state_label.clear()
        self.image_view.set_image(None)

    def _load_preview(self, path_value: object) -> None:
        self._token += 1
        token = self._token
        self.image_view.set_image(None)
        if not path_value:
            return
        path = Path(str(path_value))
        if not path.is_file():
            return
        self.loader.load(str(path), token, DEFAULT_PREVIEW_MAX_EDGE)

    def _on_preview_loaded(self, token: int, image: object) -> None:
        if int(token) != self._token:
            return
        self.image_view.set_image(image if isinstance(image, QImage) else None)


def _format_lists(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)
