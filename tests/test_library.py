from pathlib import Path

from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


def _jpg(path: Path) -> None:
    Image.new("RGB", (100, 80), "red").save(path, "JPEG")


def test_scan_adds_new_images(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    _jpg(source / "A.jpg")
    _jpg(source / "B.jpg")
    svc = LibraryService(project)
    svc.add_source_folder(source)
    result = svc.scan()
    assert result.added == 2
    rows = project.connection.execute("SELECT file_name FROM media ORDER BY file_name").fetchall()
    assert [r[0] for r in rows] == ["A.jpg", "B.jpg"]
    project.close()


def test_duplicate_absolute_path_rejected(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    _jpg(source / "A.jpg")
    svc = LibraryService(project)
    svc.add_source_folder(source)
    svc.scan()
    second = svc.scan()
    assert second.added == 0
    count = project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    assert count == 1
    project.close()


def test_missing_media_detected_without_deleting_database_row(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    _jpg(photo)
    svc = LibraryService(project)
    svc.add_source_folder(source)
    svc.scan()
    photo.unlink()
    result = svc.scan()
    assert result.missing == 1
    row = project.connection.execute("SELECT missing, file_name FROM media").fetchone()
    assert row["missing"] == 1
    assert row["file_name"] == "A.jpg"
    project.close()
