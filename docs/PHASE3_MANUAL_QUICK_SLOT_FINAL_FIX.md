# Phase 3 Quick-Slot Policy Update & Final Fix Checklist

## 0. Context

Repository:

```text
saintlica010/lightlocalphotosort
```

Current fix branch under review:

```text
fix/phase3-test-bugs
```

Current reviewed HEAD:

```text
dec44361515c09484187a04b7e53fa5001aa8742
```

This document records a **new explicit product decision from the user** that supersedes the earlier Phase 3 auto-create behavior.

Do not modify `main`.

Do not merge until independent review.

---

# 1. New Product Decision — Quick Slots Require Explicit Binding

## 1.1 Final required behavior

Quick slots `1..9` are **persistent explicit bindings**.

Number keys must only operate on a slot that the user has explicitly bound to a named list.

Required behavior:

```text
slot 3 is bound to “网站”
↓
press 3
↓
add current selection to “网站”
```

For `Shift+3`:

```text
slot 3 is bound to “网站”
↓
press Shift+3
↓
add current selection to “网站”
↓
advance using existing Phase 2 advance semantics
```

---

## 1.2 Unbound slots

If a slot has no binding:

```text
press 3
```

must **not**:

- create `快捷名单 3`;
- bind the third list automatically;
- bind any existing list automatically;
- add media anywhere;
- advance selection.

Instead, show a non-blocking Simplified Chinese status message, such as:

```text
快捷键 3 尚未绑定。请先为名单绑定快捷键。
```

No modal dialog is required.

---

## 1.3 No automatic mapping to list order

Do **not** map:

```text
slot N → Nth row in current sidebar
```

Do **not** map:

```text
slot N → Nth result of ListRepository.list_all()
```

Do **not** infer a slot from alphabetical order, creation order, current visual order, selected list, or list ID.

Quick-slot meaning must remain stable and explicit.

Renaming, sorting, creating, or deleting unrelated lists must never silently change what a number key means.

---

## 1.4 No automatic list creation

The earlier Phase 3 behavior:

```text
unbound slot
→ create 快捷名单 N
```

is cancelled.

The application must no longer automatically create `快捷名单 1..9` from a number-key press.

Users create normal named lists using the existing list creation UI, then explicitly bind those lists to `1..9`.

---

## 1.5 Delete behavior

If:

```text
slot 3 → 网站
```

and the user deletes `网站`:

```text
slot 3 → unbound
```

After deletion, pressing `3` must do nothing except display the unbound-slot status message.

It must **not** recreate `快捷名单 3` and must **not** bind another existing list.

The slot stays empty until the user explicitly binds another list.

---

## 1.6 Rename behavior

If:

```text
slot 3 → 网站
```

and the user renames the list:

```text
网站 → 首页候选
```

then:

```text
slot 3 → 首页候选
```

must remain intact.

Bindings are by `list_id`, not display name.

---

## 1.7 Rebinding

Users may bind an existing list from the explicit `绑定快捷键` control and/or list context menu.

The UI should display current occupancy:

```text
1  未绑定
2  客户
3  网站
4  未绑定
...
```

If the selected target slot is already occupied by another list, require confirmation before replacing the binding.

Rebinding must not change list membership.

---

# 2. Update `docs/PHASE3_PLAN.md`

The current Phase 3 plan still contains the old auto-create specification.

This is now stale and must be changed.

## 2.1 Replace §3.4

Remove the requirement that pressing an unbound number automatically creates `快捷名单 N`.

Replace it with a section equivalent to:

```markdown
## 3.4 Unbound quick slots

Quick slots require explicit binding.

If the user presses `1..9` and that slot is unbound:

- do not create a list;
- do not bind an existing list automatically;
- do not change list membership;
- do not advance;
- show a non-blocking Simplified Chinese status message explaining that the slot must be bound first.

Quick-slot bindings are created only through explicit user actions in the list UI.
```

## 2.2 Replace §3.5 delete semantics

Old behavior:

```text
delete bound list
→ press same number
→ recreate 快捷名单 N
```

