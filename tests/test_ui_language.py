"""All user-facing UI text must be Simplified Chinese.

Source-code identifiers, tests and developer docs stay English; this file only
guards what a user can actually see. User data — filenames, paths, list names,
metadata values, extension strings — must be preserved verbatim and never
translated.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QWidget,
)

from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow

CJK = re.compile(r"[一-鿿]")

# English words that must never reach the user. Deliberately narrow: it names
# the vocabulary this UI actually uses, so a false positive is a real miss.
ENGLISH_UI_WORDS = re.compile(
    r"\b(File|Edit|New|Open|Add|Remove|Scan|Scanning|Undo|Redo|Reject|Rejected"
    r"|Restore|Move|Up|Down|Start|End|List|Lists|Library|All|Unassigned"
    r"|Image|Video|Any|Present|Missing|Folder|Name|Path|Dimensions|Size"
    r"|Captured|Modified|Import|Delete|Rename|Yes|No|bytes|already|exists"
    r"|project|Project|media|Database|busy)\b"
)

# Items that legitimately contain no Chinese: user data and literal values.
ALLOWED_EXACT = {
    "",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".mp4",
    ".mov",
}


def _visible_texts(widget: QWidget) -> list[str]:
    texts: list[str] = []
    for child in widget.findChildren(QWidget):
        if isinstance(child, (QLabel, QPushButton)):
            texts.append(child.text())
        elif isinstance(child, QComboBox):
            texts.extend(child.itemText(i) for i in range(child.count()))
        elif isinstance(child, QListWidget):
            texts.extend(child.item(i).text() for i in range(child.count()))
    return texts


def _all_action_texts(window: MainWindow) -> list[str]:
    texts: list[str] = []
    for menu_action in window.menuBar().actions():
        texts.append(menu_action.text())
        menu = menu_action.menu()
        if menu is not None:
            texts.extend(action.text() for action in menu.actions())
    return texts


@pytest.fixture
def loaded_window(qtbot, tmp_path: Path):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "Holiday.jpg", "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.add_source_folder(source)
    window.scan()
    qtbot.waitUntil(lambda: window.media_grid.model.rowCount() == 1, timeout=8000)
    yield window, project
    project.close()


def test_menus_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    titles = [action.text() for action in window.menuBar().actions()]
    assert "文件" in titles
    assert "编辑" in titles


def test_primary_actions_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    assert window.scan_action.text() == "扫描"
    assert window.add_source_action.text() == "添加源文件夹"
    assert window.remove_source_action.text() == "移除源文件夹"
    assert window.open_original_action.text() == "打开原文件"
    assert window.move_up_action.text() == "上移"
    assert window.move_down_action.text() == "下移"
    assert window.move_start_action.text() == "移到开头"
    assert window.move_end_action.text() == "移到末尾"


def test_library_views_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    views = window.library_panel.views
    names = [views.item(i).text() for i in range(views.count())]
    assert names == ["全部", "未分配", "已排除"]


def test_filter_options_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    panel = window.library_panel
    assert panel.type_combo.itemText(0) == "全部"
    assert panel.type_combo.itemText(1) == "图片"
    assert panel.type_combo.itemText(2) == "视频"
    assert panel.extension_combo.itemText(0) == "任意扩展名"
    assert panel.folder_combo.itemText(0) == "任意文件夹"
    assert panel.missing_combo.itemText(0) == "任意"
    assert panel.missing_combo.itemText(1) == "存在"
    assert panel.missing_combo.itemText(2) == "缺失"


def test_extension_values_are_not_translated(loaded_window) -> None:
    window, _project = loaded_window
    combo = window.library_panel.extension_combo
    values = [combo.itemData(i) for i in range(combo.count())]
    assert ".jpg" in values
    assert None in values


def test_preview_form_labels_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    form = window.preview_panel.findChild(QFormLayout)
    assert form is not None
    rows = []
    for i in range(form.rowCount()):
        item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
        if item is not None and item.widget() is not None:
            rows.append(item.widget().text())
    assert rows == [
        "文件名",
        "路径",
        "尺寸",
        "大小",
        "拍摄时间",
        "修改时间",
        "名单",
        "已排除",
    ]


def test_list_buttons_are_chinese(loaded_window) -> None:
    window, _project = loaded_window
    panel = window.library_panel.list_panel
    assert panel.new_button.text() == "新建"
    assert panel.rename_button.text() == "重命名"
    assert panel.delete_button.text() == "删除"


def test_status_text_is_chinese(loaded_window) -> None:
    window, _project = loaded_window
    window.show_library_view("all")
    assert window.statusBar().currentMessage() == "媒体库（自动排序）"


def test_no_english_ui_words_remain(loaded_window) -> None:
    """Sweep every visible text for English UI vocabulary."""
    window, _project = loaded_window
    offenders: list[str] = []
    for text in _visible_texts(window) + _all_action_texts(window):
        if text in ALLOWED_EXACT or CJK.search(text):
            continue
        if ENGLISH_UI_WORDS.search(text):
            offenders.append(text)
    assert offenders == []


def test_qt_standard_dialog_buttons_are_chinese(qtbot) -> None:
    """Qt's own Yes/No/OK labels come from Qt's catalogue, not from our code."""
    from PySide6.QtWidgets import QMessageBox

    from local_media_curator.app import create_app

    create_app()
    box = QMessageBox()
    qtbot.addWidget(box)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel
    )
    texts = [button.text() for button in box.buttons()]
    assert texts
    assert all(CJK.search(text) for text in texts), texts


def test_user_data_is_never_translated(loaded_window) -> None:
    window, _project = loaded_window
    row = window.media_grid.model.row_at(0)
    assert row["file_name"] == "Holiday.jpg"
    window.list_service.create("Promotional")
    window.refresh()
    lists_widget = window.library_panel.list_panel.lists_widget
    assert lists_widget.item(0).text() == "Promotional"
