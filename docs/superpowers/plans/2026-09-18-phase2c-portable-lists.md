# Phase 2C Portable Lists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export and import named virtual lists as `.llplist.json` so membership and independent manual order round-trip across projects and remapped source roots, without copying or modifying source media.

**Architecture:** A pure domain document (`PortableList`) serializes to JSON. `ExportService` builds the document from `ListService` + source folders + media rows, and imports by layered matching (source+relative path, remapped root, then filename+size+mtime). Qt dialogs only choose files, collect remaps, and show a Chinese summary. No schema change.

**Tech Stack:** Python 3.12, PySide6, stdlib `json`/`pathlib`/`sqlite3`, pytest, pytest-qt. Work in `C:\downloadbook\2026shbookfair\.worktrees\codex-phase2-1` on `codex/phase2-1`. Use `.venv\Scripts\python.exe` (3.12.13). `QT_QPA_PLATFORM=offscreen` for GUI tests.

## Global Constraints

- Spec: `docs/PHASE2_PLAN.md` sections 7, 8, 15 (Phase 2C), and tests named in section 16.
- Canonical format string is exactly `light-local-photo-list`; version is integer `1`; file extension `.llplist.json`.
- Do not use absolute paths as the only identity. Matching identity is `source` + `relative_path`, then remapped root + `relative_path`, then `file_name` + `file_size` + `modified_at`.
- `relative_path` is POSIX (`2026/IMG_0001.jpg`), never an absolute path.
- `order` is 0-based and must round-trip exactly for matched items. This is release-blocking.
- Zero candidates → missing. Two or more candidates → ambiguous. Never silently choose an ambiguous candidate.
- Phase 2 export means list/manifest export, not copying physical source media.
- Never modify, rename, move, or delete source media; never write EXIF/XMP; never create caches inside source folders.
- Protected directories are read-only and never test output: `photos/`, `phototakeplan/`, `lightphotosprt/`.
- Automated tests use `tmp_path` fixtures only.
- No SQLAlchemy, Alembic, cloud, telemetry, video work, CSV/TXT/clipboard (those are Phase 2D), or schema bump. `SCHEMA_VERSION` stays 2.
- User-facing UI is Simplified Chinese. Identifiers stay English.
- Git: never `git add .`; stage explicit paths; do not merge `main`; do not push unless asked.
- Python: `.venv\Scripts\python.exe`; `QT_QPA_PLATFORM=offscreen`.
- Follow existing layers: widgets do not run SQL; services own behavior.

---

### Task 1: Portable list JSON document

**Files:**
- Create: `src/local_media_curator/domain/portable_list.py`
- Test: `tests/test_portable_list.py`

**Interfaces:**
- Consumes: stdlib `json` only
- Produces:
  - `FORMAT = "light-local-photo-list"`
  - `VERSION = 1`
  - `PortableItem(order: int, source: str, relative_path: str, file_name: str, file_size: int | None, modified_at: str | None, absolute_path: str | None = None)`
  - `PortableList(name: str, items: list[PortableItem])`
  - `to_json(document: PortableList) -> str` (UTF-8 JSON, `ensure_ascii=False`, indent 2)
  - `from_json(text: str) -> PortableList` raising `ValueError` for wrong `format`, unsupported `version`, missing `list.name`, or non-list `items`
  - JSON shape:

```json
{
  "format": "light-local-photo-list",
  "version": 1,
  "list": { "name": "Website Final" },
  "items": [
    {
      "order": 0,
      "source": "camera-a",
      "relative_path": "2026/IMG_0001.jpg",
      "file_name": "IMG_0001.jpg",
      "file_size": 8421943,
      "modified_at": "2026-08-31T20:31:12"
    }
  ]
}
```

`absolute_path` may be written as an auxiliary field but must be optional on load.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_portable_list.py
import json

import pytest

from local_media_curator.domain.portable_list import (
    FORMAT,
    VERSION,
    PortableItem,
    PortableList,
    from_json,
    to_json,
)


def test_round_trip_preserves_order_and_fields() -> None:
    document = PortableList(
        name="Website Final",
        items=[
            PortableItem(
                order=0,
                source="camera-a",
                relative_path="2026/IMG_0001.jpg",
                file_name="IMG_0001.jpg",
                file_size=8421943,
                modified_at="2026-08-31T20:31:12",
            ),
            PortableItem(
                order=1,
                source="camera-a",
                relative_path="2026/IMG_0002.jpg",
                file_name="IMG_0002.jpg",
                file_size=12,
                modified_at="2026-08-31T20:32:00",
            ),
        ],
    )
    loaded = from_json(to_json(document))
    assert loaded.name == "Website Final"
    assert [item.file_name for item in loaded.items] == ["IMG_0001.jpg", "IMG_0002.jpg"]
    assert [item.order for item in loaded.items] == [0, 1]
    payload = json.loads(to_json(document))
    assert payload["format"] == FORMAT == "light-local-photo-list"
    assert payload["version"] == VERSION == 1
    assert "absolute_path" not in payload["items"][0]


