# State -- Process-Tools

> Overwritten by the Planner each morning. One page max. Reflects the current state of the world as of the last Planner run.

## Last updated

2026-05-01 07:10 -- process-tools-planner (automated).

## Current focus

Unblock the BPMN/Camunda P1 GUI gate -- structural validation is done; the only remaining work is an attended Worker session (or Eric running it manually) since unattended scheduled Workers cannot service `request_access` interactive dialogs. Backlog otherwise idle: 12 open PROPOSED items, none `[x]`-approved, two of them P1 (commit-or-stash the 0.6.1/0.6.2 patch line; refresh `.git/index` from HEAD).

## Open threads

- **Nimbus -> BPMN 2.0 migration gate** (P1 `[in-progress]`): structural validator 24/24 PASS; nimbus-skeleton tests 40/40 PASS. Eric authorized Option B (computer-use Worker) on 2026-04-30 + waiver in CLAUDE.md. **Operational gap discovered post-answer (worker-12pm 2026-04-30):** scheduled Workers cannot click through `request_access`. Item now waiting on Eric's B1/B2/B3 pick (attended Worker session / Eric runs it himself / defer with structural validator as the gate). Re-queued with explicit `requires attended Worker only` constraint so unattended chains skip cleanly.
- **Two long-pending P1 PROPOSED items shaping every morning's friction**: (1) auditor 2026-04-29 commit-or-stash for the 0.6.1/0.6.2 patch line (uncommitted ~840 LOC tracked diff + 1933 LOC untracked); (2) auditor 2026-04-30 `git read-tree HEAD` to refresh stale `.git/index`. Both are zero-risk, blast-radius-tiny, and would clear the chronic plumbing-path commit workaround. Awaiting Eric's `[x]`.
- **CLAUDE.md waiver edit uncommitted on disk for 36+ hours** (auditor 2026-05-01 PROPOSED P2): risk is the `git show HEAD:CLAUDE.md > CLAUDE.md` truncation-recovery procedure silently strips the waiver if a future repair fires. Single-file bookkeeping commit when Eric is ready.
- **GitHub MCP unavailable** (NEEDS-INPUT, night-auditor 2026-04-30): blocks the auditor's PR/CI/push-verification section but NOT today's workers. Local `git reflog show origin/main` covers the "did they push?" check; cannot answer "is there an open PR?" or "did CI pass?".
- **Audit-quality concern (2nd occurrence in 48h)**: night-auditor confabulated push-policy text on 2026-04-30 -- cowork-session PROPOSED entry already proposes the fix (3-line role-doc edit; quote from disk via bash, grep before publishing). Tonight's auditor (2026-05-01 00:05) self-corrected with an explicit anti-confabulation grounding line. Researcher 2026-05-01 04:00 produced full source-trace evidence (`research/2026-05-01-night-auditor-confabulation.md`).

## Recent decisions

- 2026-05-01 (researcher): night-auditor's 2026-04-30 push-policy reconciliation finding is grounded in invented policy text -- pure confabulation per all 8 verification tests. The cowork-session PROPOSED entry is the corrective; this research file is its evidence.
- 2026-05-01 (night-auditor): cleanest audit night this week -- 0 broken, 0 new improvables, 1 risky (uncommitted CLAUDE.md waiver). 702/702 tests still green; foundational-files truncation repair from worker-8am 2026-04-30 holding.
- 2026-04-30 (researcher): origin/main 2026-04-29 drift explained -- single manual evening push by Eric, not silent worker pushes (`research/2026-04-30-push-mystery.md`).
- 2026-04-30 (Eric): BPMN/Camunda waiver added to CLAUDE.md authorizing Option B for the BPMN P1 only; cowork-session push-policy PROPOSED resolved no-action (policy text was confabulated).

## Known constraints

- Air-gapped target -- no network calls in shipped binaries.
- READ-ONLY against `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/` until tracked-vs-ignored decision lands. Tracked counts (19/20/8) unchanged since 2026-04-29.
- Edit/Write tool truncation cap is active for state files >~3 KB on overwrite. Established workaround: python binary-mode read+write via bash. Today's planner run uses this pattern.
- `request_access` interactive approval dialogs cannot be serviced by unattended scheduled Workers -- BPMN P1 is the load-bearing example. Schedule any GUI-gated queue item explicitly for an attended Worker session, or expect skip.
- Stuck `.git/index.lock` (~31h) + chronic stale `.git/index` -- every Worker run uses the `GIT_INDEX_FILE=/tmp/...` plumbing-path commit workaround. Two PROPOSED P1 items would resolve; neither approved.
- Workers commit locally and don't push. Eric pushes manually during evening review (per push-mystery research).
- Test counts: 702 green -- 606 requirements-extractor / 40 nimbus-skeleton / 26 process-tools-common / 30 compliance-matrix.
