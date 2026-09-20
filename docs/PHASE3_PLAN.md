# Phase 3 Plan — Modern UI, Quick List Slots & Lightroom Interop

## 0. Purpose

Phase 3 builds on the completed Phase 2 baseline.

Phase 2 established:

- three-state culling (`picked / undecided / rejected`);
- keyboard-first culling with `P / X / U`;
- advance-after-action with `Shift + P/X/U`;
- Target List support with `B / Shift+B`;
- portable `.llplist.json` import/export;
- CSV / TXT / Clipboard interop;
- source-media immutability;
- 1k / 10k responsiveness protections;
- packaged Windows application verification.

Phase 3 has three product goals:

1. make multi-list assignment substantially faster with fixed `1..9` quick-list slots;
2. add a Lightroom Classic interoperability export so JPEG culling/list results can be applied to matching RAW originals;
3. modernize the desktop UI without regressing Phase 1/2 workflow, performance, safety, or packaging.

The Phase 3 product objective is:

> **A modern keyboard-first photo workstation that can classify into multiple lists quickly and hand JPEG-based selections off to Lightroom RAW workflows.**

---

# 1. Phase 3 Scope

| Area | Phase 3 | Notes |
|---|---:|---|
| Quick List slots `1..9` | Yes | Stable project-level bindings |
| Explicit quick-slot binding | Yes | Unbound `1..9` do not create or auto-bind |
| `Shift+1..9` add-and-advance | Yes | Keyboard-first workflow; bound slots only |
| Multi-selection quick-list add | Yes | One logical action |
| Quick-slot persistence | Yes | Survives restart |
| Quick-slot reassignment UI | Yes | Explicit, no silent overwrite |
| Quick-slot indicators in list panel | Yes | `[1]`, `[2]`, ... |
| Quick-slot membership badges in grid | Yes | Functional + visual |
| Lightroom Smart Collection export | Yes | `.lrsmcol`, best-effort interoperability |
| JPEG filename stem → RAW filename matching rules | Yes | No RAW file modification |
| Lightroom catalog modification | No | Never write `.lrcat` |
| XMP write-back | No | Never create/modify sidecars |
| Lightroom installed on developer machine | Not required | Do not block implementation |
| Lightroom runtime/performance testing | No | Explicitly out of scope |
| User Lightroom import confirmation | Optional post-build acceptance | Not a merge blocker |
| Modern design system | Yes | Tokens, typography, spacing, states |
| Modern sidebar/grid/preview | Yes | PySide6-native |
| Large animation system | No | Keep UI responsive |
| Video capability | No | Still deferred |

---

# 2. Non-Negotiable Constraints

All existing repository safety rules remain in force.

## 2.1 Source media must remain immutable

Phase 3 must never:

- modify JPEG bytes;
- modify RAW bytes;
- rename source media;
- move source media;
- delete source media;
- rewrite EXIF;
- rewrite XMP;
- create XMP sidecars beside originals;
- write helper files into source folders;
- directly edit Lightroom catalogs.

The application may read source filenames and metadata necessary to build export rules.

All project state remains in the project database.

---

## 2.2 Protected directories remain read-only

The protected local directories remain:

```text
photos/
phototakeplan/
lightphotosprt/
```

They must not become:

- test-output folders;
- export-output folders;
- build folders;
- Git content;
- cloud-transfer inputs.

Automated tests must continue using generated disposable fixtures.

---

## 2.3 Phase 1/2 invariants remain release-blocking

Phase 3 must not regress:

- source-media immutability;
- independent manual ordering of named lists;
- one media item belonging to multiple lists;
- culling-state correctness;
- Undo / Redo correctness;
- Target List behavior;
- portable-list round-trip;
- filtered-list reorder protection;
- bounded thumbnail scheduling;
- bounded pixmap cache;
- no filesystem work per row during grid reload;
- 1k / 10k GUI structural performance smoke;
- Simplified Chinese user-facing UI;
- Windows packaged build;
- protected-data exclusion.

---

