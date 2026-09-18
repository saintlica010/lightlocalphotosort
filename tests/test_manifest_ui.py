from pathlib import Path

from PIL import Image

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.list_service import ListService
from local_media_curator.services.project_service import create_project
from local_media_curator.ui.main_window import MainWindow


def test_export_and_import_actions_are_chinese(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.export_list_action.text() == "导出名单..."
    assert window.import_list_action.text() == "导入名单..."


def test_export_then_import_round_trip_via_actions(qtbot, tmp_path: Path, monkeypatch) -> None:
    project = create_project(tmp_path / "proj")
    source = tmp_path / "camera-a"
    source.mkdir()
    Image.new("RGB", (12, 12), "red").save(source / "A.jpg", "JPEG")
    Image.new("RGB", (12, 12), "red").save(source / "B.jpg", "JPEG")
    LibraryService(project).add_source_folder(source)
    LibraryService(project).scan()
    ids = {
        str(row["file_name"]): int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    lists = ListService(project)
    list_id = lists.create("Website")
    lists.add_items(list_id, [ids["B.jpg"], ids["A.jpg"]])
    dest = tmp_path / "Website.llplist.json"

    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.list_panel.lists_widget.setCurrentRow(0)

    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_save_file",
        lambda *args, **kwargs: dest,
    )
    window.export_list_action.trigger()
    assert dest.is_file()

    lists.replace_items(list_id, [])
    window.refresh()
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.choose_open_file",
        lambda *args, **kwargs: dest,
    )
    monkeypatch.setattr(
        "local_media_curator.ui.main_window.show_import_summary",
        lambda *args, **kwargs: None,
    )
    window.import_list_action.trigger()
    assert ListService(project).ordered_media_ids(list_id) == [ids["B.jpg"], ids["A.jpg"]]
    project.close()
