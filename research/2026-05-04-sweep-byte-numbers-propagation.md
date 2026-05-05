# Sweep file's "byte-equal to HEAD" numbers: where they came from and when they went stale

Researcher run, 2026-05-04 ~04:00 local. Read-only. One bounded question, picked from the night-auditor 2026-05-04 00:05 PROPOSED entry's explicit ask.

## Question

(Verbatim from PROPOSED.md, 2026-05-04 night-auditor entry, "What it would do" line.)

> While there, fold the corrected byte/line numbers into STATE.md "Known constraints" and into `research/2026-05-02-night-auditor-confabulation-sweep.md` if it carries the wrong figures.

The sub-question this run answers: **does `research/2026-05-02-night-auditor-confabulation-sweep.md` carry the 2102 / 2188 "byte-equal to HEAD" numbers, and if so, what is the upstream source for those numbers and what are they actually claiming?** The night-auditor 2026-05-04 measured disk sizes 2682 / 4126 / 2477 for `roles/{planner,worker,night-auditor}.md` — disk EXCEEDS HEAD by +580 / +1938 / +647 bytes — and refuted the "byte-equal" framing as "empirically false the moment it was written." If the sweep file is upstream of STATE.md "Known constraints" and the auditor-2026-05-03 PROPOSED P2, then it is the load-bearing artifact for whether the corrective described in PROPOSED needs to also extend to amending the sweep itself.

## What I checked

Project root: `C:\Users\erics\Documents\GitHub\Process-Tools` (mounted at `/sessions/festive-wizardly-brown/mnt/Process-Tools/`). All evidence ran via the bash sandbox to defend against the Read-vs-disk disconnect.

1. Read the sweep file in full (124 lines / 15999 bytes per `wc`).
2. `grep -n -E '\b2102\b|\b2188\b|byte-equal' STATE.md QUEUE.md PROPOSED.md NEEDS-INPUT.md DONE.md JOURNAL.md research/*.md` — to find every occurrence of the 2102/2188 numbers and the "byte-equal" phrasing across the project.
3. Re-measured on-disk role-file sizes via three independent commands (`wc -c`, `stat -c %s`, `python3 len(open(rb).read())`) — all three agreeing.
4. `git cat-file -s HEAD:roles/{night-auditor,planner,worker}.md` for HEAD blob sizes.
5. `diff <(cat <file>) <(git show HEAD:<file>)` for content parity (default-format and unified) on all three role files.
6. `stat -c '%y'` mtimes on the sweep file and the three role files.
7. `git log --all --diff-filter=M --format='%h %ai %s' -- roles/{night-auditor,planner,worker}.md` to confirm the role files have only ever been touched by one commit (7c4edf7, 2026-04-26).
8. Pulled the worker-8am 2026-04-30 08:00 JOURNAL entry (lines 278+) to confirm its post-repair verification — the canonical "files match HEAD" datum that Auditor 3 then re-cited.
9. Pulled the auditor-3 (2026-05-01 00:05) JOURNAL entry to confirm where the 2102/2188 numbers first appeared in audit prose.
10. Compared the sweep's mtime against the role files' mtime to determine the ordering of the two events.

## What I found

### The sweep file does carry 2102 / 2188

`research/2026-05-02-night-auditor-confabulation-sweep.md` line 68 (the Auditor 3 row of the per-auditor table):

> **"Foundational-files truncation re-check ... `roles/planner.md` disk 2102 == HEAD 2102, `roles/worker.md` disk 2188 == HEAD 2188 ... Worker-8am 2026-04-30 repair held overnight."** | **INSUFFICIENT CHECK** — byte counts match, but `diff <(cat roles/planner.md) <(git show HEAD:roles/planner.md)` returns 13 lines of differences ... `roles/worker.md` content diff is 42 lines ... The mtimes on both files are 2026-04-30 14:07:46 UTC — pre-audit but post-repair-by-worker-8am.

The sweep accepts these byte numbers AS still-true at sweep time and adds the content-drift finding on top. The sweep's verdict for the row is "INSUFFICIENT CHECK" — but the insufficiency it identifies is using `wc -c` parity as a proxy for content parity, NOT the byte numbers themselves being stale.

### Upstream source of 2102 / 2188 in audit prose

JOURNAL.md, auditor-3 entry (2026-05-01 00:05), "did" section:

> Foundational-files truncation re-check: `roles/night-auditor.md` disk 1830 == HEAD 1830, `roles/planner.md` disk 2102 == HEAD 2102, `roles/worker.md` disk 2188 == HEAD 2188. Worker-8am 2026-04-30 repair held overnight.

This is where the 2102 / 2188 numbers first appear in audit prose. They were correct as a point-in-time observation at 2026-05-01 00:05 — at that moment, mtime on the role files was still 2026-04-30 14:07:46 UTC (the worker-8am repair timestamp), the worker-8am post-repair verification (JOURNAL line 282-291) had set them to HEAD-equal, and nothing had modified them since.

The sweep then cited Auditor 3's wording (in quotes, marking it as Auditor 3's claim) and recorded the verdict as "INSUFFICIENT CHECK" — the verdict critiques the byte-vs-content failure mode but does NOT critique the byte numbers themselves.