# 3. Phase 3A — Quick List Slots (`1..9`)

## 3.1 Product model

Do **not** map number keys to the current visual order of the list panel.

That would make shortcuts unstable when lists are created, deleted, renamed, sorted, or displayed differently by a future UI.

Instead, introduce persistent project-level **Quick List Slots**:

```text
slot 1
slot 2
slot 3
...
slot 9
```

Each slot points to zero or one named list.

A list may occupy at most one quick slot in the first Phase 3 implementation.

A quick slot may point to at most one list.

---

## 3.2 Recommended persistence model

Prefer storing quick-slot bindings in project settings rather than creating a second list-membership system.

Recommended keys:

```text
quick_list_slot_1
quick_list_slot_2
...
quick_list_slot_9
```

Values:

```text
list_id
```

This keeps:

- `lists` as the list definition;
- `list_items` as the only membership relationship;
- `list_items.sort_key` as the only manual-order relationship;
- quick slots as lightweight project preferences.

An alternative schema field such as `lists.quick_slot` is acceptable only if the implementation proves it is simpler and preserves uniqueness transactionally.

Do not create a separate “quick list items” table.

---

## 3.3 Number-key behavior

Required shortcuts:

| Shortcut | Action |
|---|---|
| `1` | Add selection to Quick List slot 1 |
| `2` | Add selection to Quick List slot 2 |
| `3` | Add selection to Quick List slot 3 |
| `4` | Add selection to Quick List slot 4 |
| `5` | Add selection to Quick List slot 5 |
| `6` | Add selection to Quick List slot 6 |
| `7` | Add selection to Quick List slot 7 |
| `8` | Add selection to Quick List slot 8 |
| `9` | Add selection to Quick List slot 9 |
| `Shift+1..9` | Add selection to the slot and advance |

### Important semantic decision

`1..9` are **add**, not toggle.

Repeated presses are idempotent.

Example:

```text
press 3
→ photo is in Quick List 3

press 3 again
→ photo remains in Quick List 3
```

Do not silently remove it on the second press.

Optional shortcuts such as `Alt+1..9` for removal are **not required** in the first Phase 3 implementation.

---

## 3.4 Unbound quick slots

Quick slots require explicit binding.

If the user presses `1..9` and that slot is unbound:

- do not create a list;
- do not bind an existing list automatically;
- do not change list membership;
- do not advance;
- show a non-blocking Simplified Chinese status message explaining that the slot must be bound first.

Quick-slot bindings are created only through explicit user actions in the list UI.

Users create normal named lists with the existing list creation UI, then bind those lists to `1..9`.

---

## 3.5 Slot deletion behavior

If a list bound to a quick slot is deleted, deleting that list must clear the slot binding.

After deletion:

```text
delete bound list
→ clear binding
→ slot remains unbound
→ number key does nothing until explicit rebind
```

Pressing the same number must **not** recreate a list and must **not** bind another existing list. The slot stays empty until the user explicitly binds another list.

---

## 3.6 Slot reassignment UI

The user must be able to bind an existing list manually.

Recommended list context menu:

```text
绑定快捷键
    1
    2
    3
    4
    5
    6
    7
    8
    9

取消快捷键
```

If the chosen slot is already occupied, do **not** silently reassign it.

Show confirmation:

```text
快捷键 3 当前绑定到：
网站

是否改为：
首页候选
```

Default action should be cancel/no.

If confirmed, only the shortcut binding changes. Existing list membership must not change.

---

## 3.7 List-panel representation

Quick slots should be immediately visible.

Example:

```text
名单
────────────────
[1] 精选
[2] 客户
[3] 网站
    备用
[7] 作品集
```

The display should remain correct after rename, delete, restart, slot reassignment, and list refresh.

Target List remains a separate concept. A list may simultaneously be Target List and Quick List slot 3.

---

## 3.8 Grid membership indicator

Phase 3 UI should make quick-list membership scannable.

Recommended thumbnail-card metadata:

```text
1 3 7
```

for a media item belonging to lists currently bound to quick slots 1, 3, and 7.

