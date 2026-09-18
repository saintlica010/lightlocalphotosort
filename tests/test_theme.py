from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.theme import ICON_POLICY, TOKENS, ThemeTokens, stylesheet
from local_media_curator.ui.theme_prototype import ThemePrototype


def test_tokens_cover_phase3d_and_states_differ() -> None:
    tokens = ThemeTokens()
    assert tokens.picked != tokens.rejected
    assert tokens.selection != tokens.hover
    assert tokens.focus != tokens.border
    assert tokens.surface_0 != tokens.surface_3
    assert tokens.accent != tokens.error
    for name in (
        "space_xs",
        "space_sm",
        "space_md",
        "space_lg",
        "radius",
        "border_width",
        "font_size_sm",
        "font_size_md",
        "font_size_lg",
        "font_weight_regular",
        "font_weight_medium",
        "line_height",
        "icon_sm",
        "icon_md",
        "thumbnail_spacing",
        "sidebar_row_height",
        "toolbar_height",
    ):
        assert getattr(tokens, name) > 0
    assert ICON_POLICY == "text-markers"
    assert TOKENS == tokens


def test_stylesheet_is_token_driven_and_has_no_animation() -> None:
    sheet = stylesheet(TOKENS)
    for color in (
        TOKENS.surface_0,
        TOKENS.text,
        TOKENS.accent,
        TOKENS.selection,
        TOKENS.hover,
        TOKENS.focus,
        TOKENS.picked,
        TOKENS.rejected,
        TOKENS.error,
    ):
        assert color in sheet
    assert f"min-height: {TOKENS.sidebar_row_height}px" in sheet
    assert f"min-height: {TOKENS.toolbar_height}px" in sheet
    assert ":hover" in sheet
    assert ":selected" in sheet
    assert ":focus" in sheet
    lowered = sheet.lower()
    assert "animation" not in lowered
    assert "transition" not in lowered
    assert "qfluent" not in lowered


def test_prototype_uses_tokens_without_touching_main_window(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.styleSheet() == ""
    assert window.theme_prototype_action.text() == "设计样板..."
    prototype = ThemePrototype()
    qtbot.addWidget(prototype)
    sheet = prototype.styleSheet()
    assert TOKENS.picked in sheet
    assert TOKENS.rejected in sheet
    assert prototype.picked.text() == "✓ 已选"
    assert prototype.rejected.text() == "× 已排除"
    assert prototype.picked.objectName() != prototype.rejected.objectName()
    assert prototype.field.objectName() == "themeField"
