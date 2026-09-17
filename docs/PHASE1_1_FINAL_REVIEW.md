# Phase 1.1 Final Review — Required Fixes Before Merge

Reviewed branch: `feat/phase1-mvp`

Reviewed head: `6c97b8d90a36ebff7e2325f7297fa502344ab0f2`

Status: **Do not merge to `main` and do not start Phase 2 until the blocking items below are completed and re-reviewed.**

This document supplements `AGENTS.md`. Existing rules on local-only processing, source immutability, protected data, independent list ordering, and no cloud/telemetry remain in force.

---

# 1. Hard requirement: all user-facing UI must be Simplified Chinese

All user-visible interface text must use **简体中文**.

This includes:

- window titles;
- top-level menus;
- menu actions;
- context menus;
- buttons;
- labels;
- Library/List view names;
- filter names and options;
- status-bar text;
- scan progress text;
- dialogs;
- warnings and error messages;
- confirmation prompts;
- tooltips;
- placeholders and empty states;
- list-management controls;
- Reject / Restore / Undo / Redo operations;
- Project / Source Folder UI.

Suggested translations:

```text
File                 -> 文件
Edit                 -> 编辑
New Project          -> 新建项目
Open Project         -> 打开项目
Add Source Folder    -> 添加源文件夹
Remove Source Folder -> 移除源文件夹
Scan                 -> 扫描
Open Original        -> 打开原文件
Undo                 -> 撤销
Redo                 -> 重做
Reject               -> 排除
Restore              -> 恢复
Add to List          -> 添加到名单
Remove from List     -> 从名单移除
Move Up              -> 上移
Move Down            -> 下移
Move to Start        -> 移到开头
Move to End          -> 移到末尾
All                  -> 全部
Unassigned           -> 未分配
Rejected             -> 已排除
Image                -> 图片
Video                -> 视频
Any extension        -> 任意扩展名
Any folder           -> 任意文件夹
Present              -> 存在
Missing              -> 缺失
Scanning...           -> 正在扫描…
Library (sorted)     -> 媒体库（自动排序）
List (manual order)  -> 名单（手动排序）
```

Do not translate user data:

- filenames;
- file paths;
- user-created list names;
- metadata values;
- extension strings such as `.jpg`, `.png`, `.mov`;
- imported planning/list contents.

Source-code variable names, tests, internal identifiers, comments, and developer documentation may remain English as long as they are not directly exposed in the final UI.

Required UI tests:

- File/Edit menus are Chinese;
- primary actions are Chinese;
- Library views are Chinese;
- filter labels/options are Chinese;
- scan progress is Chinese;
- automatic-sort/manual-order status text is Chinese;
- overlap/path warnings are Chinese.

---

# 2. MERGE BLOCKER: disable reorder while a named list is filtered

Current problem:

A manually ordered named list can still be reordered while display filters hide some members.

Example full list:

```text
A
B
C
D
```

Filtered view:

```text
B
D
```

If the user drags `D` before `B`, the visible grid may submit only `[D, B]` to the full-list reorder path. Hidden items may then move implicitly.

Hidden photos must never change position because of a reorder action performed on a filtered subset.

Phase 1 required fix:

```text
Named list + no active filter
    -> drag reorder enabled
    -> Move Up enabled
    -> Move Down enabled
    -> Move to Start enabled
    -> Move to End enabled

Named list + any active filter
    -> drag reorder disabled
    -> Move Up disabled
    -> Move Down disabled
    -> Move to Start disabled
    -> Move to End disabled
    -> status: 名单（已筛选，排序已禁用）
```

Do not implement a complex filtered-subset reorder algorithm in this final Phase 1 patch.

Required tests:

- unfiltered named list allows reorder;
- type filter disables reorder;
- extension filter disables reorder;
- source-folder filter disables reorder;
- missing/present filter disables reorder;
- clearing filters restores reorder;
- filter activation/clearing never modifies stored `sort_key`;
- keyboard reorder actions while filtered cannot change order;
- hidden members remain in exactly the same stored positions.

