from local_media_curator.ui.main_window import MainWindow


def test_main_window_has_three_panels(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.library_panel is not None
    assert window.media_grid is not None
    assert window.preview_panel is not None
