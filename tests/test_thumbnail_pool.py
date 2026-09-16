from pathlib import Path

from PIL import Image
from PySide6.QtCore import QCoreApplication

from local_media_curator.media.thumbnail_pool import MAX_WORKERS, ThumbnailPool
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.media_model import MediaListModel


def test_thumbnail_pool_emits_ready(qtbot, tmp_path: Path) -> None:
    assert QCoreApplication.instance() is not None
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (80, 80), "red").save(photo, "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    pool = ThumbnailPool(project)
    assert pool.max_workers == MAX_WORKERS
    with qtbot.waitSignal(pool.ready, timeout=8000) as blocker:
        pool.request([(int(media_id), str(photo))])
    assert blocker.args[0] == media_id
    out = Path(blocker.args[1])
    assert out.is_file()
    assert project.thumbnails_dir in out.parents
    project.close()


def test_thumbnail_pool_skips_missing_source(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "src"
    source.mkdir()
    photo = source / "A.jpg"
    Image.new("RGB", (40, 40), "green").save(photo, "JPEG")
    lib = LibraryService(project)
    lib.add_source_folder(source)
    lib.scan()
    media_id = int(project.connection.execute("SELECT id FROM media").fetchone()[0])
    pool = ThumbnailPool(project)
    with qtbot.waitSignal(pool.ready, timeout=8000) as blocker:
        pool.request([(999, str(tmp_path / "missing.jpg")), (media_id, str(photo))])
    assert blocker.args[0] == media_id
    assert Path(blocker.args[1]).is_file()
    project.close()


def test_set_thumbnail_path_emits_data_changed(qtbot) -> None:
    model = MediaListModel(
        [
            {"id": 1, "file_name": "A.jpg", "ordinal": 1, "rejected": False},
            {"id": 2, "file_name": "B.jpg", "ordinal": 2, "rejected": True},
        ]
    )
    resets: list[int] = []
    model.modelReset.connect(lambda: resets.append(1))
    with qtbot.waitSignal(model.dataChanged, timeout=1000) as blocker:
        model.set_thumbnail_path(2, "/tmp/b.webp")
    top, bottom, *_rest = blocker.args
    assert top.row() == 1
    assert bottom.row() == 1
    assert resets == []
    assert model.data(model.index(1), MediaListModel.ThumbnailPathRole) == "/tmp/b.webp"
    assert model.data(model.index(0), MediaListModel.ThumbnailPathRole) is None


def test_pool_sync_bounds_pending_and_promotes_visible(qtbot, tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    pool = ThumbnailPool(project)
    needed = {i: str(tmp_path / f"{i}.jpg") for i in range(10_000)}
    pool.sync(needed, visible_ids=list(range(10)))
    assert len(pool.pending_ids()) + len(pool.inflight_ids()) <= 64
    first_pending = pool.pending_ids()
    assert 9999 not in first_pending
    pool.sync(needed, visible_ids=[9999])
    ordered = list(pool.inflight_ids()) + pool.pending_ids()
    assert 9999 in ordered
    assert ordered[0] == 9999 or 9999 in pool.inflight_ids()
    assert len(pool.pending_ids()) + len(pool.inflight_ids()) <= 64
    pool.clear()
    project.close()
