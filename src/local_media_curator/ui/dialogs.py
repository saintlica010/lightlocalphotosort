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


def ask_text(
    parent: QWidget | None, title: str, label: str, text: str = ""
) -> str | None:
    """Text input with Chinese buttons set by us, not by Qt.

    Same reason as show_warning: `qt_zh_CN` loads from the source tree but not
    inside the frozen EXE, so a dialog whose title and label are Chinese would
    still come up with English OK / Cancel buttons.
    """
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(text)
    dialog.setOkButtonText("确定")
    dialog.setCancelButtonText("取消")
    if dialog.exec() != QInputDialog.DialogCode.Accepted:
        return None
    return dialog.textValue()


def ask_item(
    parent: QWidget | None,
    title: str,
    label: str,
    items: list[str],
    current: int = 0,
) -> str | None:
    """Item picker with Chinese buttons. See ask_text."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setComboBoxItems(items)
    dialog.setComboBoxEditable(False)
    if 0 <= current < len(items):
        dialog.setTextValue(items[current])
    dialog.setOkButtonText("确定")
    dialog.setCancelButtonText("取消")
    if dialog.exec() != QInputDialog.DialogCode.Accepted:
        return None
    return dialog.textValue()


def choose_existing_directory(parent: QWidget | None, title: str) -> Path | None:
    chosen = QFileDialog.getExistingDirectory(parent, title)
    if not chosen:
        return None
    return Path(chosen)


def choose_save_file(
    parent: QWidget | None,
    title: str,
    named_filter: str,
    default_name: str = "",
) -> Path | None:
    chosen, _selected = QFileDialog.getSaveFileName(
        parent, title, default_name, named_filter
    )
    if not chosen:
        return None
    return Path(chosen)


def choose_open_file(
    parent: QWidget | None, title: str, named_filter: str
) -> Path | None:
    chosen, _selected = QFileDialog.getOpenFileName(
        parent, title, "", named_filter
    )
    if not chosen:
        return None
    return Path(chosen)


def show_import_summary(
    parent: QWidget | None, matched: int, missing: int, ambiguous: int
) -> None:
    """Show import match counts with Chinese OK. See show_warning."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("导入名单")
    box.setText(f"已匹配：{matched}\n缺失：{missing}\n歧义：{ambiguous}")
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.button(QMessageBox.StandardButton.Ok).setText("确定")
    box.exec()


def choose_list_name(
    parent: QWidget | None,
    names: list[str],
    title: str = "添加到名单",
) -> str | None:
    if not names:
        return None
    chosen = ask_item(parent, title, "名单：", names, 0)
    if chosen is None:
        return None
    chosen = chosen.strip()
    return chosen or None
