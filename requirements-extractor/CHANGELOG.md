# Changelog

All notable changes to **Document Data Extractor** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html). Pre-1.0
behaviour: minor versions may include breaking CLI / config / output-shape
changes — they will always be called out under a **Breaking** subhead.

## [Unreleased]

## [0.6.2] — 2026-04-27

### Added — multi-action requirement detection + decomposition
- New `requirements_extractor/multi_action.py` module.  An additive
  parser post-pass detects single-modal sentences with multiple verb
  phrases (e.g. *"Software engineers shall create unit tests,
  implement CICD Pipelines, and integrate software quality control
  systems."*) and either flags them for reviewer attention or splits
  them into N atomic sub-requirements with hierarchical sub-IDs.
  Per ISO/IEC/IEEE 29148 §5.2.4 (Singular principle) and INCOSE
  *Guide for Writing Requirements*, each requirement should express
  one thought.
- Three modes selected via `extraction.multi_action.mode`:
  - `single` — emit one requirement, source-faithful, byte-identical
    to 0.6.1 output.
  - `flag` (DEFAULT) — emit one requirement with a one-line
    `Multi-action sentence: …` note in the `notes` column.
  - `split` — emit the parent (text preserved) plus N child rows.
    Children carry hierarchical sub-IDs (`REQ-abc12345.1`,
    `REQ-abc12345.2`, …), parent's actor / heading / source-line
    context, and a `parent_id` field linking back to the parent.
- spaCy dependency-parser path with a regex fallback for the
  air-gapped binary; mirrors the offline-fallback architecture from
  `actor_heuristics.py`.
- Shared-verb disambiguation gate: phrases that all share the same
  normalised head verb (e.g. *"shall be available 99.9% … with mean
  time to recovery less than 1 hour"*) are kept as a single
  requirement.  Imperfect heuristic (~80%); flagged on the detection
  record for reviewer surfacing.
- Procedural required-action gate: detection is disabled when
  `force_requirement=True` so multi-action splitting never fragments
  rows in a `Required Action` table (mirrors the 0.6.1 compound
  gate).  See PATCH-0.6.2-NOTES.md for the autonomous design call.
- Five synthetic fixtures under `samples/procedures/multi_action/` and
  their generator — Eric's canonical 3-action case, two-action OR,
  shared-verb compound (negative), 0.6.1 compound + multi-action
  pipeline interaction, and a multi-action sentence inside a
  procedural required-action table (negative).
- 44 new tests in `tests/test_multi_action.py` (pure-helper detection
  rules, all 3 modes per fixture, config-flag wiring + mode
  validation).

### Added — 0.6.1 regression baseline test
- `tests/baselines/procedures_baseline_0_6_1.json` (~70 KB) snapshots
  the 0.6.1 row-level output for every fixture in
  `samples/procedures/` AND `samples/procedures/compound/` (all 16
  fixtures).
- `tests/test_regression_baseline_062.py` (3 tests) re-parses each
  fixture in `single` mode and asserts its row count + every per-row
  column (including `notes`) matches the 0.6.1 baseline byte-for-byte
  — the canary for any unintended drift between 0.6.1 and 0.6.2 in
  source-faithful single-mode operation.

### Configuration
- New `extraction.multi_action` namespace (or flat `multi_action`)
  with three keys:
  - `mode: flag` (default) | `single` | `split`
  - `enabled: true` (default; set false to disable detection
    entirely)
  - `min_actions: 2` (default; only trigger when 2+ verb phrases
    detected)
- Invalid mode values and `min_actions < 2` are rejected with a
  `ValueError` at config-load time.
- The `extraction:` namespace key continues to accept `compound` and
  now also accepts `multi_action`; both can be set together.

### Schema
- `Requirement` dataclass gains a new `parent_id` field (default
  `""`) populated for split-mode sub-requirements only.  Existing
  writers ignore the field; ReqIF export of decomposition relations
  is documented but deferred (separate patch).

### Behaviour preserved (intentionally)
- Default `single` and `enabled: false` modes both produce
  byte-identical row-level output to 0.6.1, including the existing
  `notes` annotations from 0.6.1 compound rows.  Pinned by the new
  regression baseline test.
- All 559 pre-existing tests pass unchanged.

### Known limitations
- Shared-verb heuristic is ~80% accurate; `imperfect` flag on the
  detection record marks ambiguous cases.
- Irregular verb forms (`hold`/`held`, `write`/`wrote`) won't
  normalise to the same lemma.
- Cross-modal sentences (two `shall`/`must` tokens) are explicitly
  rejected by the detection algorithm.
- ReqIF decomposition-relation export is documented in
  PATCH-0.6.2-NOTES.md but not yet implemented.

## [0.6.1] — 2026-04-27

### Added — compound-requirement detection
- New `requirements_extractor/compound.py` module.  An additive parser
  pre-pass detects modal-verb paragraphs ending with `:` followed by a
  bulleted / dashed / numbered / lettered list of conditions, and
  aggregates them into a single compound requirement.  Captures the
  field-gap pattern where a lead-in paragraph (no terminal punctuation,
  ends in `:`) and its conditions (no modal verbs) both fell through
  the 0.6.0 detector and emitted zero requirements.
- Connectors (`and` / `or` / `unless`) inferred from items' trailing
  tokens; rendered as `(all of)`, `(any of)`, or `(unless any of)` in
  the synthetic compound text so reviewers see polarity at a glance.
- `where:` definition-list lead-ins are explicitly excluded — those
  introduce glossary blocks, not condition lists, and are left to the
  legacy per-paragraph walker.
- Five synthetic fixtures under `samples/procedures/compound/` and
  their generator (`generate.py`) — AND list, OR list, mixed
  numbered/dash markers, `where:` negative case, `unless:` exclusion.
- 45 new tests in `tests/test_compound.py` (pure-helper rules +
  end-to-end fixture parses + config-flag wiring).

### Added — regression baseline test
- `tests/baselines/procedures_baseline_0_6_0.json` (60 KB) snapshots
  the 0.6.0 row-level output for every fixture in `samples/procedures/`.
- `tests/test_regression_baseline.py` (3 tests) re-parses each fixture
  and asserts its row count + every per-row column matches the
  baseline byte-for-byte — the canary for any unintended drift in
  the shipping parser.

### Configuration
- New `extraction.compound.enabled` flag (or flat `compound.enabled`).
  Default ON.  Set to `false` in any `--config` or per-doc
  `<stem>.reqx.yaml` to revert compound detection without rebuilding
  the binary.
- The `extraction:` namespace key is accepted at the top level as a
  natural-language wrapper around `compound`; keys other than
  `compound` under `extraction` are rejected with a clear error.

### Behaviour preserved (intentionally)
- Procedural required-action tables (`force_requirement=True`) skip
  compound detection.  Each bullet is already an atomic requirement
  by virtue of the column header; aggregating would *drop*
  requirements rather than capture additional ones.  Documented as
  the autonomous design call in `PATCH-0.6.1-NOTES.md`.

## [0.6.0] — 2026-04-26

### Added — rule-based actor-extraction fallback
- `requirements_extractor/actor_heuristics.py` (~460 lines). Ten
  heuristics, each a pure `str -> List[str]` function with the example
  sentence inline. Each rule is conservative — false positives are
  worse than false negatives because reviewers audit the output xlsx
  and noise costs them time.
- Heuristic catalogue: `_h_by_agent`, `_h_send_to`, `_h_possessive`,
  `_h_compound_subject`, `_h_conditional_subject`, `_h_for_beneficiary`,
  `_h_implicit_passive`, `_h_hyphenated_role`, `_h_between`,
  `_h_appositive`.
- Role-shape probe (`_is_role_phrase`) gates every rule's output: head
  noun in a curated role-noun list (Service, System, Manager, …) OR
  agent-noun morpheme (-er/-or/-ist/-ant/-ent) with Title case OR a
  2–6-letter all-caps acronym.
- Wired into `ActorResolver` via opt-in `use_heuristics=True`
  constructor flag. Order is regex → nlp → rule (highest-confidence
  first; cross-source dedup).
- Default off so existing test fixtures stay green; caller opts in.
- 36 new tests in `tests/test_actor_heuristics.py` — per-rule positive
  and negative tests (false-positive control is the real failure mode),
  end-to-end through `extract_actor_candidates`, three integration
  tests for `ActorResolver(use_heuristics=True)`.

### Added — cross-tool integration test
- `tests/integration/test_extractor_to_compliance_matrix.py` (243 lines)
  exercises the DDE → compliance-matrix path end-to-end.
- `docs/INTEGRATION.md` describes the integration contract.

### Added — DDE → nimbus-skeleton integration test
- `tests/integration/test_extractor_to_nimbus_skeleton.py` (6 tests)
  mirrors the existing `test_extractor_to_compliance_matrix.py` for
  the second downstream consumer. Verifies the five-default-output
  shape, the six-output-with-`--bpmn` shape, manifest content,
  review xlsx well-formedness, and BPMN XML well-formedness.

### Removed (Breaking)
- `requirements_extractor.json_writer` and `requirements_extractor.md_writer`
  compatibility shims have been removed. Their canonical
  implementations have lived in `requirements_extractor.writers_extra`
  for some time; the shims existed only for backward import-path
  compatibility. Importing either module now raises `ImportError`
  with a pointer to the canonical name. **Migration:**
  `from requirements_extractor.writers_extra import write_requirements_json,
  write_requirements_md, requirement_to_dict`.

  Eric confirmed (REFACTOR.md item T1, 2026-04-25) no external scripts
  use the old import paths. The placeholder modules remain on disk
  with `raise ImportError` bodies — they can be physically removed in
  the same commit or a follow-up.

### Fixed
- `actors.load_actors_from_xlsx` and `diff._read_requirements_workbook`
  now close the openpyxl workbook explicitly via try/finally. Linux
  was tolerating the leaked handle (delete-on-last-close); Windows
  raised `PermissionError [WinError 32]` whenever a caller used
  `tempfile.TemporaryDirectory` to manage the input file, which
  surfaced as 7 tests erroring on Windows but passing on Linux. No
  behavioural change beyond releasing the file handle.

### Test count
- Total suite is now **511 tests** (469 from 0.5.0 + 36
  actor-heuristics + 6 nimbus-integration). All 511 green on both
  Linux and Windows after the handle-close fix.

### Open follow-ups (not yet wired)
- CLI flag `--actor-heuristics` (default off) — currently only
  available via Python API.
- GUI checkbox for the same.
- Configurable role-noun whitelist (`_ROLE_HEAD_NOUNS`) once corpus
  feedback shows whether the default list is too tight or too loose.

## [0.5.0] — 2026-04-24

This release captures everything between the original 0.1.0 scaffold and
the current head. The project is now feature-complete against its
internal punch list (the REVIEW.md carryovers list is empty). The two
remaining items — PyInstaller smoke test on Eric's restricted Windows
network, and real Cameo / DOORS ReqIF import validation — both require
hardware / software that the dev sandbox doesn't have. Baseline:
**469 tests passing, 0 failing.**

### Added — input formats
- `.doc` (legacy Word) input via LibreOffice's headless converter.
- `.pdf` input via `pdfplumber`, preserving table structure where the
  PDF was emitted from a structured source.
- Auto-discovery of per-document config side-car files
  (`<spec>.reqx.yaml` next to a `<spec>.docx`).

### Added — output formats and dialects
- **JSON writer** (`requirements.json`) — flat list of requirement
  dicts including the new `context` field.
- **Markdown writer** (`requirements.md`) — human-friendly review table.
  Intentionally omits the source-preview column to keep PR-review
  tables narrow.
- **ReqIF 1.2 writer** (`requirements.reqif`) with three dialect
  variants:
  - `basic` — vendor-neutral, stable_id as LONG-NAME.
  - `cameo` — text preview as LONG-NAME (matches Cameo's import
    conventions).
  - `doors` — adds `ReqIF.ForeignID` + `ReqIF.ChapterName` and a
    SPECIFICATION-TYPE block.
- All emit-formats can be combined: `--emit json,md,reqif` produces
  every shape alongside the xlsx.

### Added — `diff` subcommand
- `document-data-extractor diff <old.xlsx> <new.xlsx>` produces a
  colour-coded third workbook showing **Added / Removed / Changed**
  rows.
- Stable IDs hash `(source_file, primary_actor, text)` — the diff
  matches by that identity so renaming a source file between two runs
  shows up as removed-then-added. The `diff --help` block documents
  this and the README has a dedicated *Diff mode* section with both
  supported workflows.
- Exit code reflects change presence (useful for CI gates around spec
  drift).

### Added — extraction quality
- **NER actor canonicalisation.** When NLP is available, secondary
  actors detected in requirement text are canonicalised against the
  actors list so `the operator` and `Operator` fold to the same entry.
- **Confidence heuristic upgrade.** Rebalanced to give more weight to
  modal keywords appearing inside structured table rows than to the
  same modal in surrounding prose.
- **Cross-source dedup.** When the same requirement text appears
  verbatim in multiple input files (common for boilerplate inherited
  across sub-specs), the dedup orchestration keeps the first occurrence
  and records the dropped sources so you can audit.
- **Procedural-table parser improvements.** Header-aware row detection,
  multi-actor cell support, actor continuation across rows, and bullet
  rows. Stress-tested with `samples/procedures/long_procedure.docx` and
  `mixed_language.docx`.

### Added — review aids
- **Inline source-preview Context column** (REVIEW §3.8). Rightmost
  xlsx column carries up to 280 chars of the surrounding paragraph
  text, with sentence-friendly truncation. Suppressed when the context
  matches the requirement verbatim. Markdown writer omits it
  intentionally; JSON / ReqIF / xlsx all carry it.
- **Smart boilerplate auto-skip** (`auto_boilerplate: true` by
  default). 25 default section titles (Glossary, Acronyms, References,
  Revision History, Document Control, Table of Contents, Approvals,
  Distribution, Sign-offs, Applicable Documents, …) are now skipped
  out of the box. Both section-row title path and a new heading-scope
  skip honour the list. User `titles:` entries layer on top.

### Added — packaging
- `packaging/DocumentDataExtractor.spec` PyInstaller spec that bundles
  spaCy + `en_core_web_sm-3.7.1` + pdfplumber + tkinterdnd2 directly
  into the exe (so the work-network machine doesn't need to download
  the spaCy model at runtime).
- `packaging/build.bat` runs the build.
- `packaging/build-requirements.txt` pins spacy<3.8, pydantic<3,
  pydantic-core<3, thinc<9 (mutually compatible matrix).
- `docs/NLP_BUNDLE_SMOKE_TEST.md` — manual runbook for Windows builds
  including a 7-step **sandbox-side pre-flight checklist** that catches
  failures without needing a real build.

### Added — GUI
- "Getting started" first-run modal (re-accessible from Help menu).
- Hover tooltips on every option control.
- Drag-and-drop input file support (via `tkinterdnd2`).
- `_fit_window_to_content` so the window doesn't open clipped.
- Persistent settings across runs.
- Cancellable runs.

### Added — docs
- `README.md` — full user guide including supported formats, project
  layout, diff mode, config keys, GUI walkthrough.
- `docs/PROJECT_OVERVIEW.md` — re-onboarding doc covering what the
  project is, design decisions worth knowing, and a copy-paste prompt
  block for new Claude sessions.
- `docs/SESSION_STATUS.md` — reverse-chronological session changelog.
- `docs/REVIEW.md`, `docs/FIELD_NOTES.md`, several `docs/PLAN-*.md`
  files (all marked DISCHARGED).
- `samples/sample_config.yaml` documents every config knob.

### Changed
- Package import name remains `requirements_extractor` for compatibility;
  surface name is **Document Data Extractor**, CLI entry point is
  `document-data-extractor`.
- PDF page-text extraction is suppressed on any page where tables were
  found (no more double-emit of requirements that appear both in a
  table and in surrounding prose).
- Dataclass mutable defaults reworked to use `field(default_factory=...)`.

### Fixed
- PDF double-emit on tabular pages (regression test
  `TestPdfNoDoubleEmit`).
- Diff filename-sensitivity — now documented at the help level rather
  than discovered by surprise.
- GUI window initial-geometry clipping on first run.

### Internal
- Extraction orchestration split into `_orchestration.py`.
- Procedural-table subsystem extracted to `procedural.py`.
- Keywords loader split out of `config.py`.
- 17 modules under `requirements_extractor/` + 469 tests under `tests/`.
- `.gitignore` covers `__pycache__/`, `.venv/`, PyInstaller build
  artefacts, IDE scratch, and root-level scratch outputs.

## [0.1.0] — Initial scaffold

- Tkinter GUI + CLI entry points.
- `.docx` parser with section / table / heading awareness.
- xlsx output with stable `REQ-<8hex>` IDs hashed from
  `(source_file, primary_actor, text)`.
- Hard / Soft requirement classification via modal keywords.
- Polarity tagging (Positive / Negative) for shall-not etc.
- Sentence splitter, dry-run mode, basic actors auto-detection.
- Persistent GUI settings.

[0.6.0]: #060--2026-04-26
[0.5.0]: #050--2026-04-24
[0.1.0]: #010--initial-scaffold