New required behavior:

```text
delete bound list
→ clear binding
→ slot remains unbound
→ number key does nothing until explicit rebind
```

## 2.3 Update Phase 3 Merge Gate

Remove:

```markdown
- [x] Empty slot auto-creates `快捷名单 N`
```

Replace with:

```markdown
- [ ] Unbound number keys do not create or auto-bind lists
- [ ] Quick slots require explicit user binding
- [ ] Deleting a bound list leaves the slot unbound
```

Keep and verify:

```markdown
- [ ] Quick slots `1..9` are stable and persistent
- [ ] Number shortcuts add idempotently
- [ ] Multi-selection quick add works
- [ ] `Shift+1..9` add-and-advance works for bound slots
- [ ] Rename preserves slot
- [ ] Delete clears slot
- [ ] Slot reassignment does not alter list membership
- [ ] Text-entry focus prevents numeric shortcut misfires
```

Only mark these `[x]` after the final branch is verified.

## 2.4 Update packaged smoke instructions

Replace any step equivalent to:

```text
press 1 with slot 1 empty → 快捷名单 1 is created
```

with:

```text
press 1 with slot 1 unbound
→ no list created
→ no media membership changed
→ no selection advance
→ Chinese status message displayed
```

Then test explicit binding and deletion:

```text
bind existing list to slot 1
→ press 1
→ selected media enters that list

delete the slot-1 list
→ slot 1 clears
→ press 1
→ nothing is recreated
```

---

# 3. Resolve Contradictory `ensure_quick_slot()` Semantics

At `dec4436`, UI code correctly refuses to operate on unbound slots, but `ListService.ensure_quick_slot()` still implements stale behavior:

```text
unbound slot
→ try Nth list
→ otherwise create 快捷名单 N
```

This conflicts with the new product decision.

## Required change

Do not leave a public service method whose behavior contradicts the product policy.

Preferred solution:

### Option A — remove `ensure_quick_slot()`

If it is no longer required by production code:

- remove `ensure_quick_slot()`;
- remove/update stale tests that call it;
- use:
  - `quick_slot_list_id()`
  - `bind_quick_slot()`
  - `unbind_quick_slot()`

as the explicit quick-slot API.

This is preferred.

### Option B — redefine it

Only if removing it would create unnecessary compatibility churn, redefine it so that it never creates or auto-binds.

For example:

```python
def ensure_quick_slot(slot: int) -> int | None:
    return quick_slot_list_id(slot)
```

However, the method name becomes misleading, so removal is cleaner.

## Acceptance

- [ ] no production/service path silently auto-creates `快捷名单 N`
- [ ] no production/service path binds the Nth list automatically
- [ ] tests no longer encode the old implicit-binding behavior

---

# 4. Quick-Slot Test Corrections

The following final behavior must be covered.

## Required tests

Add/keep tests equivalent to:

```text
test_unbound_number_key_does_not_create_list
test_unbound_number_key_does_not_change_membership
test_unbound_number_key_shows_status_message

test_unbound_shift_number_does_not_create_list
test_unbound_shift_number_does_not_advance

test_number_key_adds_to_explicitly_bound_list
test_number_key_is_idempotent
test_number_key_adds_multi_selection_as_one_undo

test_shift_number_adds_and_advances_when_bound
test_shift_number_advances_when_already_member

test_rename_preserves_quick_slot

test_delete_bound_list_clears_slot
test_deleted_quick_list_stays_gone_when_number_pressed

test_rebind_occupied_slot_requires_confirmation
test_rebind_does_not_change_list_membership

test_number_shortcuts_ignored_in_text_editors
test_number_shortcuts_ignored_in_editable_combobox
```

Delete or rewrite stale tests such as:

```text
test_ensure_empty_slot_auto_creates_named_list
test_ensure_quick_slot_uses_existing_nth_list
test_ensure_quick_slot_still_creates_when_no_nth_list
```

because these are no longer valid Phase 3 requirements.

---

# 5. Fix Delete Transaction Safety