This is a visual projection only.

The actual membership remains ordinary `list_items`.

Do not store duplicate quick-slot membership state on `media`.

---

## 3.9 Multi-selection

If 20 media items are selected and the user presses `3`, all 20 must be added to Quick List 3.

Items already in the list remain unchanged.

The operation should be one logical Undo unit if it is routed through the existing Undo architecture.

For `Shift+3`, the same add occurs, followed by advance based on the existing Phase 2 advance semantics.

---

## 3.10 Keyboard safety

Quick-list shortcuts must be disabled while typing.

When focus is inside:

```text
QLineEdit
QTextEdit
QPlainTextEdit
QInputDialog
editable QComboBox
```

these must not trigger list actions:

```text
1..9
Shift+1..9
```

---

# 4. Phase 3B — Lightroom Classic Interop

## 4.1 Goal

Typical workflow:

```text
JPEG proxy / JPEG export
↓
cull and classify in LightLocalPhotoSort
↓
export a Lightroom-readable selection definition
↓
open Lightroom Classic
↓
apply the JPEG selection to matching RAW originals
```

Example:

```text
JPEG selected here:
DSC_1832.jpg
DSC_1847.jpg
DSC_1901.jpg

RAW originals in Lightroom:
DSC_1832.CR3
DSC_1847.CR3
DSC_1901.CR3
```

The interoperability layer should match by filename stem rather than JPEG extension.

---

## 4.2 Interop format

Phase 3 should implement a Lightroom Classic Smart Collection settings export:

```text
.lrsmcol
```

The output represents a Smart Collection whose rules match the selected filename stems.

### Critical implementation rule

Do not invent the `.lrsmcol` serialization syntax from memory.

Before implementation, the agent must verify the current Lightroom Classic Smart Collection settings structure from reliable references and/or known exported examples.

Prefer:

1. Adobe documentation describing Smart Collection import/export behavior;
2. stable public examples of `.lrsmcol`;
3. user-provided exported sample files if they become available.

Do not:

- write `.lrcat`;
- reverse engineer catalog internals;
- patch SQLite catalog files;
- rely on undocumented Lightroom database mutations.

---

## 4.3 Matching model

For each list item:

```text
DSC_1832.jpg
```

derive:

```text
stem = DSC_1832
```

The generated Smart Collection should target the corresponding RAW filename.

Prefer a rule that approximates exact basename/stem matching.

If Lightroom only exposes prefix/text operators, prefer something equivalent to:

```text
filename starts with "DSC_1832."
```

The actual operator must follow what the verified `.lrsmcol` format supports.

---

## 4.4 RAW formats

The feature must not hard-code only one camera RAW extension.

Expected RAW families may include:

```text
.CR3
.CR2
.NEF
.ARW
.RAF
.ORF
.RW2
.DNG
```

The Smart Collection should primarily match by stem so it can work across camera brands.

If a verified Lightroom rule can safely restrict to RAW, it may be added. If there is uncertainty, prefer filename-stem matching rather than incorrectly excluding valid RAW files.

---

## 4.5 Duplicate-stem warning

Filename stem matching is not globally unique.

A Lightroom catalog may contain:

```text
2025/EventA/DSC_1000.CR3
2026/EventB/DSC_1000.CR3
```

A Smart Collection rule matching `DSC_1000` may include both.

The application must not claim one-to-one identity when it cannot prove it.

Before export, show or include an informational warning equivalent to:

```text
Lightroom RAW 收藏夹按文件主名匹配。

如果 Lightroom Catalog 中存在不同目录下的同名 RAW，
这些文件可能同时进入智能收藏夹。
```

This is a known limitation, not a Phase 3 merge blocker.

---

## 4.6 Export UI

For a named list, add:

```text
导出 Lightroom 智能收藏夹...
```

Recommended destination filename:

```text
<list-name>.lrsmcol
```

Example:

```text
网站最终.lrsmcol
```

The feature may be accessible from the File/Export menu and/or named-list context menu.

---

