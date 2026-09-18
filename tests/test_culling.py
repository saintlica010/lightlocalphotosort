from pathlib import Path

from PIL import Image
from PySide6.QtGui import QKeySequence

from local_media_curator.services.library_service import LibraryService
from local_media_curator.services.project_service import create_project
from local_media_curator.services.rejection_service import RejectionService
from local_media_curator.services.undo_commands import CurationUndoStack
from local_media_curator.ui.main_window import MainWindow


def _setup(tmp_path: Path, names: tuple[str, ...] = ("A.jpg", "B.jpg", "C.jpg")):
    project = create_project(tmp_path / "project")
    source = tmp_path / "source"
    source.mkdir()
    for name in names:
        Image.new("RGB", (12, 12), "red").save(source / name, "JPEG")
    library = LibraryService(project)
    library.add_source_folder(source)
    library.scan()
    ids = {
        row["file_name"]: int(row["id"])
        for row in project.connection.execute("SELECT id, file_name FROM media")
    }
    return project, library, ids


def test_new_media_defaults_to_undecided(tmp_path: Path) -> None:
    project, library, ids = _setup(tmp_path, ("A.jpg",))
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "undecided"
    assert library.list_media(culling_state="undecided")[0].culling_state == "undecided"
    project.close()


def test_culling_state_filters_and_counts(tmp_path: Path) -> None:
    project, library, ids = _setup(tmp_path)
    service = RejectionService(project)
    service.set_state([ids["A.jpg"]], "picked")
    service.set_state([ids["B.jpg"]], "rejected")
    assert [item.file_name for item in library.list_media(culling_state="picked")] == ["A.jpg"]
    assert [item.file_name for item in library.list_media(culling_state="undecided")] == ["C.jpg"]
    assert [item.file_name for item in library.list_media(culling_state="rejected")] == ["B.jpg"]
    assert library.culling_counts() == {"picked": 1, "undecided": 1, "rejected": 1}
    project.close()


def test_all_view_contains_all_culling_states(qtbot, tmp_path: Path) -> None:
    project, library, ids = _setup(tmp_path)
    service = RejectionService(project)
    service.set_state([ids["A.jpg"]], "picked")
    service.set_state([ids["B.jpg"]], "rejected")
    assert sorted(
        item.file_name for item in library.list_media(include_rejected=True)
    ) == ["A.jpg", "B.jpg", "C.jpg"]
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.show_library_view("all")
    assert window.media_grid.model.rowCount() == 3
    assert sorted(
        window.media_grid.model.row_at(i)["file_name"] for i in range(3)
    ) == ["A.jpg", "B.jpg", "C.jpg"]
    project.close()


def test_bulk_culling_is_one_undo_unit_and_restores_mixed_states(tmp_path: Path) -> None:
    project, _library, ids = _setup(tmp_path)
    stack = CurationUndoStack(project)
    stack.set_culling_state([ids["A.jpg"]], "picked")
    stack.set_culling_state([ids["B.jpg"]], "rejected")
    before_count = stack._stack.count()
    stack.set_culling_state(
        [ids["A.jpg"], ids["B.jpg"], ids["C.jpg"]], "picked"
    )
    assert stack._stack.count() == before_count + 1
    assert all(
        row["culling_state"] == "picked"
        for row in project.connection.execute("SELECT culling_state FROM media")
    )
    stack.undo()
    states = {
        row["file_name"]: row["culling_state"]
        for row in project.connection.execute("SELECT file_name, culling_state FROM media")
    }
    assert states == {"A.jpg": "picked", "B.jpg": "rejected", "C.jpg": "undecided"}
    stack.redo()
    assert all(
        row["culling_state"] == "picked"
        for row in project.connection.execute("SELECT culling_state FROM media")
    )
    project.close()


def test_p_x_u_shortcuts_update_single_selection(qtbot, tmp_path: Path) -> None:
    project, _library, ids = _setup(tmp_path, ("A.jpg",))
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.media_grid.view.setCurrentIndex(window.media_grid.model.index(0))

    window.pick_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "picked"
    window.culling_reject_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "rejected"
    window.undecide_action.trigger()
    assert project.connection.execute(
        "SELECT culling_state FROM media WHERE id = ?", (ids["A.jpg"],)
    ).fetchone()[0] == "undecided"
    assert window.pick_action.shortcut() == QKeySequence("P")
    assert window.culling_reject_action.shortcut() == QKeySequence("X")
    assert window.undecide_action.shortcut() == QKeySequence("U")
    project.close()


def test_culling_views_and_live_counts(qtbot, tmp_path: Path) -> None:
    project, _library, ids = _setup(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_project(project)
    window.set_culling_state("picked", [ids["A.jpg"]])
    window.set_culling_state("rejected", [ids["B.jpg"]])
    window.show_library_view("picked")
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "A.jpg"
    window.show_library_view("undecided")
    assert window.media_grid.model.rowCount() == 1
    assert window.media_grid.model.row_at(0)["file_name"] == "C.jpg"
    assert window.library_panel.culling_count_labels["picked"].text() == "已选：1"
    assert window.library_panel.culling_count_labels["undecided"].text() == "未决定：1"
    assert window.library_panel.culling_count_labels["rejected"].text() == "已排除：1"
    project.close()
