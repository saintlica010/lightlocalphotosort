import hashlib
from pathlib import Path

from PIL import Image

from local_media_curator.domain.lightroom_smart_collection import (
    DUPLICATE_STEM_WARNING,
    jpeg_stem,
    render_lrsmcol,
    unique_jpeg_stems,
)
from local_media_curator.services.export_service import ExportService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow


def _jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), "red").save(path, "JPEG")


def _project(tmp_path: Path, files: dict[str, str]):
    """files maps relative posix path -> how to write: jpeg or raw bytes."""
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera"
    for rel, kind in files.items():
        path = source / rel
        if kind == "jpeg":
            _jpeg(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(kind if isinstance(kind, bytes) else b"not-a-photo")
    library = LibraryService(project)
    library.add_source_folder(source)
    library.scan()
    return project, source


def _fingerprint(root: Path) -> dict[str, str]:
    found = {}
    for path in root.rglob("*"):
        if path.is_file():
            found[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def test_jpeg_stem_extension_case_and_non_jpeg() -> None:
    assert jpeg_stem("DSC_1832.jpg") == "DSC_1832"
    assert jpeg_stem("DSC_1832.JPEG") == "DSC_1832"
    assert jpeg_stem("DSC_1832.jpeg") == "DSC_1832"
    assert jpeg_stem("DSC_1832.CR3") is None
    assert jpeg_stem("my photo.jpg") == "my photo"
    assert jpeg_stem("照片.jpg") == "照片"


def test_render_matches_verified_lrsmcol_structure() -> None:
    text = render_lrsmcol("网站最终", ["DSC_1832"])
    assert 'type = "LibrarySmartCollection"' in text
    assert "version = 0" in text
    assert 'criteria = "filename"' in text
    assert 'operation = "beginsWith"' in text
    assert 'value = "DSC_1832."' in text
    assert 'value2 = ""' in text
    assert 'combine = "union"' in text
    assert text.startswith("s = {\n")
    assert text.endswith("}\n")


def test_render_escapes_and_is_deterministic() -> None:
    first = render_lrsmcol('网站"最终', ['say "hi', "我的 照片", "a\\b"])
    second = render_lrsmcol('网站"最终', ["a\\b", "我的 照片", 'say "hi'])
    assert first == second
    assert 'value = "a\\\\b."' in first
    assert 'value = "say \\"hi."' in first
    assert 'value = "我的 照片."' in first
    assert 'title = "网站\\"最终"' in first


def test_render_large_list_is_deterministic() -> None:
    stems = [f"DSC_{index:04d}" for index in range(2000)]
    first = render_lrsmcol("big", stems)
    assert first.count('operation = "beginsWith"') == 2000
    assert render_lrsmcol("big", list(reversed(stems))) == first


def test_lightroom_export_empty_list(tmp_path: Path) -> None:
    project, _source = _project(tmp_path, {"A.jpg": "jpeg"})
    list_id = ListService(project).create("空名单")
    destination = tmp_path / "空名单.lrsmcol"
    ExportService(project).export_lightroom_smart_collection(list_id, destination)
    text = destination.read_text(encoding="utf-8")
    assert 'criteria = "filename"' not in text
    assert 'combine = "union"' in text
    project.close()


def test_lightroom_export_uses_stems_and_dedupes(tmp_path: Path) -> None:
    project, source = _project(
        tmp_path,
        {
            "a/DSC_1832.jpg": "jpeg",
            "b/DSC_1832.JPEG": "jpeg",
            "c/Photo Name.jpeg": "jpeg",
            "d/note.png": "jpeg",
        },
    )
    # note.png was written as jpeg bytes but named png; scanner may still index it.
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("网站")
    lists.add_items(list_id, list(ids.values()))
    destination = tmp_path / "网站.lrsmcol"
    ExportService(project).export_lightroom_smart_collection(list_id, destination)
    text = destination.read_text(encoding="utf-8")
    assert text.count('value = "DSC_1832."') == 1
    assert 'value = "Photo Name."' in text
    assert ".png" not in text
    assert source.joinpath("a/DSC_1832.jpg").is_file()
    project.close()


def test_lightroom_export_is_deterministic(tmp_path: Path) -> None:
    project, _source = _project(tmp_path, {"DSC_1901.jpg": "jpeg"})
    lists = ListService(project)
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    list_id = lists.create("作品集")
    lists.add_items(list_id, [media_id])
    first = tmp_path / "a.lrsmcol"
    second = tmp_path / "b.lrsmcol"
    service = ExportService(project)
    service.export_lightroom_smart_collection(list_id, first)
    service.export_lightroom_smart_collection(list_id, second)
    assert first.read_bytes() == second.read_bytes()
    project.close()


def test_lightroom_export_does_not_touch_sources(tmp_path: Path) -> None:
    project, source = _project(tmp_path, {"DSC_1832.jpg": "jpeg"})
    raw = source / "DSC_1832.CR3"
    xmp = source / "DSC_1832.xmp"
    catalog = source / "catalog.lrcat"
    raw.write_bytes(b"RAWDATA")
    xmp.write_bytes(b"<xmp>")
    catalog.write_bytes(b"LRDB")
    before = _fingerprint(source)
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    list_id = ListService(project).create("网站")
    ListService(project).add_items(list_id, [media_id])
    ExportService(project).export_lightroom_smart_collection(
        list_id, tmp_path / "网站.lrsmcol"
    )
    assert _fingerprint(source) == before
    assert not (tmp_path / "proj").joinpath("catalog.lrcat").exists()
    project.close()


def test_export_action_is_experimental_and_warns(qtbot, tmp_path, monkeypatch) -> None:
    project, _source = _project(tmp_path, {"DSC_1832.jpg": "jpeg"})
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    media_id = project.connection.execute("SELECT id FROM media").fetchone()[0]
    list_id = window.list_service.create("网站最终")
    window.list_service.add_items(list_id, [media_id])
    window.refresh()
    window.list_panel.lists_widget.setCurrentRow(0)
    assert "实验性" in window.export_lightroom_action.text()
    menu = window.list_panel.context_menu_for(list_id)
    assert any("实验性" in action.text() for action in menu.actions())

    shown: list[tuple] = []
    destination = tmp_path / "网站最终.lrsmcol"

    def fake_warning(_parent, title, text):
        shown.append((title, text))

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_warning", fake_warning
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_save_file",
        lambda *_args, **_kwargs: destination,
    )
    window.export_lightroom_action.trigger()
    assert shown
    assert shown[0][0] == "Lightroom 智能收藏夹导出（实验性）"
    assert shown[0][1] == DUPLICATE_STEM_WARNING
    assert "同名 RAW" in shown[0][1]
    assert destination.is_file()
    assert 'operation = "beginsWith"' in destination.read_text(encoding="utf-8")
    project.close()


def test_unique_stems_helper_sorts() -> None:
    assert unique_jpeg_stems(["b.JPG", "a.jpeg", "b.jpg", "c.CR3"]) == ["a", "b"]
