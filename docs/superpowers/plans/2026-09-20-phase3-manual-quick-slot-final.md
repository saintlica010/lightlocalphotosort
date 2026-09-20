# Phase 3 Manual Quick-Slot Final Fix — SDD Tasks

Source spec: `docs/PHASE3_MANUAL_QUICK_SLOT_FINAL_FIX.md`

Branch: `fix/phase3-test-bugs`
Worktree: `C:\downloadbook\2026shbookfair\.worktrees\fix-phase3-test-bugs`
Base HEAD at plan start: `dec44361515c09484187a04b7e53fa5001aa8742`
Do **not** modify `main`. Do **not** merge.

## Global Constraints

- Work only in the worktree above, on `fix/phase3-test-bugs`.
- Git author: `lica.liu <lica.liu@users.noreply.github.com>`.
- Never `git add .`. Stage explicit paths only.
- Never touch, commit, or upload `photos/`, `phototakeplan/`, `lightphotosprt/`, `dist/`.
- Python 3.12 only via `.venv\Scripts\python.exe`. Set `$env:QT_QPA_PLATFORM='offscreen'` for pytest.
- Prefer Option A: **remove** `ListService.ensure_quick_slot()`. Do not keep a misleading wrapper.
- Numbers 1–9 never create or choose lists automatically. A number key only sends the current selection to the named list the user explicitly bound. Unbound slots change nothing except a Simplified Chinese status message.
- Do not map slot N to the Nth sidebar row or `list_all()` index.
- Preserve existing UI fixes: `QMenu::item` padding/color, `QMessageBox QLabel` / `QInputDialog QLabel` light text, explicit `绑定快捷键` control, occupancy labels, occupied-slot confirmation, context-menu `删除名单`.
- Lightroom `.lrsmcol` JPEG-only export remains unchanged and non-blocking.
- Keep the 10k populated quick-list structural regression (no timing thresholds).
- Schema stays at version 2. Do not bump `PRAGMA user_version`.
- Commits: small, testable, conventional (`fix(lists):`, `test(lists):`, `docs:`).

## Product rule (verbatim)

> **Numbers 1–9 never create or choose lists automatically. A number key only sends the current selection to the named list that the user has explicitly bound to that slot. If the slot is unbound, nothing is changed.**

---

## Task 1: Remove `ensure_quick_slot()` (Option A)

TDD required.

`ListService.ensure_quick_slot()` still auto-binds the Nth existing list or creates `快捷名单 N`. That contradicts the product decision. Production UI already uses `quick_slot_list_id()` / `bind_quick_slot()` / `unbind_quick_slot()` and does not call `ensure_quick_slot`.

### Steps

1. **RED.** Delete or rewrite these stale tests so they no longer encode auto-create / Nth-list bind:
   - `test_ensure_empty_slot_auto_creates_named_list`
   - `test_ensure_quick_slot_uses_existing_nth_list`
   - `test_ensure_quick_slot_still_creates_when_no_nth_list`
2. Add a service-level test that fails while `ensure_quick_slot` still exists, for example:
   - `assert not hasattr(ListService, "ensure_quick_slot")`
   - plus a behavior test: with three named lists and no bindings, all slots remain unbound and no `快捷名单 N` is created.
3. Run the new/changed tests and confirm they fail for the expected reason.
4. **GREEN.** Remove `ensure_quick_slot` from `src/local_media_curator/services/list_service.py`. Grep the worktree; no production or test caller may remain except the `hasattr` assertion.
5. Run `tests/test_quick_slots.py` then the full suite with `QT_QPA_PLATFORM=offscreen`.
6. Commit, e.g. `fix(lists): remove ensure_quick_slot auto-create path`.

### Acceptance

- [ ] no production/service path silently auto-creates `快捷名单 N`
- [ ] no production/service path binds the Nth list automatically
- [ ] tests no longer encode the old implicit-binding behavior
- [ ] `ensure_quick_slot` is gone from production code

Do not change `ListService.delete()` in this task. Do not edit `docs/PHASE3_PLAN.md` in this task.

---

## Task 2: Complete required quick-slot tests

TDD required for any missing coverage. Do not change production unless a new test reveals a real gap.

Keep existing passing tests that already match the new policy.

### Required names (add if missing; keep if already present under an equivalent name)

```text
test_unbound_number_key_does_not_create_list
test_unbound_number_key_does_not_change_membership
test_unbound_number_key_shows_status_message

test_unbound_shift_number_does_not_create_list
test_unbound_shift_number_does_not_advance

test_number_key_adds_to_explicitly_bound_list   # may already exist as test_number_key_adds_to_user_bound_list
test_number_key_is_idempotent
test_number_key_adds_multi_selection_as_one_undo

test_shift_number_adds_and_advances_when_bound
test_shift_number_advances_when_already_member

test_rename_preserves_quick_slot

test_delete_bound_list_clears_slot
test_deleted_quick_list_stays_gone_when_number_pressed

test_rebind_occupied_slot_requires_confirmation
test_rebind_does_not_change_list_membership     # may already exist as test_rebind_moves_slot_without_changing_membership

test_number_shortcuts_ignored_in_text_editors
test_number_shortcuts_ignored_in_editable_combobox
```