def test_from_json_rejects_wrong_format() -> None:
    with pytest.raises(ValueError):
        from_json('{"format": "other", "version": 1, "list": {"name": "A"}, "items": []}')


def test_from_json_accepts_optional_absolute_path() -> None:
    text = json.dumps(
        {
            "format": "light-local-photo-list",
            "version": 1,
            "list": {"name": "A"},
            "items": [
                {
                    "order": 0,
                    "source": "src",
                    "relative_path": "A.jpg",
                    "file_name": "A.jpg",
                    "file_size": 1,
                    "modified_at": "2026-01-01T00:00:00",
                    "absolute_path": "D:/Photos/A.jpg",
                }
            ],
        }
    )
    loaded = from_json(text)
    assert loaded.items[0].absolute_path == "D:/Photos/A.jpg"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_portable_list.py -q`
Expected: FAIL with import error for `local_media_curator.domain.portable_list`

- [ ] **Step 3: Implement `portable_list.py`**

Keep it stdlib-only. `to_json` omits `absolute_path` when it is `None`. `from_json` reads items in document order and does not sort by `order` here (export writes them already ordered).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_portable_list.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/domain/portable_list.py tests/test_portable_list.py
git commit -m "feat(export): add portable list JSON document"
```

---

### Task 2: Export a named list to `.llplist.json`

**Files:**
- Create: `src/local_media_curator/services/export_service.py`
- Test: `tests/test_manifest_export.py`

**Interfaces:**
- Consumes: `PortableList` / `PortableItem` / `to_json`; `ListService.ordered_media_ids`; `MediaRepository.get_by_ids`; `SourceFolderRepository.list_enabled`; `normalize_path`
- Produces:
  - `source_labels(folder_paths: list[str]) -> dict[str, str]` mapping normalized source path → unique label. Start with `Path(path).name`; if two folders share a name, prefix parent names with `/` until unique (`camera-a/photos` vs `camera-b/photos`).
  - `relative_to_source(absolute: str, source_root: str) -> str` using `Path.resolve().relative_to(...).as_posix()`.
  - `owning_source(absolute: str, folder_paths: list[str]) -> str | None` longest normalized prefix (folder itself or `folder + os.sep`).
  - `ExportService(project).export_list(list_id: int, destination: Path) -> PortableList` writes UTF-8 JSON, returns the document. Raises `ValueError("名单不存在。")` if the list is missing.
  - Items are written in current manual order with `order` 0..n-1.
  - `source` is the unique label of the owning source folder.
  - Do not write source bytes. Do not change source files.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_manifest_export.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_manifest_export.py -q`
Expected: FAIL importing `ExportService`

- [ ] **Step 3: Implement export**

`export_list` looks up the list name via `ListService.all_lists()`. Load media with `MediaRepository.get_by_ids(ordered_ids)` so order is preserved. Write with `destination.write_text(to_json(document), encoding="utf-8")`. Create parent dirs if needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_manifest_export.py tests/test_portable_list.py tests/test_scan_immutability.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/services/export_service.py tests/test_manifest_export.py
git commit -m "feat(export): write .llplist.json manifests"
```

---

### Task 3: Import with layered matching and exact order

**Files:**
- Modify: `src/local_media_curator/services/export_service.py`
- Modify: `src/local_media_curator/services/list_service.py` (add `replace_items`)
- Test: `tests/test_manifest_import.py`

