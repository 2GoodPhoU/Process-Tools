# BPMN modeler validation samples

This directory holds sample outputs produced by running DDE +
nimbus-skeleton against `requirements-extractor/samples/procedures/simple_two_actors.docx`.
Use the `.bpmn` file here to validate that the BPMN 2.0 emitter
produces output that real-world tools accept (REFACTOR.md item S3).

## How to validate

Concrete pass/fail walkthrough; full grounding in
`research/2026-04-29-camunda-import-checklist.md`.

### Procedure

1. Open `simple_two_actors.bpmn` in **Camunda Modeler 5.x** desktop
   ([download](https://camunda.com/download/modeler/)). Capture: opens /
   does-not-open. If does-not-open, copy the error text verbatim into
   DECISIONS.md and stop.
2. Walk the canvas against the pass-criterion table below. Pass / fail
   each row.
3. Open the same file in **demo.bpmn.io** (drag-and-drop). Repeat the
   walk. demo.bpmn.io is the reference renderer -- if Camunda passes
   and bpmn.io fails, that's a Camunda-specific quirk worth a
   DECISIONS entry.
4. In Camunda Modeler, save the file (no edits). Diff the saved file
   against the original at the structural level (ids, lane membership,
   flow source/target preserved). Skip XML-byte diff -- Camunda
   reformats whitespace + attribute order on save; structural identity
   is the gate, not byte identity.
5. If everything passes, append a DECISIONS.md entry "BPMN modeler
   validation -- first pass" with the Camunda Modeler version number,
   the bpmn.io date stamp, and a one-line "structural integrity
   confirmed against simple_two_actors fixture." Mark the QUEUE.md
   item done.
6. If anything fails, do NOT edit `nimbus-skeleton/` source -- orphan-
   dirs decision is unresolved per CLAUDE.md off-limits and the queue
   item explicitly says "stop and write to NEEDS-INPUT.md." Capture
   the failure with: which renderer, what step, what error text, what
   was expected.

### Pass-criterion table

| Element | Pass criterion |
| ------- | -------------- |
| Pool | One pool labelled "Process Skeleton" (the `Participant_1` name). |
| Lanes | Two lanes inside the pool: "Operator" (top) and "Supervisor" (bottom). |
| Tasks | Four tasks visible. Two land in Operator, two in Supervisor. |
| Start event | Single thin-circle start event in the Operator lane (left edge of pool, vertically centered on the pool). |
| End event | Single thick-circle end event (right edge of pool, vertically centered). |
| Sequence flows | Six sequence flows total, all rendered as solid arrows. No "floating" flows (an arrow with one end unconnected). |
| Cross-lane edges | Edges that cross between Operator and Supervisor route as right-angle elbows (4 waypoints), not straight diagonals. |
| Gateways | None in this sample (the seed corpus has no gateway). If a future sample exercises one, render as a diamond. |
| Text annotations | None in this sample. If a future sample exercises one, render as a folded-corner rectangle below the pool. |
| `BPMNShape` for every flow node | Inspect the saved XML after re-save: no flow node lacks a `BPMNShape`. (Camunda will preserve all of ours.) |
| `BPMNEdge` for every sequence flow with >=2 waypoints | Same. Inspection of the source file shows every flow has 2 or 4 waypoints. |

Lint warnings tagged "Camunda 7" or "Zeebe" (e.g. "task type not set",
"missing service implementation") are *runtime* concerns, not BPMN-2
conformance failures. Document them in DECISIONS but do not treat as
failures. The structural tests in
`nimbus-skeleton/tests/test_bpmn_emitter.py` already cover ~80% of
likely failure modes -- this validation step is catching the
remaining 20% (the "modeler refuses for a subtle reason" class).

## How this sample was generated

```bash
# From repo root, with .venv-workshop active and reqs installed:
python -m requirements_extractor.cli --no-summary \
    requirements requirements-extractor/samples/procedures/simple_two_actors.docx \
    -o /tmp/dde.xlsx

python -m nimbus_skeleton.cli \
    --requirements /tmp/dde.xlsx \
    --output-dir samples/bpmn_validation/ \
    --basename simple_two_actors \
    --bpmn
```

## What's here

| File                            | Purpose                                       |
|---------------------------------|-----------------------------------------------|
| `simple_two_actors.bpmn`        | The BPMN 2.0 file to load in the modeler.     |
| `simple_two_actors.puml`        | PlantUML version (paste at plantuml.com).     |
| `simple_two_actors.skel.yaml`   | Tool-neutral pivot manifest.                  |
| `simple_two_actors.xmi`         | UML 2.5 XMI for Cameo / EA / MagicDraw.       |
| `simple_two_actors.vsdx`        | Native Visio file (Nimbus import path).       |
| `simple_two_actors.review.xlsx` | Flagged-items audit side-car (empty here).    |

These are byte-stable across runs -- re-running the same pipeline on
the same fixture produces identical bytes (asserted by the test
suite). So if you check these into git as a goldens set, a `git diff`
will surface any unintended emitter regression.
