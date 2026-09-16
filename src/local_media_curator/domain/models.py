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


@dataclass(frozen=True)
class Media:
    id: int
    absolute_path: str
    normalized_path: str
    media_type: str
    file_name: str
    extension: str | None
    file_size: int | None
    width: int | None
    height: int | None
    duration_ms: int | None
    captured_at: str | None
    modified_at: str | None
    imported_at: str
    rejected: bool
    missing: bool
    fingerprint: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Media:
        return cls(
            id=int(row["id"]),
            absolute_path=str(row["absolute_path"]),
            normalized_path=str(row["normalized_path"]),
            media_type=str(row["media_type"]),
            file_name=str(row["file_name"]),
            extension=row["extension"],
            file_size=row["file_size"],
            width=row["width"],
            height=row["height"],
            duration_ms=row["duration_ms"],
            captured_at=row["captured_at"],
            modified_at=row["modified_at"],
            imported_at=str(row["imported_at"]),
            rejected=bool(row["rejected"]),
            missing=bool(row["missing"]),
            fingerprint=row["fingerprint"],
        )
