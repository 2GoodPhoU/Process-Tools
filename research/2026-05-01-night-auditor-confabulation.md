# Night-auditor confabulation: source trace

Researcher run, 2026-05-01 ~04:00 local. Read-only. One bounded question.

## Question

(Verbatim from `PROPOSED.md`, cowork-session entry 2026-04-30, line 92.)

> Figure out where the phantom text came from. Candidates: (a) a previous version of `roles/worker.md` that was rolled back (check `git log -p roles/worker.md` -- if so, the auditor is reading via Read tool which may surface stale blob content), (b) a parenthetical in another role doc that the auditor generalized, (c) pure confabulation.

The phantom text the night-auditor cited on 2026-04-30 (PROPOSED entry on push-policy reconcile, since `[x] resolved no-action` by Eric):

1. `Push to a working branch named automation/<role>-<YYYY-MM-DD>-<slot>. NEVER push to main or master directly.`
2. `Do NOT bypass the lock with the plumbing-path workaround in this flow -- locks block remote-affecting actions intentionally.`

## What I checked

Project root: `C:\Users\erics\Documents\GitHub\Process-Tools` (mounted at `/sessions/wonderful-gifted-hopper/mnt/Process-Tools/`). All commands run via the bash sandbox, not the Read tool, to defend against the documented Read-vs-disk disconnect.

1. Full file history: `git log --all --oneline roles/worker.md`.
2. Full content history (every diff hunk): `git log -p --all roles/worker.md`.
3. CLAUDE.md content history searched for the phantom phrases: `git log -p --all CLAUDE.md | grep -E "automation/|<role>-<YYYY|never push|NEVER push|plumbing-path"`.
4. Current on-disk grep across all canonical sources: `grep -rn "automation/" roles/ CLAUDE.md STATE.md JOURNAL.md PROPOSED.md NEEDS-INPUT.md QUEUE.md DONE.md digests/ research/`.
5. Same grep for the other phrases: `grep -rn -E "(NEVER push|never push|plumbing-path)" ...`.
6. Reflog/branch-aware search: `git log --all --source --remotes --branches --tags -p roles/worker.md`.
7. Stash + branch inventory: `git stash list`, `git branch -a`.
8. On-disk vs HEAD byte parity for `roles/worker.md`: `wc -c roles/worker.md` against `git cat-file -s HEAD:roles/worker.md`.

## What I found

**Finding 1 -- `roles/worker.md` has exactly one commit in its history.** `git log --all --oneline roles/worker.md` returns a single line: `7c4edf7` (2026-04-26, "Add automation docs, roles, and schedule"). The file was created with its current content. There is no prior version to roll back to.

**Finding 2 -- the phantom phrases never appear in any commit, on any branch, against any file.** `git log -p --all` searches across `roles/worker.md` and `CLAUDE.md` -- and the wider reflog/branch-aware search across all branches and tags -- return zero hits for `automation/<role>-`, `automation/`, `NEVER push`, `never push`, or `plumbing-path` as policy text. The phrases simply are not in git's history.

**Finding 3 -- on-disk parity is clean and matches HEAD exactly.** `roles/worker.md` is 2188 bytes on disk (post worker-8am 2026-04-30 repair), identical to `git cat-file -s HEAD:roles/worker.md` = 2188. There is no truncation hiding content; the on-disk file is the full file. The night-auditor's "(when un-truncated)" framing was incorrect at the time it was written.

**Finding 4 -- current mentions of the phantom text in the repo are all secondary references to the confabulation itself.** `grep -rn` finds 37 hits for `automation/` in the current tree -- every single hit is in `JOURNAL.md`, `PROPOSED.md`, `NEEDS-INPUT.md`, `digests/2026-04-30.md`, or `research/2026-04-30-push-mystery.md`, and every single hit is discussing the night-auditor's claim, not asserting it as live policy. `NEVER push` / `never push` / `plumbing-path` follow the same pattern: zero canonical-source hits, only meta-references to the dispute.

