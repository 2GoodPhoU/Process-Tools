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

- [in-progress] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import.
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler (free desktop), confirm structural integrity (lanes, tasks, gateways, sequence flows, text annotations) round-trips cleanly. Document any failures as DECISIONS doc entries.
  - Constraint: READ-ONLY against `nimbus-skeleton/`. Orphan-dirs tracked-vs-ignored decision is unresolved (see CLAUDE.md off-limits). Do NOT edit source under `nimbus-skeleton/`, `compliance-matrix/`, or `process-tools-common/`. Emit BPMN artifacts to your run's scratch dir; record findings in `nimbus-skeleton/DECISIONS.md` (file may be created -- that's a doc, not source). If the emitter run requires a code change to produce a clean import, stop and write to NEEDS-INPUT.md.
  - Notes: Closes the Nimbus -> BPMN 2.0 migration-path validation gate. **Read `research/2026-04-29-camunda-import-checklist.md` first** -- it has the per-element pass-criterion table (section 2), the round-trip-as-structural-identity rule (section 3), the list of Camunda 5.x lint warnings that are NOT failures (section 4: platform-tag noise, executionPlatform missing, Zeebe runtime hints), and a 6-step Worker procedure (section 6). Use those, don't redo the research.
  - **Worker-9am 2026-04-29:** programmatic structural validation done (24/24 PASS) and section-5 unittest pins re-run green (40/40 in nimbus-skeleton). The remaining ~20% is the GUI gate (Camunda Modeler desktop + demo.bpmn.io drag-drop + save round-trip), which an unattended Worker cannot exercise. See `research/2026-04-29-bpmn-structural-validation.md` for the partial-validation report, and the NEEDS-INPUT entry for the three paths Eric can pick from to unblock the GUI step. **Workers: skip this item until Eric answers the NEEDS-INPUT.**
