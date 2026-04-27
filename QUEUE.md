# Queue — Process-Tools

> Prioritized work waiting to be picked up by Workers. The Planner curates this each morning. Workers pick the top unchecked item.

## Format

Each item:

```
- [ ] [P0|P1|P2] Title — one-sentence description.
  - Definition of done: ...
  - Notes: ...
```

Use `[in-progress]` instead of `[ ]` if a Worker started but couldn't finish (with a note in NEEDS-INPUT.md about what blocked them).

---

- [ ] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import.
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler (free desktop), confirm structural integrity (lanes, tasks, gateways, sequence flows, text annotations) round-trips cleanly. Document any failures as DECISIONS doc entries.
  - Notes: This closes the Nimbus → BPMN 2.0 migration-path validation gate.