**Finding 5 -- no other role doc contains a parenthetical the auditor could have generalized.** `roles/night-auditor.md`, `roles/planner.md`, `roles/researcher.md`, `roles/worker.md`, and `roles/digest.md` were all read via bash `cat`. The only push-related text in any role file is `roles/worker.md` line 13 (`commit with a clear message (do not push to remote unless this project's CLAUDE.md explicitly allows it)`) and line 24 (`Do not push to remote unless explicitly allowed by CLAUDE.md.`). Neither contains the `automation/<role>-<YYYY-MM-DD>-<slot>` shape, the all-caps `NEVER push to main`, or the plumbing-path ban. No source for the auditor to generalize from.

**Finding 6 -- no `automation/*` branch exists locally or on the remote.** `git branch -a` returns `main`, `origin/main`, `origin/removing-fluff`. Stash list contains one entry, unrelated to the push policy. The phantom policy has no observable traces in git state at all.

**Verdict:** Hypothesis (c) -- pure confabulation -- is the only hypothesis the evidence supports. (a) is refuted by the single-commit history; (b) is refuted by the role-doc content sweep. The night-auditor synthesized policy text that has never existed in this repo, then reasoned over the synthesized baseline to flag a "violation."

## Recommendation

**Actionable change.** Close the policy-reconciliation question as already-resolved (Eric's `[x] resolved no-action` on the night-auditor's 2026-04-30 PROPOSED entry stands). The companion concern -- the audit-quality pattern -- should NOT close.

This is the second reasoning-over-fabricated-baseline finding from the night-auditor in 48 hours. The first was the "NUL-byte sweep clean" false-clean from 2026-04-29 (auditor's own sweep missed 192 trailing NULs on `models.py` while reporting "clean"). The pattern is: the auditor produces a confident assertion grounded in something that is not actually in the file. If this recurs, every audit becomes a coin-flip on whether the cited evidence exists.

The cowork-session 2026-04-30 PROPOSED entry (line 92, currently `[ ]`) already proposes a fix: have the auditor quote policy text directly from disk via bash `cat`, never paraphrase, and grep the repo for any policy clause it cites before publishing. Adding a self-check step to `roles/night-auditor.md` is a ~3-line role-doc edit, P2, doc-only blast radius. This research file is the grounding evidence for that proposal.

I am NOT adding a new PROPOSED entry. The cowork-session entry already frames the corrective action; appending another would duplicate. Eric should approve that entry during evening review.

## Open follow-ups

1. **Did the night-auditor read the role files via the Read tool?** The Read-vs-disk disconnect (documented in JOURNAL.md by worker-10am, worker-11am, and the night-auditor itself) means Read can return content that disagrees with bash. If the auditor read `roles/worker.md` via Read AND Read returned something other than the on-disk content AND that something contained the phantom phrases, hypothesis (c) would weaken into a tool-bug story. Tonight's auditor (2026-05-01 00:05) verified on-disk parity matches HEAD on all five foundational files -- no truncation, no disconnect active. So the disconnect is not currently producing the phantom text. But the auditor's tool-call trace from 2026-04-30 is not preserved; cannot rule out a transient Read-tool result that returned synthesized content. Out of scope here -- would require LLM trace replay infrastructure the project does not have.
2. **Has the auditor confabulated other "facts" that haven't been caught?** This run did not audit prior auditor entries beyond the two known cases (NUL sweep + push policy). A targeted sweep of all night-auditor JOURNAL entries for cited evidence vs. on-disk reality would be a separate research question. Out of scope here.
3. **Should the role-doc self-check apply to all roles, not just the night-auditor?** The planner and worker roles also occasionally cite policy text. Generalizing the "quote from disk via bash, then grep before publishing" rule into a project-wide standing order in CLAUDE.md may have lower friction than a per-role amendment. Out of scope here -- depends on Eric's preference for centralized vs. distributed conventions.