Known gaps at plan start (verify, do not assume):

- unbound Shift+number must not create a list and must not advance
- unbound number must not change membership (explicit assertion)
- unbound number must show a Simplified Chinese status containing `尚未绑定`

Status text may match the existing UI:

```text
快捷键 {n} 尚未绑定。请在左侧名单上右键或点「绑定快捷键」。
```

Do not add Lightroom tests. Do not add timing benchmarks. Do not implement the delete-rollback test here (Task 3).

Run focused tests then full suite. Commit, e.g. `test(lists): cover unbound shift and explicit bind policy`.

---

## Task 3: Transactional `ListService.delete()`

TDD required.

Current `delete()` clears quick-slot settings then deletes the list then commits, with no rollback on failure.

### RED

Add a synthetic/mock failure-path test that proves:

```text
delete starts
→ database failure occurs
→ transaction rolls back
→ list still exists
→ quick-slot binding still exists
→ target-list state remains consistent
```

Use a disposable pytest temp project. Do not touch real user data.

Also keep/add a success-path assertion:

- successful delete clears the bound quick slot
- successful delete clears the target-list reference when that list was the target

### GREEN

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

`ListRepository.delete` already clears `target_list_id` in the same connection. Keep that. Rollback must cover both the slot-clear writes and the list delete.

Exception type may be narrowed if appropriate, but database-operation failures must roll back.

UI already catches `sqlite3.Error` and shows `无法删除名单`. Do not leave a dirty transaction after that warning.

Run focused tests then full suite. Commit, e.g. `fix(lists): roll back failed list deletion`.

---

## Task 4: Documentation consistency

No production-code changes.

### `docs/PHASE3_PLAN.md`

Replace §3.4 with unbound-slot explicit-bind semantics (do not auto-create `快捷名单 N`).

Replace §3.5 delete semantics: delete clears the binding; slot stays unbound; number key does nothing until explicit rebind.

Update packaged smoke: unbound press 1 creates nothing; then explicit bind; then delete leaves slot unbound.

Update Phase 3 Merge Gate Quick List section to the new items, left **unchecked** `[ ]` until Task 5–7 verification. Remove `Empty slot auto-creates 快捷名单 N` as a current requirement.

### Other current docs

Search and correct stale current-tense claims:

```text
auto-create
自动创建
快捷名单 N
ensure_quick_slot
Nth list
第 N 个名单
```

Files known to be stale: `ARCHITECTURE.md`, `README.md`, `docs/OPENCODE_HANDOFF_PHASE3.md`. Historical plans (e.g. `docs/superpowers/plans/2026-09-20-phase3-test-bugs.md`) may keep old wording only if marked **superseded**.

Also add/commit `docs/PHASE3_MANUAL_QUICK_SLOT_FINAL_FIX.md` if not already tracked.

Do not mark Independent Review. Do not edit `docs/verification/phase3_windows_smoke.md` yet (Task 7).

Commit, e.g. `docs: require explicit quick-slot binding`.

---

## Task 5: Full Windows automated suite

On this worktree HEAD:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

Record in the implementer report (and a small note file under `.superpowers/sdd/`):

```text
branch
exact HEAD SHA
Windows version
Python version
PySide6 version
PyInstaller version
exact pytest result (passed/skipped/failed)
```

Confirm the run includes quick-slot policy tests, the delete-rollback test, and the 10k populated quick-list test.

If the suite fails, fix only failures caused by Tasks 1–4; do not expand scope.

If all pass, commit nothing unless a tiny recording file belongs in `docs/verification/` — prefer leaving SHA recording for Task 7.

---

## Task 6: Rebuild packaged Windows app

Rebuild from this HEAD using `build/local_media_curator.spec` / `scripts/build_windows.ps1`.

Verify:

```text
build succeeds
EXE launches
no ICU/Qt startup failure
normal close works
```

Do not commit `dist/`. Do not copy the `.exe` alone.

Automated pytest already covers unbound/bind/delete policy. Packaged interactive keypress smoke is best-effort: launch and close at minimum. Record the EXE path:

```text
.worktrees/fix-phase3-test-bugs/dist/local_media_curator/local_media_curator.exe
```

---

## Task 7: Verification docs, audit, and push

Update `docs/verification/phase3_windows_smoke.md`: preserve historical evidence, mark old runs superseded, record the new HEAD SHA, full-suite result, packaged build PASS, unbound/bind/delete policy PASS (cite automated tests + EXE launch), Lightroom real import `NOT TESTED — NON-BLOCKING`, protected-data audit PASS.

After evidence exists, mark the Phase 3 Quick List merge-gate items `[x]` in `docs/PHASE3_PLAN.md` (not Independent Review).

Git audit before push:

```bash
git status --short
git diff --stat origin/codex/phase3...HEAD
git diff --name-only origin/codex/phase3...HEAD
```

Confirm no protected paths. Confirm `main` is untouched.

Push only `fix/phase3-test-bugs` with `git -c http.sslBackend=openssl push -u origin fix/phase3-test-bugs`.

After push, `git rev-parse HEAD` and `git rev-parse origin/fix/phase3-test-bugs` must match.