### The decisive timing evidence

| Event | Timestamp (UTC) |
|---|---|
| Worker-8am 2026-04-30 restores role files to HEAD via `git show HEAD:<file> > <file>` (mtime advances) | 2026-04-30 14:07:46 |
| Auditor 3 (2026-05-01 00:05) records disk == HEAD at 2102 / 2188 (true at this moment) | 2026-05-01 00:05 |
| Role files modified to add skill-hook content (current mtime, no further changes since) | 2026-05-02 07:46:12–29 |
| Sweep file written (current mtime — final save) | 2026-05-02 10:14:49 |
| Tonight (auditor 2026-05-04 00:05) re-measures disk sizes 2682 / 4126 / 2477 | 2026-05-04 00:05 |
| This research run | 2026-05-04 04:00 local (~10:00 UTC) |

The sweep's final mtime (2026-05-02 10:14:49 UTC) is **2 hours 28 minutes AFTER** the role files were modified to their current larger sizes (2026-05-02 07:46:12-29 UTC). At the moment the sweep file was written, on-disk reality was already 2682 / 4126 / 2477 — not 2102 / 2188 / 1830. The sweep's "byte-equal to HEAD" claim was therefore empirically false at sweep authoring time.

The sweep was internally inconsistent in a specific way: the byte numbers (2102 / 2188) describe the pre-2026-05-02-07:46 state; the content-drift finding (skill-hook refs to `engineering:testing-strategy` / `engineering:code-review` / `engineering:debug`) describes the post-2026-05-02-07:46 state. The sweep merged these two observations as if simultaneous. The skill-hook content was not on disk at Auditor 3's time (worker-8am had just cleanly restored to HEAD ~10h prior); it appears to have been added at 2026-05-02 07:46 — between Auditor 3 and the sweep's authoring.

### Three downstream artifacts inherit the wrong numbers

1. **`STATE.md` line 37** ("Known constraints"):
   > `roles/planner.md` (2102 bytes) and `roles/worker.md` (2188 bytes) are byte-equal to HEAD but content-different by 13 / 42 lines.

   Attribution: "researcher 2026-05-02; re-verified by auditor 2026-05-03". Currently false on disk — the planner overwrites STATE.md each morning, so this attribution chain has been re-asserted by the planner each of the past 2-3 mornings without re-measurement.

2. **`PROPOSED.md` line 97** (auditor 2026-05-03 PROPOSED P2 entry, "Why" field):
   > researcher 2026-05-02 04:00 documented (and STATE.md "Known constraints" carries forward) that both files are byte-equal to HEAD (2102 / 2188 bytes — so no `wc -c` parity check catches the drift) but content-different.

   This PROPOSED's premise ("`wc -c` parity check does NOT catch the drift") is the inversion of current reality (`wc -c` DOES catch the drift, since disk 2682/4126/2477 ≠ HEAD 2102/2188/1830). The three options (restore-from-HEAD / commit-with-intent / re-finish-then-commit) are still relevant; the framing argument for why they are needed is wrong.

3. **`PROPOSED.md` line 102+** (auditor 2026-05-04 entry, filed last night) is the empirical correction. It lists the correct disk numbers (2682 / 4126 / 2477), the correct HEAD numbers (2102 / 2188 / 1830), and the correct delta (+580 / +1938 / +647). This is the entry that asked this research run to also check the sweep file.

### What about the mtime claim?

The sweep also asserts, in the same row: "The mtimes on both files are 2026-04-30 14:07:46 UTC — pre-audit but post-repair-by-worker-8am." That mtime claim was true at Auditor 3's audit time and remained true through the early hours of 2026-05-02. By the time the sweep file was actually written (2026-05-02 10:14:49 UTC), the role-file mtime had already advanced to 2026-05-02 07:46 UTC. The sweep's mtime claim is the same shape of error as its byte-count claim — a value inherited from the prior auditor's frame instead of re-measured at sweep time.

### Worker-8am repair was clean — content drift came later

JOURNAL.md, worker-8am 2026-04-30 entry (line 282 onwards):
> CLAUDE.md, roles/night-auditor.md, roles/planner.md, roles/worker.md: restored from HEAD via `git show HEAD:<file> > <file>`. Final sizes: 82/4660, 36/1830, 37/2102, 35/2188 — all match HEAD exactly.
> ...
> All 4 files match HEAD byte-for-byte: `wc -lc` identical to `git show HEAD:<file> | wc -lc` on all four. ... `git diff --stat HEAD -- CLAUDE.md roles/night-auditor.md roles/planner.md roles/worker.md`: empty (zero delta).

The worker-8am repair WAS clean. There is no scenario where the role files held skill-hook content at 2026-04-30 14:07 (just-restored-to-HEAD) AND the sweep observed both byte-equal and content-different at 2026-05-02 ~10:14 unless modification happened in between. The role-file mtime (2026-05-02 07:46) marks that modification — almost certainly an Eric / cowork-session edit (the only commit that ever touched these files is 7c4edf7 from 2026-04-26 21:47). That edit added the skill-hook block and grew the files by +580 / +1938 / +647 bytes.

