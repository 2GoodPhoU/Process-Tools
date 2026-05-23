# Research -- 2026-05-12 -- Post-pause state pin (Eric's 2026-05-11 cowork-session + 2026-05-12 ~05:21 UTC edits)

## Question

Verbatim per role spec (no `[research]`-tagged QUEUE/NEEDS-INPUT item; selecting the P1 needing grounding): **what is the current empirical state of Process-Tools at 2026-05-12 04:00, after (a) the 3-day automation pause from 2026-05-09 22:55 UTC -> 2026-05-12 04:00, (b) Eric's 2026-05-11 cowork-session that resolved BPMN B1/B2/B3 and orphan-dir 3.7, and (c) Eric's 2026-05-12 ~05:21 UTC edits to STATE.md / CLAUDE.md / DECISIONS-orphan-dirs.md / NEEDS-INPUT.md? What has changed since the auditor 2026-05-09 00:05 baseline, and what is load-bearing for the next Planner / Worker / Auditor?**

Pick rationale: the previous two Researcher slots (2026-05-08 + 2026-05-09) filed `[no queued question]` artifacts because state was byte-identical to prior days. That premise no longer holds today -- state has demonstrably changed (new HEAD commit, two open decisions resolved, four state files edited). A fresh empirical pin is now actionable, not diminishing-returns. Not inventing a question; grounding the next Planner's STATE.md refresh.

## What I checked

- **JOURNAL.md** tail via bash (file is ~696 KB, cannot Read whole): last entry is `digest 2026-05-09 16:45`. Zero automation entries from 2026-05-10, 2026-05-11, 2026-05-12. JOURNAL mtime: 2026-05-09 22:55 UTC. **The scheduled-task chain (auditor 00:05 / researcher 04:00 / planner 07:10 / worker 8am-12pm / digest 16:45) has not run for ~2.5 days.** Cowork-session 2026-05-11 BPMN-gate resolution is visible only in the NEEDS-INPUT.md edit; it was not journaled.
- **Git plumbing** (read-only): `git rev-parse HEAD` -> `bdc9e04`; `git rev-parse origin/main` -> `4b114de`. **Local is 1 ahead / 0 behind**. The new commit (`requirements-extractor 0.6.2 follow-up: (compound) split-mode guard + regression test`) was authored by Eric during the 2026-05-11 cowork-session. Twenty most-recent commits: 1 new (`bdc9e04`) then the unchanged 2026-05-05/-06 worker plumbing-path chain. STATE.md (in the body, still dated "2026-05-09 ~07:10") claims HEAD `4b114de` matches origin/main 0/0 -- **this is now stale**.
- **`.git/index` situation**: `head -c 12 .git/index | xxd` -> `DIRC 0002 000000ea` (= 234 entries, decimal 0xea); index size 27871b; mtime **2026-05-07 06:06:47 UTC** (unchanged for 5 days). `.git/index.lock` (0 bytes) mtime **2026-05-07 06:07:44 UTC** -- also unchanged; still held by a Windows-side process. New artifact alongside: `.git/index.test_write` (0 bytes, mtime 2026-05-07 10:09:44 UTC) -- presumed audit-side capability probe, harmless. `git ls-files | wc -l` = **234**; `git ls-tree -r HEAD | wc -l` = **235**; the missing entry is still `RELEASE-NOTES-1.0.md`. `git diff --cached --name-status` still reports `D RELEASE-NOTES-1.0.md` + 7 staged-modifications matching `261a674:`. `git fsck --no-progress`: 13 dangling lines (unchanged); **no `bad index file` line** (trailer-SHA1 still self-consistent). The new HEAD `bdc9e04` was therefore written via the same `GIT_INDEX_FILE=/tmp/...` plumbing-path workaround Workers have been using -- confirmed by index mtime unchanged across the commit.
- **File-system mtimes** (`ls -la --time-style=full-iso`): STATE.md 2026-05-12 05:21:23 UTC; CLAUDE.md 2026-05-12 05:21:11 UTC; DECISIONS-orphan-dirs.md 2026-05-12 05:21:32 UTC; NEEDS-INPUT.md 2026-05-12 05:19:58 UTC. QUEUE.md, PROPOSED.md, DONE.md, JOURNAL.md, ROADMAP.md untouched today.
- **Diff content** for the four edited files (working-tree vs HEAD via `git diff HEAD --`): summarised in "What I found" section below.
- **Counts**: NEEDS-INPUT 5 open / 1 `[answered]`; QUEUE 17 open / 2 `[in-progress]`; PROPOSED 0 `[x]` / 29 open.
- **BPMN sample artifact** (relevant to the new eric-action item): `samples/bpmn_validation/simple_two_actors.bpmn` is present (6317b, mtime 2026-04-27). Full sibling set (`.puml`, `.skel.yaml`, `.xmi`, `.review.xlsx`, `.vsdx`, `README.md`) all present. Ready for Eric's manual Camunda walkthrough.
- **Previous research files**: `research/` directory has 13 files; newest is `2026-05-09-no-queued-question.md`. No files for 2026-05-10 or 2026-05-11. This file becomes the 14th.

