from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    root: Path
    db_path: Path
    thumbnails_dir: Path
    logs_dir: Path
    connection: sqlite3.Connection

    def close(self) -> None:
        self.connection.close()


@dataclass
class ImageMetadata:
    size: int
    width: int
    height: int
    captured_at: str


@dataclass
class ScanResult:
    added: int = 0
    missing: int = 0
    unchanged: int = 0
    modified: int = 0
