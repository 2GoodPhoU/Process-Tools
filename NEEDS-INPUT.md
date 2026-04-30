# Needs Input — Process-Tools

> Questions and blockers that need human answers before automation can proceed. Cleared during the evening review window.

## How to respond

- Add your answer inline under the question.
- Mark `[answered]` once resolved. The next Planner run will clear answered items and act on them.
- If a question turned into actual work, the Planner will move it to QUEUE.md.

## Format

```
- [ ] [from: role / YYYY-MM-DD HH:MM] Question
  - Context: ...
  - What I tried: ...
  - What I need from you: a decision / clarification / approval / new information
```

---

- [ ] [from: worker-9am / 2026-04-29 09:00] BPMN/Camunda validation: GUI step needs a human or computer-use Worker.
  - Context: QUEUE.md P1 ("Validate the new BPMN 2.0 emitter output against Camunda Modeler's import") expects a Worker to (a) open `samples/bpmn_validation/simple_two_actors.bpmn` in Camunda Modeler 5.x desktop, (b) walk the rendered canvas against the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, (c) drop the same file in demo.bpmn.io, (d) save in Camunda and structural-diff the saved file. Steps (a), (c), (d) are GUI-bound. Today's 9am scheduled Worker is unattended — no human at the keyboard, no `request_access` for Camunda Modeler or Chrome.
  - What I tried: completed everything I could without the GUI. (1) Re-ran `bash scripts/test_all.sh` — ALL GREEN, 702 tests across 4 tools, including all 40 nimbus-skeleton emitter tests (the section-5 list, ~80% of the failure surface per the research file). (2) Wrote a stdlib-only programmatic validator (`/tmp/bpmn_run/validate_bpmn_structural.py`, ~180 LOC) that walks the section-2 table against the file and asserts every check that's verifiable from the XML alone — 24 checks total, **all 24 pass**. The "what would actually block import" rows from section 1 of the research file (`flowNodeRef` resolution, `incoming`/`outgoing` mirrors, `targetNamespace` set, full BPMNDI block) all pass. The 2026-04-26 DI fix is doing its job. (3) Wrote `research/2026-04-29-bpmn-structural-validation.md` with the full pass/fail table and explicit list of what's NOT covered.
  - What I need from you: pick one to unblock the GUI gate.
    - **Option A (manual):** open `samples/bpmn_validation/simple_two_actors.bpmn` in Camunda Modeler 5.x desktop yourself, walk section 2 of the checklist, drop in demo.bpmn.io, save+diff. ~15 minutes. The expected outcome per the research is "opens cleanly, platform-tag lint warnings only." If everything passes, append the DECISIONS.md entry per section-6 step 5 and mark the queue item done.
    - **Option B (computer-use Worker):** explicitly authorize a future scheduled Worker to use computer-use and/or the Chrome MCP for this task. With that approval, a Worker run could open Camunda Modeler via `open_application` and capture a screenshot, and could drag-drop the file into demo.bpmn.io via the Chrome extension. Adds blast radius (a Worker is normally code-only and read-only against the orphan-dirs); needs an explicit one-line waiver in CLAUDE.md or roles/worker.md.
    - **Option C (defer):** leave `[in-progress]` and let the Planner re-queue once the GUI gate is sorted. The structural validator + unittest pins are sufficient confidence to proceed with downstream work that depends on the BPMN emitter, but they are not the same as "Camunda Modeler accepts the file."
  - Bailout rule cited: `roles/worker.md` "The task is larger than you thought and would clearly take more than one Worker run." The work that fits in one unattended run is done; the GUI work is not workable in this role.

- [ ] [from: night-auditor / 2026-04-30 00:05] GitHub MCP unavailable for nightly audit; PR/CI drift section skipped.
  - Context: `roles/night-auditor.md` (HEAD version, the on-disk file is truncated — see tonight's P0) requires this run to call `mcp__plugin_engineering_github__*` tools to (a) list open PRs and flag any older than 7 days, (b) fetch CI/check status on each open PR, (c) cross-reference Worker journal-entry push claims against remote branches.
  - What I tried: searched the deferred-tools list for any `+github` or `plugin engineering` tools — none surfaced. The available `mcp__plugin_*` tools all belong to the productivity / product-management plugins (Slack, Notion, Linear, Atlassian, Amplitude, Figma, Fireflies, Intercom, Pendo, ms365), none of them GitHub. Confirmed via `git remote -v` that the remote IS GitHub (`https://github.com/2GoodPhoU/Process-Tools.git`), so the issue is the MCP isn't installed/authenticated, not that the project lacks a remote.
  - What I need from you: install + authenticate a GitHub MCP for this project, OR explicitly waive the PR/CI/push-verification section of the night-auditor role for this project. Without the MCP, the auditor cannot enforce the new push policy in `roles/worker.md` (when un-truncated). Today's audit had to rely on the local reflog (`git reflog show origin/main`) to confirm pushes happened — that works for "did they push?" but not for "is there an open PR?" or "did CI pass?".
  - Local-only fallback findings (do not require the MCP): all of today's worker commits ARE on `origin/main` per the reflog (`update by push` entry to `382ee397`). No `automation/*` branches exist on the remote. This contradicts both worker journal claims ("not pushed") and the (truncated-on-disk but visible-via-Read) `roles/worker.md` policy. See tonight's PROPOSED entry for the policy reconciliation question.

- [ ] [from: worker-11am / 2026-04-30 11:00] QUEUE is empty of eligible items; only the blocked BPMN P1 [in-progress] remains.
  - Context: After worker-10am closed the P2 PyInstaller spec audit, QUEUE.md has exactly one item left: the BPMN/Camunda P1 marked [in-progress] and blocked on the BPMN GUI-gate question above (still unanswered since 2026-04-29 09:00). Per `roles/worker.md`, a Worker skips an `[in-progress]` item that's awaiting human input -- with no other items, this run has nothing to pick up. Worker-10am explicitly forecast this state and recommended the 11am Worker hit the "no eligible items" path.
  - What I tried: re-read QUEUE.md (1 item, blocked), JOURNAL.md last 6h (covers night-auditor 00:05, researcher 04:00, planner 07:10, worker-8am 08:00, worker-9am 09:00, worker-10am 10:00), NEEDS-INPUT.md (2 open items, neither answered), PROPOSED.md (11 open items, none `[x]`-approved by Eric). Confirmed disk-side state via bash `wc -lc` matches Read-tool output for QUEUE.md / NEEDS-INPUT.md / JOURNAL.md / PROPOSED.md / DONE.md (0 NUL bytes, clean trailing newlines). Did NOT run `bash scripts/test_all.sh` -- worker-9am ran it 2h ago (702/702, ALL GREEN); no source has been touched since.
  - What I need from you: either (a) answer the BPMN GUI-gate question (option A/B/C above) so the 12pm Worker can close the P1, OR (b) approve one or more of the 11 PROPOSED items so the planner can re-queue work for tomorrow morning's chain. Without one of those, the 12pm Worker will hit the same empty-queue state. The 11 PROPOSED items split roughly: 2 P1s (commit-or-stash the 0.6.1/0.6.2 patch line; refresh `.git/index` from HEAD), 9 P2s (everything else). The two P1s are the ones blocking-adjacent to current pain -- the auditor flagged them yesterday, and today's stale `MM`/`D ??` ghost-diffs are the cost of the index one not being approved.
  - Bailout rule cited: `roles/worker.md` step 2 -- "If the top item is already `[in-progress]` from a prior Worker, read its NEEDS-INPUT entry -- if the human hasn't answered yet, skip and pick the next item." With no next item, the role spec implies stop.
