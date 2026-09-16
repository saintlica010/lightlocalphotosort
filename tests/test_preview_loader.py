import threading
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


def test_rapid_loads_skip_obsolete_queued_work(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    paths = []
    for name in ("A.jpg", "B.jpg", "C.jpg", "D.jpg"):
        path = tmp_path / name
        Image.new("RGB", (80, 80), "white").save(path, "JPEG")
        paths.append(path)

    started: list[str] = []
    decoded: list[str] = []
    gate = threading.Event()
    release_a = threading.Event()

    from local_media_curator.media import preview_loader as module

    real = module.load_preview_image

    def slow_load(path: Path, max_edge: int):
        name = Path(path).name
        started.append(name)
        if name == "A.jpg":
            gate.set()
            release_a.wait(timeout=5)
        decoded.append(name)
        return real(path, max_edge)

    monkeypatch.setattr(module, "load_preview_image", slow_load)
    loader = module.PreviewLoader()
    loaded_tokens: list[int] = []
    loader.loaded.connect(lambda token, _image: loaded_tokens.append(int(token)))
    loader.load(str(paths[0]), 1, 400)
    qtbot.waitUntil(lambda: gate.is_set(), timeout=8000)
    loader.load(str(paths[1]), 2, 400)
    loader.load(str(paths[2]), 3, 400)
    loader.load(str(paths[3]), 4, 400)
    release_a.set()
    qtbot.waitUntil(lambda: 4 in loaded_tokens, timeout=8000)
    assert 2 not in loaded_tokens
    assert 3 not in loaded_tokens
    assert loaded_tokens[-1] == 4
    assert "B.jpg" not in decoded
    assert "C.jpg" not in decoded
