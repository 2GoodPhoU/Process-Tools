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
