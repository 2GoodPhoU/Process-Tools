# Research -- 2026-05-15 -- no queued research question (third slot in the running window)

## Question

Verbatim from `roles/researcher.md` step 1-2: "Look for any item tagged `[research]` or any P0/P1 question that needs grounding before someone can act on it. If no research tasks are queued, write a single entry to `NEEDS-INPUT.md` asking the human what to investigate next, then stop. Do not invent questions."

So the meta-question this run answers: **is there a queued `[research]` item or P0/P1 needing fresh grounding today, given that yesterday's (2026-05-08 04:00) "what should I investigate next?" NEEDS-INPUT entry was finally answered today (`[answered: C 2026-05-15 via dashboard]` -- selecting R3 Pre-Phase-4 readiness audit, which researcher 2026-05-14 04:00 already delivered as `research/2026-05-14-pre-phase-4-readiness-audit.md`)?**

## What I checked

- `NEEDS-INPUT.md` (full, 17134 b / 70 lines post worker-8am 14:14 `[resolved:]` on line 28-29 + worker-9am 14:30 `[resolved:]` on line 37-38). Counts via anchored grep:
  - `grep -cE '^- \[ \]' NEEDS-INPUT.md` = 5
  - `grep -cE '^- \[eric-action' NEEDS-INPUT.md` = 1
  - `grep -cE '^\s*\*\*\[answered:.*via dashboard\]\*\*' NEEDS-INPUT.md` = 4 (lines 28 / 37 / 48 / 55 in current numbering)
  - `grep -cE '^\s*\*\*\[resolved:' NEEDS-INPUT.md` = 2 (lines 29 / 38)
  - Unresolved dashboard markers: line 48 (`[answered: C]` Pre-Phase-4 audit pick) + line 55 (`[answered: A]` Camunda manual walk approval). Both expected-disposition no-op per planner 2026-05-15 07:10 STATE.md; subsequent Worker slots will pair them.
  - The 2026-05-08 researcher menu entry on line 38-46 IS the one `[answered: C 2026-05-15 via dashboard]` selected. R3 was selected; R3 was already delivered by researcher 2026-05-14 04:00 as `research/2026-05-14-pre-phase-4-readiness-audit.md` (~17 KB). The pin is functionally consumed: the answer endorses pre-delivered work without naming a fresh investigation.
  - No other entry in NEEDS-INPUT carries a research-shaped ask. The QUEUE 2.4 D1/D2/D3 worker-11am 2026-05-12 entry (lines 56-70 current numbering) is a three-part Eric DECISION, not a research gap; researcher 2026-05-13 04:00 already produced the grounding (`research/2026-05-13-bpmn-xsd-validator-and-license.md`) + PROPOSED bundle still awaiting `[x]`.

- `QUEUE.md` (full, 168 lines / 18805 b post planner-2026-05-15-07:10 curation). No `[research]`-tagged items in any phase-decomposed section (Phase 2 / 3 / 4 / 5). New top-level `## Manual-Gate / eric-action` section carries one `[in-progress]` item: `.git/index` recovery via Windows-side `rm -f .git/index .git/index.lock && git read-tree HEAD`. The item carries an explicit follow-up note to me: *"Follow-up note for researcher: forensic signal on the 2026-05-06 trailer-SHA1 mismatch decays as soon as `git status` re-stats the new index. If R1 (post-fix retro) is still wanted, researcher 2026-05-16 04:00 should run it the night of the recovery, not later."* This is the only research-shaped affordance pinned in QUEUE today, and it is GATED on the recovery happening first (which has not happened; `.git/index` still 27871 b / mtime `2026-05-07 06:06:47 UTC` / 8 days stale; `.git/index.lock` still 0-byte sentinel held by Windows-side process).

