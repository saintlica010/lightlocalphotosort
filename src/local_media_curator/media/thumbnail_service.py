from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from local_media_curator.domain.models import Project

DEFAULT_PROFILE = "default"
PROFILE_VERSIONS = {"default": 1}
PROFILE_MAX_EDGE = {"default": 256}


class ThumbnailService:
    def __init__(self, project: Project) -> None:
        self._project = project

    def cached_path(
        self,
        media_id: int,
        source_path: Path,
        mtime: int | float | None = None,
        size: int | None = None,
        profile: str = DEFAULT_PROFILE,
    ) -> Path | None:
        source_path = Path(source_path)
        try:
            mtime, size = self._source_mtime_size(source_path, mtime, size)
            out = self._output_path(media_id, mtime, size, profile)
            self._assert_inside_cache(out)
        except (OSError, ValueError):
            return None
        if out.is_file() and out.stat().st_size > 0:
            return out
        return None

    def ensure(
        self,
        media_id: int,
        source_path: Path,
        mtime: int | float | None = None,
        size: int | None = None,
        profile: str = DEFAULT_PROFILE,
    ) -> Path:
        source_path = Path(source_path)
        mtime, size = self._source_mtime_size(source_path, mtime, size)
        out = self._output_path(media_id, mtime, size, profile)
        self._assert_inside_cache(out)
        if out.is_file() and out.stat().st_size > 0:
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        self._render(source_path, out, PROFILE_MAX_EDGE.get(profile, 256))
        return out

    def _source_mtime_size(
        self,
        source_path: Path,
        mtime: int | float | None,
        size: int | None,
    ) -> tuple[int | float, int]:
        if mtime is None or size is None:
            stat = source_path.stat()
            if mtime is None:
                mtime = stat.st_mtime_ns
            if size is None:
                size = stat.st_size
        assert size is not None and mtime is not None
        return mtime, size

    def _output_path(
        self,
        media_id: int,
        mtime: int | float,
        size: int,
        profile: str,
    ) -> Path:
        version = PROFILE_VERSIONS.get(profile, 1)
        digest = hashlib.sha256(
            f"{media_id}:{mtime}:{size}:{profile}:{version}".encode()
        ).hexdigest()
        return self._project.thumbnails_dir / profile / digest[:2] / f"{digest}.webp"

    def _assert_inside_cache(self, out: Path) -> None:
        cache_root = self._project.thumbnails_dir.resolve()
        if cache_root not in out.resolve().parents:
            raise ValueError("thumbnail path is outside project.thumbnails_dir")

    def _render(self, source: Path, dest: Path, max_edge: int) -> None:
        tmp = dest.with_suffix(".webp.tmp")
        try:
            with source.open("rb") as fh:
                with Image.open(fh) as img:
                    try:
                        oriented = ImageOps.exif_transpose(img)
                    except (OSError, ValueError, AttributeError, SyntaxError):
                        oriented = img
                    if oriented is not None:
                        img = oriented
                    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                    rgb = img.convert("RGB")
                    rgb.save(tmp, "WEBP", quality=80)
        except (OSError, UnidentifiedImageError, ValueError, SyntaxError):
            Image.new("RGB", (max_edge, max_edge), (48, 48, 48)).save(tmp, "WEBP")
        tmp.replace(dest)