**This item is merge-blocking.**

---

# 3. MERGE EVIDENCE: complete the workflow in the actual packaged EXE

Current evidence proves:

- PyInstaller one-folder build succeeds;
- the packaged EXE launches;
- the process stays alive;
- it can close cleanly;
- source-code pytest covers a large part of the end-to-end workflow.

It does not yet prove the **packaged EXE itself** completes the full workflow.

Run:

```text
dist/local_media_curator/local_media_curator.exe
```

Use generated/synthetic media only.

Required packaged-EXE manual smoke:

1. launch the EXE;
2. create a new project;
3. add a synthetic source folder;
4. scan;
5. confirm thumbnails appear;
6. preview an image;
7. create two named lists;
8. add the same photos to both lists;
9. arrange the two lists into different orders;
10. verify their orders remain independent;
11. reject a photo;
12. restore it;
13. exercise Undo and Redo;
14. close the EXE;
15. reopen the same project using the EXE;
16. verify list membership, independent order, and rejection state persisted;
17. verify source file bytes, names, paths, and timestamps were not modified;
18. verify all visible application UI is Chinese.

Update:

```text
docs/verification/phase1_1_windows_smoke.md
```

The report must explicitly distinguish:

```text
packaged EXE manual smoke
```

from:

```text
pytest/source-code automated smoke
```

Do not use the source-code pytest result as a substitute for the packaged-EXE workflow.

---

# 4. MERGE EVIDENCE: add a real 1k / 10k GUI smoke through MainWindow

The current performance smoke is useful for SQL/query/scheduler behavior, but it does not fully exercise the actual Qt window/model/view path with 1,000 and 10,000 items.

Add a GUI-level synthetic smoke that instantiates the real `MainWindow`.

Required 1k/10k GUI coverage:

- 1,000-item initial library display;
- 10,000-item initial library display;
- `_reload_grid` / model reset;
- filter change;
- sort change;
- named-list display;
- viewport changes;
- scrolling;
- bounded thumbnail pending/inflight work while scrolling;
- bounded pixmap cache;
- rapid selection / preview navigation;
- manual reorder in an unfiltered named list;
- filtered named-list view with reorder disabled.

Do not generate 10,000 high-resolution JPEGs. Direct synthetic DB rows are acceptable, but the smoke must pass through the real Qt `MainWindow`, model, view, and relevant event handling.

Prefer structural assertions over fragile timing SLAs:

- grid reload does not execute per-row filesystem calls;
- grid reload does not execute one list-membership SQL query per item;
- thumbnail queue stays bounded;
- visible rows are promoted;
- repeated viewport changes do not produce unbounded queue growth;
- pixmap cache never exceeds its configured bound;
- rapid preview requests skip obsolete pending work;
- filtered named-list reorder actions remain disabled.

Update:

```text
docs/verification/phase1_1_performance.md
```

Include representative local timings and queue/cache observations.

---

# 5. Final regression

After implementing the final patch, run the full suite using Python 3.12 or 3.13:

```text
QT_QPA_PLATFORM=offscreen
python -m pytest -q
```

Record the exact result.

Do not report only selected test files.

---

# 6. Preserve already-correct Phase 1.1 behavior

Do not regress:

- source-media immutability;
- source folder may be read-only;
- project/source root separation;
- project-local database/cache/logs;
- no cloud dependency;
- no telemetry;
- no remote AI;
- protected local data excluded from Git;
- one media item may belong to multiple lists;
- each list owns independent order;
- sparse integer `sort_key`;
- unfiltered named-list drag reorder persists;
- library sorting does not rewrite list order;
- Reject / Restore;
- Undo / Redo;
- bulk list-membership lookup;
- viewport-driven thumbnail scheduling;
- bounded thumbnail pending queue;
- bounded decoded pixmap cache;
- latest-selection-wins preview;
- scan outside the GUI thread;
- cooperative scan cancellation;
- scan progress reporting;
- scan batch commits;
- source-folder overlap protection;
- Phase 1 filter UI;
- Windows one-folder PyInstaller packaging.

