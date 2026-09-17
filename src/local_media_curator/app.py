from __future__ import annotations

import sys

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication

from local_media_curator.domain.models import Project
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.main_window import MainWindow


def install_chinese_translations(app: QApplication) -> QTranslator | None:
    """Translate Qt's own strings.

    Our own labels are Chinese in the source, but standard dialog buttons —
    Yes / No / Cancel / OK — are rendered by Qt from its own catalogue. Without
    this they appear in English inside an otherwise Chinese UI.
    """
    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qt_zh_CN", path):
        app.installTranslator(translator)
        return translator
    return None


def create_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        install_chinese_translations(existing)
        return existing
    app = QApplication(sys.argv)
    install_chinese_translations(app)
    return app


def bind_undo_stack(window: MainWindow, project: Project) -> CurationUndoStack:
    stack = CurationUndoStack(project)
    window.set_undo_stack(stack)
    return stack


def run() -> int:
    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()
