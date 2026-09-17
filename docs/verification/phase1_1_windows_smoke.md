# Phase 1.1 Windows PyInstaller Smoke

Date: 2026-09-17
Branch: `feat/phase1-mvp`
Environment: Windows 10 Pro, Python 3.12.10 (project `.venv`), PySide6 6.11.2, PyInstaller 6.22.3.

> **Status: the packaged EXE has been run by the user and the defects it exposed are
> fixed and rebuilt.** See section 3a for what that pass found. The remaining steps of
> the 18-step walkthrough (section 4) are **partially covered** — the steps marked
> unconfirmed there have not been demonstrated and are not claimed.

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

## 3a. First packaged-EXE pass — what it found

The user ran the built EXE before this section was written. It exposed two real
defects, both of which the source-tree tests had missed, plus one behaviour that
was correct but confusing:

1. **Confirmation and warning buttons were English.** The first translation pass
   relied on Qt's own catalogue, and `QTranslator.load("qt_zh_CN")` returns `True`
   from the source tree but `False` inside the frozen bundle — with the `.qm` file
   present and byte-identical. Buttons are now set by our own code in
   `ui/dialogs.py`, verified in a frozen bundle: `['是', '否']`, `['确定']`.
2. **The error message was English.** Only the dialog *title* had been translated;
   the text comes from the exception via `str(exc)`. Messages that reach the user
   are now Chinese.
3. **"Project root cannot be inside photos" was correct behaviour, not a bug.** The
   user picked the photos folder as the *project* location. Creating a project there
   would put `project.sqlite3`, `thumbnails/` and `logs/` inside the real photo tree,
   which `AGENTS.md` §14/§17 forbids. The correct flow is: create the project
   elsewhere, then add the photos folder as a *source folder*.

Also found while changing those messages: four `match=` assertions in the test suite
were passing for the wrong reason. `pytest`'s `tmp_path` embeds the test name, and
that path appears in the message, so `match="overlap"` and `match="photos"` were
matching the fixture directory rather than the behaviour. One was only caught because
pytest truncates long tmp names and the truncation removed the word. All four now
match the message text.

Rebuilt after the fixes; the shipped EXE is newer than every source change.

## 4. Packaged EXE — manual workflow walkthrough

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

**Confirmed so far:** step 1 (launch) and the project-creation guard in step 2.
**Not yet demonstrated on the packaged EXE:** steps 3–18. Do not report this section as
passed until they have been run against
`dist/local_media_curator/local_media_curator.exe`.

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

- [x] build, launch, and automatable checks (sections 1 and 3)
- [x] first packaged-EXE pass by the user; its findings fixed and rebuilt (section 3a)
- [x] §4 of `docs/PHASE1_1_FINAL_REVIEW.md` — 1k/10k GUI smoke through `MainWindow`
      (`tests/test_perf_gui_smoke.py`, numbers in `phase1_1_performance.md`)
- [ ] run the remaining 18-step walkthrough on the packaged EXE (section 4, steps 3–18)
- [ ] record the outcome here, including step 17's before/after
- [ ] confirm the packaged-EXE UI is Chinese end to end (step 18)

The packaged-EXE workflow is the last thing standing between this branch and the
§8 merge gate in `docs/PHASE1_1_FINAL_REVIEW.md`.
