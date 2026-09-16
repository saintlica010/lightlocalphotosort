from pathlib import Path

from PIL import Image

from local_media_curator.media.preview_loader import PreviewLoader


def test_preview_loader_emits_downsampled_image(qtbot, tmp_path: Path) -> None:
    path = tmp_path / "big.jpg"
    Image.new("RGB", (1200, 800), "white").save(path, "JPEG")
    loader = PreviewLoader()
    with qtbot.waitSignal(loader.loaded, timeout=8000) as blocker:
        loader.load(str(path), token=7, max_edge=400)
    token, image = blocker.args
    assert token == 7
    assert max(image.width(), image.height()) <= 400


def test_open_path_helper(monkeypatch, tmp_path: Path) -> None:
    from local_media_curator.media.preview_loader import open_path

    seen: list[str] = []
    monkeypatch.setattr(
        "local_media_curator.media.preview_loader._open_url",
        lambda url: seen.append(url),
    )
    photo = tmp_path / "A.jpg"
    photo.write_bytes(b"x")
    open_path(photo)
    assert seen and seen[0].endswith("A.jpg")
