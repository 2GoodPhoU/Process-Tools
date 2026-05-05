# State -- Process-Tools

> Overwritten by the Planner each morning. One page max. Reflects the current state of the world as of the last Planner run.

## Last updated

2026-05-05 ~07:10 -- process-tools-planner (automated). Today is Tuesday 2026-05-05. Eva validation week ENDED 2026-05-03; the "no new scheduled tasks during Eva validation week" CLAUDE.md "Don't" line is now stale (doc-only nit -- folds into 3.3/3.4 next-pull-ready commit). Inputs read this run: JOURNAL.md (last 24h), NEEDS-INPUT.md (1 [answered] cleared, 3 open remain), PROPOSED.md (18 open), QUEUE.md (25 items unchanged), DONE.md (last 7 days), `research/2026-05-05-role-files-truncation-check.md` (researcher 04:00 most-recent file).

## Current focus

Throughput remains bottlenecked on Eric-side approvals -- 18 PROPOSED open, 0 `[x]`-approved, 5 consecutive zero-commit calendar days, 22+ consecutive empty-queue Worker shifts. Five next-pull-ready QUEUE items (3.1 build.log gitignore, 3.3 CLAUDE.md test counts, 3.4 CLAUDE.md harness wording, 4.5 RELEASE-NOTES-1.0.md scaffold, 5.4 DECISIONS.md CUSTOMER_HANDOFF stub) carry NO open Eric gate and are pickable by today's morning chain -- this is the load-bearing path that ends the empty-queue chain. Today's load-bearing evening-review items: BPMN B1/B2/B3 pick (~115h since worker-12pm 2026-04-30 12:00 NEEDS-INPUT) + the two zero-risk P1 PROPOSED (commit-or-stash 0.6.1/0.6.2 + `git read-tree HEAD`) + orphan-dir A/B/C pick + (NEW) commit-with-intent on `roles/{night-auditor,planner,worker}.md` + CLAUDE.md per researcher 2026-05-05 recommendation.

## Open threads

- **Nimbus -> BPMN 2.0 migration gate** (P1 [in-progress] / 2.5): structural validator 24/24 PASS; nimbus-skeleton 40/40 PASS. Eric authorized Option B 2026-04-30 + waiver in CLAUDE.md (~115h uncommitted on disk). Operational gap: scheduled Workers cannot service `request_access`. Item still pending Eric's B1/B2/B3 pick. QUEUE entry carries explicit `REQUIRES ATTENDED WORKER ONLY` so today's chain skips cleanly. Closure unblocks decomposed items 2.3 + 4.2 + the CLAUDE.md waiver removal.

- **Two zero-risk P1 PROPOSED items still gating bookkeeping hygiene**: (1) auditor 2026-04-29 commit-or-stash for the 0.6.1/0.6.2 patch line (~8 days uncommitted; crossed the week mark 2026-05-04); (2) auditor 2026-04-30 `git read-tree HEAD` to refresh `.git/index` (now ~140h stale per `stat -c '%y' .git/index` = 2026-04-29 17:06 UTC). Both zero-risk; either alone restores morning-chain throughput; both eliminate the daily ghost-diff hazard. Awaiting Eric's `[x]`. Closure unblocks decomposed items 3.2 + 3.8 + Phase 4.

- **Orphan-dir tracked-vs-ignored decision (3.7)**: inputs in `DECISIONS-orphan-dirs.md` (worker-10am 2026-04-29; three options A status-quo / B formalize / C untrack). Not yet picked. Decomposed items 2.1 + 2.2 + 2.3 + 2.4 + 4.2 + 4.3 + 4.4 + 4.6 are gated on this -- they touch `nimbus-skeleton/` or `compliance-matrix/` or `process-tools-common/` and CLAUDE.md off-limits rule still applies. Highest-leverage Phase 4 unblock alongside the BPMN gate.

- **Role-file commit-with-intent (NEW load-bearing item)**: researcher 2026-05-05 04:00 (`research/2026-05-05-role-files-truncation-check.md`) verified via `tail -c 200 | xxd` that all three on-disk role files end on a complete sentence + single trailing newline, internally coherent, policy-aligned with CLAUDE.md push-policy + the open NEEDS-INPUT GitHub-MCP entry. Recommendation: option (b) commit-with-intent -- bundle `roles/{night-auditor,planner,worker}.md` + CLAUDE.md as one commit titled e.g. `chore(roles+claude): land 2026-05-04 batch edits + skill-hook integration`. Auditor 2026-05-05 00:05 PROPOSED (empirical refresh) is the structurally correct successor to the auditor 2026-05-03 PROPOSED (which carries two empirically-false claims: "truncates step 6 mid-bullet" -- contradicted by xxd evidence; diff-line counts "13 / 42" -- superseded by current 17 / 5 / 46). Per planner role spec, no auto-prune; Eric prunes during evening review.

