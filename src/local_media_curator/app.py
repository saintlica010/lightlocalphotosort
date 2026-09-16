from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from local_media_curator.domain.models import Project
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.main_window import MainWindow


def create_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication(sys.argv)


def bind_undo_stack(window: MainWindow, project: Project) -> CurationUndoStack:
    stack = CurationUndoStack(project)
    window.set_undo_stack(stack)
    return stack