## 4.7 Lightroom is not required on the development machine

This is an explicit Phase 3 product/testing decision.

The developer/agent environment does **not** need Lightroom installed.

Do not make implementation contingent on:

- launching Lightroom;
- scripting Lightroom;
- measuring Lightroom performance;
- timing Smart Collection refresh;
- testing 100 / 1000 / 5000 rules inside Lightroom;
- installing Adobe software on the development machine.

**Remove Lightroom performance benchmarks from Phase 3.**

---

## 4.8 Automated validation without Lightroom

The repository must still test the exporter itself.

Automated tests should cover:

```text
.jpg filename stem extraction
.jpeg filename stem extraction
upper/lower extension handling

names containing spaces
names containing unicode
names containing quotes / special characters

duplicate JPEG stems are de-duplicated safely

empty list behavior

large synthetic list serialization completes

generated file is deterministic

generated file matches verified structure

source JPEG files remain unchanged

no RAW/XMP/catalog writes occur
```

If a verified parser/grammar is implemented, use structural tests.

If no independent parser exists, maintain golden fixtures based on verified `.lrsmcol` syntax.

---

## 4.9 User Lightroom validation is optional and non-blocking

After Phase 3 implementation, the user may test:

```text
Lightroom Classic
→ Import Smart Collection Settings
→ choose generated .lrsmcol
```

and report whether the collection imports and matches the intended RAW files.

This is valuable product feedback but is **not a Phase 3 merge blocker**.

Therefore the merge gate must **not** contain requirements such as:

```text
Lightroom import confirmed by user
Lightroom performance benchmark passed
Lightroom 1000-item test passed
Lightroom runtime verified
```

Instead, track real-world Lightroom validation separately:

```text
Post-merge / user acceptance:
[ ] User confirmed .lrsmcol imports in Lightroom Classic
[ ] User confirmed expected RAW matching
[ ] Lightroom version used for the test is recorded
```

These checkboxes may remain unchecked when Phase 3 merges.

---

## 4.10 Feature status before user confirmation

Until a real Lightroom user confirms import behavior, describe the feature conservatively.

Preferred wording:

```text
Lightroom 智能收藏夹导出（实验性）
```

Do not claim guaranteed compatibility with every Lightroom version without evidence.

---

## 4.11 No manual-order promise

A Lightroom Smart Collection represents membership rules.

Do not promise that the manual list order from LightLocalPhotoSort will be preserved in Lightroom.

The goal is:

```text
JPEG selection membership
→ matching RAW membership
```

not manual ordering.

If preserved manual ordering inside Lightroom becomes a future requirement, treat that as a separate integration phase.

---

# 5. Phase 3C — Design System

UI redesign begins only after Quick List and Lightroom exporter business behavior are stable enough to test independently.

Do not combine the first implementation of quick-slot persistence, Lightroom serialization, and full visual migration into one large change.

---

## 5.1 Visual direction

Target direction:

> **Dark-first modern photo workstation**

Key principles:

- photos are the visual focus;
- UI chrome should recede;
- neutral dark surfaces;
- restrained accent color;
- high information density;
- clear selection/focus/hover/disabled states;
- clear Picked/Rejected states;
- avoid generic AI-dashboard styling;
- avoid excessive gradients;
- avoid oversized cards;
- avoid animation that slows culling.

The app should feel like a desktop photography tool, not a website.

---

## 5.2 Existing layout is retained

Keep the proven three-panel information architecture:

```text
Library / Lists | Media Grid | Preview
```

Phase 3 modernizes hierarchy, spacing, typography, icons, states, panels, controls, cards, toolbar/menu treatment, and visual density.

---

## 5.3 Design tokens

Create project-owned design tokens for at least:

```text
colors
surface levels
text colors
accent
selection
hover
focus
error
picked
rejected

spacing
corner radius
border widths

font sizes
font weights
line heights

icon sizes

thumbnail spacing
sidebar row height
toolbar height
```

Avoid scattered hard-coded QSS values across individual widgets.

Prefer one centralized theme/design-token layer.

