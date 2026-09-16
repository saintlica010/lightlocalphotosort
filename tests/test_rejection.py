import hashlib
from pathlib import Path

from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.services.rejection_service import RejectionService
from local_media_curator.ui.library_panel import LibraryPanel


def test_reject_and_restore(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (10, 10)).save(source / "A.jpg", "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    rejection = RejectionService(project)
    rejection.reject([media_id])
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 1
    visible = lib.list_media(include_rejected=False)
    assert visible == []
    rejected = lib.list_media(include_rejected=True, rejected_only=True)
    assert [m.id for m in rejected] == [media_id]
    rejection.restore([media_id])
    assert project.connection.execute("SELECT rejected FROM media").fetchone()[0] == 0
    project.close()


def test_reject_does_not_delete_source_files(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (10, 10)).save(photo, "JPEG")
    before = {
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
        "name": photo.name,
    }
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    RejectionService(project).reject([media_id])
    after = {
        "hash": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "size": photo.stat().st_size,
        "mtime": photo.stat().st_mtime_ns,
        "name": photo.name,
    }
    assert after == before
    assert photo.is_file()
    assert project.connection.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 1
    restored = lib.list_media(include_rejected=False)
    assert restored == []
    RejectionService(project).restore([media_id])
    visible = lib.list_media()
    assert [m.id for m in visible] == [media_id]
    project.close()


def test_library_panel_has_all_unassigned_rejected_views(qtbot) -> None:
    panel = LibraryPanel()
    qtbot.addWidget(panel)
    labels = [panel.views.item(i).text() for i in range(panel.views.count())]
    assert labels == ["All", "Unassigned", "Rejected"]
