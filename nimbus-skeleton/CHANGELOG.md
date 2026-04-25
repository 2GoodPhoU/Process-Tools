# Changelog

All notable changes to **Nimbus Skeleton Mapper** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).
Pre-1.0 behaviour: minor versions may include breaking CLI / output-shape
changes — they will always be called out under a **Breaking** subhead.

## [0.1.0] — 2026-04-24

Initial scaffold. Pipeline DDE xlsx → swimlane-and-flow skeleton →
four output formats. 13 tests passing.

### Added — pipeline
- DDE xlsx loader for the requirements side and the actors side. Loader
  is a thin wrapper over `process_tools_common.dde_xlsx` so the DDE
  column-name mapping is shared with compliance-matrix.
- Classifier that decides whether each requirement becomes:
  - an **activity** (modal-imperative, e.g. `shall`, `must`, `will`)
  - a **gateway** (conditional language: `if`, `when`, `unless`, `in
    case of`, `in the event that`, `provided that`, `whenever`)
  - a **note** (declarative — no modal verb, no conditional)
  Negative-polarity activities and modal-less candidates are emitted
  as activities with `flagged=True` so the reviewer can audit them.
- Builder that walks DDE rows in source-document order, assembles a
  ``Skeleton`` (actors + activities + gateways + notes + sequence-flow
  edges), and emits cross-actor handoffs when consecutive rows change
  primary actor. Doesn't try to detect loops, parallel branches, or
  merge points — those are explicit human-judgment items.
- Pivot type ``Skeleton`` in ``models.py``. All emitters consume the
  pivot — none reach back to DDE rows directly. Adding a new emitter
  is a one-file addition.

### Added — output formats
- **PlantUML** (`.puml`) — UML 2.x activity-diagram syntax with
  `|swimlane|` partitions, `if/endif` for gateways, `note right` for
  flagged items. Renders at plantuml.com or any PlantUML CLI.
- **YAML manifest** (`.skel.yaml`) — tool-neutral pivot file. Falls
  back to JSON (which is valid YAML 1.2) when PyYAML isn't installed.
  Two runs over the same input produce byte-identical manifests
  (trivially diffable).
- **UML 2.5 XMI** (`.xmi`) — OMG-spec interchange format. Importable
  into Cameo Systems Modeler, Enterprise Architect, MagicDraw,
  Papyrus. Emits `uml:Activity` with `OpaqueAction` / `DecisionNode`
  / `ActivityPartition` (swimlane) / `ControlFlow` elements bracketed
  by `InitialNode` and `ActivityFinalNode`. Hand-built XML for
  byte-stable output across Python minor versions.
- **Review side-car** (`.review.xlsx`) — flagged-activity audit
  workbook with a `Reviewer Decision` column.

### Added — CLI
- `nimbus-skeleton --requirements R.xlsx --output-dir D/` with
  optional `--actors A.xlsx`, `--basename`, `--title`, and `--no-xmi`
  flags.

### Investigated — Nimbus import-format pathway (does NOT change code yet)
- TIBCO Nimbus 10.6.1 User Guide (Eric uploaded both Admin and User
  guides). Confirmed Nimbus's diagram-import paths are **MS Visio
  (`.vsd` / `.vsdx`)** with a rules-based shape mapping, **ARIS XML
  EPC** diagrams, and `.cpk` packaged maps. Nimbus does NOT import
  XMI, BPMN-XML, or its own export XML. The realistic Nimbus path
  from this tool is via Visio — **phase 2** is a `.vsdx` emitter that
  walks the YAML manifest and emits stencil-named shapes (Process,
  Decision, Terminator, swimlane bands).
- Page citations preserved in `README.md` under "Phase 2 — Visio
  import path" so future sessions don't re-derive.

[0.1.0]: #010--2026-04-24
