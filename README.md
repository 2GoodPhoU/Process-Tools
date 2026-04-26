# Process-Tools

A workshop of small Python tools that aid process modelling work for
defence-industry contracts. The tools chain off each other but each one
is independently runnable.

The user is a process modeller who originally built TIBCO Nimbus
models for compliance with procedure documents and industry standards.
With Nimbus on-premise's retirement on 2025-09-01, the strategic
output target has shifted to **BPMN 2.0** (the open standard every
modern modeller reads); the Visio (`.vsdx`) path is still produced for
any Nimbus instance still in operation. These tools automate the parts
of the modelling workflow that are tedious by hand.

For the unified roadmap (shipped highlights, in-progress, next, later,
risk register), see [`ROADMAP.md`](./ROADMAP.md).

## The four tools

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
                                                                              ├─ skeleton.vsdx   (Visio / Nimbus)
                                                                              ├─ skeleton.bpmn   (BPMN 2.0, opt-in)
                                                                              └─ skeleton.review.xlsx

                                  [process-tools-common]   ◀── shared DDE-xlsx schema package
                                       (consumed by Compliance Matrix and Nimbus Skeleton)
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

**Status:** v0.1.0 — end-to-end pipeline green; **23 tests passing**.
Five matchers shipped (the four originals plus `fuzzy_id`, a pure-stdlib
Levenshtein matcher for typo'd / reformatted citations). Threshold
tuning against real spec / procedure pairs is the obvious next step.

### 3. [`nimbus-skeleton/`](./nimbus-skeleton/) — Nimbus Skeleton Mapper

Turns DDE-extracted requirements into a starter process-model
skeleton: swimlanes per actor, action nodes from imperative
requirements, sequence flows from document order, decision gateways
from conditional language. Designed as a head-start for
hand-finishing in any modern BPMN or UML tool — historically TIBCO
Nimbus, now also Camunda Modeler, bpmn.io, Cameo, Enterprise
Architect, MagicDraw, etc.

Six output formats from one run:
- `skeleton.puml` — PlantUML (instant viz, paste into plantuml.com)
- `skeleton.skel.yaml` — tool-neutral YAML manifest (the pivot file)
- `skeleton.xmi` — UML 2.5 XMI (Cameo / EA / MagicDraw / Papyrus)
- `skeleton.vsdx` — native Visio with shape NameUs that match
  TIBCO Nimbus's default Visio-import rules
- `skeleton.bpmn` — BPMN 2.0 XML (opt-in via `--bpmn`); the strategic
  interchange format post-Nimbus retirement, importable into Camunda
  Modeler, bpmn.io, and most modern BPMN tools
- `skeleton.review.xlsx` — flagged-items side-car for human triage

**Status:** v0.1.0 — **33 tests passing**. All five emitters live;
BPMN 2.0 emitter shipped 2026-04-25 in response to the Nimbus
on-premise retirement.

### 4. [`process-tools-common/`](./process-tools-common/) — Shared DDE schema package

The shared spine for compliance-matrix and nimbus-skeleton. Centralises
the DDE xlsx schema (`HEADER_MAP`, `iter_dde_records`,
`iter_actor_records`) so a future DDE column rename or addition only
needs reflecting in one place. Both consumers wire it in via a small
`sys.path` bootstrap until the repo settles on a packaging convention.

**Status:** v0.1.0 — 9 tests passing. Stable; consumers depend on it.

## Working with these tools

### One-time setup: install runtime deps + git pre-commit hook

Install the workshop's runtime dependencies into whichever Python you
plan to use for the test suites:

```powershell
cd C:\Users\erics\Documents\GitHub\Process-Tools
pip install -r requirements.txt
```

This installs `openpyxl`, `pyyaml`, and `python-docx` — the core deps
shared across the four tools. Optional extras (spaCy for NER,
tkinterdnd2 for GUI drag-and-drop, pdfplumber for PDF input) live in
`requirements-extractor/requirements-optional.txt`.



The repo ships a small pre-commit hook that guards against the
documented file-tail truncation hazard. Install once after cloning:

```powershell
# Windows (PowerShell):
.\scripts\install-hooks.ps1

# Linux / macOS / Git Bash:
bash scripts/install-hooks.sh
```

The hook runs `python -m py_compile` and a NUL-byte check on every
staged `.py` file. Self-contained — no `pip install pre-commit`
needed. See [`scripts/pre-commit-check.sh`](./scripts/pre-commit-check.sh).

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

Workshop-wide runner (run from repo root):

```powershell
# Windows (PowerShell):
.\scripts\test_all.ps1

# Linux / macOS / Git Bash:
bash scripts/test_all.sh

# If GNU make is on PATH:
make test-all
```

Per-tool, if you prefer:

```bash
cd requirements-extractor && python -m unittest discover tests   # 511 tests
cd compliance-matrix      && python -m unittest discover tests   # 30 tests
cd nimbus-skeleton        && python -m unittest discover tests   # 33 tests
cd process-tools-common   && python -m unittest discover tests   # 26 tests
```

**Total: 600 tests across the workshop.**

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
├── ROADMAP.md                          (unified roadmap)
├── ACTION_ITEMS.md                     (most recent overnight log)
├── WHEN_YOU_RETURN.md                  (next-session entry point)
├── requirements-extractor/             (DDE — the foundation tool)
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── docs/
│   ├── packaging/                      (PyInstaller spec + build scripts)
│   ├── samples/                        (fixtures and sample specs)
│   ├── research/                       (alternatives surveys, sources)
│   ├── tests/                          (505 tests, incl. integration/)
│   └── requirements_extractor/         (Python package, 18 modules)
├── compliance-matrix/                  (cross-references reqs vs clauses)
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── tests/                          (23 tests)
│   └── compliance_matrix/              (5 matchers + combiner + writer)
├── nimbus-skeleton/                    (DDE → process-model skeleton)
│   ├── CHANGELOG.md
│   ├── README.md
│   ├── tests/                          (33 tests)
│   └── nimbus_skeleton/                (loader + classifier + builder + 5 emitters)
└── process-tools-common/               (shared DDE-xlsx schema)
    ├── CHANGELOG.md
    ├── tests/                          (9 tests)
    └── process_tools_common/           (dde_xlsx module)
```

## Future direction

The full roadmap lives in [`ROADMAP.md`](./ROADMAP.md). Cross-cutting
near-term highlights:

- **Real-corpus threshold tuning** for the compliance matrix's fuzzy
  matchers (TF-IDF + Jaccard + Levenshtein cutoffs are educated guesses
  today).
- **BPMN modeler validation** — open Nimbus Skeleton's `.bpmn` output
  in Camunda Modeler / bpmn.io against a real DDE-derived skeleton.
- **PyInstaller bundles** for compliance-matrix and nimbus-skeleton, so
  they run on the same restricted-network Windows machine DDE targets.
- **CLI / GUI plumbing for the new actor heuristics** — currently only
  available via Python API.
- **Refactoring pass** — see `REFACTOR.md` for the consolidated
  punch list of stability, deduplication, and trim opportunities.