## Problem

Current `ListService.delete()` roughly does:

```python
_clear_quick_slots_for(list_id)
_lists.delete(list_id)
connection.commit()
```

If a SQLite error occurs after clearing the setting but before successful commit, the caller catches the exception, but `ListService.delete()` does not explicitly rollback.

This can leave the connection in a dirty transaction state.

## Required change

Make list deletion transactional.

Recommended structure:

```python
def delete(self, list_id: int) -> None:
    conn = self._project.connection
    try:
        self._clear_quick_slots_for(list_id)
        self._lists.delete(list_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

The exact exception type may be narrowed if appropriate, but rollback must occur for database-operation failure.

## Required tests

Add a failure-path test that proves:

```text
delete starts
→ database failure occurs
→ transaction rolls back
→ list still exists
→ quick-slot binding still exists
→ target-list state remains consistent
```

Use a synthetic/mock failure.

Do not corrupt a real project.

## Acceptance

- [ ] successful delete clears bound quick slot
- [ ] successful delete clears target-list reference when applicable
- [ ] failed delete rolls back all partial state
- [ ] UI warning does not leave a dirty transaction

---

# 6. Preserve the Valid UI Fixes

The following fixes in `fix/phase3-test-bugs` should remain:

## Menu item layout

Keep explicit `QMenu::item` padding and text color.

## Dialog readability

Keep explicit light text for:

```text
QMessageBox QLabel
QInputDialog QLabel
```

## Quick-slot binding UI

Keep:

- explicit `绑定快捷键` control;
- occupancy labels such as `2  客户`;
- current slot check state;
- confirmation before replacing an occupied slot;
- `删除名单` in the context menu if desired.

Do not reintroduce implicit slot assignment merely to simplify UI.

---

# 7. Lightroom Behavior Remains Unchanged

Do not add Lightroom installation as a requirement.

Keep:

```text
Lightroom 智能收藏夹导出（实验性）
```

Real Lightroom import remains optional user acceptance and **NON-BLOCKING**.

Keep the existing repository-owned corrections:

- empty list rejected;
- non-JPEG-only list rejected;
- no output file created on validation failure;
- no source media modification;
- no XMP modification/creation;
- no `.lrcat` modification.

Do not add Lightroom performance benchmarks.

---

# 8. Preserve the 10k Populated Quick-List Regression

Keep the current structural regression covering approximately:

```text
10,000 media
9 populated quick slots
5,000 memberships per slot
```

It should continue verifying:

- real `MainWindow` refresh path;
- delegate/model rendering;
- bounded thumbnail scheduling;
- bounded/chunked quick-slot membership SQL;
- correct quick-slot badges;
- no per-row filesystem regression.

Do not replace it with timing thresholds.

---

# 9. Re-run Final Windows Automated Suite on the New HEAD

The existing Windows verification document verifies an earlier code revision.

The fix branch contains runtime changes after that commit.

Therefore the old `280 passed` result cannot be the final evidence for the new HEAD.

After completing the fixes above, run on Windows:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv312\Scripts\python.exe -m pytest -q
```

Record:

```text
branch
exact HEAD SHA
Windows version
Python version
PySide6 version
PyInstaller version
exact pytest result
```

## Acceptance

- [ ] final HEAD full suite passes
- [ ] exact pass/skip/fail count recorded
- [ ] quick-slot policy tests are included in that run
- [ ] delete rollback test is included in that run
- [ ] 10k populated quick-list test is included

---

# 10. Rebuild Packaged Windows App From Final HEAD

Because runtime UI/list behavior changed after the previous packaged verification, rebuild the EXE from the final HEAD.

Use the existing PyInstaller spec.

Verify:

```text
build succeeds
EXE launches
no ICU/Qt startup failure
normal close works
```

Do not include protected directories or `dist/` in Git.

---

# 11. Packaged Quick-Slot Smoke for the New Policy

Use synthetic data.

At minimum manually verify in the packaged EXE:

## Unbound behavior

```text
slot 1 unbound
select photo
press 1
```

