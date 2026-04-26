# Changelog

All notable changes to **Compliance Matrix Generator** are recorded
here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).
Pre-1.0 behaviour: minor versions may include breaking CLI / output-shape
changes — they will always be called out under a **Breaking** subhead.

## [Unreleased]

### Added — fuzzy-id matcher (5th matcher)
- `compliance_matrix/matchers/fuzzy_id.py` (~225 lines, pure-stdlib
  Levenshtein implementation — no `rapidfuzz` dependency). Fires on
  section / clause IDs that differ between contract and procedure by
  spelling variation, formatting drift (e.g. `DO-178C Section 6.3.1`
  vs `6.3.1`), or typos.
- `--fuzzy-id-threshold` CLI flag (default 0.85) for the
  Levenshtein-distance cutoff.
- `--no-fuzzy-id` CLI flag to skip the matcher.
- 20 unit tests in `tests/test_fuzzy_id.py` covering the Levenshtein
  primitive, ID normalisation, threshold boundaries, and corpus-level
  matching behaviour. Total suite is now 23 tests.

### Added — shared loader
- `compliance_matrix/loader.py` is now a thin wrapper over
  `process_tools_common.dde_xlsx`. Adding or renaming a DDE column
  is a one-line change in the shared package — both consumer tools
  pick it up.

### Fixed
- `combiner.DEFAULT_WEIGHTS` now includes an explicit `fuzzy_id: 0.95`
  weight (REFACTOR.md item S1). Previously the matcher fired correctly
  but its score multiplied by the `weights.get(..., 0.5)` fallback;
  documentation had advertised 0.60 then 0.95 — neither matched
  reality. Tightened with a regression test in `test_combiner.py`
  that asserts every shipped matcher has an entry in
  `DEFAULT_WEIGHTS`.

### Changed — CLI plumbing
- `--quiet` flag and the quiet-aware logger are now centralised in
  `process_tools_common.cli_helpers` (`add_quiet_flag`, `make_logger`).
  No user-visible behaviour change; the local boilerplate is gone.

### Changed — loader
- `compliance_matrix/loader.py` is further thinned over the shared
  `process_tools_common.dde_xlsx.load_into` helper. Previously
  duplicated the iterate-and-filter loop in both consumer tools;
  centralising it means a future schema change in
  `iter_dde_records` is picked up by both consumers automatically.

### Test count
- Total suite is now **30 tests** (3 smoke + 20 fuzzy-id + 7 new
  combiner regression tests).

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
