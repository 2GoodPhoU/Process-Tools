# Camunda Modeler import checklist for the nimbus-skeleton BPMN 2.0 emitter

> Researcher run, 2026-04-29. Grounding for QUEUE.md P1 "Validate the new
> BPMN 2.0 emitter output against Camunda Modeler's import." Read-only.

## Question

What specific structural and conformance points should a Worker check
when running `samples/bpmn_validation/simple_two_actors.bpmn` through
Camunda Modeler (desktop, free) and demo.bpmn.io? The queue item's
definition of done lists "lanes, tasks, gateways, sequence flows, text
annotations" and "no invalid BPMN / incoming-outgoing missing errors,"
but doesn't enumerate the exact things that pass or fail an import in
the current Camunda Modeler 5.x line. Goal: turn that loose list into a
concrete pass/fail checklist the Worker can apply without re-deriving
it.

## What I checked

- `samples/bpmn_validation/simple_two_actors.bpmn` (the actual emitter
  output we're validating).
- `samples/bpmn_validation/README.md` (validation procedure as
  documented today).
- `nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py` (full emitter,
  including `render`, `_compute_layout`, `_safe_id`, layout constants).
  Read end-to-end; the docstring on lines 1-48 describes the design and
  references the 2026-04-26 DI decision.
- `nimbus-skeleton/tests/test_bpmn_emitter.py` (structural test
  coverage — what the suite already pins).
- `DECISIONS.md` — `2026-04-26 — BPMN DI generation` entry. Establishes
  that bpmn.io and recent Camunda Modeler refuse DI-less files; the
  emitter ships full BPMNDI with integer-pixel coordinates.
- `requirements-extractor/research/2026-04-25-stack-alternatives-survey.md`
  for prior context on the BPMN 2.0 migration path.
- Web search (April 2026):
  - Camunda Modeler download page (current desktop version).
  - `camunda/camunda-modeler` GitHub (issues #4277 missing-BPMN-shape
    warning, #1522 old-file compatibility).
  - bpmn.io blog post on bpmnlint, the BPMN-2-rule lint engine the
    Camunda Modeler 5.x built-in linter is built on.
  - Camunda Modeler 5.0.0 release notes (executionPlatform attribute,
    Camunda 7 vs Camunda 8 dual mode).
  - bpmn.io / Camunda forum threads on "no diagram to display" import
    failure mode and on `modeler:executionPlatform` namespace warnings.

I did NOT run Camunda Modeler or demo.bpmn.io against the file —
Researcher role is read-only, and a desktop GUI tool isn't an
in-process check. That's the Worker's step. The point of this file is
to make sure when the Worker runs it, they know what to look at.

## What I found

### 1. Current Camunda Modeler line is 5.x; vanilla BPMN 2.0 is supported but tagged with an "execution platform"

The current desktop Camunda Modeler is in the 5.x line (5.46 as of
mid-April 2026 per the download page). It opens vanilla BPMN 2.0 files
without errors, but tags the file with a default *execution platform*
("Camunda 7" or "Camunda 8 / Zeebe") via the status-bar selector. The
file we emit has no `xmlns:modeler` namespace and no
`modeler:executionPlatform` attribute on `<bpmn:definitions>`, so the
modeler picks a default and may surface non-fatal lint warnings about
elements that aren't valid for that platform.

Behaviour to expect on import:

- File opens. The diagram renders. This is a successful import.
- The status bar shows a platform badge. This is cosmetic for our
  purposes — we are not deploying.
- The "Problems" / lint panel may list warnings tagged "Camunda 7" or
  "Zeebe" (e.g. "task type not set", "missing service implementation").
  These are *runtime* concerns, not BPMN 2.0 conformance failures, and
  do not block opening or saving. Document them in DECISIONS but do
  not treat them as failures.

What *would* block import:
- Missing `targetNamespace` on `<bpmn:definitions>`. We set
  `http://nimbus-skeleton/bpmn`. Pass.
- Missing `BPMNDiagram` section ("no diagram to display" — bpmn.io
  refuses, recent Camunda Modeler refuses). The 2026-04-26 DI
  decision addresses this; we now emit a full DI block. Pass on
  inspection of the sample file.
- `flowNodeRef` pointing to an id that doesn't exist in the same
  process — schema-valid but a runtime "unresolved reference" warning
  surfaces. Inspection of the sample shows every `flowNodeRef`
  matches an actual `<bpmn:task>` id. Pass.
- `incoming`/`outgoing` mismatch with `sequenceFlow` source/target.
  Camunda Modeler is strict here; the emitter's own comment on
  line 117 calls this out. Inspection of the sample shows every
  `sequenceFlow` is mirrored by exactly one `incoming` on its target
  and one `outgoing` on its source. Pass.

### 2. Diagram Interchange (BPMNDI) requirements

bpmn.io and Camunda Modeler 5.x both refuse to render a BPMN file that
lacks a `<bpmndi:BPMNDiagram>`. They will *also* warn (issue #4277 in
camunda/camunda-modeler) when a flow node lacks a corresponding
`<bpmndi:BPMNShape>` — the file opens, but the missing element is
either invisible or auto-positioned at (0,0), depending on Modeler
version.

What the Worker should verify in the rendered canvas:

| Element                                                   | Pass criterion                                                                                                           |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Pool                                                      | One pool labelled "Process Skeleton" (the `Participant_1` name).                                                         |
| Lanes                                                     | Two lanes inside the pool: "Operator" (top) and "Supervisor" (bottom).                                                   |
| Tasks                                                     | Four tasks visible. Two land in Operator, two in Supervisor.                                                             |
| Start event                                               | Single thin-circle start event in the Operator lane (left edge of pool, vertically centered on the pool).                |
| End event                                                 | Single thick-circle end event (right edge of pool, vertically centered).                                                 |
| Sequence flows                                            | Six sequence flows total, all rendered as solid arrows. No "floating" flows (an arrow with one end unconnected).         |
| Cross-lane edges                                          | Edges that cross between Operator and Supervisor route as right-angle elbows (4 waypoints), not straight diagonals.      |
| Gateways                                                  | None in this sample (the seed corpus has no gateway). If a future sample exercises one, render as a diamond.             |
| Text annotations                                          | None in this sample. If a future sample exercises one, render as a folded-corner rectangle below the pool.               |
| `BPMNShape` for every flow node                           | Inspect the saved XML after re-save: no flow node lacks a `BPMNShape`. (Camunda will preserve all of ours.)              |
| `BPMNEdge` for every sequence flow with ≥2 waypoints      | Same. Inspection of the source file shows every flow has 2 or 4 waypoints. Pass.                                         |

### 3. Round-trip on save: structural identity, NOT byte identity

Camunda Modeler reformats XML on save: attribute ordering, indentation,
and whitespace differ from our emitter's output. The byte-stability
test (`test_two_renders_equal`) only pins emitter → emitter
determinism — it does NOT survive a Camunda round-trip, and shouldn't
be expected to.

What to compare after Camunda saves the file:

- All `id=` attributes preserved on `bpmn:task`, `bpmn:lane`,
  `bpmn:sequenceFlow`, `bpmn:startEvent`, `bpmn:endEvent`.
- Each task is still `<flowNodeRef>`'d under the same lane it started
  in (Camunda will not silently re-shuffle lanes).
- Source/target of every sequence flow unchanged.
- `BPMNDiagram` still present. Coordinates may have shifted (Camunda
  will sometimes re-snap to its grid); that's expected.
- The `exporter` attribute may or may not be rewritten to "Camunda
  Modeler X.Y.Z". Both are valid; the emitter sets ours to
  `nimbus-skeleton`/`1.0` initially.

If Camunda's saved file *adds* a `<bpmn:definitions xmlns:modeler="...
"  modeler:executionPlatform="Camunda Platform" ...>` declaration,
that's expected — Camunda Modeler 5.x stamps the platform on first
save. It does not invalidate the file for re-import elsewhere.

### 4. Known Camunda Modeler import quirks that are NOT failures for us

- **"Missing BPMN shape" warning (issue #4277).** Surfaces only when
  a flow node has no `BPMNShape`. Our emitter generates a shape for
  every task / gateway / event / annotation in `_compute_layout`.
  Should not fire.
- **Old-file refusal (issue #1522).** Affects files that predate the
  Camunda Modeler 3.x format migration (~2019). Our output is freshly
  emitted; not in scope.
- **FEEL-namespace misdetection (issue #944).** Triggers if the file
  contains the FEEL DMN namespace and Camunda Modeler tries to open it
  as a DMN file. Our file declares only BPMN/BPMNDI/DC/DI/XSI; not in
  scope.
- **Lint warnings on missing service implementations / unset task
  types.** Built-in linter from Modeler 5.0+. These are platform-tag
  warnings (Camunda 7 / Zeebe runtime concerns), not BPMN-2 conformance
  errors. Document if surfaced; do not treat as failures.

### 5. Structural points already covered by the unittest suite

The Worker does not need to manually re-verify these — they're pinned
by `nimbus-skeleton/tests/test_bpmn_emitter.py` and run on every
emitter change:

- Root element is `<bpmn:definitions>`.
- One `bpmn:laneSet` with one lane per actor.
- `flowNodeRef` ids match emitted task ids.
- Every `bpmn:sequenceFlow` has both `sourceRef` and `targetRef`.
- Byte-stability across two runs of the same input.
- `bpmn:exclusiveGateway` is emitted for `Skeleton.gateways` rows.
- `bpmn:documentation` block fires for flagged activities.
- `bpmn:textAnnotation` + `bpmn:association` fire for `Note` rows.
- DI section: shape per flow node, edge per sequence flow, ≥2
  waypoints per edge.

That accounts for ~80% of the failure surface (per the original S3
framing in DECISIONS.md). The Camunda Modeler / bpmn.io step is
catching the remaining 20% — the "modeler refuses for a subtle reason"
class — which is what this checklist is designed for.

### 6. Recommended Worker procedure (concrete sequence)

1. Open `samples/bpmn_validation/simple_two_actors.bpmn` in Camunda
   Modeler 5.x desktop. Capture: opens / does-not-open. If does-not-
   open, copy the error text verbatim into DECISIONS.md and stop.
2. Walk the canvas against the table in section 2 above. Pass / fail
   each row.
3. Open the same file in demo.bpmn.io (drag-and-drop). Repeat the
   walk. demo.bpmn.io is the reference renderer — if Camunda passes
   and bpmn.io fails, that's a Camunda-specific quirk worth a
   DECISIONS entry.
4. In Camunda Modeler, save the file (no edits). Diff the saved file
   against the original at the structural level (ids, lane membership,
   flow source/target preserved). Skip XML-byte diff — irrelevant.
5. If everything passes, append a DECISIONS.md entry "BPMN modeler
   validation — first pass" with the Camunda Modeler version number,
   the bpmn.io date stamp, and a one-line "structural integrity
   confirmed against simple_two_actors fixture." Mark QUEUE.md item
   done.
6. If anything fails, do NOT edit `nimbus-skeleton/` source — orphan-
   dirs decision is unresolved per CLAUDE.md off-limits and the
   queue item explicitly says "stop and write to NEEDS-INPUT.md."
   Capture the failure with: which renderer, what step, what error
   text, what was expected.

## Recommendation

**Actionable change.** Update the validation README and / or the queue
item with the concrete checklist in section 2 + procedure in section
6, so the Worker who picks this up isn't deriving the pass/fail gates
from scratch. I'll propose this as a doc-only change in PROPOSED.md
rather than editing the README directly (Researcher is read-only).

The validation itself is unblocked: there's no evidence in either the
emitter source, the sample file, or the public Camunda Modeler /
bpmn.io issue queues that the file we emit will fail to import. The
2026-04-26 DI fix is the load-bearing change; everything since then
looks structurally clean. Worker should proceed.

## Open follow-ups

- **Worker still needs to physically open the file in Camunda Modeler
  desktop.** Researcher cannot do that. The expected outcome based on
  this analysis is "opens cleanly with platform-tag lint warnings only,"
  but until a human (or computer-use Worker) confirms it, the gate is
  open.
- **Gateway-bearing fixture.** The current fixture exercises only
  tasks + flows + lanes. Once gateways land in skeletons used in the
  field, a second validation pass against a gateway-bearing fixture is
  warranted — the diamond rendering and outgoing-flow conditions are
  not exercised by the current sample. Likely a separate queue item,
  not a blocker for the current P1.
- **Larger-skeleton fixture.** The DECISIONS entry flags ~50 nodes as
  the point at which the deterministic horizontal-grid layout becomes
  hard to read. We should validate at least once at that scale before
  the emitter goes into routine use, to confirm Camunda Modeler still
  accepts our coordinates without bailing on any layout heuristic of
  its own. Not a blocker.
- **Round-trip diff tooling.** "Structural identity, not byte
  identity" (section 3) is asserted but not automated. A small
  comparison script that diffs two BPMN files at the (id, parent-lane,
  source, target) level would make this a cheap CI step. Not in scope
  for this run; flagging for a future PROPOSED.md.
