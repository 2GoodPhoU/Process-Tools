# BPMN modeler validation samples

This directory holds sample outputs produced by running DDE +
nimbus-skeleton against `requirements-extractor/samples/procedures/simple_two_actors.docx`.
Use the `.bpmn` file here to validate that the BPMN 2.0 emitter
produces output that real-world tools accept (REFACTOR.md item S3).

## How to validate

1. Open `simple_two_actors.bpmn` in a real BPMN modeler:
   - **[Camunda Modeler](https://camunda.com/download/modeler/)** —
     desktop app, the most common defense-side BPMN tool.
   - **[bpmn.io](https://demo.bpmn.io/)** — browser-based reference
     viewer maintained by Camunda; drag-and-drop the file in.
2. Verify visually:
   - Two lanes appear: **Operator** and **Supervisor**.
   - Four tasks land in the correct lanes (two each).
   - Start event flows into the first Operator task; end event has
     two incoming flows.
   - No "invalid BPMN" / "incoming/outgoing missing" errors at
     import time.
3. If anything's off, the structural tests in
   `nimbus-skeleton/tests/test_bpmn_emitter.py` cover ~80% of likely
   failure modes — the remaining 20% is "the modeler refuses for a
   subtle reason," which is what this validation step is for.

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

These are byte-stable across runs — re-running the same pipeline on
the same fixture produces identical bytes (asserted by the test
suite). So if you check these into git as a goldens set, a `git diff`
will surface any unintended emitter regression.