---

# 7. Protected local data remains an absolute rule

The following local directories are real user data / local reference material:

```text
photos/
phototakeplan/
lightphotosprt/
```

They remain read-only unless the user explicitly authorizes a specific operation.

Never:

- modify files in them;
- rename files in them;
- move files in them;
- delete files in them;
- rewrite EXIF/XMP;
- create sidecars;
- place project DB/cache/logs inside them;
- use them as automated test output;
- commit them;
- upload them;
- include real filenames/path inventories/private metadata in reports;
- include screenshots exposing private photos in committed verification docs.

Automated tests use generated `tmp_path` / temporary synthetic fixtures only.

---

# 8. Merge acceptance gate

## Functional

- [ ] Filtered named-list reorder is disabled.
- [ ] Clearing filters restores reorder.
- [ ] Hidden list members cannot move due to filtered operations.
- [ ] Independent order across lists remains correct.
- [ ] Filter activation/clearing never rewrites `sort_key`.

## Chinese UI

- [ ] All menus are Chinese.
- [ ] All actions/buttons are Chinese.
- [ ] All filter/view labels and options are Chinese.
- [ ] All dialogs/warnings/status messages are Chinese.
- [ ] Scan progress is Chinese.
- [ ] Manual/automatic ordering status text is Chinese.
- [ ] User filenames/paths/list names/metadata are preserved verbatim.
- [ ] Representative Chinese UI strings are covered by tests.

## Performance

- [ ] 1k GUI smoke passes.
- [ ] 10k GUI smoke passes.
- [ ] Thumbnail work remains bounded.
- [ ] Pixmap cache remains bounded.
- [ ] Grid reload has no per-row filesystem work.
- [ ] Grid reload has no per-row list-membership SQL.
- [ ] Repeated scrolling does not create unbounded queue growth.

## Packaging

- [ ] PyInstaller one-folder build succeeds.
- [ ] Packaged EXE launches.
- [ ] Packaged EXE completes the full synthetic workflow.
- [ ] Packaged EXE can reopen a project with state preserved.
- [ ] Packaged EXE UI is Chinese.
- [ ] Package/build artifacts contain no protected user data.

## Regression

- [ ] Full pytest suite passes.
- [ ] Tests use generated/temp data only.
- [ ] Source immutability tests remain green.
- [ ] Existing list/order/undo/reject tests remain green.

---

# 9. Required handoff for final re-review

When the final patch is complete, provide:

1. branch name;
2. final HEAD SHA;
3. `main...feat/phase1-mvp` diff/PR link;
4. exact full pytest summary;
5. commits added for this final patch;
6. updated packaged-EXE smoke report;
7. updated 1k/10k GUI performance report;
8. explicit confirmation that all user-facing UI is Simplified Chinese;
9. known limitations intentionally deferred to Phase 2.

Do not start Phase 2 before this final review is complete.

---

# 10. Recommended final-patch scope

Keep this patch small.

Suggested commits:

```text
fix(ui): disable reorder in filtered lists
feat(i18n): use Chinese user-facing UI strings
test(ui): cover Chinese strings and filtered reorder lock
test(perf): add 1k and 10k MainWindow GUI smoke
docs(verify): update packaged exe and gui performance evidence
```

Do not broaden this work into:

- video thumbnails;
- embedded video playback;
- HEIC;
- export features;
- installer redesign;
- cloud sync;
- AI classification;
- unrelated refactors.

The goal is to make Phase 1 safely mergeable, not to expand scope.

Priority remains:

```text
source safety
> correctness
> responsiveness
> clarity
> extra features
```
