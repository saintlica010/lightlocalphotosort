"""Phase 3D design tokens and the one QSS that reads them.

Phase 3E applies the same sheet to the sidebar, lists, filters, grid,
preview, menus, owned dialogs, and the status bar. Grid cards are still
painted by the thumbnail delegate; it reads these tokens instead of literals.
"""

from __future__ import annotations

from dataclasses import dataclass

# Text markers already used by the grid (✓ ×, slot numbers). No icon font
# and no third-party icon pack.
ICON_POLICY = "text-markers"


@dataclass(frozen=True)
class ThemeTokens:
    surface_0: str = "#141414"
    surface_1: str = "#1c1c1c"
    surface_2: str = "#242424"
    surface_3: str = "#2c2c2c"
    text: str = "#e8e8e8"
    text_muted: str = "#9b9b9b"
    accent: str = "#c4a46a"
    selection: str = "#3a4a5c"
    hover: str = "#2a2a2a"
    focus: str = "#e0c89a"
    error: str = "#c45c4a"
    picked: str = "#7dcea0"
    rejected: str = "#e07a6a"
    border: str = "#3a3a3a"
    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    radius: int = 2
    border_width: int = 1
    font_size_sm: int = 11
    font_size_md: int = 13
    font_size_lg: int = 16
    font_weight_regular: int = 400
    font_weight_medium: int = 600
    line_height: int = 18
    icon_sm: int = 14
    icon_md: int = 18
    thumbnail_spacing: int = 8
    sidebar_row_height: int = 28
    toolbar_height: int = 36


TOKENS = ThemeTokens()


