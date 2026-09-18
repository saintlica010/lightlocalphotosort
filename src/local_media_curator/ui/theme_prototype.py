"""Representative Phase 3D components. Not wired to library, lists, or export."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from local_media_curator.ui.theme import TOKENS, stylesheet


class ThemePrototype(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("themePrototype")
        self.tokens = TOKENS
        self.setStyleSheet(stylesheet(self.tokens))

        title = QLabel("设计样板")
        title.setObjectName("themeTitle")
        note = QLabel("照片是主体。样板只展示颜色和状态，不筛选、不改名单。")
        note.setObjectName("themeNote")
        note.setWordWrap(True)

        toolbar = QFrame()
        toolbar.setObjectName("themeToolbar")
        field = QLineEdit()
        field.setObjectName("themeField")
        field.setPlaceholderText("样板输入")
        self.field = field
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            TOKENS.space_sm, 0, TOKENS.space_sm, 0
        )
        toolbar_layout.addWidget(field)

        sidebar = QListWidget()
        sidebar.setObjectName("themeSidebar")
        sidebar.addItem("[1] 精选")
        sidebar.addItem("    备用")
        self.sidebar = sidebar

        card = QFrame()
        card.setObjectName("themeCard")
        picked = QLabel("✓ 已选")
        picked.setObjectName("pickedState")
        rejected = QLabel("× 已排除")
        rejected.setObjectName("rejectedState")
        self.picked = picked
        self.rejected = rejected
        states = QHBoxLayout(card)
        states.setContentsMargins(TOKENS.space_sm, TOKENS.space_sm, TOKENS.space_sm, TOKENS.space_sm)
        states.setSpacing(TOKENS.thumbnail_spacing)
        states.addWidget(picked)
        states.addWidget(rejected)
        states.addStretch(1)

        error = QLabel("缺失")
        error.setObjectName("errorState")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(TOKENS.space_md, TOKENS.space_md, TOKENS.space_md, TOKENS.space_md)
        layout.setSpacing(TOKENS.space_sm)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(toolbar)
        layout.addWidget(sidebar, stretch=1)
        layout.addWidget(card)
        layout.addWidget(error)


def open_theme_prototype(parent: QWidget | None) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("设计样板")
    dialog.resize(420, 360)
    body = ThemePrototype(dialog)
    close = QPushButton("关闭")
    close.clicked.connect(dialog.accept)
    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(0, 0, 0, TOKENS.space_sm)
    outer.addWidget(body, stretch=1)
    row = QHBoxLayout()
    row.addStretch(1)
    row.addWidget(close)
    row.setContentsMargins(TOKENS.space_md, 0, TOKENS.space_md, 0)
    outer.addLayout(row)
    dialog.exec()