Expected:

```text
no list created
no item added
selection does not advance
status message explains slot is unbound
```

Then:

```text
press Shift+1
```

Expected:

```text
no list created
no membership change
no selection advance
```

## Explicit bind

Create or use a normal named list such as `网站`.

Bind it to slot 1.

Then:

```text
press 1
```

Expected:

```text
selected photo enters 网站
```

Press again:

```text
membership remains once
```

Then:

```text
Shift+1
```

Expected:

```text
add idempotently
advance correctly
```

## Delete

Delete:

```text
[1] 网站
```

Expected:

```text
slot 1 clears
list remains deleted
```

Then press `1`.

Expected:

```text
no list recreated
slot remains unbound
```

## Rebind

Bind another list to slot 1 and verify the shortcut now operates on the new list.

---

# 12. Update Windows Verification Document

Update:

```text
docs/verification/phase3_windows_smoke.md
```

so it references the **new final HEAD**, not only the previous verified commit.

Preserve historical evidence but clearly mark old runs as historical/superseded.

The new verification should state:

```text
Verified branch:
fix/phase3-test-bugs or final codex/phase3 after integration

Verified commit:
<FINAL_SHA>

Full suite:
<ACTUAL RESULT>

Packaged build:
PASS

Packaged unbound quick-slot behavior:
PASS

Explicit quick-slot bind:
PASS

Delete leaves slot unbound:
PASS

Protected-data audit:
PASS
```

Lightroom real import remains:

```text
NOT TESTED — NON-BLOCKING
```

---

# 13. Update Merge Gate to Match the New Product Decision

The final Phase 3 merge gate must no longer claim auto-create.

Quick List gate should look approximately like:

```markdown
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
```

Do not leave:

```text
Empty slot auto-creates 快捷名单 N
```

anywhere as a current requirement.

Historical references should be clearly marked as superseded if retained.

---

# 14. Documentation Consistency Search

Before finalizing, search the repository for stale terms:

```text
auto-create
自动创建
快捷名单 N
ensure_quick_slot
Nth list
第 N 个名单
```

Review every match.

Any current documentation claiming:

```text
press an unbound number
→ creates/binds a list
```

must be corrected.

Historical docs may retain old wording only when explicitly marked historical/superseded.

---

# 15. Final Git / Protected-Data Audit

Before push:

```bash
git status --short
git diff --stat codex/phase3...HEAD
git diff --name-only codex/phase3...HEAD
```

Confirm no protected paths:

```text
photos/
phototakeplan/
lightphotosprt/
dist/
```

Confirm `main` remains unchanged.

Push only the intended branch.

After push:

```bash
git rev-parse HEAD
git rev-parse origin/fix/phase3-test-bugs
```

must match.

---

# 16. Ready for Independent Review

Return the branch for review only after all of the following are true:

- [ ] Phase 3 plan explicitly requires manual quick-slot binding
- [ ] all auto-create requirements are removed/superseded
- [ ] no Nth-list implicit mapping remains in production behavior
- [ ] `ensure_quick_slot()` stale semantics are removed or neutralized
- [ ] unbound number key does nothing except status feedback
- [ ] unbound Shift+number does not advance
- [ ] deleting a bound list leaves the slot unbound
- [ ] rename preserves binding
- [ ] explicit binding/rebinding UI works
- [ ] delete path has transaction rollback
- [ ] Windows full suite passes on final HEAD
- [ ] 10k populated quick-list regression passes
- [ ] final packaged EXE builds and launches
- [ ] packaged explicit-bind/unbound/delete smoke passes
- [ ] protected-data audit passes
- [ ] verification documentation references the final SHA
- [ ] Lightroom real import remains non-blocking
- [ ] branch is pushed
- [ ] `main` remains untouched
- [ ] Independent Review remains unchecked until external review

## Final product rule

> **Numbers 1–9 never create or choose lists automatically. A number key only sends the current selection to the named list that the user has explicitly bound to that slot. If the slot is unbound, nothing is changed.**
