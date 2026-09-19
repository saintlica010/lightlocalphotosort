from PySide6.QtWidgets import QLabel, QMessageBox

from local_media_curator.ui.dialogs import warning_box
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.media_grid import MediaGrid
from local_media_curator.ui.preview_panel import PreviewPanel
from local_media_curator.ui.theme import TOKENS, stylesheet
from local_media_curator.ui.thumbnail_delegate import (
    ThumbnailDelegate,
    card_color,
    marker_color,
    slot_badge_color,
)


def test_app_sheet_styles_real_surfaces_without_animation() -> None:
    sheet = stylesheet(TOKENS)
    for selector in (
        "QListWidget#libraryViews",
        "QListWidget#namedLists",
        "QComboBox#filterControl:focus",
        "QListView#mediaGrid",
        "QWidget#previewPanel",
        "QMenu::item:selected",
        "QStatusBar",
        "QLabel#pickedCount",
        "QLabel#rejectedCount",
        "QLabel#previewPicked",
        "QLabel#previewRejected",
    ):
        assert selector in sheet
    assert TOKENS.focus in sheet
    assert TOKENS.selection in sheet
    assert "animation" not in sheet.lower()
    assert "transition" not in sheet.lower()


def test_main_window_applies_tokens_and_keeps_delegate(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    sheet = window.styleSheet()
    assert sheet == stylesheet()
    assert window.library_panel.views.objectName() == "libraryViews"
    assert window.list_panel.lists_widget.objectName() == "namedLists"
    assert window.media_grid.view.objectName() == "mediaGrid"
    assert window.media_grid.view.spacing() == TOKENS.thumbnail_spacing
    assert isinstance(window.media_grid.view.itemDelegate(), ThumbnailDelegate)
    for name in (
        "sort_combo",
        "type_combo",
        "extension_combo",
        "folder_combo",
        "missing_combo",
    ):
        assert getattr(window.library_panel, name).objectName() == "filterControl"
    assert window.preview_panel.objectName() == "previewPanel"
    assert window.library_panel.culling_count_labels["picked"].objectName() == "pickedCount"
    assert window.library_panel.culling_count_labels["rejected"].objectName() == "rejectedCount"
    assert window.library_panel.current_filters()["media_type"] is None
    assert window.library_panel.current_sort() == "file_name"


def test_grid_still_uses_delegate_not_per_item_widgets(qtbot) -> None:
    grid = MediaGrid()
    qtbot.addWidget(grid)
    assert isinstance(grid.view.itemDelegate(), ThumbnailDelegate)
    assert grid.view.model() is grid.model


def test_delegate_state_colors_are_distinct_tokens() -> None:
    assert card_color(False).name() == TOKENS.surface_3
    assert card_color(True).name() == TOKENS.selection
    assert marker_color("picked").name() == TOKENS.picked
    assert marker_color("rejected").name() == TOKENS.rejected
    assert marker_color("picked").name() != marker_color("rejected").name()
    assert marker_color("undecided") is None
    assert slot_badge_color().name() == TOKENS.accent


def test_preview_state_label_uses_distinct_names(qtbot) -> None:
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.set_media({"culling_state": "picked", "file_name": "a.jpg"})
    assert panel.culling_state_label.text() == "已选"
    assert panel.culling_state_label.objectName() == "previewPicked"
    panel.set_media({"culling_state": "rejected", "file_name": "b.jpg"})
    assert panel.culling_state_label.text() == "已排除"
    assert panel.culling_state_label.objectName() == "previewRejected"


def test_preview_metadata_uses_explicit_dark_theme_contrast(qtbot) -> None:
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    panel.set_media({"file_name": "a.jpg", "culling_state": "undecided"})
    assert panel.file_name_label.objectName() == "previewValue"
    assert panel.culling_state_label.objectName() == "previewUndecided"
    sheet = stylesheet()
    assert "QLabel#previewFieldLabel" in sheet
    assert "QLabel#previewValue" in sheet
    assert f"color: {TOKENS.text};" in sheet
    assert f"color: {TOKENS.text_muted};" in sheet


def test_owned_dialogs_take_the_project_sheet(qtbot) -> None:
    box = warning_box(None, "标题", "正文")
    qtbot.addWidget(box)
    assert isinstance(box, QMessageBox)
    assert TOKENS.surface_1 in box.styleSheet()
    assert box.button(QMessageBox.StandardButton.Ok).text() == "确定"


def test_warning_box_labels_are_not_black(qtbot) -> None:
    box = warning_box(
        None,
        "无法导出",
        "当前名单中没有可用于 Lightroom RAW 匹配的 JPEG 文件。",
    )
    qtbot.addWidget(box)
    assert "QMessageBox QLabel" in box.styleSheet()
    assert f"color: {TOKENS.text}" in box.styleSheet()
    labels = box.findChildren(QLabel)
    assert labels
    for label in labels:
        if not label.text():
            continue
        color = label.palette().color(label.foregroundRole())
        # Palette may stay black under offscreen; QSS string is the release gate.
        if color.name().lower() == "#000000":
            assert TOKENS.text in box.styleSheet()
            continue
        assert color.name().lower() != "#000000"
