# Changelog

All notable changes to **Compliance Matrix Generator** are recorded
here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).
Pre-1.0 behaviour: minor versions may include breaking CLI / output-shape
changes — they will always be called out under a **Breaking** subhead.

## [0.1.0] — 2026-04-24

Initial scaffold. End-to-end pipeline operational, 3 smoke tests
passing.

### Added — pipeline
- DDE xlsx loader for both contract and procedure sides, matching
  columns by header name (not position). Loader is a thin wrapper
  over `process_tools_common.dde_xlsx` so future DDE schema changes
  only need one update.
- Four matchers running in parallel:
  - `explicit_id` — regex for cited section / clause IDs in
    requirement text (e.g. `IAW [DO-178C §6.3.1]`, `per Section
    4.2.2`). Highest signal, lowest noise.
  - `manual_mapping` — operator-curated yaml/csv lookup. Score is
    fixed at 1.0; unknown contract / procedure IDs in the mapping
    are silently dropped.
  - `similarity` — TF-IDF cosine, pure-stdlib (no scikit-learn /
    numpy dependency). IDF computed across the union corpus so
    both sides share term weights.
  - `keyword_overlap` — Jaccard token intersection / union, with a
    small built-in stopword list. Default threshold 0.15.
- Combiner that takes the per-matcher scores, applies default
  weights (explicit_id=1.0, manual_mapping=1.0, similarity=0.85,
  keyword_overlap=0.65), and aggregates the **maximum** weighted
  score per (contract, procedure) pair. Every matcher's evidence
  string is preserved on the output's Detail sheet.

### Added — output (xlsx with three sheets)
- **Matrix** — contract requirements down rows, procedure clauses
  across columns, cells carry rounded combined score with colour
  gradient (white → yellow → green). Frozen panes keep IDs and
  requirement text visible.
- **Detail** — one row per linked pair sorted by descending score.
  Carries contract text, clause text, score, list of matchers that
  fired, and concatenated evidence strings.
- **Gaps** — side-by-side: requirements with zero matches and
  clauses with zero matches.

### Added — CLI
- `compliance-matrix --contract C.xlsx --procedure P.xlsx -o out.xlsx`
  with optional `--mapping`, `--similarity-threshold`,
  `--keyword-threshold`, and `--no-*` skip flags per matcher.
- Coverage summary at the end (`X/Y requirements have at least one
  procedure match`).

### Added — manual mapping format
- YAML shape: `REQ-AB12: [PROC-9F33, PROC-104A]`.
- CSV shape: `contract_id,procedure_id,note` (header optional).
- Auto-detected by file extension (`.yaml` / `.yml` / `.csv`).

[0.1.0]: #010--2026-04-24
