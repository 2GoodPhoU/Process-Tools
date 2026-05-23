# PROPOSED.md backlog freshness audit -- candidates-to-retire pass

> researcher 2026-05-17 -- bounded read-only audit per `roles/researcher.md` step 2/3. Source-of-truth for the recommendation column is the bash-verified empirical state at run time, not memory or other state-file claims.

## Question

(R5 from the researcher 2026-05-15 04:00 menu on `NEEDS-INPUT.md` lines 75-86, still open and unconsumed, self-picked per researcher-role precedent established by researcher 2026-05-16 selecting R4 without dashboard answer.)

> PROPOSED.md backlog freshness audit. 34 open `[ ]` / 0 `[x]`-approved with several entries plausibly functionally moot post-`261a674` 2026-05-05 / post-`bbcbff5` 2026-05-12 / post-planner-2026-05-15-07:10 Manual-Gate promotion. Cross-check each entry against `git log --since=2026-04-29 --oneline` + the QUEUE Manual-Gate promotion + the cowork-session 2026-05-04 P1 numeric-fact auto-update authorization scope; produce a candidates-to-retire list with "moot reason" per entry. Value: thins the PROPOSED stack from 34 to ~15-20, making evening-review tractable.

## What I checked

- `PROPOSED.md` -- read full file in three chunks (1-120 / 120-240 / 240-end). 34 open `[ ]` entries enumerated. One entry (line 133, cowork-session 2026-05-04 `TO-PUSH.md`) is structurally malformed -- truncated mid-word at "becaus" in the `- Why:` field with no closing fields, an artifact of the same Edit-tool truncation hazard CLAUDE.md flags.
- `git log --since='2026-04-29' --pretty=format:'%h %ci %s'` (32 commits enumerated through HEAD `d1500e17` 2026-05-16 worker-8am).
- `git status -s` on the repo root (pin: index 27871 b / mtime 2026-05-07 06:06:47 UTC unchanged 10 days; `.git/index.lock` 0-byte Windows-held sentinel still present; `D RELEASE-NOTES-1.0.md` staged-delete still present + matching `?? RELEASE-NOTES-1.0.md` untracked working-tree file confirms the 2026-05-07 RISKY P1 data-loss vector is still load-bearing).
- File-existence probes for the housekeeping-candidate artifacts: `ROADMAP.md.new` (15454 b on disk, mtime 2026-05-04 17:58 UTC -- still present); `test_write.tmp` (0 b, mtime 2026-05-06 10:10 UTC -- still present); `.dashboard-enrichment.json` (8070 b, mtime 2026-05-14 05:56 UTC -- still present); `RELEASE-NOTES-1.0.md` (5839 b -- still present on disk and in HEAD).
- `schedule.json` git-status pin: `git status --porcelain schedule.json` -> empty (clean); `git diff HEAD schedule.json` -> empty. Working tree matches HEAD byte-exact. The auditor 2026-05-05 P2 housekeeping entry (line 147) sub-item (2) about the "7-day-uncommitted comment-only schedule.json update" is empirically obsolete -- the comment update is now in HEAD.
- Role-file disk-vs-HEAD pin via `wc -c <file>` + `git cat-file -s HEAD:<file>` + `diff <(git show HEAD:<file>) <file>`:
  - `roles/night-auditor.md` -- disk 5642 b / HEAD 3441 b / DIFF (+2201 b drift).
  - `roles/planner.md` -- disk 2682 b / HEAD 2682 b / **EQ**.
  - `roles/worker.md` -- disk 6976 b / HEAD 5588 b / DIFF (+1388 b drift).
  - `roles/researcher.md` -- disk 2275 b / HEAD 2275 b / EQ.
  - `roles/digest.md` -- disk 1344 b / HEAD 1344 b / EQ.
  - `CLAUDE.md` -- disk 6728 b / HEAD 6223 b / DIFF (+505 b drift -- the BPMN/Camunda waiver block plus the May-2026 push-policy clarifications).
