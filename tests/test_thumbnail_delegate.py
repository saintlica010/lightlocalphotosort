from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem

from local_media_curator.ui.media_model import MediaListModel
from local_media_curator.ui.thumbnail_delegate import ThumbnailDelegate


def test_delegate_paint_does_not_open_source_image(qtbot, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "A.jpg"
    Image.new("RGB", (40, 40), "red").save(source, "JPEG")
    opened: list[str] = []
    real_open = Path.open

    def tracking_open(self, *args, **kwargs):
        opened.append(str(self))
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    model = MediaListModel(
        [
            {
                "id": 1,
                "file_name": "A.jpg",
                "absolute_path": str(source),
                "thumbnail_path": None,
                "ordinal": 1,
                "rejected": False,
            }
        ]
    )
    delegate = ThumbnailDelegate()
    image = QImage(200, 220, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 176, 196)
    delegate.paint(painter, option, model.index(0))
    painter.end()
    assert str(source) not in opened
    assert not any(path.endswith("A.jpg") for path in opened)


def test_delegate_paint_may_open_webp_but_not_jpeg_source(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "A.jpg"
    thumb = tmp_path / "A.webp"
    Image.new("RGB", (40, 40), "red").save(source, "JPEG")
    Image.new("RGB", (20, 20), "blue").save(thumb, "WEBP")
    opened: list[str] = []
    real_open = Path.open

    def tracking_open(self, *args, **kwargs):
        opened.append(str(self))
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    model = MediaListModel(
        [
            {
                "id": 1,
                "file_name": "A.jpg",
                "absolute_path": str(source),
                "thumbnail_path": str(thumb),
                "ordinal": 1,
                "rejected": False,
            }
        ]
    )
    delegate = ThumbnailDelegate()
    image = QImage(200, 220, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 176, 196)
    delegate.paint(painter, option, model.index(0))
    painter.end()
    assert str(source) not in opened
    assert not any(path.endswith("A.jpg") for path in opened)