## What I found

**1. New HEAD commit `bdc9e04` (Eric 2026-05-11 cowork-session, requirements-extractor 0.6.2 follow-up).** Local is 1 ahead of `origin/main`; per the 2026-05-04 push policy (CLAUDE.md, committed in `261a674`), remote-push is informational and Eric pushes manually each evening. STATE.md still claims 0/0 -- next Planner refresh will correct.

**2. BPMN B1/B2/B3 question is `[answered]` -- option (a).** NEEDS-INPUT.md line 36-37 carries Eric's resolution (recorded 2026-05-11 cowork-session): **"option (a) -- Eric will run the Camunda Modeler walkthrough manually. Equivalent to option B2 in the menu below ... the QUEUE structural-validator P1 stays open ... CLAUDE.md task-specific waiver removal will land when the queue item closes per the waiver's self-sunset clause."** A new entry `[eric-action / 2026-05-11]` at line 56-60 captures the manual walk: open `samples/bpmn_validation/simple_two_actors.bpmn` in Camunda Modeler 5.x, walk the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, drop into demo.bpmn.io, save + structural-diff, file findings in `nimbus-skeleton/DECISIONS.md`. Time-box ~15 min. On completion: QUEUE 2.5 closes + CLAUDE.md waiver self-sunsets. Workers may continue extending the structural validator in parallel.

**3. Orphan-dir 3.7 question is resolved (option A: kept tracked as proper packages).** DECISIONS-orphan-dirs.md gained a new blockquote at the top: **"DECISION (Eric, recorded 2026-05-11 cowork-session, effective 2026-05-05): Option A -- keep tracked as proper packages. No formalization (no `pyproject.toml` / packaging-metadata additions); no untracking. State already matches: all three dirs were tracked as of 2026-04-29 per section 2 below. Follow-up work is doc cleanup only -- QUEUE 3.7 lifts the read-only off-limits rule in CLAUDE.md and corrects the stale 'untracked' framing in `ACTION_ITEMS.md` Phase-0 + `COMMIT_PLAN.md`."** CLAUDE.md was edited in lockstep: the off-limits paragraph now reads "tracked-vs-ignored question is resolved 2026-05-05: kept tracked as proper packages ... Read-only off-limits constraint stays in place pending the Phase 3 doc-alignment lift (QUEUE 3.7 closure)." STATE.md content (body, not date stamp) carries the same framing.