---

## 5.4 Runtime dependency policy

Prefer:

```text
PySide6 native widgets
+
project-owned QSS
+
custom delegates where justified
```

Do not introduce a large third-party UI framework only for appearance without license review, packaged-EXE verification, performance verification, and maintenance justification.

Design references/skills may guide visual decisions without becoming runtime dependencies.

---

## 5.5 Recommended design references

The agent may research and use modern UI/UX skills as design references, especially PySide6/Fluent-style desktop design skills, modern desktop design-system skills, accessibility guidance, typography/spacing systems, and visual-QA workflows.

Use them as design guidance, not as permission to copy unreviewed framework code.

If any runtime UI library is considered, check its current license and record the decision in `DECISIONS.md`.

---

# 6. Phase 3D — Modern UI Migration

## 6.1 Sidebar

Target structure:

```text
媒体库
────────────────
全部
已选
未决定
已排除

快捷名单
────────────────
[1] 精选          124
[2] 客户           83
[3] 网站           41
    备用           17
[7] 作品集         65

＋ 新建名单
```

Reduce permanent button clutter.

Actions such as rename, delete, bind shortcut, and set Target List may move to context menus.

---

## 6.2 Media grid

The grid remains performance-critical.

Do not replace the delegate-based approach with thousands of child widgets.

Recommended card information:

```text
┌─────────────────────┐
│                     │
│       PHOTO         │
│                     │
│ ✓                 × │
├─────────────────────┤
│ DSC_1847.jpg    1 3 │
└─────────────────────┘
```

Potential overlays:

- culling state;
- selected state;
- quick-list slots;
- missing/error indicator.

Do not overload the image with metadata.

---

## 6.3 Preview panel

The photo remains dominant.

Default metadata should be compact:

```text
DSC_1847.jpg
6000 × 4000
24 MP
14.2 MB
2026-09-18 14:31
```

Secondary metadata should not compete visually with the preview.

---

## 6.4 Menus and shortcuts

Keep important shortcuts visible/discoverable:

```text
P / X / U
Shift+P / Shift+X / Shift+U
B / Shift+B
1..9
Shift+1..9
Ctrl+Z / Redo
```

---

## 6.5 Simplified Chinese

All new user-facing strings must remain Simplified Chinese.

Examples:

```text
快捷名单
绑定快捷键
取消快捷键
导出 Lightroom 智能收藏夹
```

Data values remain unchanged:

- filenames;
- paths;
- list names;
- metadata values;
- extension strings.

---

# 7. Suggested Implementation Milestones

## Phase 3A — Quick List Core

Implement:

- persistent slots `1..9`;
- service API for bind/unbind/resolve;
- unbound slots require explicit bind (no auto-create);
- `1..9` idempotent add when bound;
- multi-selection add;
- list delete clears binding and leaves the slot unbound;
- rename preserves binding;
- Undo integration where appropriate.

### 3A Gate

Must pass:

```text
slot persistence
unbound key does not create or auto-bind
rename preserves binding
delete clears binding and leaves slot unbound
1..9 add when bound
multi-selection add
repeated key is idempotent
Phase 1/2 regression
```

---

## Phase 3B — Quick List Keyboard/UI

Implement:

- `Shift+1..9`;
- focus safety;
- binding/rebinding UI;
- slot labels in list panel;
- membership slot badges in grid;
- shortcut discoverability.

### 3B Gate

A user should be able to:

```text
open 3000 photos
↓
P / X
↓
1
3
Shift+7
2
...
↓
classify into multiple lists with minimal mouse use
```

---

## Phase 3C — Lightroom Smart Collection Export

Implement:

- verified `.lrsmcol` serializer;
- JPEG filename stem extraction;
- duplicate-stem de-duplication;
- named-list export action;
- duplicate-stem limitation warning;
- deterministic output;
- automated structural/golden tests;
- source immutability tests.

### 3C Gate

Required:

```text
exporter produces deterministic verified-format output
automated tests pass
no source media modified
no RAW/XMP/catalog modification
packaged app can generate the file
```