### Re-measured today (2026-05-04 ~10:00 UTC)

| File | wc -c (disk) | stat (disk) | py-len (disk) | wc -l (disk) | HEAD blob | HEAD wc -l | mtime |
|---|---|---|---|---|---|---|---|
| roles/night-auditor.md | 2477 | 2477 | 2477 | 40 | 1830 | 36 | 2026-05-02 07:46:29 UTC |
| roles/planner.md | 2682 | 2682 | 2682 | 41 | 2102 | 37 | 2026-05-02 07:46:20 UTC |
| roles/worker.md | 4126 | 4126 | 4126 | 50 | 2188 | 35 | 2026-05-02 07:46:12 UTC |

Current `diff | wc -l` against HEAD: 5 / 5 / 34 (night-auditor / planner / worker), NOT 13 / 42 as the sweep claimed for planner / worker. The sweep's diff-line counts are also stale or inherited.

## Recommendation

**Actionable change.** The corrective is simple and bounded:

1. **Amend `research/2026-05-02-night-auditor-confabulation-sweep.md` line 68** with a footnote (or inline correction) noting that (a) the byte numbers cited (2102 / 2188) describe Auditor 3's audit-time state and were already stale by sweep authoring time (mtime of the sweep file is 2026-05-02 10:14 UTC, ~2.5h after the role files were modified to their current larger sizes at 07:46 UTC); (b) at sweep authoring time, on-disk sizes were 2682 / 4126 (current); (c) the diff-line counts (13 / 42) are also of indeterminate provenance — current measurement returns 5 / 34. The sweep's underlying *finding* (audit-quality discipline insufficient, byte-vs-content parity gap exists) remains valid; only the specific numbers are stale. **This research run did NOT amend the sweep file** — it is a research output, and per researcher-role spec ("do not modify code"), out of scope. Eric (or the next research run with explicit authorization) is the right party to amend it.

2. **Amend `STATE.md` line 37 ("Known constraints")** with the correct numbers when the planner next overwrites STATE.md (planner runs at 07:10 each morning and is the only role that owns STATE.md). The corrected line should cite disk 2682 / 4126 / 2477 against HEAD 2102 / 2188 / 1830, the +580 / +1938 / +647 deltas, and acknowledge the drift covers all three role files (not just planner / worker). Tonight's auditor 2026-05-04 PROPOSED already asks for this.

3. **Update `PROPOSED.md` line 97** (auditor 2026-05-03 entry) framing: replace "no `wc -c` parity check catches the drift" with "`wc -c` parity check now DOES catch the drift" and update the cited byte numbers. The three options menu is otherwise correct.

4. **Do NOT add a new PROPOSED entry.** Tonight's auditor 2026-05-04 PROPOSED entry already covers the same scope. Opening a separate PROPOSED would clutter the inbox Eric is already triaging at 15 open items. This research file is the grounding evidence for the auditor's empirical correction, not an independent proposal.

The deeper finding — that the audit-quality issue extends to research files — is itself worth folding into the cowork-session 2026-04-30 PROPOSED entry as a fifth sub-correction: **"Numeric / size / mtime claims about external files must be re-measured at the moment of writing, not inherited from the prior author's framing — applies to research and digest authors, not just auditors."** The sweep file (a research output) failed exactly this check; the corrective should target the role broadly, not just the night-auditor. This is consistent with researcher 2026-05-03's recommendation to broaden the scope of the corrective from "auditor" to "any role making quantitative claims."

## Open follow-ups

1. **Who edited the role files at 2026-05-02 07:46 UTC, and was the truncation in the skill-hook addition intentional?** The current disk content of `roles/worker.md` cleanly references the three engineering skills in steps 3, 5, 6 but does NOT appear truncated mid-sentence in this researcher's spot read (lines 1-30). The sweep claimed the disk file "truncates step 6 mid-bullet ending on `\ No newline at end of file`" — a check this run did NOT fully exhaustively verify across all 50 lines of the disk file. Worth one more `tail -c 80` check to determine whether the on-disk role files are themselves a partial / truncated edit (which would shift the three-options menu in PROPOSED toward "re-finish-then-commit") or a clean intentional edit (which would shift toward "commit-with-intent").
2. **Has the sweep file's diff-line counts (13 / 42) propagated downstream the same way the byte numbers did?** Quick `grep -n '13.* line\|42.* line\|13/42\|13 / 42' STATE.md PROPOSED.md JOURNAL.md` would map the count's reach. STATE.md line 37 already carries "13 / 42 lines"; this research run did not check whether the actual current diff-line counts (5 / 34 by `diff | wc -l`) are smaller because the sweep over-counted, or because the on-disk content has changed again since sweep time.
3. **Should research files carry a re-measurement footer?** The sweep's failure mode — inheriting numbers from the prior author's frame — is the same shape audit prose has been failing at. A standardized "Re-measurement at write time: <numbers>" block at the bottom of each research file would let downstream consumers see the as-of timestamp and the actual measurement, not just whatever was quoted in-line. Out of scope for this run; would be a researcher-role spec change.
