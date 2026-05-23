# 2026-05-08 -- no queued research question; documenting the check

## Question

Per `roles/researcher.md` step 1: scan `NEEDS-INPUT.md` and `QUEUE.md` for any item tagged `[research]` or any P0/P1 question that needs grounding before someone can act on it. Pick ONE. If none, file a single NEEDS-INPUT entry and stop.

## What I checked

Read-only; no source / state-file mutations beyond this research file + a NEEDS-INPUT append + the JOURNAL append per role spec.

- `NEEDS-INPUT.md` (44 lines / 8926b; 3 open entries; 0 actually `[answered]`):
  - GitHub-MCP install/waive (auditor 2026-04-30) -- not a research question; an install/policy decision.
  - Empty-queue precedent (worker-11am 2026-04-30) -- already-grounded; structural state, not a research gap.
  - BPMN B1/B2/B3 (worker-12pm 2026-04-30) -- decision, not research.
- `QUEUE.md` (152 lines / 14783b post-planner-2026-05-07-07:10):
  - Top is BPMN P1 [in-progress] `REQUIRES ATTENDED WORKER ONLY`. Not tagged `[research]`. Operational gap, not a knowledge gap.
  - Decomposed (next-pull-ready) section empty.
  - Phase 2 / 3 / 4 / 5 items: none tagged `[research]`; all gated on Eric `[x]` of various PROPOSED entries.
- `PROPOSED.md` (192 lines / 52018b; 0 `[x]`-approved):
  - The 5 entries auditor 2026-05-07 filed (3 RISKY + 2 IMPROVABLE) covering the `.git/index` thread + housekeeping. The RISKY P1 verification gate (line 160) was empirically grounded by `research/2026-05-07-git-index-corruption-flip-verification.md` yesterday; the destructive-staged-delete (line 167) and broader-divergence (line 174) entries were both verified in the same file. No fresh grounding needed.
  - Older entries (auditor 2026-04-29 / 2026-04-30 / 2026-05-01 / 2026-05-03 / 2026-05-04 / 2026-05-05 / 2026-05-06 + cowork-session 2026-04-30 / 2026-05-04) are all decisions / housekeeping / process changes; none ask a research question.
- Auditor 2026-05-08 00:05 hand-off (JOURNAL.md line 2342) explicitly noted to me: "tonight's `.git/index` state is unchanged from your 2026-05-07 04:00 finding (per-file blob hashes still match `261a674:`; ls-files still 234; mtime 2026-05-07 06:06:47 UTC unchanged); a follow-up research file is unlikely to add signal unless a NEW question surfaces." Empirical state is byte-identical to yesterday.
- Empirical sanity-check this run: HEAD `4b114de` matches `origin/main` 0/0; `git fsck` clean (13 dangling lines, no `bad index file`); `git ls-files | wc -l` = 234 vs `git ls-tree -r HEAD | wc -l` = 235; `.git/index` size 27871b / mtime 2026-05-07 06:06:47 UTC unchanged; `.git/index.lock` still 0-byte sentinel (mtime 2026-05-07 06:07:44 UTC); PROPOSED `[x]`-count = 0; NEEDS-INPUT `[answered]`-count = 0.

## What I found

No queued `[research]` items. No P0/P1 question that needs fresh grounding to act on. The chronic `.git/index` thread (highest-leverage Eric `[x]` for ~9 days now) is fully grounded by `research/2026-05-06-git-index-corruption-validation.md` + `research/2026-05-07-git-index-corruption-flip-verification.md`; the action it gates is Eric's Windows-side `rm -f .git/index .git/index.lock && git read-tree HEAD` invocation, not more research.

The 4 open follow-ups from yesterday's research file are noted for the record:

1. **2026-05-06 corruption retro** (was the trailer-SHA1 mismatch a real corrupt-write or body/trailer mismatch that auto-recovered?). Yesterday's researcher flagged this as "worth a brief post-fix retro once the lock clears" -- gated on the lock clearing, which has not happened.
2. **Windows-side lock-holder forensics** (which process took the lock at 2026-04-29 17:10:14 UTC and never released?). Not answerable from the Linux audit environment; requires Windows-side process / event-log / AV-log inspection.
3. **Defensive `git fsck` step in the night-auditor role** (one-line addition to `roles/night-auditor.md` so structural breaks surface the morning after, not 7 days after). Process change, not research; would belong in PROPOSED if Eric wants the discipline. Auditor 2026-05-07's clean `git fsck` already runs this check de facto (the resolution-by-side-effect is the visible artifact); formalizing it would just lock in the existing pattern.
4. **Lock as protective barrier flagging** (worker-side reminder that removing `.git/index.lock` without `git read-tree HEAD` in the same atomic sequence enables the data-loss vector). Already captured in researcher 2026-05-07 04:00 section 6 + planner 2026-05-07 07:10 STATE.md "Known constraints" + auditor 2026-05-08 00:05 verified-section. No fresh research needed.

Per role spec point 2: **"If no research tasks are queued, write a single entry to `NEEDS-INPUT.md` asking the human what to investigate next, then stop. Do not invent questions."** Filing NEEDS-INPUT entry + this stub research file (per role spec point 5: "Do not skip writing the research file even if findings are thin").

## Recommendation

**No action.** Today's researcher slot produces no fresh grounding because none is needed; the highest-leverage open work is Eric's `[x]` on the existing `.git/index` thread (5 PROPOSED entries; one Windows-side command retires all 5). NEEDS-INPUT entry filed for direction on the next research question once the lock clears and the post-fix retros become tractable.

## Open follow-ups

Same as yesterday's file's open follow-ups (re-iterating so the next researcher has them in one place):

1. Post-fix retro on the 2026-05-06 corruption mechanism (gated on lock clearing).
2. Windows-side lock-holder forensics (requires Windows-side access).
3. Formalize the defensive `git fsck` step in `roles/night-auditor.md` -- worth filing as a PROPOSED if Eric wants the discipline; not research.
4. Lock-as-protective-barrier reminder in `roles/worker.md` -- already documented; could be formalized as a PROPOSED.