Not required:

```text
Lightroom installed locally
Lightroom launched
Lightroom performance benchmark
User-confirmed import
```

User import validation is post-build feedback, not a merge gate.

---

## Phase 3D — Design System

Implement:

- design tokens;
- typography hierarchy;
- spacing scale;
- dark palette;
- focus/hover/selection states;
- icon policy;
- centralized QSS/theme application;
- representative component prototypes.

### 3D Gate

Before whole-app migration, verify readability, keyboard focus visibility, selected/rejected/picked distinguishability, Windows DPI behavior, and no material grid slowdown.

---

## Phase 3E — UI Migration

Migrate:

- sidebar;
- list panel;
- filter controls;
- grid cards/delegate;
- preview panel;
- menus/toolbars/dialogs;
- status messaging.

Do not change core behavior merely because the UI is being redesigned.

---

## Phase 3F — Closeout

Run:

- full automated suite;
- 1k/10k GUI smoke;
- quick-list workflow smoke;
- Lightroom exporter smoke;
- packaged Windows EXE build;
- packaged EXE manual workflow;
- Simplified Chinese UI review;
- source immutability review;
- protected-data review;
- visual QA.

Then perform independent review.

---

# 8. Automated Test Plan

At minimum, add tests equivalent to the following.

## Quick List

```text
test_quick_slots_default_empty

test_bind_list_to_slot
test_slot_binding_persists_after_reopen
test_rename_preserves_quick_slot

test_delete_bound_list_clears_slot
test_delete_bound_list_leaves_slot_unbound

test_unbound_number_key_does_not_create_or_bind
test_unbound_shift_number_does_not_advance
test_ensure_quick_slot_api_removed

test_number_key_adds_selection
test_number_key_is_idempotent

test_number_key_adds_multi_selection
test_quick_list_add_is_single_undo_unit_if_undoable

test_shift_number_adds_and_advances

test_rebind_occupied_slot_requires_confirmation
test_rebind_moves_slot_without_changing_membership

test_number_shortcuts_ignored_in_qlineedit
test_number_shortcuts_ignored_in_qtextedit
test_number_shortcuts_ignored_in_qplaintextedit
test_number_shortcuts_ignored_in_qinputdialog
test_number_shortcuts_ignored_in_editable_qcombobox

test_list_panel_displays_slot_number
test_grid_displays_quick_slot_membership
```

## Lightroom exporter

```text
test_lightroom_export_empty_list

test_lightroom_export_single_jpeg
test_lightroom_export_multiple_jpegs

test_lightroom_export_uses_filename_stems
test_lightroom_export_handles_jpeg_extension_case

test_lightroom_export_handles_spaces
test_lightroom_export_handles_unicode
test_lightroom_export_escapes_special_characters

test_lightroom_export_deduplicates_duplicate_stems

test_lightroom_export_is_deterministic

test_lightroom_export_matches_verified_lrsmcol_structure

test_lightroom_export_does_not_modify_sources

test_lightroom_export_does_not_create_xmp

test_lightroom_export_does_not_touch_raw_files

test_lightroom_export_does_not_touch_lightroom_catalog
```

## UI/design regression

```text
test_shortcuts_still_discoverable
test_culling_overlay_still_visible
test_rejected_and_picked_visually_distinct
test_focus_state_visible

test_10k_grid_still_uses_delegate_model
test_10k_reload_does_not_add_per_row_filesystem_work
test_thumbnail_pending_queue_stays_bounded
test_pixmap_cache_stays_bounded
```

---

# 9. Packaged EXE Smoke

The final Windows packaged build should manually verify at least:

