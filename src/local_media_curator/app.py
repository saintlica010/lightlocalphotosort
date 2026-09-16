from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication


def create_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication(sys.argv)