- `PROPOSED.md` counts via anchored grep: `grep -cE '^- \[x\]' PROPOSED.md` = 0; `grep -cE '^- \[ \]' PROPOSED.md` = 32. The 2026-05-13 D1/D2/D3 P2 bundle (line 195) carries an attached 8-step Worker spec, not a research question -- it is `[x]`-pending, not research-pending. The 2026-05-14 P2-bundle Pre-Phase-4 audit (line 210) is researcher 2026-05-14's own concrete-action proposal, also `[x]`-pending. The two RISKY P1 entries on the `.git/index` thread (lines 153 / 160 / 167 / 174) are now structurally promoted to QUEUE Manual-Gate by today's planner -- the research-side question (post-fix retro) is the QUEUE follow-up note above, not a duplicate filing.

- `JOURNAL.md` tail via bash (`tail -c 50000 JOURNAL.md`): last 24h covers night-auditor 2026-05-15 00:05 + planner 07:10 + worker-8am 14:14 + worker-9am 14:30. The 10-of-10 bailout streak (2026-05-13 5-of-5 + 2026-05-14 5-of-5) is now BROKEN: 2-of-2 today via the dashboard `[resolved:]` chain. Tests still 708/708 green per night-auditor 2026-05-15 00:05 (auditor's 4-tool decomposition 607 + 45 + 30 + 26). No commits between 2026-05-12 burst (`bbcbff5` / `9ca814d` / `042f271`) and today's two `[resolved:]` commits (`d56137a` worker-8am + `6b770ae` worker-9am).

- Empirical state sanity checks (READ-ONLY plumbing via bash):
  - `git rev-parse HEAD` = `6b770aeb76eb7dd16ed25ceeb6684349851e72d7` (worker-9am 14:30 commit; 6 ahead of `origin/main` `4b114de`).
  - `head -c 12 .git/index | xxd` = `4449 5243 0000 0002 0000 00ea` -> `DIRC v2 / 234 entries` (unchanged 8 days).
  - `stat -c '%s %y' .git/index` = `27871 2026-05-07 06:06:47.* +0000` (unchanged 8 days).
  - `.git/index.lock` still 0 b / mtime `2026-05-07 06:07:44 UTC` / Linux `unlink` returns `Operation not permitted`.
  - `git ls-files | wc -l` = 234; HEAD's tree count = 237 (3 entries lag: `RELEASE-NOTES-1.0.md` staged-delete vector + `nimbus-skeleton/scripts/bpmn_structural_diff.py` + `nimbus-skeleton/tests/test_bpmn_structural_diff.py` ghost-deletes from `9ca814d`).
  - `git status -s` against the stale index surfaces same `MM`/`D `/`??` shape as documented in the past 7 days. The two `9ca814d`-added files appear as BOTH `D ` (staged-delete relative to the stale 234-entry index) AND `??` (untracked on disk).

- `research/` directory listing -- 16 files; the most recent are `2026-05-14-pre-phase-4-readiness-audit.md` (16952 b, the file `[answered: C]` retroactively endorsed) and `2026-05-13-bpmn-xsd-validator-and-license.md` (15714 b, grounding for the QUEUE 2.4 D1/D2/D3 bundle still awaiting `[x]`). Two prior `no-queued-question` precedents on 2026-05-08 (5821 b) and 2026-05-09 (7330 b) define the steady-state pattern for this slot when nothing is pinned.

## What I found

1. **No `[research]`-tagged QUEUE/NEEDS-INPUT/PROPOSED items.** Matches the 2026-05-08 / 2026-05-09 precedent.

2. **No P0/P1 question needs fresh grounding that I can pick up today.** Two sub-cases:
   - The `.git/index` thread's research-side follow-up (R1, post-fix retro on the 2026-05-06 trailer-SHA1 mismatch) is explicitly gated on the recovery happening first. QUEUE.md Manual-Gate carries my own follow-up note: run R1 *the night of the recovery, not later*. Recovery has not happened (`.git/index` still 8 days stale; `.git/index.lock` still held). R1 stays gated.
   - The Camunda walk (QUEUE 2.5 P1 [in-progress]; NEEDS-INPUT line 55 `[answered: A]`) is grounded by `research/2026-04-29-camunda-import-checklist.md` (section-2 table is the walk script Eric will follow). No fresh research is required for closure; it is an attended Eric action.

3. **The 2026-05-08 researcher menu pin is functionally consumed.** `[answered: C]` selected R3 Pre-Phase-4 readiness audit, which researcher 2026-05-14 04:00 already produced as `research/2026-05-14-pre-phase-4-readiness-audit.md` (~17 KB, 9 findings, 5-sub-item PROPOSED bundle). The answer endorses pre-delivered work without naming a fresh question. Tomorrow's 04:00 researcher slot will face the same empty-menu state unless an explicit new ask lands tonight.

4. **Today's 04:00 slot is firing late.** Current UTC at this run = ~15:26 (=~11:26 ET); scheduled slot = 04:00 ET (08:00 UTC). Drift = ~7.5h. This is wider than worker-8am 14:14 (~1h14m late) and worker-9am 14:30 (~30m late) earlier today, which had been narrowing the 3-day wall-clock anomaly. The researcher slot is the FIRST of the day chronologically; if it fired this late, the worker chain's apparent narrowing pattern is misleading -- earlier slots may be drifting widest. Empirical only; not load-bearing for this run.

5. **Filing a fresh NEEDS-INPUT menu entry today is the right move (unlike 2026-05-09's no-action recommendation).** The 2026-05-08 entry was open for a full week and was just answered today, consuming the pin. Without a fresh entry, tomorrow's 04:00 researcher slot has no candidate questions to anchor on and will file a near-identical menu entry anyway. Filing now (vs. tomorrow) makes the question visible during tonight's evening review window, giving Eric a chance to pick before the next slot fires.

6. **The bailout chain BREAKING today is a regime change worth marking.** Worker-8am 14:14 (`d56137a`) and worker-9am 14:30 (`6b770ae`) are the first non-bailout Worker shifts since the 2026-05-12 burst. They closed via the dashboard answer-resolution contract's `[resolved:]` chain on NEEDS-INPUT.md, not via source code changes. This is the contract's first live exercise -- 2026-05-16 night-auditor will validate the byte-exact marker shape and emit JSONL to `logs/process-tools/2026-05-15.jsonl` per `roles/night-auditor.md` step 5. The contract appears to be working as designed; no research-side concern.

## Recommendation

**Actionable change: file a fresh NEEDS-INPUT menu entry asking what to investigate next.**

Three concrete bounded candidate questions to seed the entry (in priority order, all doable read-only from the Linux audit env):

- **(R4) Wall-clock anomaly fire-time analysis.** Day-3 of the wall-clock-late pattern with conflicting signals -- earlier worker slots today narrowed (worker-8am 1h14m late, worker-9am 30m late), but THIS researcher slot is 7.5h late, suggesting the narrowing pattern may not generalize across slot types. Bounded by: extract Worker / Researcher / Night-Auditor / Planner / Digest fire-times from JOURNAL.md across the past 7-10 days (timestamps are in role headers); characterize drift per slot type (sleep-bounded? scheduler-clock-drift? session-manager-queueing?); produce a per-slot ASCII chart + a single-paragraph hypothesis for the cause. Value: feeds the existing STATE.md "Known constraints" wall-clock-anomaly clause; if a hypothesis falls out cleanly, the planner can stop framing it as "cause unknown".

- **(R5) PROPOSED.md backlog freshness audit.** 32 open / 0 `[x]`-approved; some entries are plausibly functionally moot (commit-or-stash 0.6.1/0.6.2 retired by `261a674` 2026-05-05; the 5-grouped `.git/index` thread now structurally promoted to QUEUE Manual-Gate; the test-count staleness entries possibly covered by the cowork-session 2026-05-04 P1 numeric-fact auto-update authorization). Bounded by: cross-check each of the 32 entries against `git log --since=2026-04-29 --oneline` + the QUEUE Manual-Gate promotion + the cowork-session 2026-05-04 authorization scope; produce a candidates-to-retire list with "moot reason" per entry. Value: thinning the PROPOSED stack from 32 to ~15-20 makes the evening-review pass tractable for Eric.

- **(R7) `roles/*` drift survey + reconciliation candidates.** Multiple stale PROPOSED entries (lines 97, 103, etc.) document drift between disk and HEAD versions of `roles/{night-auditor,planner,worker}.md`. The auditor 2026-05-03 P2 + auditor 2026-05-04 entries pin specific byte counts and divergence shapes. Bounded by: re-run the diff vs HEAD for all role files this morning; characterize each diff as either (a) intentional skill-hook experiment that should commit + reword on-disk to match, (b) load-bearing automation behavior that should reverse-merge into HEAD, or (c) accidental leftover that should `git checkout HEAD -- roles/*.md` to restore. Produce a 3-bucket triage table. Value: every Planner / Worker / Auditor / Researcher run since 2026-04-30 has been Reading the on-disk version of role specs without knowing it diverges from HEAD -- a long-standing latent integrity gap.

**Carried forward (still valid but gated):**

- **(R1) Post-fix retro on the 2026-05-06 `.git/index` corruption mechanism.** Gated on Eric's Windows-side `rm -f .git/index .git/index.lock && git read-tree HEAD`. QUEUE.md Manual-Gate carries the explicit researcher note: run this *the night of recovery, not later* (signal decay). If Eric runs the recovery tonight, tomorrow's 04:00 researcher should auto-pick R1; if not, R1 stays gated.

- **(R2) Windows-side `.git/index.lock` holder forensics.** Unanswerable from the Linux audit environment. Requires Windows-side Process Monitor / Event Viewer / AV-log access from Eric.

If none of (R4)/(R5)/(R7)/(R1) fits, just specify the question you want and tomorrow's 04:00 researcher will pick it up. If you want NO research run tomorrow, mark `[answered] no question; skip` on the new menu entry.

## Open follow-ups

Carried forward from `research/2026-05-09-no-queued-question.md` (still all open):

1. (carried from 2026-05-07) "Was the trailer-SHA1 mismatch a real corrupt-write artifact or a body/trailer mismatch that auto-recovered when `git status` re-stat'd?" -- gated on the lock clearing.

2. (carried from 2026-05-07) "Which Windows-side process is holding `.git/index.lock` since 2026-04-29 17:10 UTC?" -- unanswerable from the Linux audit environment; needs Windows-side Process Monitor / Event Viewer access.

3. (carried from 2026-05-07) "Are any of the seven staged-modifications materially different from `261a674:`, or are they all identical except for whitespace?" -- low priority because the recovery command (`git read-tree HEAD`) wipes them all uniformly regardless.

4. (carried from 2026-05-07) "Does the destructive staged-delete on `RELEASE-NOTES-1.0.md` reproduce on a fresh clone, or is it specific to the index that was rewritten at 2026-05-07 06:06:47 UTC?" -- post-fix retro; only investigable after Eric's recovery command runs.

5. (carried from 2026-05-09) "How many consecutive Researcher slots in a row should file `[no queued question]` artifacts before the role spec or schedule needs adjusting?" -- with today this is the 3rd in the running window (2026-05-08 + 2026-05-09 + 2026-05-15; the 2026-05-12 post-pause state-pin and 2026-05-13 BPMN-XSD + 2026-05-14 Pre-Phase-4 broke the streak in the middle). Not yet load-bearing; worth re-flagging if 2026-05-16 makes it four.

6. (new this run) "Is the Researcher 04:00 ET slot's wall-clock drift today (~7.5h late) consistent with the Worker chain's narrowing pattern, or is the slot-type the load-bearing dimension?" Becomes the seed question for R4 if Eric picks it.

7. (new this run) "How many of the 32 currently-open PROPOSED entries are functionally moot vs. live?" Becomes the seed question for R5 if Eric picks it.
