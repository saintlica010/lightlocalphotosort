# Phase 3 Windows Verification

## Verified revision

Branch: `fix/phase3-test-bugs`

Verified commit: `710ea9b5dd30d6112ae67225a28bedc121e136db`

Code HEAD immediately before this verification-docs commit:
`5ee3c6d01926b6add28d950d67d4cd94e3e3398d`

The automated suite and packaged build were run against that code tree. This
docs commit records the evidence; the final verified SHA is the commit that
adds this file revision. No merge or change to `main` was made during this
verification. Push of `fix/phase3-test-bugs` was deferred to whole-branch
review.

## Environment

Windows: Microsoft Windows NT 10.0.26200.0

Python: 3.12.13 (`.venv`, not `.venv312`)

PySide6: 6.11.2

PyInstaller: 6.22.3

## Automated suite

Command:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **291 passed in 29.31s** (0 skipped, 0 failed)

The run includes:

- explicit quick-slot policy tests (unbound number keys do not auto-create
  `快捷名单 N`; bind/delete leave unbound slots unbound);
- `test_delete_rolls_back_on_failure`;
- `test_10k_main_window_with_populated_quick_lists_stays_structural` (bounded
  SQL batches, delegate/model use, slot badges, bounded thumbnail queue shape
  without timing thresholds).

## Quick-slot policy (repository-owned)

Automated pytest coverage for unbound / bind / delete policy: **PASS**.

Packaged interactive keypress walkthrough in the GUI was **not** run in this
verification. Repository-owned unbound/bind/delete policy is cited from the
automated suite above. Packaged interactive walkthrough remains not fully
exercised.

## UI and exporter fixes

- Preview field names use readable muted token text and metadata values use
  high-contrast token text: **PASS** (prior / retained).
- Picked/rejected preview state colors remain distinct: **PASS** (prior /
  retained).
- Production Edit menu no longer exposes `设计样板...`: **PASS** (prior /
  retained).
- Empty and non-JPEG-only Lightroom lists raise a clear Chinese validation
  error before creating an output file: **PASS** (prior / retained).
- Source immutability tests for Lightroom export: **PASS** (prior / retained).

## Packaged build

Build command:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller build/local_media_curator.spec
```

Build: **PASS**

Launch: **PASS** — `dist/local_media_curator/local_media_curator.exe` launched;
no ICU/Qt stderr observed; process stayed up 5 seconds then was stopped.

EXE: `dist/local_media_curator/local_media_curator.exe`

## Packaged interactive workflow

The following remain unchecked because they were not manually exercised in the
packaged GUI in this run:

- Existing Phase 2 project persistence walkthrough;
- packaged quick-list keyboard workflow and rebind/delete walkthrough;
- packaged `.lrsmcol` generation and packaged empty-list validation;
- visual DPI walkthrough beyond startup.

## Lightroom user acceptance

Lightroom Classic real import: **NOT TESTED — NON-BLOCKING**. Lightroom was
not launched, and no `.lrcat`, XMP, RAW, or source media was accessed or
modified.

## Protected-data audit

Git tracked protected paths and `dist/`: **PASS** — none found in the
verification commit (confirmed with `git status --short`,
`git diff --name-only origin/codex/phase3...HEAD`, and staged-path review).

`main` remained at `fd8819177aed42296c4af26e3ada95802b4e1312` and was not
modified.

---

## Historical / superseded — `codex/phase3` at `4c38d0d` (280 passed)

The following evidence is retained for history and is **superseded** by the
`fix/phase3-test-bugs` verification above (291 passed, explicit quick-slot
binding policy).

Branch: `codex/phase3`

Verified code commit: `4c38d0dcf6092c6cf5b3f756f51715013262c3c4`

Environment then: Windows 10.0.19045; Python 3.12.14 (`.venv312`);
PySide6 6.11.2; PyInstaller 6.22.3.

Suite: `$env:QT_QPA_PLATFORM='offscreen'; .\.venv312\Scripts\python.exe -m pytest -q`
→ **280 passed in 17.79s** (included real `MainWindow` 10k / 9-slot structural
regression).

Packaged build: **PASS** via
`.\.venv312\Scripts\python.exe -m PyInstaller --noconfirm --clean build\local_media_curator.spec`.
Launch/clean exit **PASS** (title `本地媒体整理`, alive 6s, normal close,
exit `0`). EXE SHA-256:
`09BBAD18A674BD2727F8F07BD549451F7D3B456F64D959DCFC1F30967D997A20`.

Packaged interactive workflow and Lightroom Classic real import were left
unchecked / **NOT TESTED — NON-BLOCKING** in that run as well. Protected-data
audit then: **PASS**; package 218 files / 135,046,617 bytes with no protected
trees or root-level ICU DLLs. Untracked `.venv312/` was preserved and not
included in Git.
