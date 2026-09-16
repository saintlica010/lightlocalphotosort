import hashlib
from pathlib import Path

from PIL import Image

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