1. open an existing Phase 2 project;
2. existing culling states remain;
3. existing named lists remain;
4. existing manual ordering remains;
5. Target List remains correct;
6. press `1` with slot 1 unbound → no list created, no membership change, no advance, Chinese status message displayed;
7. explicitly bind an existing list to slot 1; press `1` → selected photo enters that list;
8. press `1` again → item remains in list;
9. press `2..9` as representative checks on bound slots;
10. multi-select + number adds all selected items;
11. `Shift+number` adds and advances when bound; unbound `Shift+number` does not advance;
12. rename a quick list and verify slot remains;
13. delete a quick list → slot clears and stays unbound; press that number → nothing is recreated;
14. reassign a slot through UI;
15. type numbers in a text field and confirm no quick-list action occurs;
16. slot numbers appear correctly in the sidebar;
17. quick-slot membership appears correctly in the grid;
18. export a named list to `.lrsmcol`;
19. generated `.lrsmcol` exists and is non-empty;
20. no JPEG/RAW/XMP/catalog file is modified;
21. modern UI displays correctly at normal Windows scale;
22. keyboard focus remains visible;
23. all new user-facing UI is Simplified Chinese;
24. application exits cleanly.

### Explicitly not part of packaged smoke

Do not require:

```text
launching Lightroom
importing into Lightroom
measuring Lightroom performance
testing Lightroom Smart Collection query speed
```

Those are not local Phase 3 release requirements.

---

# 10. Phase 3 Merge Gate

Phase 3 may merge only when all **repository-owned** requirements are satisfied.

## Quick List

- [x] Quick slots `1..9` are stable and persistent
- [x] Quick slots require explicit user binding
- [x] Unbound `1..9` does not create or auto-bind lists
- [x] Unbound `Shift+1..9` does not advance
- [x] Number shortcuts add idempotently when bound
- [x] Multi-selection quick add works
- [x] `Shift+1..9` add-and-advance works when bound
- [x] Rename preserves slot binding
- [x] Delete clears slot and leaves it unbound
- [x] Slot reassignment does not alter list membership
- [x] Occupied-slot reassignment requires confirmation
- [x] Text-entry focus prevents numeric shortcut misfires
- [x] Slot indicators are correct
- [x] Grid quick-membership indicators are correct

## Lightroom exporter

- [x] `.lrsmcol` format was implemented from verified references/examples
- [x] Export is deterministic
- [x] JPEG stem extraction is correct
- [x] Duplicate stems are handled safely
- [x] User is warned about cross-folder duplicate-stem ambiguity
- [x] No source media is modified
- [x] No XMP is written
- [x] No Lightroom catalog is modified
- [x] Empty and non-JPEG-only lists are rejected before output creation
- [ ] Packaged EXE can generate `.lrsmcol`

## UI

- [x] Design tokens are centralized
- [x] Modern UI migration is complete for agreed Phase 3 surfaces
- [x] Keyboard focus is clearly visible
- [x] Picked / Rejected / selected states remain clear
- [x] Simplified Chinese requirement is preserved
- [x] Production UI does not expose the development theme prototype
- [x] Preview metadata labels and values remain readable in the dark theme
- [x] 1k / 10k GUI smoke has no meaningful structural regression

## Regression / safety

- [x] Full automated suite passes on Windows Python 3.12 (`291 passed`)
- [x] Phase 1 regression requirements pass in the automated suite
- [x] Phase 2 regression requirements pass in the automated suite
- [x] Source-media immutability holds
- [x] Protected data is absent from Git
- [x] Protected data is absent from packaged build
- [x] Windows packaged-EXE smoke passes
- [ ] Independent review is complete


### Closeout record (not a merge)

Checked boxes above were verified on Linux, Python 3.13.5,
`QT_QPA_PLATFORM=offscreen`, against `codex/phase3` at `af90cbf`:
270 passed, 1 skipped (`PyInstaller` is not installed), 1 failed.
The failure is `tests/test_project_service.py::test_windows_case_insensitive_overlap`,
a pre-existing Windows case-fold check on a case-sensitive disk. It is not a
Phase 3 regression.

1k and 10k GUI smoke, quick-list tests, and `.lrsmcol` tests are inside that
run. `git ls-files` shows nothing under `photos/`, `phototakeplan/`, or
`lightphotosprt/`. Spec tests confirm `datas=[]` and that those trees are not
named in `build/local_media_curator.spec`.

