import hashlib
import json
from pathlib import Path

from PIL import Image

from local_media_curator.services.export_service import ExportService, source_labels
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project


def _setup(tmp_path: Path):
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    nested = source / "2026"
    nested.mkdir(parents=True)
    for name in ("IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg"):
        Image.new("RGB", (12, 12), "red").save(nested / name, "JPEG")
    library = LibraryService(project)
    library.add_source_folder(source)
    library.scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website Final")
    lists.add_items(list_id, [ids["IMG_0002.jpg"], ids["IMG_0001.jpg"], ids["IMG_0003.jpg"]])
    return project, source, list_id, ids


def test_source_labels_disambiguate_duplicate_folder_names(tmp_path: Path) -> None:
    a = str(tmp_path / "camera-a" / "photos")
    b = str(tmp_path / "camera-b" / "photos")
    labels = source_labels([a, b])
    assert labels[a] != labels[b]
    assert labels[a].endswith("photos")
    assert "camera-a" in labels[a] or "camera-a" in labels[a].replace("\\", "/")


def test_manifest_export_preserves_order(tmp_path: Path) -> None:
    project, source, list_id, _ids = _setup(tmp_path)
    destination = tmp_path / "website.llplist.json"
    photos = list((source / "2026").glob("*.jpg"))
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos}
    document = ExportService(project).export_list(list_id, destination)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in photos}
    assert after == before
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["format"] == "light-local-photo-list"
    assert payload["list"]["name"] == "Website Final"
    assert [item["file_name"] for item in payload["items"]] == [
        "IMG_0002.jpg",
        "IMG_0001.jpg",
        "IMG_0003.jpg",
    ]
    assert [item["order"] for item in payload["items"]] == [0, 1, 2]
    assert payload["items"][0]["relative_path"] == "2026/IMG_0002.jpg"
    assert payload["items"][0]["source"] == "camera-a"
    assert "\\" not in payload["items"][0]["relative_path"]
    assert document.items[0].file_name == "IMG_0002.jpg"
    project.close()
