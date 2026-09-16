from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import IFD, Base

from local_media_curator.domain.models import ImageMetadata

_DATETIME_ORIGINAL = int(Base.DateTimeOriginal)


def _iso_from_mtime(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).isoformat(timespec="seconds")


def _exif_datetime_to_iso(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return text


def _read_datetime_original(img: Image.Image) -> str | None:
    try:
        exif = img.getexif()
    except (OSError, ValueError, AttributeError):
        return None
    if not exif:
        return None
    raw = exif.get(_DATETIME_ORIGINAL)
    if raw is None:
        try:
            raw = exif.get_ifd(IFD.Exif).get(_DATETIME_ORIGINAL)
        except (KeyError, TypeError, AttributeError):
            raw = None
    return _exif_datetime_to_iso(raw)


def extract_image_metadata(path: Path) -> ImageMetadata:
    stat = path.stat()
    with path.open("rb") as fh:
        with Image.open(fh) as img:
            width, height = img.size
            captured_at = _read_datetime_original(img)
    if not captured_at:
        captured_at = _iso_from_mtime(stat.st_mtime)
    return ImageMetadata(
        size=stat.st_size,
        width=width,
        height=height,
        captured_at=captured_at,
    )
