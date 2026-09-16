from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QInputDialog, QWidget


def choose_existing_directory(parent: QWidget | None, title: str) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, title)
    if not chosen:
        return None
    return Path(chosen)


def choose_list_name(
    parent: QWidget | None,
    names: list[str],
    title: str = "Add to List",
) -> str | None:
    if not names:
        return None
    chosen, ok = QInputDialog.getItem(parent, title, "List:", names, 0, False)
    if not ok:
        return None
    chosen = chosen.strip()
    return chosen or None
