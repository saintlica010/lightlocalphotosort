from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget


def show_warning(parent: QWidget | None, title: str, text: str) -> None:
    """Show a warning with Chinese button text set by us, not by Qt.

    Relying on Qt's own catalogue is not safe here: loading `qt_zh_CN`
    succeeds from the source tree but fails inside the frozen EXE, which left
    English buttons in an otherwise Chinese UI. Setting the text explicitly
    makes the result independent of packaging.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.button(QMessageBox.StandardButton.Ok).setText("确定")
    box.exec()


def ask_confirm(parent: QWidget | None, title: str, text: str) -> bool:
    """Yes/No confirmation in Chinese. Defaults to No. See show_warning."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.button(QMessageBox.StandardButton.Yes).setText("是")
    box.button(QMessageBox.StandardButton.No).setText("否")
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


def choose_existing_directory(parent: QWidget | None, title: str) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, title)
    if not chosen:
        return None
    return Path(chosen)


def choose_list_name(
    parent: QWidget | None,
    names: list[str],
    title: str = "添加到名单",
) -> str | None:
    if not names:
        return None
    chosen, ok = QInputDialog.getItem(parent, title, "名单：", names, 0, False)
    if not ok:
        return None
    chosen = chosen.strip()
    return chosen or None
