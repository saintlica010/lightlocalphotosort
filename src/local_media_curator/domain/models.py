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