- CLAUDE.md test-count claim: line 11 still says `unittest discover (606 in requirements-extractor + 40 in nimbus-skeleton + 30 in compliance-matrix + 26 in process-tools-common = 702 total)`. Auditor 2026-05-17 00:05 pin: `708/708 across 4 sub-tools (26 process-tools-common + 30 compliance-matrix + 45 nimbus-skeleton + 607 requirements-extractor)`. Drift: +1 requirements-extractor / +5 nimbus-skeleton / +6 total since the last refresh commit `2935e30` 2026-05-05.
- `samples/bpmn_validation/*` CRLF pin via `python3 ... .count(b'\r\n')`: `.bpmn` 111 / `.puml` 13 / `.xmi` 27 / `.skel.yaml` 31. All four CRLF counts match the auditor 2026-05-05 PROPOSED entry's numbers byte-exact. The drift is unchanged in 12 days.
- `JOURNAL.md` NUL-byte pin: `python3 -c "d=open('JOURNAL.md','rb').read(); print(d.count(b'\x00'))"` -> 3. Matches the auditor 2026-05-17 RISKY entry's finding.
- `STATE.md` "Open threads" + "Known constraints" + "Recent decisions" sections, cross-referenced against each PROPOSED entry's status.
- `QUEUE.md` Manual-Gate section -- confirms `.git/index` refresh is `[in-progress]` eric-action since planner 2026-05-15 07:10 promotion. The promotion grounding is NEEDS-INPUT line 36 `[answered: B 2026-05-15 via dashboard]`.
- Researcher role spec: this entry adopts the role's read-only-and-bounded posture; recommendation column carries no auto-actions, only retire/amend/keep judgments.

## What I found

The 34 open entries decompose into 5 disposition buckets. Numbers are 1-indexed line numbers in `PROPOSED.md` as of this run.

### Bucket A -- Fully moot (committed work or QUEUE-promoted; safe to retire outright)

| Line | Title (abbrev) | Moot reason |
|------|---------------|-------------|
| 23 | auditor 2026-04-29: commit-or-stash 0.6.1/0.6.2 patch line in `requirements-extractor/` | Committed by Eric in `261a674` 2026-05-05 "Update ROADMAP/CLAUDE; add requirements-extractor" + worker `2935e30` "refresh CLAUDE.md test counts" + the surrounding worker chain. The ~840 LOC patch line is now in HEAD. STATE.md "Manual-Gate" entry at line 23-29 of QUEUE.md confirms this in its grounding note ("one of the two (commit-or-stash 0.6.1/0.6.2) was already DONE by `261a674` 2026-05-05 so is moot"). |
| 41 | researcher 2026-04-29: fold Camunda Modeler import checklist into `samples/bpmn_validation/README.md` | Committed by worker-12pm `f734248` 2026-05-05 "P2 fold Camunda import checklist into samples/bpmn_validation/README.md (QUEUE 2.2)". |
| 47 | researcher 2026-04-29: small structural-diff helper for BPMN before/after Camunda re-save | Committed by worker-9am `9ca814d` 2026-05-13 "P1 BPMN structural-diff helper + 5 tests (QUEUE 2.1)". (Note: the file currently shows as `D` in `git status -s` because the on-disk index is stale; HEAD has the file at the expected path. The Manual-Gate `.git/index` recovery closes that visual artifact.) |
| 65 | auditor 2026-04-30: refresh `.git/index` from HEAD via `git read-tree HEAD` | Promoted to QUEUE.md Manual-Gate `[in-progress]` eric-action by planner 2026-05-15 07:10 per NEEDS-INPUT line 36 `[answered: B 2026-05-15 via dashboard]`. The PROPOSED entry's intent is now tracked in QUEUE.md; no separate `[x]` needed. (The 4 successor entries -- lines 153/160/167/174 -- co-retire when Eric runs the Windows-side recovery; see Bucket E.) |

**Bucket A total**: 4 entries. Retire by deletion or by strike-through with a one-line `[retired: <reason> <commit-SHA-or-promotion-source>]` annotation.

### Bucket B -- Partially moot (amend / scope-reduce; do not retire wholesale)

