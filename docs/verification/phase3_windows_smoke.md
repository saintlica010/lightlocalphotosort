# Phase 3 Windows Verification

## Verified revision

Branch: `codex/phase3`

Verified code commit: `4c38d0dcf6092c6cf5b3f756f51715013262c3c4`

The automated suite and packaged build were run against the same code tree
recorded by this commit. No merge or change to `main` was made during this
verification.

## Environment

Windows: Windows 10.0.19045

Python: 3.12.14

PySide6: 6.11.2

PyInstaller: 6.22.3

## Automated suite

Command:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv312\Scripts\python.exe -m pytest -q
```

Result: **280 passed in 17.79s**

The run includes the real `MainWindow` 10,000-media / 9 populated quick-list
structural regression. It verifies bounded SQL batches, delegate/model use,
slot badges, and bounded thumbnail queue shape without timing thresholds.

## UI and exporter fixes

- Preview field names use readable muted token text and metadata values use
  high-contrast token text: **PASS**.
- Picked/rejected preview state colors remain distinct: **PASS**.
- Production Edit menu no longer exposes `设计样板...`: **PASS**.
- Empty and non-JPEG-only Lightroom lists raise a clear Chinese validation
  error before creating an output file: **PASS**.
- Source immutability tests for Lightroom export: **PASS**.

## Packaged build

Build command:

```powershell
.\.venv312\Scripts\python.exe -m PyInstaller --noconfirm --clean build\local_media_curator.spec
```

Build: **PASS**

Launch/clean exit: **PASS** — window title `本地媒体整理`, alive after 6
seconds, normal close within 15 seconds, exit code `0`.

EXE: `dist/local_media_curator/local_media_curator.exe`

EXE SHA-256:
`09BBAD18A674BD2727F8F07BD549451F7D3B456F64D959DCFC1F30967D997A20`

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

Git tracked protected paths and `dist/`: **PASS** — none found.

Final package: **PASS** — 218 files, 135,046,617 bytes; no `photos/`,
`phototakeplan/`, `lightphotosprt/`, media files, `.lrcat`, XMP, SQLite/DB
files, or root-level ICU DLLs were present.

The existing untracked `.venv312/` was preserved and not included in Git.
