# Compliance Matrix Generator

Cross-references contract / spec requirements against procedure or
industry-standard clauses and produces a coverage-matrix xlsx — the kind
of artefact contracts and audit teams ask for when the question is "do
we comply with the standard?"

Both inputs are xlsx workbooks produced by **Document Data Extractor
(DDE)** (the sibling tool in `Process-Tools/requirements-extractor/`).
Run DDE on the contract document, run it again on the procedure /
standard document, then feed both xlsx files into this tool.

## Status

**End-to-end pipeline green; 23 tests passing.** The five matchers,
combiner, and three-sheet xlsx writer are all wired up. Tuning the
similarity / keyword / fuzzy-id thresholds against real spec /
procedure pairs is the obvious next step.

## How it works

```
   contract.docx ─[DDE]─▶ contract.xlsx ─┐
                                          │
   procedure.docx ─[DDE]─▶ procedure.xlsx ─┼─▶ compliance-matrix ─▶ matrix.xlsx
                                          │
   manual_mapping.yaml ─────────────────────┘   (optional)
```

Five matchers run in parallel:

| Matcher           | Approach                              | Strengths                       | Weight |
|-------------------|---------------------------------------|---------------------------------|--------|
| `explicit_id`     | Regex on cited section / clause IDs   | Highest signal, lowest noise    | 1.00   |
| `manual_mapping`  | Operator-curated yaml/csv lookup      | Gold standard, re-usable        | 1.00   |
| `similarity`      | TF-IDF cosine on requirement/clause text | Catches paraphrased links     | 0.85   |
| `keyword_overlap` | Token Jaccard on shared content words | Cheap baseline, transparent     | 0.65   |
| `fuzzy_id`        | Levenshtein distance on section refs  | Catches typos & format variations | 0.50 (default fallback — see refactor list) |

Per-matcher scores are weighted and the **maximum** is taken as the
combined score. Every matcher's evidence is preserved on the output's
`Detail` sheet so a reviewer can audit *why* each link fired.

## Output

A single xlsx with three sheets:

- **Matrix** — requirements down rows, clauses across columns, cells
  carry the rounded combined score with colour gradient (white → yellow
  → green). Frozen panes keep the IDs and requirement text visible.
- **Detail** — one row per linked pair, sorted by descending score.
  Carries the contract text, clause text, score, list of matchers that
  fired, and concatenated evidence strings.
- **Gaps** — side-by-side: requirements with zero matches, clauses
  with zero matches. The "what's missing" lens.

## Manual mapping file format

YAML (preferred for hand-editing)::

    # mapping.yaml
    REQ-AB12: [PROC-9F33, PROC-104A]
    REQ-CD34:
      - PROC-2211
      - PROC-77AC

CSV (preferred for export from spreadsheets)::

    contract_id,procedure_id,note
    REQ-AB12,PROC-9F33,reviewed by EY
    REQ-CD34,PROC-2211,covers §6.3.1

Pass with `--mapping path/to/file.yaml`. Unknown contract / procedure
IDs in the mapping are silently dropped (they're typically stale entries
from a prior run, where stable IDs have since regenerated).

## Quick start

```bash
cd compliance-matrix
python -m unittest discover tests        # green smoke test
python run_cli.py \
    --contract  ../requirements-extractor/sample_contract.xlsx \
    --procedure ../requirements-extractor/sample_procedure.xlsx \
    --mapping   samples/sample_mapping.yaml \
    -o coverage_matrix.xlsx
```

The CLI prints a coverage summary at the end (`X/Y requirements have at
least one procedure match`).

## CLI reference

```
compliance-matrix --contract C.xlsx --procedure P.xlsx -o out.xlsx
                  [--mapping M.yaml] [--similarity-threshold 0.20]
                  [--keyword-threshold 0.15] [--fuzzy-id-threshold 0.85]
                  [--no-similarity] [--no-keyword-overlap] [--no-explicit-id]
                  [--no-fuzzy-id] [-q]
```

| Flag                       | Default | Notes                                        |
|----------------------------|---------|----------------------------------------------|
| `--similarity-threshold`   | 0.20    | TF-IDF cosine cutoff                         |
| `--keyword-threshold`      | 0.15    | Jaccard cutoff                               |
| `--fuzzy-id-threshold`     | 0.85    | Levenshtein-distance cutoff (section refs)  |
| `--no-similarity`          | off     | Skip TF-IDF matcher (e.g. for fast first pass) |
| `--no-keyword-overlap`     | off     | Skip Jaccard matcher                         |
| `--no-explicit-id`         | off     | Skip regex-citation matcher                  |
| `--no-fuzzy-id`            | off     | Skip fuzzy-id matcher                        |
| `-q` / `--quiet`           | off     | Suppress progress output                     |

## Project layout

```
compliance-matrix/
├── CHANGELOG.md
├── README.md
├── run_cli.py                          (CLI shortcut)
├── compliance_matrix/
│   ├── __init__.py
│   ├── models.py                       (DDERow, Match, CombinedMatch)
│   ├── loader.py                       (thin wrapper over process-tools-common)
│   ├── combiner.py                     (matcher score fusion)
│   ├── matrix_writer.py                (3-sheet xlsx output)
│   ├── cli.py                          (argparse entry point)
│   └── matchers/
│       ├── __init__.py
│       ├── explicit_id.py              (regex on cited IDs)
│       ├── manual_mapping.py           (operator yaml/csv lookup)
│       ├── fuzzy_id.py                 (pure-stdlib Levenshtein on IDs)
│       ├── similarity.py               (pure-stdlib TF-IDF)
│       └── keyword_overlap.py          (token Jaccard)
└── tests/
    ├── test_smoke.py                   (end-to-end pipeline)
    └── test_fuzzy_id.py                (fuzzy-id matcher unit tests)
```

## Dependencies

- `openpyxl` — already pulled in by DDE.
- `pyyaml` — only needed if you use a YAML manual mapping file. CSV
  format works without it.
- `process-tools-common` — sibling package, wired in via a small
  `sys.path` bootstrap in `loader.py`.

## Open questions for next iteration

- **Threshold tuning.** The defaults are reasonable starting points but
  haven't been validated against a real spec / procedure pair. Run on
  Eric's actual contract docs and see what level produces the right
  signal-to-noise.
- **Fuzzy-id weight.** The matcher ships using the combiner's 0.5
  fallback weight rather than an explicit entry in `DEFAULT_WEIGHTS`.
  Pick a deliberate weight once the matcher's behaviour is calibrated
  against real data. Tracked in `Process-Tools/REFACTOR.md`.
- **Coverage scoring.** The "X/Y requirements have at least one match"
  summary is binary — every match counts equally. A weighted version
  (a single keyword-overlap hit isn't really "coverage") might be
  worth adding once thresholds are tuned.
- **HTML output.** The xlsx output is the contracted deliverable, but
  an HTML coverage matrix with collapsible evidence panels would be
  much faster to skim during a review.