**Interfaces:**
- Consumes: Task 1–2 APIs; `ListService.create` / `replace_items`
- Produces:
  - `ListService.replace_items(list_id: int, media_ids: list[int]) -> None` deletes current `list_items` for that list, then `add_items` in the given order (sparse keys 1024, 2048, …). Other lists are untouched.
  - `@dataclass class ImportResult: list_id: int; matched: int; missing: list[PortableItem]; ambiguous: list[PortableItem]`
  - `ExportService.import_list(path: Path, remaps: dict[str, Path] | None = None) -> ImportResult`
  - Matching, per item, stop at the first decisive level:
    1. Level 1: owning project source folder whose `source_labels` value equals `item.source`, then `normalize_path(Path(folder) / Path(relative_path))` lookup in `media.normalized_path`.
    2. Level 2: if `remaps` has `item.source`, join that root with `relative_path` and look up `normalized_path`.
    3. Level 3: candidates among remaining media where `file_name`, `file_size`, and `modified_at` all equal the item. One candidate → match. Two or more → ambiguous. Zero → missing.
  - Never auto-pick ambiguous. Matched media ids are applied in document item order (skip missing/ambiguous).
  - If a list with `document.name` exists, `replace_items` that list; otherwise `create` then `replace_items`.
  - Do not modify source files.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_manifest_import.py
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
```

Level-3 file_size/mtime: both `A.jpg` files are identical 12x12 JPEGs, so they will share size; mtime may differ by a second. If mtimes differ, set both files' mtimes equal in the test with `os.utime` before scan so level 3 truly collides. Prefer that over rewriting JSON after scan.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_manifest_import.py -q`
Expected: FAIL (`replace_items` or `import_list` missing)

- [ ] **Step 3: Implement `replace_items` and `import_list`**

`replace_items` must run in one transaction. Matching must not use `LIKE`. Use `normalize_path` for joined remapped paths. When `file_size` or `modified_at` on the item is `None`, level 3 does not match that item (treat as missing unless level 1/2 hit).

For `test_manifest_import_after_source_root_change`, export `source` label is `D-Photos` (folder name). Remap key is that label.

- [ ] **Step 4: Run tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_manifest_import.py tests/test_manifest_export.py tests/test_lists.py tests/test_scan_immutability.py -q`
Expected: PASS. Independent list order in `test_lists.py` still holds.

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/services/export_service.py src/local_media_curator/services/list_service.py tests/test_manifest_import.py
git commit -m "feat(export): import portable lists with remapping"
```

---

### Task 4: Chinese export/import UI

**Files:**
- Modify: `src/local_media_curator/ui/dialogs.py`
- Modify: `src/local_media_curator/ui/main_window.py`
- Modify: `tests/test_ui_language.py` (new action texts must stay Chinese)
- Test: `tests/test_manifest_ui.py`

**Interfaces:**
- Consumes: `ExportService.export_list` / `import_list`; existing `show_warning`, `ask_item`, `choose_existing_directory`
- Produces:
  - `choose_save_file(parent, title: str, named_filter: str, default_name: str = "") -> Path | None`
  - `choose_open_file(parent, title: str, named_filter: str) -> Path | None`
  - `show_import_summary(parent, matched: int, missing: int, ambiguous: int) -> None` with text:

```text
已匹配：{matched}
缺失：{missing}
歧义：{ambiguous}
```

  - `MainWindow` File menu actions:
    - `导出名单...` object/attr `export_list_action`
    - `导入名单...` object/attr `import_list_action`
  - Filter string: `可移植名单 (*.llplist.json)`
  - Export: require an open project; if a named list is selected in `list_panel`, export that list; otherwise `ask_item` among list names. Default filename `{name}.llplist.json`.
  - Import: open file, call `import_list`; if `missing` and the user can remap, for each distinct missing `source` label call `choose_existing_directory` with title `为源 {source} 选择新根目录`, then `import_list` again with remaps. Always show `show_import_summary`. Refresh lists/grid after a successful import (`matched > 0` or a list was created).
  - Enable both actions only when a project is open (`_set_project_actions_enabled`).
  - Do not implement CSV/TXT/clipboard.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_manifest_ui.py
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
```

Also extend `tests/test_ui_language.py` `ENGLISH_UI_WORDS` only if a new English word would false-positive; do not add Export/Import as allowed English UI.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_manifest_ui.py tests/test_ui_language.py -q`
Expected: FAIL (`export_list_action` missing)

- [ ] **Step 3: Wire menus and dialogs**

Import the new dialog helpers in `main_window.py`. Catch `ValueError` from export/import and `show_warning(self, "无法导出", str(exc))` / `"无法导入"`.

- [ ] **Step 4: Run tests**

Run: `$env:QT_QPA_PLATFORM="offscreen"; .venv\Scripts\python.exe -m pytest tests/test_manifest_ui.py tests/test_ui_language.py tests/test_manifest_import.py tests/test_manifest_export.py -q`
Then full suite once: `.venv\Scripts\python.exe -m pytest -q`
Expected: all previously passing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/ui/dialogs.py src/local_media_curator/ui/main_window.py tests/test_manifest_ui.py tests/test_ui_language.py
git commit -m "feat(ui): wire portable list export and import"
```

---

## Notes for later (out of this plan)

Phase 2D: CSV, TXT, clipboard, packaged-EXE smoke, docs closeout. Do not start 2D in these tasks.
