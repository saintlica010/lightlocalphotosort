from __future__ import annotations

from pathlib import Path

from local_media_curator.db.connection import connect
from local_media_curator.db.migrations import apply_migrations
from local_media_curator.domain.models import Project

_DB_NAME = "project.sqlite3"
_THUMBNAILS_DIR = "thumbnails"
_LOGS_DIR = "logs"
_PROTECTED_DIR_NAMES = frozenset({"photos", "phototakeplan", "lightphotosprt"})


def _reject_protected_project_root(root: Path) -> None:
    blocked = {
        part for part in root.parts if part.casefold() in _PROTECTED_DIR_NAMES
    }
    if blocked:
        names = ", ".join(sorted(blocked, key=str.casefold))
        raise ValueError(
            f"Project root cannot be inside {names}: {root}"
        )


def create_project(root: Path) -> Project:
    root = root.resolve()
    _reject_protected_project_root(root)
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / _DB_NAME
    thumbnails_dir = root / _THUMBNAILS_DIR
    logs_dir = root / _LOGS_DIR
    thumbnails_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    connection = connect(db_path)
    apply_migrations(connection)
    return Project(
        root=root,
        db_path=db_path,
        thumbnails_dir=thumbnails_dir,
        logs_dir=logs_dir,
        connection=connection,
    )


def open_project(root: Path) -> Project:
    root = root.resolve()
    _reject_protected_project_root(root)
    db_path = root / _DB_NAME
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    thumbnails_dir = root / _THUMBNAILS_DIR
    logs_dir = root / _LOGS_DIR
    thumbnails_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    connection = connect(db_path)
    apply_migrations(connection)
    return Project(
        root=root,
        db_path=db_path,
        thumbnails_dir=thumbnails_dir,
        logs_dir=logs_dir,
        connection=connection,
    )