def stylesheet(tokens: ThemeTokens = TOKENS) -> str:
    """Project-owned QSS. Every color and measure comes from ``tokens``."""
    t = tokens
    return f"""
QWidget#themePrototype {{
  background: {t.surface_0};
  color: {t.text};
  font-size: {t.font_size_md}px;
}}
QLabel#themeTitle {{
  color: {t.text};
  font-size: {t.font_size_lg}px;
  font-weight: {t.font_weight_medium};
}}
QLabel#themeNote {{
  color: {t.text_muted};
  font-size: {t.font_size_sm}px;
}}
QFrame#themeToolbar {{
  background: {t.surface_1};
  min-height: {t.toolbar_height}px;
  max-height: {t.toolbar_height}px;
  border-bottom: {t.border_width}px solid {t.accent};
}}
QListWidget#themeSidebar {{
  background: {t.surface_1};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  outline: none;
  font-size: {t.font_size_md}px;
}}
QListWidget#themeSidebar::item {{
  min-height: {t.sidebar_row_height}px;
  padding-left: {t.space_sm}px;
  padding-right: {t.space_sm}px;
}}
QListWidget#themeSidebar::item:hover {{
  background: {t.hover};
}}
QListWidget#themeSidebar::item:selected {{
  background: {t.selection};
  color: {t.text};
}}
QListWidget#themeSidebar::item:focus {{
  border: {t.border_width}px solid {t.focus};
}}
QLineEdit#themeField {{
  background: {t.surface_2};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  border-radius: {t.radius}px;
  padding: {t.space_xs}px {t.space_sm}px;
  min-height: {t.line_height}px;
  selection-background-color: {t.selection};
}}
QLineEdit#themeField:hover {{
  background: {t.hover};
}}
QLineEdit#themeField:focus {{
  border: {t.border_width}px solid {t.focus};
}}
QLabel#pickedState {{
  color: {t.picked};
  background: {t.surface_2};
  font-size: {t.icon_md}px;
  font-weight: {t.font_weight_medium};
  padding: {t.space_xs}px {t.space_sm}px;
  border-radius: {t.radius}px;
}}
QLabel#rejectedState {{
  color: {t.rejected};
  background: {t.surface_2};
  font-size: {t.icon_md}px;
  font-weight: {t.font_weight_medium};
  padding: {t.space_xs}px {t.space_sm}px;
  border-radius: {t.radius}px;
}}
QLabel#errorState {{
  color: {t.error};
  font-size: {t.font_size_sm}px;
}}
QFrame#themeCard {{
  background: {t.surface_3};
  border: {t.border_width}px solid {t.border};
  border-radius: {t.radius}px;
}}
QMainWindow, QDialog, QMessageBox, QInputDialog {{
  background: {t.surface_0};
  color: {t.text};
  font-size: {t.font_size_md}px;
}}
QMenuBar, QMenu, QStatusBar {{
  background: {t.surface_1};
  color: {t.text};
  font-size: {t.font_size_md}px;
}}
QMenu::item {{
  color: {t.text};
  padding: {t.space_xs}px {t.space_lg}px {t.space_xs}px {t.space_md}px;
  min-height: {t.line_height}px;
}}
QMenu::item:selected, QMenu::item:hover {{
  background: {t.selection};
  color: {t.text};
}}
QMenu::separator {{
  height: {t.border_width}px;
  background: {t.border};
  margin: {t.space_xs}px {t.space_sm}px;
}}
QMenuBar::item:selected {{
  background: {t.selection};
  color: {t.text};
}}
QMessageBox QLabel, QInputDialog QLabel {{
  color: {t.text};
  background: transparent;
}}
QPushButton {{
  background: {t.surface_2};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  border-radius: {t.radius}px;
  padding: {t.space_xs}px {t.space_sm}px;
  min-height: {t.line_height}px;
}}
QPushButton:hover {{
  background: {t.hover};
}}
QPushButton:focus, QComboBox#filterControl:focus, QLineEdit:focus {{
  border: {t.border_width}px solid {t.focus};
}}
QComboBox#filterControl {{
  background: {t.surface_2};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  border-radius: {t.radius}px;
  padding: {t.space_xs}px {t.space_sm}px;
  min-height: {t.line_height}px;
}}
QComboBox#filterControl:hover {{
  background: {t.hover};
}}
QComboBox QAbstractItemView {{
  background: {t.surface_2};
  color: {t.text};
  selection-background-color: {t.selection};
  selection-color: {t.text};
}}
QListWidget#libraryViews, QListWidget#namedLists {{
  background: {t.surface_1};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  outline: none;
  font-size: {t.font_size_md}px;
}}
QListWidget#libraryViews::item, QListWidget#namedLists::item {{
  min-height: {t.sidebar_row_height}px;
  padding-left: {t.space_sm}px;
  padding-right: {t.space_sm}px;
}}
QListWidget#libraryViews::item:hover, QListWidget#namedLists::item:hover {{
  background: {t.hover};
}}
QListWidget#libraryViews::item:selected, QListWidget#namedLists::item:selected {{
  background: {t.selection};
  color: {t.text};
}}
QListWidget#libraryViews::item:focus, QListWidget#namedLists::item:focus {{
  border: {t.border_width}px solid {t.focus};
}}
QListView#mediaGrid {{
  background: {t.surface_0};
  color: {t.text};
  border: {t.border_width}px solid {t.border};
  outline: none;
}}
QListView#mediaGrid:focus {{
  border: {t.border_width}px solid {t.focus};
}}
QWidget#previewPanel {{
  background: {t.surface_1};
  color: {t.text};
}}
QLabel#previewFieldLabel {{
  color: {t.text_muted};
  font-weight: {t.font_weight_medium};
}}
QLabel#previewValue {{
  color: {t.text};
}}
QGraphicsView#previewImage {{
  background: {t.surface_0};
  border: {t.border_width}px solid {t.border};
}}
QLabel#pickedCount, QLabel#previewPicked {{
  color: {t.picked};
}}
QLabel#rejectedCount, QLabel#previewRejected {{
  color: {t.rejected};
}}
QLabel#previewUndecided {{
  color: {t.text_muted};
}}
QLabel#targetListLabel {{
  color: {t.accent};
}}
QSplitter::handle {{
  background: {t.border};
}}
""".strip() + "\n"
