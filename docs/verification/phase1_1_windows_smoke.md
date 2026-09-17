# Phase 1.1 Windows PyInstaller Smoke

Date: 2026-09-17
Branch: `feat/phase1-mvp`
Environment: Windows 10 Pro, Python 3.12.10 (project `.venv`), PySide6 6.11.2, PyInstaller 6.22.3.

> **Status: partially complete.** The build and every automatable check pass. The
> packaged-EXE manual walkthrough (section 4) has **not** been performed yet and is
> **not** claimed here. See section 2 for why that distinction is enforced.

---

## 1. Build

```text
python -m PyInstaller build/local_media_curator.spec --noconfirm
```

Result: **succeeded**, `Building COLLECT ... completed successfully`.
Artefact: `dist/local_media_curator/local_media_curator.exe` (2.5 MB; one-folder
bundle 130 MB total).

The spec is unchanged: `datas=[]`, `binaries=[]`, one-folder `COLLECT`.

---

## 2. Two different kinds of evidence — do not conflate them

| | Packaged EXE manual smoke | pytest / source-code automated smoke |
|---|---|---|
| Runs | the built `local_media_curator.exe` | the source tree under `src/` |
| Proves | the frozen bundle actually works end to end | the logic is correct |
| Status | **NOT YET RUN** (section 4) | passing (section 5) |

A passing pytest run is **not** a substitute for the packaged-EXE walkthrough. The
bundle can fail in ways the source tree cannot: missing hidden imports, a Qt plugin
that PyInstaller did not collect, a data file that only exists in the repo. The plan
requires the packaged binary itself to complete the workflow.

---

## 3. Packaged EXE — automatable checks (all pass)

- **Launches.** Started detached; process alive after 8 s and after 10 s.
- **Window title is Chinese.** `MainWindowTitle` reads `本地媒体整理`. (Read via a
  fresh `Get-Process` query — reading the property off the original `Start-Process`
  object returns a stale value and will mislead you.)
- **Closes cleanly.** `CloseMainWindow()` (the same message as clicking the X)
  exits the process with nothing left running.
- **Protected data is not bundled.** No `photos/`, `phototakeplan/` or
  `lightphotosprt/` path appears anywhere under `dist/`. The spec contains no
  protected-tree references. `git diff --name-only` over the whole branch, with
  `--diff-filter=A`, shows zero protected paths and zero binary artefacts.
- **Build outputs are not committed.** `dist/` and `build/*` are gitignored;
  `git status --short` shows no build artefact.
- **No stray output.** stdout/stderr empty on launch — no traceback, no warnings.

---

## 4. Packaged EXE — manual workflow walkthrough (**NOT YET RUN**)

Run this against the **built EXE**, not the source tree:

```text
dist/local_media_curator/local_media_curator.exe
```

### Synthetic media is provided — do not use `photos/`

A generated set is ready at:

```text
dist/smoke/source/cam1/   IMG_0001.jpg  IMG_0002.jpg (portrait)  IMG_0003.jpg  IMG_0004.jpg (wide)
dist/smoke/source/cam2/   PANORAMA.png  DETAIL.png  SHOT_0007.jpg  SHOT_0008.jpg  CLIP_0009.mp4
```

Nine items across two folders, mixed formats and orientations, plus one fake `.mp4`
so the image/video and extension filters can be exercised. Create the project in:

```text
dist/smoke/project/
```

Using `photos/` would work (the scan is read-only) but there is no reason to; the
synthetic set exists so real personal media stays out of this test.

### The 18 steps

1. launch the EXE
2. create a new project — pick `dist/smoke/project/`
3. add a source folder — pick `dist/smoke/source/` (adds both cam1 and cam2 only if
   you add each subfolder; add them one at a time to exercise the folder filter)
4. scan
5. confirm thumbnails appear
6. preview a photo
7. create two named lists
8. add the same photos to both lists
9. arrange the two lists into different orders
10. verify their orders remain independent
11. reject a photo
12. restore it
13. exercise Undo and Redo
14. close the EXE
15. reopen the same project using the EXE
16. verify list membership, independent order, and rejection state persisted
17. verify source file bytes, names, paths, and timestamps were not modified
18. verify all visible application UI is Chinese

### Extra checks worth doing while the EXE is open

These cover the work added on this branch and are easy to miss in a scripted pass:

- **Filtered reorder is locked.** Open a named list, apply an extension filter
  (e.g. `.jpg`), and confirm drag-drop and all four move actions are disabled and
  the status bar reads `名单（已筛选，排序已禁用）`. Clear the filter and confirm they
  come back and the status reads `名单（手动排序）`.
- **Chinese standard buttons.** Delete a list and confirm the confirmation dialog
  shows Chinese buttons (`是` / `否`), not English `Yes` / `No`.
- **Scan progress.** With a larger folder, confirm the status bar shows
  `正在扫描… 已处理 N 个文件` rather than appearing frozen.

Record the result of step 17 with a before/after comparison — the automated test
asserts it, but the manual run should confirm the same on the real files.

---

## 5. pytest / source-code automated smoke (passing)

`tests/test_phase1_1_smoke.py` exercises the same flow synthetically on `tmp_path`
only: project create, add sibling source folder, scan, two lists sharing one photo,
independent reorder, reject/restore, undo/redo, close and reopen, membership + order
+ rejection persistence, and source SHA-256 comparison before and after.

Full suite, `QT_QPA_PLATFORM=offscreen`, Python 3.12.10:

```text
149 passed, 1 skipped
```

Repeated 6 times with no flake. On Python 3.14.3 this suite segfaults ~5% of runs in
the Pillow WebP save on a thumbnail worker thread — a toolchain defect, not a
project defect. Pin 3.12 or 3.13.

---

## 6. Remaining before this section can be called done

- [ ] run the 18-step walkthrough on the packaged EXE (section 4)
- [ ] record the outcome here, including step 17's before/after
- [ ] confirm the packaged-EXE UI is Chinese (step 18)
- [ ] §4 of `docs/PHASE1_1_FINAL_REVIEW.md` — 1k/10k GUI smoke through `MainWindow`
