from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from PIL import UnidentifiedImageError

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.domain.models import Project, ScanResult
from local_media_curator.domain.paths import normalize_path
from local_media_curator.media.metadata import extract_image_metadata

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
SCAN_COMMIT_BATCH = 256
PROGRESS_EVERY = 25


class ScanCancelled(Exception):
    pass


def _iso_from_mtime(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).isoformat(timespec="seconds")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _is_under_dir(path: Path, root: Path) -> bool:
    child = normalize_path(path)
    parent = normalize_path(root)
    if child == parent:
        return True
    return child.startswith(parent + os.sep)


def _iter_media_files(
    folder: Path, recursive: bool, skip_dirs: Iterable[Path] = ()
):
    if not folder.is_dir():
        return
    skipped = tuple(skip_dirs)
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for path in iterator:
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if not is_file or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if any(_is_under_dir(path, skip) for skip in skipped):
            continue
        yield path


def _read_fields(path: Path, ext: str, stat_result) -> tuple[str, int | None, int | None, str]:
    modified_at = _iso_from_mtime(stat_result.st_mtime)
    if ext in VIDEO_EXTENSIONS:
        return "video", None, None, modified_at
    try:
        meta = extract_image_metadata(path)
    except (OSError, UnidentifiedImageError, ValueError):
        return "image", None, None, modified_at
    return "image", meta.width, meta.height, meta.captured_at


def scan_source_folder(
    project: Project,
    folder: Path,
    *,
    recursive: bool = True,
    cancel_check: Callable[[], bool] | None = None,
    progress_cb: Callable[[int], None] | None = None,
) -> ScanResult:
    conn = project.connection
    repo = MediaRepository(conn)
    result = ScanResult()
    folder_normalized = normalize_path(folder)
    existing_rows = repo.list_under_folder(folder_normalized)
    existing_by_norm = {row["normalized_path"]: row for row in existing_rows}
    seen: set[str] = set()
    processed = 0

    try:
        for path in _iter_media_files(
            folder, recursive, skip_dirs=(project.thumbnails_dir,)
        ):
            if cancel_check is not None and cancel_check():
                raise ScanCancelled()
            try:
                stat_result = path.stat()
            except OSError:
                continue
            normalized = normalize_path(path)
            seen.add(normalized)
            ext = path.suffix.lower()
            modified_at = _iso_from_mtime(stat_result.st_mtime)
            row = existing_by_norm.get(normalized)

            if row is None:
                media_type, width, height, captured_at = _read_fields(
                    path, ext, stat_result
                )
                try:
                    repo.insert(
                        absolute_path=str(path.resolve()),
                        normalized_path=normalized,
                        media_type=media_type,
                        file_name=path.name,
                        extension=ext,
                        file_size=stat_result.st_size,
                        width=width,
                        height=height,
                        duration_ms=None,
                        captured_at=(
                            captured_at if media_type == "image" else modified_at
                        ),
                        modified_at=modified_at,
                        imported_at=_now_iso(),
                    )
                except sqlite3.IntegrityError:
                    result.unchanged += 1
                else:
                    result.added += 1
            else:
                size_changed = row["file_size"] != stat_result.st_size
                mtime_changed = row["modified_at"] != modified_at
                if size_changed or mtime_changed:
                    media_type, width, height, captured_at = _read_fields(
                        path, ext, stat_result
                    )
                    repo.update_file_metadata(
                        row["id"],
                        file_size=stat_result.st_size,
                        width=width,
                        height=height,
                        captured_at=(
                            captured_at if media_type == "image" else modified_at
                        ),
                        modified_at=modified_at,
                    )
                    result.modified += 1
                else:
                    if row["missing"]:
                        repo.set_missing(row["id"], False)
                    result.unchanged += 1

            processed += 1
            if progress_cb is not None and (
                processed == 1 or processed % PROGRESS_EVERY == 0
            ):
                progress_cb(processed)
            if processed % SCAN_COMMIT_BATCH == 0:
                conn.commit()

        for row in existing_rows:
            if cancel_check is not None and cancel_check():
                raise ScanCancelled()
            if row["normalized_path"] in seen:
                continue
            if not row["missing"]:
                repo.set_missing(row["id"], True)
            result.missing += 1

        conn.commit()
        if progress_cb is not None and (
            processed == 0 or (processed != 1 and processed % PROGRESS_EVERY != 0)
        ):
            progress_cb(processed)
    except ScanCancelled:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    return result
