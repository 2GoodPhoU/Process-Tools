# Process-Tools

A workshop of small Python tools that aid process modelling work for
defence-industry contracts. The tools chain off each other but each one
is independently runnable.

The user is a process modeller building TIBCO Nimbus models that have
to comply with procedure documents and industry standards. These tools
automate the parts of that workflow that are tedious by hand.

## The three tools

```
                   contract.docx ─────────[DDE]─┐
                                                 ├─▶ contract.xlsx ─┐
                                                 │                   │
                                                 │                   ├──▶ [Compliance Matrix]
                                                 │                   │      ├─ matrix.xlsx
                                                 │                   │      ├─ detail
                   procedure.docx ──────[DDE]────┼─▶ procedure.xlsx ─┘      └─ gaps
                                                 │
                                                 │
                                                 └─▶ requirements.xlsx ─▶ [Nimbus Skeleton]
                                                                              ├─ skeleton.puml
                                                                              ├─ skeleton.skel.yaml
                                                                              ├─ skeleton.xmi
                                                                              └─ skeleton.review.xlsx
```

### 1. [`requirements-extractor/`](./requirements-extractor/) — Document Data Extractor (DDE)

The foundation tool. Takes a Word / PDF / `.doc` specification and pulls
structured requirements out: one row per `shall` / `must` / `should`
statement, with stable IDs, polarity (positive / negative), confidence,
heading trail, primary actor, secondary actors, and a source-preview
context column.

Outputs: `xlsx` (primary), plus optional `json` / `md` / `reqif` (with
Cameo / DOORS dialect variants). Has a CLI (`document-data-extractor`)
and a Tkinter GUI. Bundles spaCy + `en_core_web_sm` into a PyInstaller
exe so it runs on restricted networks without an installer's
package-fetch path.

Read [`requirements-extractor/docs/PROJECT_OVERVIEW.md`](./requirements-extractor/docs/PROJECT_OVERVIEW.md)
for a deep re-onboarding guide.

**Status:** v0.5.0 — REVIEW carryovers list empty; 469 tests passing;
PyInstaller spec preflight green. Outstanding stretch items: real
Cameo / DOORS import validation, work-network smoke test on Windows.

### 2. [`compliance-matrix/`](./compliance-matrix/) — Compliance Matrix Generator

Cross-references contract requirements against procedure / standard
clauses. Inputs are two DDE-produced xlsx workbooks (contract side and
procedure side); output is a coverage-matrix xlsx with three sheets
(Matrix / Detail / Gaps).

Four matchers run in parallel and their scores are blended:
- `explicit_id` — regex for cited section / clause IDs (highest signal)
- `manual_mapping` — operator-curated yaml/csv lookup (gold standard)
- `similarity` — TF-IDF cosine, pure-stdlib (catches paraphrased links)
- `keyword_overlap` — token-Jaccard (cheap baseline)

**Status:** v0.1.0 — scaffold complete, end-to-end smoke test green
(3 tests). Threshold tuning against real spec / procedure pairs is the
obvious next step.

### 3. [`nimbus-skeleton/`](./nimbus-skeleton/) — Nimbus Skeleton Mapper

Turns DDE-extracted requirements into a starter UML activity diagram
skeleton: swimlanes per actor, action nodes from imperative
requirements, sequence flows from document order, decision gateways
from conditional language. Designed as a head-start for hand-finishing
in TIBCO Nimbus or any other UML / BPM tool.

Four output formats from one run:
- `skeleton.puml` — PlantUML (instant viz, paste into plantuml.com)
- `skeleton.skel.yaml` — tool-neutral YAML manifest (the pivot file)
- `skeleton.xmi` — UML 2.5 XMI (Cameo / EA / MagicDraw / Papyrus)
- `skeleton.review.xlsx` — flagged-items side-car for human triage

**Status:** v0.1.0 — scaffold complete, 13 tests passing. The realistic
Nimbus import path is via Visio (`.vsdx`) — phase 2 deliverable.

## Working with these tools

### Quickstart sequence

```bash
# 1. Extract requirements from your contract
cd requirements-extractor
python run_gui.py                       # or use the CLI
# → produces contract.xlsx

# 2. Extract requirements from your reference standard
python run_gui.py
# → produces standard.xlsx

# 3. Cross-reference them
cd ../compliance-matrix
python run_cli.py \
    --contract  ../requirements-extractor/contract.xlsx \
    --procedure ../requirements-extractor/standard.xlsx \
    -o coverage_matrix.xlsx
# → produces a 3-sheet xlsx (Matrix / Detail / Gaps)

# 4. Build a starter Nimbus model from the contract reqs
cd ../nimbus-skeleton
python run_cli.py \
    --requirements ../requirements-extractor/contract.xlsx \
    --output-dir   /tmp/skeleton_run/
# → produces .puml, .skel.yaml, .xmi, .review.xlsx
```

### Running the test suites

Each tool is independently testable:

```bash
cd requirements-extractor && python -m unittest discover tests   # 469 tests
cd compliance-matrix      && python -m unittest discover tests   # 3 tests
cd nimbus-skeleton        && python -m unittest discover tests   # 13 tests
```

**Total: 485 tests across the workshop.**

## Design principles shared across the workshop

1. **DDE xlsx is the canonical interchange.** Both downstream tools
   load DDE's xlsx output rather than re-parsing source documents.
   Loaders match columns by header *name* (not column position) so
   future DDE schema changes don't ripple downstream.

2. **Stable IDs everywhere.** DDE's `REQ-<8hex>` IDs are hashed from
   `(source_file, primary_actor, text)` and propagate through every
   downstream tool. Diff-based workflows (which DDE supports natively)
   work end-to-end.

3. **Pure-stdlib first.** Each tool minimises optional dependencies.
   Compliance matrix's similarity matcher implements TF-IDF in 50
   lines of stdlib rather than pulling scikit-learn; Nimbus skeleton's
   manifest emitter falls back to JSON when PyYAML isn't installed.
   This keeps PyInstaller bundles lean.

4. **Output formats are flat / inspectable.** xlsx for primary
   deliverables (audit-friendly), text formats (puml, yaml, xmi) for
   review and tool-handoff. Nothing is locked into a vendor format.

5. **Keep-a-Changelog discipline.** Each tool maintains its own
   `CHANGELOG.md` and `__version__`; releases tagged in git on the
   tool's own version cadence.

## Repo layout

```
Process-Tools/
├── README.md                           (this file)
├── requirements-extractor/             (DDE — the foundation tool)
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── docs/
│   ├── packaging/                      (PyInstaller spec + build scripts)
│   ├── samples/                        (fixtures and sample specs)
│   ├── tests/                          (469 tests)
│   └── requirements_extractor/         (Python package)
├── compliance-matrix/                  (cross-references reqs vs clauses)
│   ├── README.md
│   ├── tests/
│   └── compliance_matrix/
└── nimbus-skeleton/                    (DDE → UML activity skeleton)
    ├── README.md
    ├── tests/
    └── nimbus_skeleton/
```

## Future direction

- **Native `.vsdx` emitter** for Nimbus Skeleton — phase 2; the actual
  Nimbus import path per the TIBCO User Guide.
- **Shared `process_tools_common/` package** for the duplicated
  DDE-xlsx loader between compliance-matrix and nimbus-skeleton.
- **Real-corpus threshold tuning** for the compliance matrix's fuzzy
  matchers (TF-IDF + Jaccard cutoffs are educated guesses today).
- **PyInstaller bundles** for compliance-matrix and nimbus-skeleton, so
  they run on the same restricted-network Windows machine DDE targets.
