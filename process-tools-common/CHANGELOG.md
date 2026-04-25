# Changelog

All notable changes to **process-tools-common** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-24

Initial extraction. 9 tests passing.

### Added
- `process_tools_common.dde_xlsx` module with:
  - `HEADER_MAP` — canonical DDE column-name → attribute-name table.
    Adding a new DDE column is a one-line addition here that both
    consumer tools (compliance-matrix, nimbus-skeleton) pick up
    automatically.
  - `iter_dde_records(path)` — yields one dict per requirement row
    of a DDE xlsx workbook, matching columns by header **name** (not
    position) so future DDE column reorders don't break consumers.
  - `iter_actor_records(path)` / `load_actor_aliases(path)` — load
    the DDE actors workbook into `{canonical: [aliases]}`. Returns
    empty for non-actors-shaped workbooks rather than raising.
  - `normalise_header(value)` — case + whitespace tolerant header
    comparison.
- 9 unit tests covering header-name matching tolerance, required-column
  validation, empty-row skipping, and the silent fallback for
  non-actors workbooks.

### Internal
- Both consumer tools use a small `sys.path` bootstrap in their
  `loader.py` to import the shared package without requiring
  pip-installation. Once any of the three tools picks up
  `pyproject.toml`, the others can declare `process-tools-common`
  as an editable dependency and the bootstrap can go away.

[0.1.0]: #010--2026-04-24
