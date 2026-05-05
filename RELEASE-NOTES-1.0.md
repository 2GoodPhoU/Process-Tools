# Process-Tools 1.0 — Release Notes

> **Status: SCAFFOLD.** Sub-tool sections are intentionally unpopulated.
> Content lands during the 1.0 cut (per-sub-tool CHANGELOG promotions
> and the bundle tag). Until then, the per-sub-tool CHANGELOGs under
> each sub-tool directory are the authoritative source for what has
> shipped.

**Release date:** _TBD — filled in on tag day._

**Tag:** `1.0.0` (bundle — all four sub-tools tag at the same HEAD).

---

## What this release is

The Process-Tools 1.0 release is the first stable customer-deliverable
bundle of four sub-tools that together support the procedure-document
to process-model workflow on an air-gapped target:

- **requirements-extractor** — extracts requirements and actors from
  procedure documents (.docx / legacy .doc / .pdf) and emits structured
  output (xlsx, json, md, ReqIF).
- **compliance-matrix** — scaffolds traceability matrices from a
  contract workbook and a procedure workbook produced by
  requirements-extractor.
- **nimbus-skeleton** — emits process-model skeletons in PlantUML,
  YAML, XMI, Visio (`.vsdx`), and BPMN 2.0 — the BPMN path is the
  forward-looking format following the TIBCO Nimbus on-premise
  retirement (2025-09-01).
- **process-tools-common** — the shared library that the three
  consumer tools depend on (DDE schema, loader helpers, CLI helpers).

The toolkit is designed for offline-network deployment. Every Python
dependency, including the spaCy NLP model, is bundled into the
PyInstaller binaries that ship to the target machine. No network
calls occur in any shipped-binary code path.

---

## How to read these notes

Each sub-tool has its own section below summarising the
customer-relevant changes since the last shipped version. Per-tool
detail (test counts, internal refactors, decision rationale) lives in
each sub-tool's own `CHANGELOG.md`. Cross-references are listed at the
bottom of every section.

---

## requirements-extractor 1.0.0

_Section content lands during the 4.1 cut._

What customers will see in this section once filled:

- Headline capabilities since the last released version (0.6.0).
- Notable behaviour changes (compound-sentence detection,
  multi-action decomposition, the offline-network actor-extraction
  fallback).
- Output-format additions or shape changes.
- Known limitations and supported document types.

**Cross-reference:** see `requirements-extractor/CHANGELOG.md` for the
authoritative per-version changelog and
`requirements-extractor/PATCH-0.6.1-NOTES.md` /
`PATCH-0.6.2-NOTES.md` for the design notes behind the patch lines
that fold into 1.0.

---

## nimbus-skeleton 1.0.0

_Section content lands during the 4.2 cut._

What customers will see in this section once filled:

- The BPMN 2.0 emitter, including round-trip validation against
  Camunda Modeler 5.x desktop and demo.bpmn.io.
- The continued availability of the Visio (`.vsdx`) emitter for any
  Nimbus instance still in operation.
- Output formats supported in 1.0: PlantUML, YAML, XMI, `.vsdx`,
  BPMN 2.0, plus the review xlsx side-car.
- Layout behaviour for BPMN diagrams (deterministic horizontal
  swimlane grid).

**Cross-reference:** see `nimbus-skeleton/CHANGELOG.md` for the
per-version changelog and `nimbus-skeleton/DECISIONS.md` for the
BPMN diagram-interchange design rationale.

---

## compliance-matrix 1.0.0

_Section content lands during the 4.3 cut._

What customers will see in this section once filled:

- The five-matcher pipeline (similarity, keyword, structural, semantic,
  fuzzy-id) and the default thresholds validated against a real
  spec / procedure pair.
- The relevant CLI flags (e.g. `--fuzzy-id-threshold`,
  `--no-fuzzy-id`).
- Input expectations (two DDE-emitted xlsx workbooks: contract and
  procedure).

**Cross-reference:** see `compliance-matrix/CHANGELOG.md` for the
per-version changelog.

---

## process-tools-common 1.0.0

_Section content lands during the 4.4 cut._

What customers will see in this section once filled:

- The shared `dde_xlsx` schema and loader helpers.
- The shared `cli_helpers` (`add_quiet_flag`, `make_logger`).
- Notes on consumer integration (compliance-matrix and nimbus-skeleton
  pip-install or PyInstaller-bundle cleanly without a `sys.path`
  bootstrap shim).

**Cross-reference:** see `process-tools-common/CHANGELOG.md` for the
per-version changelog.

---

## Upgrade and installation

_Section content lands during the 4.6 PyInstaller bundle cut._

What customers will see in this section once filled:

- Which binaries are produced for the customer-shipping subset
  (at minimum `DocumentDataExtractor.exe`; nimbus-skeleton equivalent
  if customer needs offline BPMN emission).
- Bundle size and load time.
- Restricted-network installation procedure.
- Smoke-test commands to confirm the bundle works on the target.

---

## Known issues

_Section content lands during the 4.x cut, populated from each
sub-tool's CHANGELOG and the project DECISIONS.md as items are
identified._

---

## Cross-references

- **Roadmap and release strategy:** `ROADMAP.md` (root).
- **Per-sub-tool changelogs:**
  - `requirements-extractor/CHANGELOG.md`
  - `nimbus-skeleton/CHANGELOG.md`
  - `compliance-matrix/CHANGELOG.md`
  - `process-tools-common/CHANGELOG.md`
- **Decision logs:**
  - `DECISIONS.md` (root, architectural decisions across sub-tools).
  - `requirements-extractor/DECISIONS.md` (sub-tool decisions).
  - `nimbus-skeleton/DECISIONS.md` (sub-tool decisions, including the
    BPMN diagram-interchange rationale).
- **Patch-line context:**
  - `requirements-extractor/PATCH-0.6.1-NOTES.md`
  - `requirements-extractor/PATCH-0.6.2-NOTES.md`
- **Field notes from offline-network testing:**
  - `requirements-extractor/FIELD_NOTES.md`

---

## Revision history of this document

- **TBD** — 1.0.0 release. Initial publication.
