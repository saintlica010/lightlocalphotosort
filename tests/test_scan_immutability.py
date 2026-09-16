import hashlib
from pathlib import Path

import pytest
from PIL import Image

from local_media_curator.db.repositories import MediaRepository
from local_media_curator.media.scanner import scan_source_folder
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


def test_scan_does_not_modify_source_files(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (64, 64), "blue").save(photo, "JPEG")
    before = {
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
        "name": photo.name,
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
    }
    svc = LibraryService(project)
    svc.add_source_folder(source)
    svc.scan()
    after = {
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
        "name": photo.name,
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
    }
    assert after == before
    project.close()


def test_scan_rolls_back_on_write_failure(tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (16, 16), "blue").save(source / "A.jpg", "JPEG")
    Image.new("RGB", (16, 16), "green").save(source / "B.jpg", "JPEG")
    original = MediaRepository.insert
    calls = {"n": 0}

    def boom(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("forced scan failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MediaRepository, "insert", boom)
    with pytest.raises(RuntimeError, match="forced scan failure"):
        scan_source_folder(project, source)
    count = project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    assert count == 0
    project.close()
