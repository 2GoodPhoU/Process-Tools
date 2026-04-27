# Decisions

Append-only record of non-trivial design decisions. Entries are dated,
named, and stand on their own — anyone reading the entry should
understand the constraint, the option chosen, the alternatives
rejected, and why. Decisions can be revisited; if so, append a new
entry referencing the prior one rather than editing in place.

Voice: operator. State the call, the reason, what would change the
call. No hedging, no apology, no cheerleading.

---

## 2026-04-26 — BPMN DI generation

**Decision.** The BPMN 2.0 emitter
(`nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py`) emits a full
`<bpmndi:BPMNDiagram>` section: every shape carries a
`<bpmndi:BPMNShape>` with `<dc:Bounds>` (integer pixels), and every
sequence flow / association carries a `<bpmndi:BPMNEdge>` with at
least two `<di:waypoint>` entries. Layout is a deterministic
horizontal-swimlane grid: lanes top-to-bottom in actor-insertion
order, nodes left-to-right by longest-path rank from the start event,
events at the vertical centre of the pool, notes in a strip below the
pool, cross-lane edges routed as 4-waypoint elbows.

**Reverses.** The original 2026-04-24 emitter shipped without DI on
the assumption that "modern BPMN tools (Camunda Modeler, bpmn.io)
auto-layout on import, and shipping a hand-rolled DI section means
picking pixel coordinates that no tool would agree with anyway."
That assumption is wrong. REFACTOR.md item S3 — the modeler
validation step that exists specifically to test untested assumptions
of this shape — surfaced the failure on 2026-04-26: bpmn.io errors
out with "no diagram to display" and recent Camunda Modeler versions
behave the same way. The 80/20 framing in the original S3 entry
("structural tests cover ~80% of failure modes; the remaining 20% is
'the modeler refuses to import for a subtle reason'") turned out to
be the right framing — this is the 20%.

**Why this layout, not a smarter one.**

- *Deterministic.* Coordinates are integer functions of the in-memory
  `Skeleton` shape and a small set of named constants. The
  byte-stability test (`test_two_renders_equal`) keeps passing
  unchanged. Same skeleton → same bytes → `git diff` surfaces real
  emitter regressions, not floating-point reformatting noise.

- *Defensible without being clever.* No graph-layout library, no
  collision-resolution heuristics, no auto-orthogonal routing past
  the elbow rule. Lanes get equal heights; columns get equal widths.
  Anyone modifying the layout can do so by editing constants near
  the top of `bpmn.py` and re-running the suite. A graph-layout
  library would be a substantial dependency the air-gapped target
  can't justify and would introduce non-determinism we'd then need
  to test around.

- *Throwaway.* Every BPMN modeler users open this in re-tidies on
  first save anyway. Our job is to ship coordinates the modeler can
  *open*; perfectionist layout is the modeler's job, not ours.

**What would change the call.**

- A BPMN modeler that ships in production with reliable, deterministic
  auto-layout for DI-less files. Camunda Modeler may add this in a
  future major version; if so, we could revert to DI-less output and
  cut the layout code. Verify against the actual modeler version
  customers run before doing this.

- Skeleton learning a richer-than-XOR gateway model (parallel,
  inclusive, event-based). The current layout treats all gateways
  the same; a richer gateway model may need richer routing to read
  cleanly.

- Skeletons routinely exceeding ~50 nodes. The current grid layout
  doesn't fold or wrap; very wide diagrams will scroll horizontally.
  At that scale we'd revisit whether to introduce a layout library
  with a justified offline-bundling story.

**Files.**

- `nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py` — `_compute_ranks`,
  `_compute_layout`, layout constants, DI emission block in `render()`.
- `nimbus-skeleton/tests/test_bpmn_emitter.py` — new
  `TestBpmnEmitterDiagramInterchange` class (7 tests).
- `samples/bpmn_validation/simple_two_actors.bpmn` — regenerated.
- `nimbus-skeleton/CHANGELOG.md` — Unreleased entry updated.
- `REFACTOR.md` — S3 marked DONE.
