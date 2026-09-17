from pathlib import Path

import pytest

from local_media_curator.domain.paths import paths_overlap, reject_overlapping_roots
from local_media_curator.services.project_service import (
    create_project,
    open_project,
)


def test_create_project_layout(tmp_path: Path) -> None:
    root = tmp_path / "MyProject"
    project = create_project(root)
    assert project.root == root.resolve()
    assert project.db_path.is_file()
    assert project.thumbnails_dir.is_dir()
    assert project.logs_dir.is_dir()
    assert (root / "project.sqlite3").is_file()
    project.close()


def test_open_project_roundtrip(tmp_path: Path) -> None:
    root = tmp_path / "MyProject"
    created = create_project(root)
    created.close()
    opened = open_project(root)
    assert opened.db_path == created.db_path
    opened.close()


def test_open_missing_project_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        open_project(tmp_path / "missing")


def test_create_project_refuses_photos_tree(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="photos"):
        create_project(tmp_path / "photos" / "proj")
    assert not (tmp_path / "photos" / "proj").exists()


def test_open_project_refuses_photos_tree(tmp_path: Path) -> None:
    root = tmp_path / "photos" / "proj"
    root.mkdir(parents=True)
    (root / "project.sqlite3").write_bytes(b"")
    with pytest.raises(ValueError, match="photos"):
        open_project(root)


def test_paths_overlap_project_inside_source(tmp_path: Path) -> None:
    source = tmp_path / "Wedding2026"
    project = source / "curator-project"
    source.mkdir()
    project.mkdir()
    assert paths_overlap(project, source) is True
    with pytest.raises(ValueError, match="overlap"):
        reject_overlapping_roots(project, source)


def test_paths_overlap_source_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "MyProject"
    source = project / "inbox"
    project.mkdir()
    source.mkdir()
    assert paths_overlap(project, source) is True
    with pytest.raises(ValueError, match="overlap"):
        reject_overlapping_roots(project, source)


def test_sibling_project_and_source_allowed(tmp_path: Path) -> None:
    project = tmp_path / "MyProject"
    source = tmp_path / "Pictures"
    project.mkdir()
    source.mkdir()
    assert paths_overlap(project, source) is False
    reject_overlapping_roots(project, source)


def test_windows_case_insensitive_overlap(tmp_path: Path) -> None:
    source = tmp_path / "Pictures"
    project = source / "Proj"
    source.mkdir()
    project.mkdir()
    assert paths_overlap(project, Path(str(source).swapcase())) is True
