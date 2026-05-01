# Queue -- Process-Tools

> Prioritized work waiting to be picked up by Workers. The Planner curates this each morning. Workers pick the top unchecked item.

## Format

Each item:

```
- [ ] [P0|P1|P2] Title -- one-sentence description.
  - Definition of done: ...
  - Notes: ...
```

Use `[in-progress]` instead of `[ ]` if a Worker started but couldn't finish (with a note in NEEDS-INPUT.md about what blocked them).

---

- [in-progress] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import. **REQUIRES ATTENDED WORKER ONLY -- scheduled Workers must skip.**
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler 5.x desktop, walk the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, drag-drop into demo.bpmn.io, save in Camunda and structural-diff the saved file. Record findings (and any waiver removal) in `nimbus-skeleton/DECISIONS.md`.
  - Constraint: READ-ONLY against `nimbus-skeleton/` source. Emit BPMN artifacts to your run's scratch dir; record findings in `nimbus-skeleton/DECISIONS.md` (file may be created -- doc, not source). If the emitter run requires a code change to produce a clean import, stop and write to NEEDS-INPUT.md.
  - Computer-use waiver: CLAUDE.md "Task-specific waivers" authorizes Camunda Modeler 5.x desktop + Chrome MCP for demo.bpmn.io, scoped to this queue item only. Orphan-dirs read-only constraint still applies. Waiver self-sunsets when this item closes.
  - Operational gap (worker-12pm 2026-04-30): unattended scheduled Workers cannot service `request_access` interactive approval dialogs. The 8am-12pm scheduled chain MUST skip this item. Eric's NEEDS-INPUT entry from 2026-04-30 12:00 captures three options to actually close: B1 attended Worker session (Eric kicks off ad-hoc), B2 Eric runs Option A himself (~15 min), B3 defer + drop [in-progress] (lowest cost; weakest gate).
  - Prior progress (worker-9am 2026-04-29): programmatic structural validation 24/24 PASS (`/tmp/bpmn_run/validate_bpmn_structural.py`); section-5 unittest pins 40/40 PASS in nimbus-skeleton; full pass/fail table in `research/2026-04-29-bpmn-structural-validation.md`. The remaining work is GUI-only.
