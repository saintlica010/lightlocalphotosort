# Phase 2 — Keyboard-first Culling & Portable Lists

## 1. Phase 2 Objective

Phase 2 focuses on improving the real photo-curation workflow rather than expanding media-type support.

Core goals:

- rapidly classify photos;
- support keyboard-first high-frequency workflows;
- quickly assign photos to a target list;
- export and import portable reusable lists;
- preserve source-media immutability;
- preserve the performance, safety, and recoverability established in Phase 1.

The product goal for Phase 2 is:

> **Pick fast, classify fast, and carry lists anywhere.**

---

## 2. Scope

| Module | Phase 2 | Goal |
|---|---:|---|
| Three-state culling | Yes | Picked / Undecided / Rejected |
| Keyboard culling | Yes | P / X / U |
| Advance-after-action | Yes | Shift + P/X/U |
| Target List | Yes | One active destination list |
| Quick list assignment | Yes | B / Shift+B |
| Multi-selection operations | Yes | Bulk culling and list membership |
| Undo / Redo | Yes | All new actions undoable |
| State filters | Yes | Picked / Undecided / Rejected |
| State counters | Yes | Live counts |
| JSON list export | Yes | Portable round-trip format |
| JSON list import | Yes | Cross-project / cross-machine reuse |
| Source-root remapping | Yes | Reuse after drive/root changes |
| CSV export | Yes | Excel / Numbers / scripts |
| TXT export | Yes | Simple filename/path lists |
| Clipboard export | Yes | Fast reuse in other tools |
| Physical media copy export | No | Deferred |
| Video thumbnails | No | Deferred |
| Video playback | No | Deferred |
| Full UI redesign | No | Phase 3 |

---

# 3. Phase 2A — Culling Core

## 3.1 Three-state culling model

Introduce an explicit three-state model:

```text
Undecided
Picked
Rejected
```

Recommended field:

```text
culling_state
```

Recommended values:

```text
undecided
picked
rejected
```

Do not model this with independent booleans such as `picked` and `rejected`, because that permits invalid states.

## 3.2 Database migration

Upgrade schema version 1 → 2.

Migration:

```text
old rejected = 1
    → culling_state = rejected

old rejected = 0
    → culling_state = undecided
```

Requirements:

- existing Phase 1 projects migrate without data loss;
- named lists remain unchanged;
- manual list order remains unchanged;
- previous rejected state migrates correctly;
- source-media files remain untouched.

## 3.3 Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `P` | Mark as Picked |
| `X` | Mark as Rejected |
| `U` | Mark as Undecided |
| `Shift + P` | Mark Picked and advance |
| `Shift + X` | Mark Rejected and advance |
| `Shift + U` | Mark Undecided and advance |

Requirements:

- single selection;
- multiple selection;
- Undo;
- Redo;
- bulk action must be one undo unit.

---

# 4. Phase 2B — Keyboard Workflow and Target List

## 4.1 Target List

Introduce one active Target List.

Example:

```text
★ Website Photos
```

Provide:

```text
Set as Target List
```

and expose the current target in the UI.

The target list must persist with the project.

## 4.2 Target List shortcuts

| Shortcut | Action |
|---|---|
| `B` | Toggle selected media in/out of the Target List |
| `Shift + B` | Add to Target List and advance |

Recommended multi-selection semantics:

```text
If all selected items are already in Target List:
    remove all selected items
Else:
    add all selected items
```

Do not add Alt+1 ... Alt+9 quick-list bindings in the first Phase 2 implementation.

---

# 5. Culling Views and Counters

Add:

```text
All
Picked
Undecided
Rejected
```

Show live counts, for example:

```text
Picked       348
Undecided   1247
Rejected     905
```

Primary workflow:

```text
Undecided (3000)
↓
P / X culling
↓
Undecided (0)
```

---

# 6. Thumbnail State Overlay

Recommended semantics:

```text
Picked      ✓
Rejected    ×
Undecided   no extra marker
```

Requirements:

- do not obscure the image unnecessarily;
- do not rely on color alone;
- remain clear during multi-selection;
- do not create one QWidget per media item;
- do not regress 10k-grid performance.

Prefer drawing in the existing thumbnail delegate.

---

# 7. Portable List Format

Phase 2 “Export” means:

> **Export the list/manifest, not the source media by default.**

Canonical format:

```text
.llplist.json
```

Example:

