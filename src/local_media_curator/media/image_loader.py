from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from PySide6.QtGui import QImage

DEFAULT_PREVIEW_MAX_EDGE = 2048


def load_preview_image(path: Path, max_edge: int) -> QImage:
    """Decode `path` to a downsampled QImage. EXIF orientation is applied in memory only."""
    edge = max(int(max_edge), 1)
    try:
        with Path(path).open("rb") as fh:
            with Image.open(fh) as img:
                try:
                    oriented = ImageOps.exif_transpose(img)
                except (OSError, ValueError, AttributeError, SyntaxError):
                    oriented = img
                if oriented is not None:
                    img = oriented
                img.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                return _pil_to_qimage(img)
    except (OSError, UnidentifiedImageError, ValueError, SyntaxError):
        return QImage()


def _pil_to_qimage(img: Image.Image) -> QImage:
    rgba = img.convert("RGBA")
    width, height = rgba.size
    qimage = QImage(
        rgba.tobytes(),
        width,
        height,
        width * 4,
        QImage.Format.Format_RGBA8888,
    )
    return qimage.copy()
