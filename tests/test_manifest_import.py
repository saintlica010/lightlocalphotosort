import hashlib
from pathlib import Path

from PIL import Image

from local_media_curator.services.export_service import ExportService
from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project, open_project


def _fill(folder: Path, names: tuple[str, ...]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        Image.new("RGB", (12, 12), "red").save(folder / name, "JPEG")


def test_manifest_round_trip(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a" / "2026"
    _fill(source, ("A.jpg", "B.jpg", "C.jpg"))
    library = LibraryService(project)
    library.add_source_folder(tmp_path / "camera-a")
    library.scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"], ids["C.jpg"]])
    original_order = lists.ordered_media_ids(list_id)
    dest = tmp_path / "website.llplist.json"
    ExportService(project).export_list(list_id, dest)
    lists.replace_items(list_id, [])
    result = ExportService(project).import_list(dest)
    assert result.matched == 3
    assert result.missing == []
    assert result.ambiguous == []
    assert ListService(project).ordered_media_ids(result.list_id) == original_order
    project.close()
    reopened = open_project(tmp_path / "proj")
    website = next(row for row in ListService(reopened).all_lists() if row["name"] == "Website")
    assert ListService(reopened).ordered_media_ids(int(website["id"])) == original_order
    reopened.close()


def test_manifest_import_after_source_root_change(tmp_path: Path) -> None:
    old_project = create_project(tmp_path / "old")
    old_root = tmp_path / "D-Photos"
    _fill(old_root / "2026", ("A.jpg", "B.jpg"))
    LibraryService(old_project).add_source_folder(old_root)
    LibraryService(old_project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in old_project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(old_project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    dest = tmp_path / "website.llplist.json"
    ExportService(old_project).export_list(list_id, dest)
    old_project.close()

    new_root = tmp_path / "E-Photos"
    _fill(new_root / "2026", ("A.jpg", "B.jpg"))
    new_project = create_project(tmp_path / "new")
    LibraryService(new_project).add_source_folder(new_root)
    LibraryService(new_project).scan()
    result = ExportService(new_project).import_list(
        dest, remaps={"D-Photos": new_root}
    )
    assert result.matched == 2
    assert result.missing == []
    names = [
        row["file_name"]
        for row in new_project.connection.execute(
            """
            SELECT media.file_name FROM list_items
            JOIN media ON media.id = list_items.media_id
            WHERE list_items.list_id = ?
            ORDER BY list_items.sort_key
            """,
            (result.list_id,),
        )
    ]
    assert names == ["B.jpg", "A.jpg"]
    new_project.close()


def test_manifest_missing_media_reported(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    _fill(source, ("A.jpg",))
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["A.jpg"]])
    dest = tmp_path / "website.llplist.json"
    ExportService(project).export_list(list_id, dest)
    payload = dest.read_text(encoding="utf-8").replace("A.jpg", "GONE.jpg")
    dest.write_text(payload, encoding="utf-8")
    result = ExportService(project).import_list(dest)
    assert result.matched == 0
    assert len(result.missing) == 1
    assert result.missing[0].file_name == "GONE.jpg"
    assert ListService(project).count(result.list_id) == 0
    project.close()


def test_manifest_ambiguous_media_not_auto_matched(tmp_path: Path) -> None:
    import os

    project = create_project(tmp_path / "proj")
    one = tmp_path / "one"
    two = tmp_path / "two"
    _fill(one, ("A.jpg",))
    _fill(two, ("A.jpg",))
    stamp = 1_700_000_000
    os.utime(one / "A.jpg", (stamp, stamp))
    os.utime(two / "A.jpg", (stamp, stamp))
    library = LibraryService(project)
    library.add_source_folder(one)
    library.add_source_folder(two)
    library.scan()
    row = project.connection.execute(
        "SELECT file_size, modified_at FROM media LIMIT 1"
    ).fetchone()
    dest = tmp_path / "website.llplist.json"
    dest.write_text(
        "{\n"
        '  "format": "light-local-photo-list",\n'
        '  "version": 1,\n'
        '  "list": {"name": "Website"},\n'
        '  "items": [{\n'
        '    "order": 0,\n'
        '    "source": "other-drive",\n'
        '    "relative_path": "A.jpg",\n'
        '    "file_name": "A.jpg",\n'
        f'    "file_size": {int(row["file_size"])},\n'
        f'    "modified_at": "{row["modified_at"]}"\n'
        "  }]\n"
        "}\n",
        encoding="utf-8",
    )
    result = ExportService(project).import_list(dest)
    assert result.matched == 0
    assert len(result.ambiguous) == 1
    assert ListService(project).count(result.list_id) == 0
    project.close()


def test_import_does_not_modify_source_files(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    photo = source / "A.jpg"
    _fill(source, ("A.jpg",))
    before = hashlib.sha256(photo.read_bytes()).hexdigest()
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["A.jpg"]])
    dest = tmp_path / "website.llplist.json"
    ExportService(project).export_list(list_id, dest)
    ExportService(project).import_list(dest)
    assert hashlib.sha256(photo.read_bytes()).hexdigest() == before
    project.close()
