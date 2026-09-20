# Phase 3 Test-Bug Fixes Implementation Plan

> **SUPERSEDED.** This plan's Task 2 auto-create / Nth-list bind path is obsolete.
> Current product policy requires explicit quick-slot binding only (no auto-create
> `快捷名单 N`, no Nth-list auto-bind). See
> `docs/PHASE3_MANUAL_QUICK_SLOT_FINAL_FIX.md` and
> `docs/superpowers/plans/2026-09-20-phase3-manual-quick-slot-final.md`.
> Historical wording below is retained for audit only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three user-reported Phase 3 test issues: misaligned context-menu text, unreadable black warning/error text on the dark theme, and number keys 1–9 creating `快捷名单 N` instead of using the user's existing named lists.

**Architecture:** Keep the existing token QSS and `ListService.ensure_quick_slot`. Tighten QMenu item metrics and QMessageBox label colors in `theme.py`. Change empty-slot resolution so slot N binds to the Nth existing unbound list (current `list_all` order) before auto-creating `快捷名单 N`.

**Tech Stack:** Python 3.12, PySide6, pytest, pytest-qt. Work in `C:\downloadbook\2026shbookfair\.worktrees\fix-phase3-test-bugs` on `fix/phase3-test-bugs`. Use `.venv\Scripts\python.exe`. `QT_QPA_PLATFORM=offscreen`.

## Global Constraints

- User-facing UI is Simplified Chinese. Identifiers stay English.
- Theme colors come from `TOKENS` (`text` is `#e8e8e8`, `surface_0` is `#141414`). Do not hard-code extra palettes.
- Do not map slots to visual order on every keypress once a slot is bound. Persistence still wins.
- Auto-create `快捷名单 N` remains the fallback when there is no Nth unbound existing list.
- Lightroom export still JPEG-only (`.jpg`/`.jpeg`). Do not write XMP, `.lrcat`, or source media.
- Never modify `photos/`, `phototakeplan/`, `lightphotosprt/`. Tests use `tmp_path`.
- Never `git add .`. Do not merge `main`. Do not push unless asked.
- SCHEMA_VERSION stays 2.

---

### Task 1: Dark-theme menus and dialogs

**Files:**
- Modify: `src/local_media_curator/ui/theme.py`
- Modify: `src/local_media_curator/ui/dialogs.py` (drop the duplicate `setStyleSheet` in `warning_box`)
- Modify: `tests/test_theme.py` and/or `tests/test_theme_migration.py`

**Interfaces:**
- Consumes: `TOKENS`, `stylesheet()`
- Produces: QSS that styles `QMenu::item` with explicit padding and `color: {TOKENS.text}`, and `QMessageBox QLabel` / `QInputDialog QLabel` with `color: {TOKENS.text}` and transparent background.

Cause: styling `QMenu` without `QMenu::item` padding makes Qt keep the native icon column while the text sits in the wrong place. `QMessageBox` text is a child `QLabel` that does not inherit `QMessageBox { color }`, so it stays black on `surface_0`.

- [ ] **Step 1: Write failing tests**

In `tests/test_theme.py` (or `test_theme_migration.py`):

```python
def test_stylesheet_menu_items_have_padding_and_text_color() -> None:
    sheet = stylesheet(TOKENS)
    assert "QMenu::item" in sheet
    assert f"color: {TOKENS.text}" in sheet
    assert "padding" in sheet.split("QMenu::item", 1)[1].split("}", 1)[0]


def test_stylesheet_message_box_labels_use_text_token() -> None:
    sheet = stylesheet(TOKENS)
    assert "QMessageBox QLabel" in sheet
    block = sheet.split("QMessageBox QLabel", 1)[1].split("}", 1)[0]
    assert TOKENS.text in block
```

In `tests/test_theme_migration.py`, extend the existing warning-box test if present; otherwise add:

```python
from local_media_curator.ui.dialogs import warning_box
from PySide6.QtWidgets import QLabel, QMessageBox

def test_warning_box_labels_are_not_black(qtbot) -> None:
    box = warning_box(None, "无法导出", "当前名单中没有可用于 Lightroom RAW 匹配的 JPEG 文件。")
    qtbot.addWidget(box)
    labels = box.findChildren(QLabel)
    assert labels
    for label in labels:
        if not label.text():
            continue
        color = label.palette().color(label.foregroundRole())
        assert color.name().lower() != "#000000"
```