```json
{
  "format": "light-local-photo-list",
  "version": 1,
  "list": {
    "name": "Website Final"
  },
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

Do not use absolute paths as the only identity.

Prefer:

```text
source identifier
relative_path
file_name
file_size
modified_at
```

Absolute paths may be auxiliary only.

Manual list order must round-trip exactly. This is release-blocking.

---

# 8. Portable List Import

Use deterministic layered matching.

## Level 1 — exact source + relative path

```text
source root
+
relative_path
```

## Level 2 — remapped source root

Allow the user to specify a new root and retry:

```text
new source root
+
relative_path
```

## Level 3 — candidate matching

Use:

```text
file_name
+
file_size
+
modified_at
```

as candidate evidence.

## Level 4 — ambiguous or missing

Zero candidates:

```text
missing
```

Two or more candidates:

```text
ambiguous
```

Never silently choose an ambiguous candidate.

Show an import summary such as:

```text
Matched:    284
Missing:      7
Ambiguous:    2
```

---

# 9. CSV / TXT / Clipboard Interop

## 9.1 CSV

```csv
order,file_name,relative_path
1,IMG_0001.jpg,2026/IMG_0001.jpg
2,IMG_0038.jpg,2026/IMG_0038.jpg
```

## 9.2 TXT

```text
IMG_0001.jpg
IMG_0038.jpg
IMG_0082.jpg
```

## 9.3 Clipboard

Provide:

```text
Copy filenames
Copy absolute paths
Copy relative paths
```

---

# 10. Keyboard Safety

When a text-editing widget has focus, including:

```text
QLineEdit
QTextEdit
QPlainTextEdit
QInputDialog
editable QComboBox
```

these keys must not trigger media actions:

```text
P
X
U
B
```

Menus must expose the shortcuts so they are discoverable.

All user-facing labels remain Simplified Chinese.

---

# 11. Undo / Redo

Continue using the existing curation undo stack.

Do not introduce a second undo system.

Add commands equivalent to:

```text
SetCullingStateCommand
BulkSetCullingStateCommand
```

Target-list membership should reuse the existing membership undo architecture where possible.

---

# 12. Database Change Boundary

Keep schema changes minimal.

Recommended primary schema v2 addition:

```text
media.culling_state
```

Target List persistence may use a lightweight project-settings mechanism such as:

```text
project_settings
    target_list_id
```

Do not introduce:

- SQLAlchemy;
- Alembic;
- a new ORM;
- an event-store architecture.

Continue using:

```text
sqlite3
+
PRAGMA user_version
```

---

# 13. UI Change Boundary

Phase 2 includes only functional UI changes:

- culling-state badges;
- Target List indicator;
- shortcut labels;
- culling filters;
- state counters;
- export dialogs;
- import-result dialogs.

Do not perform the full visual redesign in Phase 2.

Defer to Phase 3:

- global theme replacement;
- complete layout redesign;
- major animation work;
- full icon-system replacement;
- Fluent/Material component migration;
- dark-mode redesign.

---

# 14. Video Capability

Video work is explicitly deferred by product decision.

Do not implement in Phase 2:

- video thumbnails;
- enhanced video metadata;
- video playback;
- video timeline/seek;
- FFmpeg integration.

Existing `.mp4` / `.mov` support remains at reduced-functionality level.

Agents must not begin video work simply because older planning documents listed it under Phase 2.

---

# 15. Implementation Milestones

## Phase 2A — Culling Core

Implement:

- schema v2;
- `culling_state`;
- v1 → v2 migration;
- P / X / U;
- multi-selection culling;
- Undo / Redo;
- Picked / Undecided / Rejected views;
- state counts;
- thumbnail state overlay.

### Phase 2A Gate

Must pass:

```text
v1 project migration
P / X / U
bulk P / X / U
Undo / Redo
state filters
state counts
source immutability
1k / 10k regression
```

Do not begin Phase 2B until 2A is independently reviewed.

## Phase 2B — Keyboard Workflow

Implement:

- Shift + P;
- Shift + X;
- Shift + U;
- Target List;
- Target List persistence;
- B;
- Shift + B;
- multi-selection Target List operation;
- keyboard focus safety;
- visible menu shortcuts.

### Phase 2B Gate

The user should be able to cull and assign photos with minimal mouse use.

## Phase 2C — Portable Lists

Implement:

- `.llplist.json`;
- JSON export;
- JSON import;
- manual-order round-trip;
- source-root remapping;
- missing-item reporting;
- ambiguous-item reporting.

### Phase 2C Gate

Export → close/reopen or use another project → import → membership restored → manual order identical.

Also test source-root relocation such as:

```text
D:\Photos
→
E:\Photos
```

## Phase 2D — Interop and Closeout

Implement:

- CSV export;
- TXT export;
- clipboard export;
- export/import UI polish;
- complete regression;
- performance validation;
- Windows packaged-EXE smoke;
- Phase 2 documentation updates.

Then perform an independent review before merge.

---

# 16. Automated Test Plan

At minimum, add tests equivalent to:

```text
test_schema_v1_migrates_to_v2

test_new_media_defaults_to_undecided

test_p_marks_picked
test_x_marks_rejected
test_u_marks_undecided

test_p_then_x_results_in_rejected

test_bulk_pick
test_bulk_reject
test_bulk_reset

test_bulk_culling_is_single_undo_unit

test_shift_p_advances
test_shift_x_advances
test_shift_u_advances

test_target_list_persists

test_b_adds_to_target_list
test_b_removes_from_target_list
test_shift_b_advances

test_shortcuts_ignored_when_editing_text

test_filter_picked
test_filter_undecided
test_filter_rejected

