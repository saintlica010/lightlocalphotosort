from pathlib import Path

from PIL import Image

from local_media_curator.media.thumbnail_service import ThumbnailService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project


def test_thumbnail_written_inside_project_not_source(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (400, 300), "green").save(photo, "JPEG")
    svc = LibraryService(project)
    svc.add_source_folder(source)
    svc.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    thumbs = ThumbnailService(project)
    out = thumbs.ensure(media_id, photo)
    assert out.is_file()
    assert project.thumbnails_dir in out.parents
    assert not any(source.rglob("*.webp"))
    project.close()


def test_cached_path_does_not_render(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (40, 40), "blue").save(photo, "JPEG")
    svc = LibraryService(project)
    svc.add_source_folder(source)
    svc.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    thumbs = ThumbnailService(project)
    assert thumbs.cached_path(media_id, photo) is None
    assert not any(project.thumbnails_dir.rglob("*.webp"))
    out = thumbs.ensure(media_id, photo)
    assert thumbs.cached_path(media_id, photo) == out
    project.close()


def test_media_list_model_constructs_with_rows(qapp) -> None:
    from local_media_curator.ui.media_model import MediaListModel

    model = MediaListModel(
        [
            {"id": 1, "file_name": "A.jpg", "ordinal": 1, "rejected": False},
            {"id": 2, "file_name": "B.jpg", "ordinal": 2, "rejected": True},
        ]
    )
    assert model.rowCount() == 2
    first = model.index(0)
    second = model.index(1)
    assert model.data(first, MediaListModel.IdRole) == 1
    assert model.data(first, MediaListModel.FileNameRole) == "A.jpg"
    assert model.data(first, MediaListModel.OrdinalRole) == 1
    assert model.data(first, MediaListModel.RejectedRole) is False
    assert model.data(second, MediaListModel.IdRole) == 2
    assert model.data(second, MediaListModel.RejectedRole) is True
