import hashlib
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QImage

from local_media_curator.media.image_loader import load_preview_image
from local_media_curator.ui.main_window import MainWindow
from local_media_curator.ui.preview_panel import PreviewPanel


def test_preview_downsamples(tmp_path: Path) -> None:
    path = tmp_path / "big.jpg"
    Image.new("RGB", (4000, 2000), "white").save(path, "JPEG")
    image = load_preview_image(path, max_edge=800)
    assert max(image.width(), image.height()) <= 800


def test_preview_applies_exif_orientation_without_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "oriented.jpg"
    source = Image.new("RGB", (100, 50), "red")
    exif = source.getexif()
    exif[0x0112] = 6  # rotate 90 CW → 50×100
    source.save(path, "JPEG", exif=exif)
    before = {
        "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
        "mtime": path.stat().st_mtime_ns,
    }

    image = load_preview_image(path, max_edge=800)

    after = {
        "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
        "mtime": path.stat().st_mtime_ns,
    }
    assert after == before
    assert image.width() == 50
    assert image.height() == 100


def test_preview_panel_displays_metadata(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "shot.jpg"
    Image.new("RGB", (120, 80), "white").save(path, "JPEG")
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.loader.loaded, timeout=8000):
        panel.set_media(
            {
                "file_name": "shot.jpg",
                "absolute_path": str(path),
                "width": 120,
                "height": 80,
                "file_size": path.stat().st_size,
                "captured_at": "2024-01-02T03:04:05",
                "modified_at": "2024-01-02T03:04:06",
                "rejected": False,
                "lists": [],
            }
        )
    assert panel.file_name_label.text() == "shot.jpg"
    assert panel.path_label.text() == str(path)
    assert panel.dimensions_label.text() == "120 × 80"
    assert str(path.stat().st_size) in panel.size_label.text()
    assert panel.captured_at_label.text() == "2024-01-02T03:04:05"
    assert panel.modified_at_label.text() == "2024-01-02T03:04:06"
    assert panel.lists_label.text() == ""
    assert panel.rejected_label.text() == "否"
    assert not panel.image_view.image().isNull()


def test_grid_selection_loads_preview(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "a.jpg"
    Image.new("RGB", (100, 60), "blue").save(path, "JPEG")
    window = MainWindow()
    qtbot.addWidget(window)
    assert isinstance(window.preview_panel, PreviewPanel)
    window.media_grid.model.set_rows(
        [
            {
                "id": 1,
                "file_name": "a.jpg",
                "ordinal": 1,
                "rejected": False,
                "absolute_path": str(path),
                "width": 100,
                "height": 60,
                "file_size": path.stat().st_size,
                "captured_at": "2020-01-01T00:00:00",
                "modified_at": "2020-01-01T00:00:01",
            }
        ]
    )
    index = window.media_grid.model.index(0)
    with qtbot.waitSignal(window.preview_panel.loader.loaded, timeout=8000):
        window.media_grid.view.setCurrentIndex(index)
    assert window.preview_panel.file_name_label.text() == "a.jpg"
    assert window.preview_panel.path_label.text() == str(path)
    assert not window.preview_panel.image_view.image().isNull()


def test_preview_panel_ignores_stale_token(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "shot.jpg"
    Image.new("RGB", (80, 50), "white").save(path, "JPEG")
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.loader.loaded, timeout=8000):
        panel.set_media(
            {
                "file_name": "shot.jpg",
                "absolute_path": str(path),
                "width": 80,
                "height": 50,
            }
        )
    current = panel.image_view.image()
    assert not current.isNull()
    stale = QImage(12, 12, QImage.Format.Format_RGB32)
    stale.fill(0)
    panel.loader.loaded.emit(0, stale)
    shown = panel.image_view.image()
    assert shown.width() == current.width()
    assert shown.height() == current.height()


def test_open_original_uses_helper(monkeypatch, qtbot, tmp_path: Path) -> None:
    path = tmp_path / "A.jpg"
    Image.new("RGB", (20, 20), "white").save(path, "JPEG")
    panel = PreviewPanel()
    qtbot.addWidget(panel)
    seen: list[str] = []
    monkeypatch.setattr(
        "local_media_curator.media.preview_loader._open_url",
        lambda url: seen.append(url),
    )
    panel.set_media(
        {
            "file_name": "A.jpg",
            "absolute_path": str(path),
            "width": 20,
            "height": 20,
        }
    )
    panel.open_original()
    assert seen and seen[0].endswith("A.jpg")