**4. CLAUDE.md off-limits constraint stays in place.** Even though the gating decision is resolved, the read-only rule on `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/` does NOT lift until QUEUE 3.7 (doc cleanup on ACTION_ITEMS.md Phase-0 + COMMIT_PLAN.md) lands. Workers and Auditors should continue to treat the three dirs as read-only this morning. The waiver carve-out for QUEUE 2.5 (Camunda Modeler 5.x + Chrome MCP for demo.bpmn.io, scoped to that queue item only) is unchanged.

**5. `.git/index` situation is byte-identical to the auditor 2026-05-09 00:05 baseline.** Index header `DIRC 0002 000000ea` (234 entries); mtime unchanged in 5 days; lock still held by Windows-side process; destructive staged-delete of `RELEASE-NOTES-1.0.md` still loaded; 7 staged-modifications still match `261a674:` not HEAD. **Recovery is unchanged: Windows-side `rm -f .git/index .git/index.lock && git read-tree HEAD` in one shell.** The new HEAD `bdc9e04` was committed via the GIT_INDEX_FILE plumbing-path workaround, same mechanism Workers have used for 5+ days. Lock-as-protection continues to shield against the data-loss vector.

**6. STATE.md date stamp is stale.** Body text reads "Last updated 2026-05-09 ~07:10 -- process-tools-planner (automated)." Eric did NOT refresh the date when he rewrote the content. The content itself is mostly accurate to **2026-05-12 morning** (orphan-dir 3.7 framed as resolved, BPMN B1/B2/B3 framed as still open -- which conflicts with the NEEDS-INPUT `[answered]`), with two factual errors: (i) STATE.md claims HEAD `4b114de` matches origin/main 0/0, but HEAD is now `bdc9e04` 1-ahead; (ii) STATE.md frames BPMN B1/B2/B3 as still pending, but the answer is captured in NEEDS-INPUT. **Next Planner run (2026-05-12 07:10) is the natural correction point.**

**7. Counts.** NEEDS-INPUT: 5 open / 1 `[answered]` (the 1 answered is BPMN B1/B2/B3; planner step 4 will clear it and act). QUEUE: 17 open / 2 `[in-progress]` (the two `[in-progress]` are both BPMN P1 entries -- the top-of-file canonical one and the Phase-2 2.5 mirror). PROPOSED: 29 open / 0 `[x]`-approved. The PROPOSED count grew by ~5 since 2026-05-09 (filed by auditor 2026-05-09 00:05); the 0 `[x]`-approval ratio is unchanged.

**8. Test counts unchanged.** 702/702 last green pin (606 + 40 + 30 + 26). No working-tree edits today touched source or test files -- only state files. The staged-diff entries on `requirements_extractor/parser.py` and `tests/test_multi_action.py` are part of the structural-stale index, not real edits.

**9. Automation pause.** 2026-05-10 + 2026-05-11 + 2026-05-12 (until this run) have **zero scheduled-task entries in JOURNAL.md**. Whether the scheduler was paused intentionally during Eric's manual edits, or whether the scheduled tasks failed to fire, is not investigable from the audit environment. Today's 04:00 researcher slot is the first automation entry after the pause; the 07:10 planner slot will be the canonical re-sync point.

## Recommendation

**No code action this run. No new PROPOSED entry. Recommendations for the next Planner (2026-05-12 07:10), in priority order:**

1. **Refresh STATE.md.** Update the date stamp to today; correct the HEAD/origin-main framing (now 1 ahead, not 0/0); correct the BPMN B1/B2/B3 framing (now `[answered]` option (a), with the eric-action item open and gating QUEUE 2.5 closure); flip the orphan-dir 3.7 framing from "pending" to "resolved option A (off-limits stays pending QUEUE 3.7 doc-cleanup)." The "Current focus" section should narrow to: (i) the eric-action BPMN walk, (ii) the `.git/index` recovery command (still highest-leverage Eric `[x]`), (iii) the empty next-pull-ready set.
2. **Clear the `[answered]` NEEDS-INPUT entry.** Per planner role step 4. The BPMN B1/B2/B3 entry is `[answered] option (a)`; planner should mark it resolved and adjust QUEUE 2.5 framing to reflect Eric-action-pending rather than B1/B2/B3-decision-pending.
3. **Do NOT promote any PROPOSED items.** 29 open / 0 `[x]`-approved; per role spec only `[x]`-approved items graduate.
4. **Do NOT modify CLAUDE.md.** The orphan-dir off-limits constraint explicitly stays in place pending QUEUE 3.7 closure; the file edit Eric made yesterday is the authoritative version.