test_culling_counts

test_thumbnail_overlay_state

test_manifest_export_preserves_order

test_manifest_round_trip

test_manifest_import_after_source_root_change

test_manifest_missing_media_reported

test_manifest_ambiguous_media_not_auto_matched

test_csv_export

test_txt_export

test_clipboard_file_names

test_clipboard_absolute_paths

test_clipboard_relative_paths

test_source_files_remain_unchanged
```

---

# 17. Phase 1 Regression Requirements

Phase 2 must preserve:

```text
one media can exist in multiple lists

independent list ordering

filtered-list reorder remains disabled

Undo / Redo correctness

Reject / Restore migration compatibility

scan cancellation

scan progress

source immutability

read-only source-folder support

thumbnail bounded pending queue

bounded pixmap cache

preview latest-selection-wins

1k GUI smoke

10k GUI smoke

packaged EXE launch

Simplified Chinese user-facing UI

protected data excluded from Git/build
```

---

# 18. Packaged EXE Smoke

The final packaged Windows build must manually verify at least:

1. open an existing Phase 1 project;
2. schema migration succeeds;
3. existing lists remain;
4. existing manual list order remains;
5. previous rejected items migrate correctly;
6. P works;
7. X works;
8. U works;
9. Shift+P/X/U work;
10. Target List works;
11. B works;
12. Shift+B works;
13. Undo / Redo works;
14. typing in input dialogs does not trigger shortcuts;
15. culling-state filters work;
16. state counts are correct;
17. JSON list export works;
18. JSON list import works;
19. list-order round-trip is exact;
20. CSV export works;
21. TXT export works;
22. Clipboard export works;
23. all new user-facing UI is Simplified Chinese;
24. source-media files remain unchanged.

---

# 19. Phase 2 Merge Gate

Phase 2 may merge to `main` only when all items below are satisfied:

- [x] Schema v1 → v2 migration has no data loss
- [x] Picked / Undecided / Rejected model is correct
- [x] P / X / U work correctly
- [x] Shift + P/X/U work correctly
- [x] Multi-selection culling works correctly
- [x] Bulk culling is one Undo unit
- [x] Target List works
- [x] Target List persists
- [x] B / Shift+B work correctly
- [x] Text-entry focus prevents shortcut misfires
- [x] Culling filters are correct
- [x] State counts are correct
- [x] Thumbnail overlays are correct
- [x] JSON manifest export works
- [x] JSON manifest import works
- [x] Manual list order round-trips exactly
- [x] Source root can be remapped
- [x] Missing items are reported
- [x] Ambiguous items are never silently auto-matched
- [x] CSV export works
- [x] TXT export works
- [x] Clipboard export works
- [x] Full Phase 1 regression suite passes
- [x] 1k / 10k GUI performance has no meaningful regression
- [x] Source-media immutability still holds
- [x] Protected data is absent from Git
- [x] Protected data is absent from packaged build
- [x] Windows packaged-EXE smoke passes
- [x] All new user-facing UI is Simplified Chinese
- [ ] Independent review is complete

---

# 20. Deferred Work

## Video

Explicitly deferred:

- video thumbnails;
- video metadata enhancement;
- video playback;
- FFmpeg integration.

## Physical Media Export

Do not implement copying the actual photo files as part of the primary Phase 2 export workflow.

Phase 2 export means:

```text
portable list / manifest export
```

## Full UI Redesign

The following belong to Phase 3:

- modern design system;
- typography system;
- spacing system;
- modern sidebar;
- redesigned thumbnail cards;
- icon system;
- dark mode;
- animation;
- visual hierarchy;
- full modern desktop UI/UX pass.

---

# 21. Phase 3 Preview

Phase 3 is tentatively:

```text
Phase 3 — Modern UI / UX
```

Objective:

> Modernize the application visually and ergonomically without breaking Phase 1/2 behavior or performance.

Before implementation:

1. research modern desktop photo-management applications;
2. research modern UI/UX agent skills;
3. define a project-specific design system;
4. evaluate Qt-native styling/component options;
5. review third-party licenses before adoption;
6. perform the actual UI migration only after the design direction is agreed.

---

# 22. Target End-to-End Workflow

```text
Open a project with 3000 photos

↓

Undecided (3000)

↓

Use:

P
X
P
P
X
X
...

↓

Picked (782)
Undecided (0)
Rejected (2218)

↓

Set:

Target List = Website Photos

↓

Browse Picked

↓

B
B
Shift+B
B

↓

Website Photos (137)

↓

Export:

website.llplist.json
website.csv

↓

On another machine

↓

Import website.llplist.json

↓

Choose/remap photo root

↓

137 items matched

↓

Membership and manual order restored
```

Throughout the workflow:

> **Never copy, move, rename, overwrite, or modify the original source photos.**

---

# 23. Definition of Done

Phase 2 is complete when the application evolves from:

> “A tool that can manage photo lists”

into:

> **“A keyboard-first photo culling tool whose curated lists can be reliably reused across projects and machines.”**
