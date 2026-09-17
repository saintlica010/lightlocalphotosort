# docs/codebase — snapshot, not current

> **These files are a point-in-time snapshot of the codebase taken on
> 2026-09-17, before the Phase 1.1 fixes landed. Several claims in them are now
> false.** They were produced by a different agent session and are kept only as
> a record of how the code looked at that moment.

Do not treat anything here as current. For live documentation use:

| Question | Read |
|---|---|
| Product rules, safety constraints | `AGENTS.md` (the authority) |
| Current architecture | `ARCHITECTURE.md` (repository root, maintained) |
| What was fixed and why | `docs/PHASE1_1_REVIEW_FIXES.md`, `docs/PHASE1_1_FINAL_REVIEW.md` |
| Current state and next work | `docs/OPENCODE_HANDOFF.md` |
| Verification evidence | `docs/verification/` |

## Known-false claims in this snapshot

Every one of these is resolved on the current branch:

- `CONCERNS.md` lists five "high"/"medium" risks — scan cancellation and
  progress, generic project/source separation, incomplete filter UI, unbounded
  thumbnail pixmap cache, preview latest-token filtering — **all five are
  fixed**.
- `ARCHITECTURE.md:55` says `ThumbnailDelegate._pixmaps` is an unbounded
  in-memory dictionary. It is a bounded LRU cache (`ui/pixmap_cache.py`).
- `ARCHITECTURE.md:57` and `STRUCTURE.md` give `MainWindow` as 683 lines. It is
  substantially larger now.
- `CONCERNS.md` section 6 carries two `[ASK USER]` questions that have both been
  answered and acted on.

If you want this directory to be useful again, regenerate it rather than
patching it. If it is not useful, delete it — nothing else references it.