**For the next Worker (2026-05-12 08:00-12:00):**

The empty-queue precedent continues -- the top item is still `[in-progress]` attended-only (QUEUE 2.5 now waiting on Eric's manual walk rather than B1/B2/B3 pick, but the operational effect is identical for unattended Workers). The 8am-12pm chain will bail unless Eric `[x]`-approves a PROPOSED between now and 08:00. Highest-leverage Eric `[x]` for tonight's evening review is still **the `.git/index` thread** (one Windows-side command + one `[x]` on any of the 5 grouped entries retires the lot spanning ~12 days now).

**For Eric (this evening):**

The two cheapest closures from yesterday's cowork-session still need a follow-through: (i) run the Camunda Modeler manual walk per the new `eric-action / 2026-05-11` NEEDS-INPUT entry (~15 min) -- closes QUEUE 2.5 and self-sunsets the CLAUDE.md waiver; (ii) run the `.git/index` recovery command on Windows (`rm -f .git/index .git/index.lock && git read-tree HEAD`) -- retires 5 PROPOSED entries spanning 12 days and removes the load-bearing data-loss vector. Either one structurally shortens the next several days of Worker bailouts.

## Open follow-ups

1. **Stale STATE.md date stamps when Eric rewrites the file manually.** Eric rewrote STATE.md content yesterday but did not refresh the "Last updated" line. Worth a one-line note in `roles/planner.md` so a future Planner reading a manually-rewritten STATE.md doesn't mistake the date for an automation timestamp. (Low priority; surfaced this run.)
2. **Should `eric-action` NEEDS-INPUT entries be a recognised type with a distinct clearing rule?** Yesterday's cowork-session introduced the new tag pattern `[eric-action / YYYY-MM-DD]`. Today's planner step 4 ("clear `[answered]` entries") doesn't cover this -- the entry is neither a question nor a worker-blocker; it's a task assigned to Eric. The clearing rule is ambiguous. (Low priority; flag for the next cowork-session.)
3. **Why did automation pause 2026-05-10 + 2026-05-11?** Not investigable from this environment. Worth a note in the next digest if it repeats.
4. **Carried from 2026-05-09 (still open):**
   - "Was the trailer-SHA1 mismatch a real corrupt-write artifact or a body/trailer mismatch that auto-recovered when `git status` re-stat'd?" -- gated on the lock clearing.
   - "Which Windows-side process is holding `.git/index.lock` since 2026-04-29 17:10 UTC?" -- unanswerable from the Linux audit environment.
   - "Are any of the seven staged-modifications materially different from `261a674:`?" -- low priority; recovery wipes them uniformly.
   - "Does the destructive staged-delete on `RELEASE-NOTES-1.0.md` reproduce on a fresh clone?" -- post-fix retro.
5. **Researcher-slot `[no queued question]` streak ended at 2.** Carried from 2026-05-09 follow-up #5. Today's slot has a real question (post-pause state pin); the meta-question about consecutive-slot threshold is moot for now. Reset the counter.

---

*Filed by Researcher 2026-05-12 04:00. No PROPOSED entries added (findings reinforce existing items rather than surface new ones). No NEEDS-INPUT entry filed (2026-05-08 researcher entry asking for next research question is still open and unambiguous; today's slot answered itself by selecting the post-pause grounding question -- not invented, surfaced by the changed state). Read-only run. JOURNAL append to follow.*
