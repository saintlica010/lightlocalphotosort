from __future__ import annotations

import os
from pathlib import Path


def normalize_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def paths_overlap(left: Path, right: Path) -> bool:
    a = normalize_path(left)
    b = normalize_path(right)
    if a == b:
        return True
    sep = os.sep
    return a.startswith(b + sep) or b.startswith(a + sep)


def reject_overlapping_roots(project_root: Path, source_root: Path) -> None:
    if paths_overlap(project_root, source_root):
        raise ValueError(
            f"Project and source folders overlap: {project_root} vs {source_root}"
        )