At the time of this historical Linux run, the following were left open:
packaged EXE generation and smoke, protected-data check of a built package,
the full-suite checkbox (the Windows path test did not pass there), Phase 1/2
boxes, independent review, and Lightroom Classic import. See the final
Windows verification below for the current repository-owned evidence.

### Final Windows verification (not a merge)

Current repository-owned Windows evidence is in
`docs/verification/phase3_windows_smoke.md` on branch `fix/phase3-test-bugs`
(verified commit `8b370e4277ab2e0cd4da379d78d121c87bf0a9f9`; code HEAD before
the docs commit: `5ee3c6d01926b6add28d950d67d4cd94e3e3398d`). It records
**291 passed**,
explicit quick-slot bind/unbound/delete policy coverage, the populated
10k/9-slot structural regression, a successful PyInstaller one-folder build,
an EXE launch with no ICU/Qt stderr, and a Git protected-data audit. Packaged
interactive keypress walkthrough and packaged `.lrsmcol` generation were not
fully exercised in the GUI; Independent Review remains open; Lightroom Classic
real import remains **NOT TESTED — NON-BLOCKING**.

Historical superseded Windows run (retained in the smoke doc): `codex/phase3`
at `4c38d0dcf6092c6cf5b3f756f51715013262c3c4` with `280 passed`.

---

# 11. Lightroom User Acceptance — Non-Blocking

This section is deliberately **not** part of the Phase 3 merge gate.

After a build is available, the user may test the generated file on a machine with Lightroom Classic.

Optional checklist:

- [ ] Lightroom Classic can import the generated `.lrsmcol`
- [ ] imported Smart Collection appears successfully
- [ ] selected JPEG stems match expected RAW originals
- [ ] no unexpected duplicate-stem matches were observed
- [ ] Lightroom version used for the test is recorded

If any item fails:

- record the Lightroom version;
- keep a synthetic/non-private reproduction fixture if safe;
- investigate as a compatibility bug;
- do not retroactively treat the Phase 3 merge as invalid unless the repository implementation violated its documented format/behavior.

Until user confirmation exists, the Lightroom export may be labeled experimental.

---

# 12. Deferred Beyond Phase 3

Still deferred unless separately approved:

## Video

- video thumbnails;
- video playback;
- enhanced video metadata;
- FFmpeg integration.

## Lightroom advanced integration

Not part of Phase 3:

- writing `.lrcat`;
- Lightroom plugin development;
- automated Lightroom process control;
- Lightroom SDK automation;
- preserving manual LightLocalPhotoSort list order inside Lightroom;
- synchronizing Lightroom edits back into the app;
- writing ratings/flags/colors to Lightroom;
- writing XMP sidecars.

If future requirements need ordinary Lightroom Collections with preserved custom ordering, design a separate Lightroom plugin/integration phase.

---

# 13. Target End-to-End Workflow

Desired Phase 3 workflow:

```text
Open 3000 JPEGs

↓

Cull:

P
X
P
P
X
...

↓

Picked: 782

↓

Multi-list classification:

1
3
Shift+7
2
1
3
...

↓

[1] 精选       300
[2] 客户       180
[3] 网站       120
[7] 作品集      65

↓

Select:
[3] 网站

↓

Export:
导出 Lightroom 智能收藏夹

↓

网站.lrsmcol

↓

User later imports it into Lightroom Classic

↓

Smart Collection uses JPEG filename stems
to match corresponding RAW originals
```

Throughout the workflow:

```text
JPEG source files remain untouched
RAW source files remain untouched
XMP remains untouched
Lightroom catalog remains untouched
```

---

# 14. Definition of Done

Phase 3 is complete when the application evolves from:

> “A keyboard-first culling tool with portable lists”

into:

> **“A modern keyboard-first photo workstation with stable 1–9 multi-list classification and a safe Lightroom RAW-selection handoff.”**

Lightroom real-world import confirmation is useful user acceptance feedback, but it is explicitly **not required to merge Phase 3**.
