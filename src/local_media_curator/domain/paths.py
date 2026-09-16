from __future__ import annotations

import os
from pathlib import Path


def normalize_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))