- **Audit-quality concern -- now extends to "any role making quantitative claims"**: 5th audit-quality finding in the running window (auditor 2026-05-05 00:05 enumeration-discipline + Read-tool drift on PROPOSED.md). Cowork-session 2026-04-30 corrective remains the canonical channel; researcher 2026-05-03 + 2026-05-04 + 2026-05-05 broadened scope from "auditor" to "any role making quantitative claims." Decision Eric's; planner flags only.

- **GitHub MCP unavailable** (NEEDS-INPUT 2026-04-30): the new `roles/night-auditor.md` "GitHub-MCP audit (NON-BLOCKING)" section explicitly waives the PR/CI/push-verification requirement when the MCP is absent (per researcher 2026-05-05 finding #2). Local `git reflog` covers "did they push?". No urgency; the role-doc waiver lands once Eric commits the role-file batch.

## Recent decisions

- 2026-05-05 (researcher 04:00): `research/2026-05-05-role-files-truncation-check.md` -- on-disk role files are clean intentional edits, not truncated. Recommendation: option (b) commit-with-intent on `roles/{night-auditor,planner,worker}.md` + CLAUDE.md. No new PROPOSED filed (auditor 2026-05-05 00:05 entry already covers the same scope).
- 2026-05-05 (auditor 00:05): cleanest audit night this week (3rd consecutive). 702/702 still green; 5th consecutive zero-commit calendar day; 100/100 .py files py_compile clean; 0 NUL bytes. Three new P2 PROPOSED filed: role-file-drift empirical refresh + CRLF normalization on `samples/bpmn_validation/*` + housekeeping (ROADMAP.md.new + schedule.json bundle). HEAD now == origin/main (Eric pushed `f6fbb7e` between 2026-05-04 18:00 UTC and 00:05; within new push policy). Read-tool drift confirmed empirically on PROPOSED.md: Read view masked a (now-cleared) mid-sentence truncation in the cowork-session 2026-05-04 TO-PUSH.md entry.
- 2026-05-05 (planner 07:10, this run): cleared one [answered] NEEDS-INPUT entry (cowork-session 2026-05-04 v1.0 release shape -- already actioned in CLAUDE.md + ROADMAP.md `[roadmap] bundle-v1-locked`). Did NOT promote any PROPOSED items (0 `[x]` checks). Did NOT modify QUEUE.md (already curated yesterday by cowork-session backlog-decomposition; 5 next-pull-ready items remain at top). Updated this STATE.md to correct the "1 commit ahead" stale claim per auditor 2026-05-05 00:05 evidence (now 0 ahead / 0 behind).

## Known constraints

- Air-gapped target -- no network calls in shipped binaries.
- READ-ONLY against `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/` until tracked-vs-ignored decision (3.7) lands. Tracked counts (19/20/8) unchanged.
- Edit/Write tool truncation cap is active for state files >~3 KB on overwrite. Established workaround: python binary-mode read+write via bash. Today's planner run uses this pattern.
- Read-vs-disk view skew is empirically load-bearing for any state file >~30 KB (auditor 2026-05-05 00:05 confirmed on PROPOSED.md; Read showed 156 lines / clean close, bash/Python initially saw mid-word truncation pre-write). Use bash/Python for any "what's actually on disk" check; Read tool may surface a different version.
- Byte-count parity vs HEAD blob is necessary but NOT sufficient for content parity. Current role-file disk vs HEAD: `roles/night-auditor.md` 3441b vs 1830b (+1611, diff 17 lines); `roles/planner.md` 2682b vs 2102b (+580, diff 5 lines); `roles/worker.md` 5588b vs 2188b (+3400, diff 46 lines); `CLAUDE.md` 6127b vs 4660b (+1467, diff 11 lines). All four are clean intentional edits per researcher 2026-05-05; awaiting commit-with-intent.
- `request_access` interactive approval dialogs cannot be serviced by unattended scheduled Workers -- BPMN P1 is the load-bearing example. Schedule any GUI-gated queue item explicitly for an attended Worker session, or expect skip.
- Stuck `.git/index.lock` (~140h, owner-locked from Windows side; mtime 2026-04-29 17:10 UTC) + chronic stale `.git/index` (mtime 2026-04-29 17:06 UTC, ~140h). Every Worker run uses the `GIT_INDEX_FILE=/tmp/...` plumbing-path commit workaround. Two PROPOSED P1 items would resolve; neither approved.
- Push policy (CLAUDE.md updated 2026-05-04): a local commit alone satisfies DoD and marks queue items DONE. Workers may attempt push to a working branch via GitHub MCP; failure is informational ("remote push deferred -- Eric pushes nightly"). Local HEAD `f6fbb7e` now matches `origin/main` (0 ahead / 0 behind, verified `git rev-list --count` this run); supersedes prior STATE.md "1 commit ahead" claim.
- Eva validation week ENDED 2026-05-03. CLAUDE.md "Don't" line on this is now stale; folds into 3.3/3.4 next-pull-ready commit when picked up.
- Test counts: 702 green -- 606 requirements-extractor / 40 nimbus-skeleton / 26 process-tools-common / 30 compliance-matrix.
