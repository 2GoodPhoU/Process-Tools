# Nimbus Skeleton Mapper

Turn DDE-extracted requirements into a starter UML activity-diagram
skeleton: swimlanes per actor, action nodes from imperative
requirements, sequence flows from document order, decision gateways
from conditional language. Designed as a head-start for hand-finishing
in TIBCO Nimbus or any other UML / BPM tool.

## Status

**Scaffold complete, all five emitters live, end-to-end smoke test
green.** PlantUML, YAML manifest, UML 2.5 XMI, **and native Visio
(`.vsdx`)** are all working; review side-car xlsx surfaces every
flagged item. The `.vsdx` uses NameU values that match TIBCO Nimbus's
default Visio import rules (Process / Decision / Dynamic connector),
so `File → Import/Export → Import from Visio` should land it as
proper Nimbus shapes without rules-file tweaking. Phase 3 candidates — see
[Phase 2 — Visio import path](#phase-2--visio-import-path) below.

## How it works

```
   requirements.docx ─[DDE]─▶ requirements.xlsx ─┐
                                                  │
   actors.docx ──────[DDE]─▶ actors.xlsx ─────────┼─▶ nimbus-skeleton ─┬─▶ skeleton.puml
                                                  │                     │
   (optional)                                     │                     ├─▶ skeleton.skel.yaml
                                                  │                     │
                                                  │                     ├─▶ skeleton.xmi   (UML 2.5)
                                                  │                     │
                                                  │                     ├─▶ skeleton.vsdx  (Nimbus path)
                                                  │                     │
                                                  └─────────────────────┴─▶ skeleton.review.xlsx
```

Pipeline stages:

1. **Loader** reads the DDE xlsx workbooks (matching columns by header
   name, not position).
2. **Classifier** decides whether each requirement becomes an activity,
   a gateway, or a note. Driven by modal-keyword and conditional-keyword
   regexes plus the DDE polarity column.
3. **Builder** assembles the in-memory `Skeleton` — actors, ordered
   activity / gateway / note nodes, sequence-flow edges. Cross-actor
   handoffs become flow edges; same-actor consecutive nodes get a flow
   too. The builder doesn't try to detect loops, parallelism, or merge
   points — those are explicit human-judgment items.
4. **Emitters** turn the skeleton into output formats: PlantUML for
   instant viz; YAML manifest as the tool-neutral pivot; UML 2.5 XMI
   for Cameo / EA / MagicDraw / Papyrus / any UML tool that speaks
   XMI; native Visio (`.vsdx`) with stencil-named shapes for the
   TIBCO Nimbus import path.
5. **Review writer** drops every `flagged=True` activity into a
   single-sheet xlsx side-car for human triage.

## Outputs

Every run produces five files in `--output-dir`:

| File                     | What it's for                                        |
|--------------------------|------------------------------------------------------|
| `skeleton.puml`          | PlantUML — paste into plantuml.com or any PlantUML   |
|                          | renderer for instant visualisation                   |
| `skeleton.skel.yaml`     | Tool-neutral manifest. Stable across runs (diffable).|
|                          | Pivot file for downstream emitters                   |
| `skeleton.xmi`           | UML 2.5 XMI. Open in Cameo / Enterprise Architect /  |
|                          | MagicDraw / Papyrus. Standards-compliant UML output  |
|                          | (OMG XMI 2.5.1 / UML 2.5)                            |
| `skeleton.vsdx`          | Native Visio file with NameU values matching Nimbus's|
|                          | default Visio-import rules. Drop into Nimbus via     |
|                          | File → Import/Export → Import from Visio. Inner      |
|                          | page1.xml is byte-stable across runs                 |
| `skeleton.review.xlsx`   | Side-car listing every flagged activity (negative    |
|                          | polarity, no modal verb, conditional branches, etc.) |
|                          | with a Reviewer Decision column                      |

## Quick start

```bash
cd nimbus-skeleton
python -m unittest discover tests        # green smoke test

python run_cli.py \
    --requirements ../requirements-extractor/sample_requirements.xlsx \
    --actors       ../requirements-extractor/sample_actors.xlsx \
    --output-dir   /tmp/skeleton_run/
```

Render the resulting `skeleton.puml`:
- **In your browser**: paste the file's contents into
  https://www.plantuml.com/plantuml/uml/
- **Locally**: `plantuml /tmp/skeleton_run/skeleton.puml` produces a PNG.

## What gets flagged for review

The builder is conservative about ambiguous cases. An activity ends up
in the review side-car when:

- The requirement has **negative polarity** (`shall not`, `must not`).
  Negative requirements model better as constraints than action nodes.

Each flagged activity's review row includes the original requirement text
from the DDE workbook so the reviewer can see the full context.
- The classifier found **no modal verb** (`shall`, `must`, `will`,
  `should`, `may`, `can`). Could still be an action — the reviewer
  confirms.
- The requirement was a **conditional / gateway**. The gateway label
  is the regex-extracted condition; both branch targets need
  reviewer attention since the builder doesn't try to guess them.

## YAML manifest schema

```yaml
version: 1
title: Process Skeleton
actors: [Operator, System, Supervisor]
activities:
  - id: REQ-AAA1
    label: log in to control console
    actor: Operator
    flagged: false
gateways:
  - id: REQ-AAA2-gw
    condition: login successful?
    actor: System
notes:
  - id: REQ-AAA9
    text: Audit log is the persistent record of system events
    actor: System
flows:
  - [REQ-AAA1, REQ-AAA2-gw]
  - [REQ-AAA2-gw, REQ-AAA2]
```

The manifest is intentionally minimal — every field is explicit, no
generated IDs, no implicit positions. If `pyyaml` isn't installed the
emitter falls back to JSON (which is valid YAML 1.2). Two runs over
the same input produce byte-identical manifests, which makes them
trivially diffable.

## CLI reference

```
nimbus-skeleton --requirements R.xlsx --output-dir D/
                [--actors A.xlsx] [--basename skeleton] [--title "..."] [-q]
```

| Flag             | Notes                                              |
|------------------|----------------------------------------------------|
| `--requirements` | Required. DDE requirements xlsx.                  |
| `--actors`       | Optional. DDE actors xlsx for alias resolution.   |
| `--output-dir`   | Required. Created if absent.                       |
| `--basename`     | Filename prefix for the three outputs (default `skeleton`). |
| `--title`        | Diagram title shown in PlantUML / manifest / XMI.  |
| `--no-xmi`       | Skip the XMI emitter (useful for fast iteration).  |
| `--no-vsdx`      | Skip the Visio (.vsdx) emitter.                    |

## Visio import path (now shipped — was Phase 2)

The realistic Nimbus import path is **MS Visio** (`.vsd` / `.vsdx`).
Per the TIBCO Nimbus 10.6.1 User Guide:

- **Pages 311–316: "Import from MS Visio."** Visio diagrams import via
  a rules engine that maps Visio shape names to Nimbus shape types.
  The default rules cover all basic flowchart shapes (rectangle for
  Auto-height Box, decision for Diamond, etc.). An `Import as BPMN
  diagrams` toggle exists for BPMN-style mapping.
- **Page 308: "Export to XML."** Nimbus *exports* its own XMI-flavoured
  XML format (Standard / Simplified) but does not appear to import that
  XML back as a diagram — it's a one-way integration channel. This is
  why our `.xmi` output targets generic UML tools (Cameo, EA, MagicDraw,
  Papyrus) rather than Nimbus directly.
- **Page 316: "Import from ARIS."** ARIS XML EPC diagrams also import.
  Lower-priority unless you have ARIS in your toolchain.

So that's exactly what `emitters/vsdx.py` does:

1. Walk the in-memory `Skeleton` (the same pivot every other emitter
   consumes).
2. Build the OOXML zip directly: `[Content_Types].xml`, the relationship
   parts, `docProps/app.xml` + `core.xml`, `visio/document.xml`,
   `visio/pages/pages.xml`, and the actual `visio/pages/page1.xml`.
3. Use `NameU="Process"` for activities, `NameU="Decision"` for
   gateways, and `NameU="Dynamic connector"` for sequence-flow edges.
   These match the default rules in Nimbus's Visio-import rules file
   (per User Guide pp.311-314), so the shapes land on the canvas as
   the right Nimbus types without any rules-file tweaking.

Nimbus import recipe: `File → Import/Export → Import from Visio` →
browse to `<basename>.vsdx` → leave the default rules file selected
(or toggle `Import as BPMN diagrams` if BPMN-flavoured shapes are
preferred). The diagram lands as a fresh map.

**Phase 3 candidates** (not yet built):

- Swimlane band shapes — currently activities are positioned in actor
  *columns* but without the rectangular swimlane band overlay. Adding
  these means emitting the cross-functional flowchart band shapes.
- Connector routing — Visio computes connector geometry on open;
  pre-routing them would make the emitted file look better before
  the user re-routes connectors interactively.

The YAML manifest's stable schema means the `vsdx` emitter can be
added without any changes to the loader, classifier, or builder.

## Project layout

```
nimbus-skeleton/
├── README.md
├── run_cli.py                          (CLI shortcut)
├── nimbus_skeleton/
│   ├── __init__.py
│   ├── models.py                       (DDERow, Activity, Gateway, Note, Skeleton)
│   ├── loader.py                       (DDE xlsx → DDERow / actors)
│   ├── classifier.py                   (activity / gateway / note decision)
│   ├── builder.py                      (DDERow list → Skeleton)
│   ├── review_writer.py                (flagged-items side-car xlsx)
│   ├── cli.py                          (argparse entry point)
│   └── emitters/
│       ├── __init__.py
│       ├── plantuml.py
│       └── manifest.py                 (tool-neutral YAML pivot)
└── tests/
    └── test_smoke.py
```

## Dependencies

- `openpyxl` — already pulled in by DDE (used for loading + review xlsx).
- `pyyaml` — optional. Without it, the manifest emitter falls back to
  JSON.

## Open questions for next iteration

- **Threshold tuning for flagged-items.** The classifier flags any
  requirement without a modal verb as "needs confirmation." On real
  spec corpora this may be too aggressive — once we have data, tune
  toward precision over recall.
- **Visio (`.vsdx`) emitter.** Phase 2 deliverable. Page citations
  above.
- **Loop / parallel detection.** Currently the builder emits a strict
  linear flow. A future version could detect cycles (the same activity
  ID flowing back into itself) and parallel branches (multiple flows
  exiting the same node) — but only after the linear case is solid
  on real specs.
- **Loader sharing with `compliance-matrix/`.** Both tools duplicate
  the DDE-xlsx loader. Once both are stable, extract into a shared
  `process_tools_common/` package.