If the palette assertion is flaky under offscreen (stylesheet color vs palette), keep the QSS string assertions as the release gate and still construct `warning_box` to prove it applies `stylesheet()`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:QT_QPA_PLATFORM="offscreen"; .venv\Scripts\python.exe -m pytest tests/test_theme.py tests/test_theme_migration.py -q`
Expected: FAIL on missing `QMenu::item` padding / `QMessageBox QLabel`.

- [ ] **Step 3: Implement QSS**

Add after the existing `QMenu` block in `stylesheet()`:

```text
QMenu::item {
  color: {t.text};
  padding: {t.space_xs}px {t.space_lg}px {t.space_xs}px {t.space_md}px;
  min-height: {t.line_height}px;
}
QMenu::item:selected, QMenu::item:hover {
  background: {t.selection};
  color: {t.text};
}
QMenu::separator {
  height: {t.border_width}px;
  background: {t.border};
  margin: {t.space_xs}px {t.space_sm}px;
}
QMessageBox QLabel, QInputDialog QLabel {
  color: {t.text};
  background: transparent;
}
```

Remove the duplicate `box.setStyleSheet(stylesheet())` in `warning_box`.

Do not restyle native `QFileDialog`.

- [ ] **Step 4: Run tests**

Run: `$env:QT_QPA_PLATFORM="offscreen"; .venv\Scripts\python.exe -m pytest tests/test_theme.py tests/test_theme_migration.py tests/test_ui_language.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/ui/theme.py src/local_media_curator/ui/dialogs.py tests/test_theme.py tests/test_theme_migration.py
git commit -m "fix(ui): align menu text and lighten dialog labels"
```

---

### Task 2: Number keys use existing lists before auto-create

**Files:**
- Modify: `src/local_media_curator/services/list_service.py` (`ensure_quick_slot`)
- Test: `tests/test_quick_slots.py`

**Interfaces:**
- Consumes: `quick_slot_list_id`, `bind_quick_slot`, `create`, `_lists.list_all()`
- Produces: `ensure_quick_slot(slot) -> int` with this order:
  1. If the slot already has a live binding, return it (unchanged).
  2. Else if `list_all()` has at least `slot` rows, take the list at index `slot - 1`. If that list is not bound to any other slot, bind this slot to it and return its id.
  3. Else create `快捷名单 {slot}`, bind it, return it.

User report: with existing named lists, pressing 1–5 still created/used `快捷名单 1`–`5`. Auto-create must be the fallback, not the first choice.

- [ ] **Step 1: Write failing tests**

```python
def test_ensure_quick_slot_uses_existing_nth_list(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    lists = ListService(project)
    first = lists.create("宣传")
    second = lists.create("网站")
    third = lists.create("活动")
    ordered = [int(row["id"]) for row in lists.all_lists()]
    assert lists.ensure_quick_slot(1) == ordered[0]
    assert lists.ensure_quick_slot(2) == ordered[1]
    assert lists.ensure_quick_slot(3) == ordered[2]
    names = {int(row["id"]): str(row["name"]) for row in lists.all_lists()}
    assert "快捷名单 1" not in names.values()
    assert lists.quick_slot_list_id(1) == ordered[0]
    project.close()


def test_ensure_quick_slot_still_creates_when_no_nth_list(tmp_path: Path) -> None:
    project = create_project(tmp_path / "proj")
    lists = ListService(project)
    lists.create("网站")
    created = lists.ensure_quick_slot(5)
    row = next(r for r in lists.all_lists() if int(r["id"]) == created)
    assert row["name"] == "快捷名单 5"
    project.close()
```

Keep existing tests that expect `快捷名单 4` when the project has **no** prior lists.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_quick_slots.py tests/test_quick_slots_ui.py -q`
Expected: FAIL on `test_ensure_quick_slot_uses_existing_nth_list`

- [ ] **Step 3: Implement**

In `ensure_quick_slot`, after the live-binding check, look up `_lists.list_all()`, pick index `slot - 1`, skip if that id is already in `quick_slots_by_list_id()`, otherwise `bind_quick_slot` and return. Then the current auto-create path.

- [ ] **Step 4: Run tests**

Run: `$env:QT_QPA_PLATFORM="offscreen"; .venv\Scripts\python.exe -m pytest tests/test_quick_slots.py tests/test_quick_slots_ui.py tests/test_lists.py -q`
Then once: `.venv\Scripts\python.exe -m pytest -q`
Expected: PASS. Independent list order still holds.

- [ ] **Step 5: Commit**

```bash
git add src/local_media_curator/services/list_service.py tests/test_quick_slots.py
git commit -m "fix(lists): bind number keys to existing lists first"
```