| Line | Title (abbrev) | Amendment |
|------|---------------|-----------|
| 96 | auditor 2026-05-03: role-file drift on 2 files (`roles/planner.md` + `roles/worker.md`) | `roles/planner.md` is now byte-EQ to HEAD (2682/2682; diff empty). Scope reduces to `roles/worker.md` only. Entry still load-bearing for worker.md (+1388 b drift). Suggest: re-cite the disk-vs-HEAD numbers in an amendment, drop the planner.md half. |
| 102 | auditor 2026-05-04: corrective on entry 96, extending to 3 files | Same correction as 96. `roles/night-auditor.md` (+2201 b) and `roles/worker.md` (+1388 b) still drift; `roles/planner.md` now EQ. Consolidating 96 + 102 + 135 into a single canonical "role-file drift (worker.md + night-auditor.md only)" entry is cleaner than carrying three overlapping framings. |
| 135 | auditor 2026-05-05: empirical refresh of role-file drift (3 files growing daily) | Same scope reduction. Numbers in the entry are now stale by ~12 days (entry says `night-auditor.md` 3441 b / `worker.md` 5588 b -- disk has grown to 5642 b / 6976 b respectively). The three-options menu (restore-from-HEAD / commit-with-intent / re-finish-then-commit) is unchanged in shape. |
| 147 | auditor 2026-05-05: housekeeping (`ROADMAP.md.new` removal + `schedule.json` comment commit) | Sub-item (2) `schedule.json` comment-only update is now in HEAD (`git diff HEAD schedule.json` empty; the comment was bundled into `261a674` 2026-05-05). Sub-item (1) `ROADMAP.md.new` (15454 b, byte-identical to `ROADMAP.md`, mtime 2026-05-04) is still on disk. Amend to keep (1) only. |
| 195 | researcher 2026-05-13: bundle-answer QUEUE 2.4 D1/D2/D3 | D1 (validator library) answered via dashboard line 73 `[answered: A 2026-05-15 via dashboard]` -> `lxml` (not the researcher's recommended `xmlschema`); pair `[resolved: 2026-05-16 by worker-8am]` byte-exact (verified by auditor 2026-05-17 JSONL emission). D2 (OMG XSD vendor sign-off) and D3 (dev-only confirm) remain open. The 8-step Worker spec in the entry is still load-bearing for D2/D3-execution post-`[x]` -- just substitute "use lxml per the line-73 dashboard answer" for the D1 recommendation. Amend to D2/D3-only + the per-step worker spec, OR keep as-is with a one-line "D1 closed via dashboard 2026-05-15; this entry covers D2+D3 only" annotation at the top. |
| 221 | auditor 2026-05-16: NEEDS-INPUT.md truncation 3-sub-action bundle | Sub-action (A) "repair NEEDS-INPUT.md tail" -- executed by planner 2026-05-16 07:10 (22603 -> 22804 b / CRLF normalized; verified by auditor 2026-05-17 disk-vs-HEAD diff empty). Sub-action (B) "pair the line-73 marker" -- executed by worker-8am `d1500e17` 2026-05-16 14:14 (verified + JSONL-emitted by auditor 2026-05-17). Sub-action (C) "adopt diff-vs-HEAD post-edit verification recipe" remains open and is the only sub-action awaiting Eric `[x]`. Amend to (C)-only OR fold (C) directly into the cowork-session 2026-05-04 P1 post-edit-verification entry (line 109 / QUEUE 3.5) -- both target the same workflow gate. |

**Bucket B total**: 6 entries. Each amends in-place; net entry-count drops by 2 if 96/102/135 consolidate into one canonical role-file-drift entry.

### Bucket C -- Superseded by a later entry (retire the older; keep the newer)

| Line | Title (abbrev) | Superseded by |
|------|---------------|---------------|
| 53 | worker-8am 2026-04-29: NUL-byte sweep on tracked `.py` files | Auditor 2026-05-17 RISKY entry (line 233) escalates scope from `*.py`-only to all tracked text-class files. Closing the broader entry covers this one. |
| 77 | worker-10am 2026-04-30: PyInstaller spec patch for `yaml` + `actor_heuristics` | Researcher 2026-05-14 readiness-audit sub-item (A) (line 211) lists all four missing hiddenimports (`yaml`, `actor_heuristics`, `compound`, `multi_action`) and explicitly retires the "once 0.6.1/0.6.2 lands" hedge as moot post-`261a674`. The 2026-05-14 entry is the canonical version. |
| 153 | auditor 2026-05-06 (P1): `.git/index` corruption (`bad index file sha1 signature`) | Auditor 2026-05-07 RISKY P1 verification gate (line 160) supersedes this with the empirical finding that `git fsck` was clean on the 2026-05-07 audit. The 2026-05-06 framing ("structurally corrupt") was empirically incorrect; the 2026-05-07 framing ("stale, with self-consistent trailer-SHA1") is what STATE.md "Known constraints" now carries. Retire 153 with a "framing-superseded by 160" annotation; preserve the chain history. |

**Bucket C total**: 3 entries. Retire by strike-through with `[superseded by line <N>]`.

### Bucket D -- Malformed (repair before re-evaluating)

| Line | Title (abbrev) | Repair needed |
|------|---------------|---------------|
| 133 | cowork-session 2026-05-04: `TO-PUSH.md` + nightly digest push checklist | Entry truncated mid-word in the `- Why:` field at "Eric pushed `ae7d9fd` (worker-12pm bookkeeping) to origin/main manually becaus" with no closing fields. The truncation is consistent with the Edit-tool ~3 KB cap that CLAUDE.md flags. Repair by either (a) deleting the entry as unrecoverable + asking cowork-session to re-file it cleanly, or (b) reconstructing the missing text from the 2026-05-04 cowork-session JOURNAL entry if it captures the intent. Without repair the entry cannot be evaluated for `[x]`. Recommend (a) -- the topic (a one-line nightly push checklist in the digest) is small enough that a re-file is cheaper than archeology. |

**Bucket D total**: 1 entry.

### Bucket E -- Still load-bearing (keep as-is)

| Line | Title (abbrev) | Status note |
|------|---------------|-------------|
| 29 | auditor 2026-04-29: Windows pre-commit hook Python discovery fix | Still applicable. Bash-script-only doc. |
| 35 | auditor 2026-04-29: fail-loud test_all.sh on test-module load errors | Still applicable. ~20 LOC bash. |
| 59 | auditor 2026-04-29: refresh CLAUDE.md test counts | Auto-resolves if cowork-session 2026-05-04 numeric-fact auto-update authorization (line 121) lands first. Both still pending; pair-approve. |
| 71 | auditor 2026-04-30: Read-tool-vs-disk doc rule | Doc-only. Compounds slowly. |
| 84 | cowork-session 2026-04-30: night-auditor confabulation investigation | Already grounded by `research/2026-05-01-night-auditor-confabulation.md` per STATE.md "Recent decisions" thread; remaining ask is the audit-role policy clause. |
| 90 | auditor 2026-05-01: commit Eric's BPMN/Camunda waiver edit to CLAUDE.md | Still applicable -- disk drifts from HEAD by +505 b (the waiver block + push-policy edits). Single bookkeeping commit. |
| 109 | cowork-session 2026-05-04 (P1): post-edit verification step in `roles/{worker,planner}.md` | QUEUE 3.5 cross-reference; the line 221 sub-action (C) duplicates the workflow ask. Pair-approve or fold. |
| 115 | cowork-session 2026-05-04 (P1): QUEUE.md `## Auto` / `## Manual Gate` split | **Soft-implementation already present**: QUEUE.md now carries a `## Manual-Gate / eric-action` section (header at line 19) holding the `.git/index` recovery + BPMN 2.5 attended-only items, and the "Decomposed (next-pull-ready)" pointer at line 42 explicitly directs Workers at the dashboard-marker queue first. The role-spec amendments to formalize the split are still missing, so the entry is **partially-implemented** -- keep, but note the soft-implementation status. Could move to Bucket B if you prefer the in-place annotation. |
| 121 | cowork-session 2026-05-04 (P1): numeric-fact auto-update authorization | Highest-leverage pending entry per researcher 2026-05-15. Once approved, retires line 59 + the recurring "CLAUDE.md test counts are stale" thread. |
| 127 | cowork-session 2026-05-04 (P2): `[auto-promote-after: Nh]` rule | Still applicable. Workflow change. |
| 141 | auditor 2026-05-05: CRLF normalization on `samples/bpmn_validation/*` | Empirical pin confirmed (CRLF counts 111/13/27/31 byte-exact to the entry's claims, 12 days unchanged). One-line `.gitattributes` change. |
| 160 | auditor 2026-05-07 (RISKY P1): `.git/index` verification gate | Tied to the QUEUE Manual-Gate item; co-retires with line 65 on Eric Windows-side recovery. |
| 167 | auditor 2026-05-07 (RISKY P1): RELEASE-NOTES-1.0.md staged-delete data-loss vector | Verified still load-bearing -- `git status -s` shows `D  RELEASE-NOTES-1.0.md` + `?? RELEASE-NOTES-1.0.md`; HEAD has the file (5839 b). Co-retires with line 65 on Manual-Gate recovery. |
| 174 | auditor 2026-05-07 (RISKY P2): broader on-disk-index/HEAD 8-mod-1-delete divergence | Same thread as 167. Co-retires with line 65. |
| 181 | auditor 2026-05-07 (P3): `test_write.tmp` 0-byte stray | Still on disk (`test_write.tmp`, 0 b, mtime 2026-05-06 10:10 UTC). One-line `.gitignore` patch. |
| 187 | auditor 2026-05-07 (P3): `git gc` on 13 dangling objects | Gated on `.git/index.lock` clearing; co-retires-or-actions with line 65. |
| 203 | auditor 2026-05-14 (P3): `.dashboard-enrichment.json` `.gitignore` entry | Still on disk (8070 b, mtime 2026-05-14 05:56 UTC). One-line `.gitignore` patch; bundle with 181. |
| 210 | researcher 2026-05-14 (P2-bundle): Pre-Phase-4 readiness 5 sub-items | Highest-leverage Phase-4-readiness item. Adopt-all is recommended per the bundle's own framing. |
| 233 | auditor 2026-05-17 (RISKY P2): JOURNAL.md NUL contamination 2-sub-action bundle | Fresh tonight. Sub-action (A) is a 2-min worker action; sub-action (B) pairs with line 53's escalation. |

**Bucket E total**: 19 entries (some pair-approve or co-retire on the same gate).

## Net effect on backlog size

Adoption of the recommendation bucket-by-bucket:

- **Adopt Bucket A only** (4 retires): backlog 34 -> 30. Low-friction win; all four have either a commit SHA or a Manual-Gate promotion as grounding.
- **Adopt A + B** (4 retires + 6 amendments, 2 net additional drops via 96/102/135 consolidation): backlog 34 -> 28.
- **Adopt A + B + C** (+ 3 supersede-retires): backlog 34 -> 25.
- **Adopt A + B + C + D-repair** (line 133 deleted as unrecoverable): backlog 34 -> 24.
- **Plus pair-approve the two zero-risk `.gitignore` items (181 + 203) as one commit, and line 59 auto-resolves on `[x]` of line 121**: practical evening-review-tractable count drops to ~20-22 open entries.

The R5 menu entry target ("thin the PROPOSED stack from 34 to ~15-20") is **achievable but tight**: getting below 20 requires either Eric `[x]`-approval of one or more Bucket E entries during the same review window, or a willingness to consolidate further (e.g. fold line 121 numeric-fact + line 127 auto-promote + line 115 QUEUE-split into a single "workflow-doc batch" entry). My read is that the **24-after-A+B+C+D shape is the right floor for a single review pass** -- further consolidation crosses into "rewriting other authors' framings" territory, which costs more in audit-quality than it saves in stack depth.

## Recommendation

**Actionable change**: in Eric's next evening-review pass, apply the per-bucket dispositions above. Concrete shape:

1. Bucket A (4 entries: 23 / 41 / 47 / 65) -- strike-through or delete with a one-line retire annotation citing the closing commit SHA or QUEUE Manual-Gate promotion source. Single keystroke per entry once the cite is at hand.
2. Bucket C (3 entries: 53 / 77 / 153) -- same shape, citing the superseding line number.
3. Bucket B (6 entries: 96 / 102 / 135 / 147 / 195 / 221) -- amend in-place. Consolidate 96+102+135 into one canonical role-file-drift entry; reduce 147 to the `ROADMAP.md.new` half; reduce 221 to sub-action (C) only; reduce 195 to D2+D3 only.
4. Bucket D (1 entry: 133) -- delete as unrecoverable; if the `TO-PUSH.md` idea is still wanted, ask cowork-session to re-file from scratch.
5. Bucket E (19 entries) -- keep, but consider pair-approving (181 + 203) as a single one-line `.gitignore` patch and pair-approving (59 + 121) as the numeric-fact-auto-update authorization that retires 59 by side-effect.

**Not actionable change**: no Bucket-F "filing-quality" recommendations. The audit-quality dimension is already adequately tracked via the cowork-session 2026-04-30 confabulation investigation entry (line 84) + the recurring drift-vs-HEAD checks that planner 2026-05-16 + auditor 2026-05-17 are now formalizing via diff-vs-HEAD post-edit recipes.

This research file is the deliverable; the bucket dispositions are recommendations to Eric, not auto-actions. Per the researcher role spec I am NOT appending to PROPOSED.md or modifying QUEUE.md / STATE.md / source. The R5 menu entry on NEEDS-INPUT line 75-86 remains structurally open -- a separate `[answered:]` dashboard write or self-pick by tomorrow's researcher slot can consume it or carry it forward.

## Open follow-ups

- **(R5-followup-1) Line 133 reconstruction**: if `TO-PUSH.md` + nightly digest one-line push checklist is still wanted, the `cowork-session` author needs to re-file. The truncated tail at "becaus" was never captured anywhere else I checked. A cheap path: have tonight's digest slot (or tomorrow's) emit one new PROPOSED entry titled "nightly push checklist in digest output" with a clean 4-field shape, and delete the truncated line 133 in the same pass.
- **(R5-followup-2) Consolidation policy**: this audit pulled 96 + 102 + 135 into one canonical role-file-drift framing, but did not pull 109 + 221(C) into one canonical post-edit-verification framing because both have independent QUEUE cross-references (QUEUE 3.5 cites 109; auditor 2026-05-17 might cite 221 in tomorrow's JSONL emission). Eric's call whether the audit-trail value of "preserve each author's framing" outweighs the stack-depth value of consolidation. My default is preserve framings; consolidate only when the older entry is empirically false (Bucket C 153) or unrecoverable (Bucket D 133).
- **(R5-followup-3) Bucket E pair-approval**: lines 181 (test_write.tmp) + 203 (.dashboard-enrichment.json) are both one-line `.gitignore` patches with zero blast radius and target the same data-loss-via-vanilla-`git add .` vector that the `.git/index` Manual-Gate item is the canonical fix for. Pair-approving them as a single commit -- possibly bundled with the Manual-Gate recovery itself -- retires two P3 entries for free.
- **(R5-followup-4) Test-count drift retire**: line 59 ("refresh CLAUDE.md test counts") and line 121 (numeric-fact auto-update authorization) are tightly coupled. Approving line 121 lets the night-auditor commit the `606+40 -> 607+45` correction directly without re-filing line 59. Approving line 59 alone re-creates the same drift the next time a test count moves. Strongly prefer line 121 as the load-bearing approval.
- **(R5-followup-5) Researcher-menu structural state**: the 2026-05-15 04:00 menu on NEEDS-INPUT line 75-86 has now been self-picked by two consecutive researchers (R4 by 2026-05-16, R5 by this run) without a formal dashboard answer. The menu's remaining candidates are R7 (`roles/*` drift survey -- partially overlaps with this audit's Bucket B 96/102/135 consolidation), R1 (post-`.git/index`-recovery retro, gated on Eric Windows-side action), and R2 (Windows-side lock-holder forensics, un-doable from this env). R7 is the only remaining doable-from-this-env candidate; if Eric wants it picked up tomorrow, no fresh `[answered:]` is needed -- tomorrow's researcher can self-pick the same way.

---

*End of file. 5 sections per role-spec template; bucket disposition is a recommendation, not an auto-action. Append-only history preserved. No source / QUEUE / STATE / PROPOSED modifications this run.*
