# Changelog

All notable changes to **process-tools-common** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — shared CLI helpers
- `process_tools_common.cli_helpers` module with:
  - `add_quiet_flag(parser)` — registers the standard `-q/--quiet`
    flag on an argparse parser. Both consumer tools (compliance-matrix,
    nimbus-skeleton) now use this instead of declaring `--quiet`
    independently.
  - `make_logger(quiet)` — returns a `print`-shaped callable that
    no-ops when `quiet=True`. Replaces the
    `log = (lambda *a, **kw: None) if quiet else print` pattern that
    was duplicated in both tool CLIs.
- 9 new tests in `tests/test_cli_helpers.py`.

### Added — dde_xlsx loader helpers
- `load_into(path, row_factory, fields=None)` — projects each DDE row
  through a caller-supplied factory (typically a dataclass
  constructor). Both consumer loaders are now ~5-line wrappers
  around this.
- `find_sidecar(input_path, *, suffix, extension=".xlsx")` — convention
  helper for "look up the actors xlsx beside the input file."
- 8 new tests in `tests/test_helpers.py`.

### Test count
- Total suite is now **26 tests** (9 from 0.1.0 + 9 cli_helpers
  + 8 dde_xlsx helpers).

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
