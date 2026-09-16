from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget


def choose_existing_directory(parent: QWidget | None, title: str) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, title)
    if not chosen:
        return None
    return Path(chosen)
