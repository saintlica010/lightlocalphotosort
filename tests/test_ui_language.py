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
    assert names == ["全部", "未分配", "已选", "未决定", "已排除"]


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
        "整理状态",
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


def test_confirm_dialog_buttons_are_chinese(qtbot, monkeypatch) -> None:
    """Asserted on our helper, not on Qt's catalogue.

    Relying on Qt's own translation turned out to be unreliable: loading
    qt_zh_CN succeeds from the source tree but fails inside the frozen EXE, so
    the confirmation dialog showed English 'Yes'/'No' in a Chinese UI. The
    button text must be set by our code so packaging cannot change it.
    """
    from PySide6.QtWidgets import QMessageBox

    from local_media_curator.ui.dialogs import ask_confirm

    captured: dict[str, list[str]] = {}

    def fake_exec(box) -> int:
        captured["texts"] = [button.text() for button in box.buttons()]
        return int(QMessageBox.StandardButton.No)

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    assert ask_confirm(None, "删除名单", "确定删除名单吗？") is False
    assert captured["texts"] == ["是", "否"]
    assert all(CJK.search(text) for text in captured["texts"])


def test_warning_dialog_button_is_chinese(qtbot, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    from local_media_curator.ui.dialogs import show_warning

    captured: dict[str, list[str]] = {}

    def fake_exec(box) -> int:
        captured["texts"] = [button.text() for button in box.buttons()]
        return int(QMessageBox.StandardButton.Ok)

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    show_warning(None, "扫描", "出错了")
    assert captured["texts"] == ["确定"]


def test_text_input_dialog_buttons_are_chinese(qtbot, monkeypatch) -> None:
    """QInputDialog's own OK/Cancel come from Qt, so we must set them.

    Same class of problem as QMessageBox: the Qt catalogue does not load inside
    the frozen EXE, so a dialog whose title and label are Chinese would still
    show English buttons.
    """
    from PySide6.QtWidgets import QInputDialog

    from local_media_curator.ui.dialogs import ask_text

    captured: dict[str, object] = {}

    def fake_exec(self) -> int:
        captured["ok"] = self.okButtonText()
        captured["cancel"] = self.cancelButtonText()
        captured["title"] = self.windowTitle()
        captured["label"] = self.labelText()
        captured["text"] = self.textValue()
        return int(QInputDialog.DialogCode.Rejected)

    monkeypatch.setattr(QInputDialog, "exec", fake_exec)
    assert ask_text(None, "新建名单", "名称：", text="现有名") is None
    assert captured["ok"] == "确定"
    assert captured["cancel"] == "取消"
    assert captured["title"] == "新建名单"
    assert captured["label"] == "名称："
    assert captured["text"] == "现有名"


def test_text_input_dialog_returns_entered_text(qtbot, monkeypatch) -> None:
    from PySide6.QtWidgets import QInputDialog

    from local_media_curator.ui.dialogs import ask_text

    def fake_exec(self) -> int:
        self.setTextValue("  新名单  ")
        return int(QInputDialog.DialogCode.Accepted)

    monkeypatch.setattr(QInputDialog, "exec", fake_exec)
    assert ask_text(None, "新建名单", "名称：") == "  新名单  "


def test_item_input_dialog_buttons_are_chinese(qtbot, monkeypatch) -> None:
    from PySide6.QtWidgets import QInputDialog

    from local_media_curator.ui.dialogs import ask_item

    captured: dict[str, object] = {}

    def fake_exec(self) -> int:
        captured["ok"] = self.okButtonText()
        captured["cancel"] = self.cancelButtonText()
        captured["items"] = list(self.comboBoxItems())
        captured["title"] = self.windowTitle()
        return int(QInputDialog.DialogCode.Accepted)

    monkeypatch.setattr(QInputDialog, "exec", fake_exec)
    assert ask_item(None, "添加到名单", "名单：", ["Promotional", "Website"]) == "Promotional"
    assert captured["ok"] == "确定"
    assert captured["cancel"] == "取消"
    assert captured["items"] == ["Promotional", "Website"]
    assert captured["title"] == "添加到名单"


def test_list_panel_uses_the_chinese_input_helpers(qtbot, monkeypatch) -> None:
    """The panel must route through the helpers, not call Qt directly."""
    from local_media_curator.ui import list_panel as panel_module
    from local_media_curator.ui.list_panel import ListPanel

    panel = ListPanel()
    qtbot.addWidget(panel)
    seen: list[tuple] = []

    def fake_text(parent, title, label, text=""):
        seen.append(("text", title, label, text))
        return "命名"

    monkeypatch.setattr(panel_module, "ask_text", fake_text)
    panel._on_new()
    assert seen == [("text", "新建名单", "名称：", "")]


def test_choose_list_name_uses_the_chinese_item_helper(monkeypatch) -> None:
    from local_media_curator.ui import dialogs as dialogs_module

    seen: list[tuple] = []

    def fake_item(parent, title, label, items, current=0):
        seen.append((title, label, list(items)))
        return "Website"

    monkeypatch.setattr(dialogs_module, "ask_item", fake_item)
    assert dialogs_module.choose_list_name(None, ["Promotional", "Website"]) == "Website"
    assert seen == [("添加到名单", "名单：", ["Promotional", "Website"])]


def test_error_messages_shown_to_users_are_chinese(tmp_path: Path) -> None:
    """These strings reach the user through str(exc) in a dialog."""
    from local_media_curator.domain.paths import reject_overlapping_roots
    from local_media_curator.services.project_service import create_project

    inside = tmp_path / "photos" / "sub"
    inside.mkdir(parents=True)
    with pytest.raises(ValueError) as protected:
        create_project(inside)
    assert CJK.search(str(protected.value))
    # The directory name is data and stays.
    assert "photos" in str(protected.value)

    source = tmp_path / "Wedding2026"
    project = source / "curator"  # nested, so the two roots overlap
    project.mkdir(parents=True)
    with pytest.raises(ValueError) as overlap:
        reject_overlapping_roots(project, source)
    assert CJK.search(str(overlap.value))


def test_user_data_is_never_translated(loaded_window) -> None:
    window, _project = loaded_window
    row = window.media_grid.model.row_at(0)
    assert row["file_name"] == "Holiday.jpg"
    window.list_service.create("Promotional")
    window.refresh()
    lists_widget = window.library_panel.list_panel.lists_widget
    assert lists_widget.item(0).text() == "Promotional"
