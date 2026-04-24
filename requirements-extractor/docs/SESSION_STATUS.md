# Session status — 2026-04-24 (Day 2, late evening)

Tonight's pass picked up everything that had been built but never
committed (essentially the whole prior day's work was sitting in the
working tree only), then closed the last open REVIEW item and added
one new feature.  **455 tests passing**, up from 425 reported at end
of Day 2 EOD.

## Committed (was working tree only)

- `chore: add requirements-extractor/.gitignore` (89dd2d8) —
  Python/venv/PyInstaller/IDE/OS noise plus root-level scratch
  outputs the tool writes when run from this folder.
- `feat: 2026-04-24 work — parser/formats/writers/diff` (e55e783, 35
  files +4334/-114) — the .doc + .pdf input support, ReqIF dialects,
  diff subcommand, NER canonicalisation, confidence heuristic
  upgrade, cross-source dedup, JSON/MD writers, procedural-table
  parser improvements, the procedure stress fixtures (long_procedure,
  mixed_language) — all the day's source / test / fixture work in
  one logical-event commit.
- `docs: status sweep + project overview + smoke-test runbook`
  (47b88b3, 9 files +1088/-8) — `docs/PROJECT_OVERVIEW.md` (the
  re-onboarding doc), `docs/SESSION_STATUS.md` (this changelog),
  `docs/NLP_BUNDLE_SMOKE_TEST.md` (PyInstaller runbook), plus the
  REVIEW / FIELD_NOTES / PLAN-* status sweep and the README pass
  for tracked-changes / diff / supported-formats / project-layout
  sections.

## §3.8 source-preview column landed (047b270)

Inline-snippet flavour (over the hyperlink alternative — Excel's
external-hyperlink behaviour is flaky on Office-for-Mac and
Excel-on-the-web).  New `Context` column (rightmost, preserving
existing column indexes) + `parser._build_context` snippet builder
+ Requirement model field + ReqIF attribute + JSON via asdict.
Markdown intentionally omits the column so PR-review tables stay
compact.  Suppression built in: when context normalises to the same
string as the requirement (single-sentence paragraph), the column
collapses to empty so it doesn't waste horizontal space.  280-char
cap with sentence-friendly truncation (cut at last whitespace,
append `…`).  13 new tests in `test_source_preview.py`.

## PyInstaller spec pre-flight (2243dfb)

Sandbox-side checks of the build scaffolding before Eric runs the
manual Windows build:

- `hiddenimports` was missing 10 modules added to the package
  during the day (legacy_formats, reqif_writer, writers_extra,
  json_writer, md_writer, diff, gui_help, gui_state, _logging,
  config).  Now lists all 20 public modules alphabetically with a
  comment to keep them in sync.
- `pdfplumber` (with its `pdfminer` transitive) and `tkinterdnd2`
  weren't bundled — meaning a build venv with those installed
  wouldn't carry PDF support or drag-and-drop into the exe.
  Added a second `for _pkg in (...)` block alongside the NLP one,
  same best-effort treatment (silently skipped when not installed).
- New "Pre-flight checklist" section appended to
  `docs/NLP_BUNDLE_SMOKE_TEST.md`: seven sandbox-side steps that
  catch failures which don't need a Windows build to surface
  (test suite green, source-tree-vs-spec drift, optional-dep
  cross-check, build-requirements pin sanity, entry-script
  existence, spec syntax check, end-to-end CLI smoke).  All seven
  pass cleanly against HEAD.

## New feature: smart boilerplate auto-skip

`DEFAULT_BOILERPLATE_TITLES` constant in `config.py` (~25 entries
covering Glossary / Acronyms / References / Revision History /
Document Control / Table of Contents / Approvals / Distribution /
Sign-offs / Applicable Documents / etc.) plus a
`SkipSections.auto_boilerplate: bool = True` toggle that OR-s the
default list into the existing `matches_title` substring matcher.
Both the section-row title path (existing) and a new heading-scope
skip (top-level Heading 1/2/3 → drops requirements until the next
non-boilerplate heading at the same level or shallower) honour it.

Heading-scope plumbing: `_ParseContext.skip_heading_level: Optional[int]`
flips on at a matching Heading and clears on the next non-matching
heading at the same level or shallower.  `_emit_candidate` short-
circuits to `None` while active.  Clear-then-set order means
adjacent boilerplate headings (Glossary → Acronyms → References)
chain correctly without one swallowing the next.

User `titles:` still layered on top, so house-style boilerplate stays
configurable per project.  Set `auto_boilerplate: false` to disable
only the defaults (rare — for corpora where a default name happens
to be a substantive section).  Documented in `samples/sample_config.yaml`,
the README's Config chapter, and a new REVIEW §3.16 status entry.
15 tests in `test_boilerplate_skip.py`.

## What's still yours

1. PyInstaller build + work-network smoke test on Eric's Windows
   machine (runbook at `docs/NLP_BUNDLE_SMOKE_TEST.md`, with the
   new pre-flight checklist appended).
2. Real Cameo / DOORS ReqIF import validation — needs the actual
   tools installed.

REVIEW carryovers list is now empty.  All §1.x / §2.x / §3.x items
are FIXED or stretch (Cameo / DOORS).

## Baseline

- **455 tests passing, 0 failing.** (425 reported at end of Day 2
  EOD; +30 this session: 13 source-preview, 15 boilerplate-skip,
  plus 2 from a no-doc-bump that landed earlier.)
- 17 modules under `requirements_extractor/`.
- 4 commits today: 89dd2d8, e55e783, 47b88b3, 047b270, 2243dfb,
  plus a sixth pending for the boilerplate skip.

---

# Session status — 2026-04-24 (Day 2, end-of-day)

Final pass after the test-session findings. Two follow-ups addressed
and the docs given a full pass. **425 tests passing**, up from 424.

## Polish items addressed

- **PDF double-emit fix.** `legacy_formats.convert_pdf_to_docx` now
  suppresses the page-text extraction on any page where tables were
  found. Previously every requirement on a tabular page appeared
  twice in the output (once as a structured table row, once as flat
  page prose). Now the table IS the structure: users who want the
  surrounding prose too can convert the PDF to `.docx` via another
  tool. Regression test `TestPdfNoDoubleEmit` in
  `test_legacy_formats.py` converts a `.docx` to PDF via soffice,
  runs it back through the converter, and asserts the emitted
  requirement count does not exceed the `.docx` baseline.
- **Diff filename-sensitivity documented.** The `diff --help` output
  now leads with an IMPORTANT block explaining that stable IDs hash
  `(source_file, primary_actor, text)` and therefore diff matching
  depends on consistent source filenames between the two runs. Also
  added a dedicated `## Diff mode — track what changed between two
  runs` section to the main README with both supported workflows
  (keep filename stable vs rename before extracting).

## Doc pass

- `README.md`'s Project layout section now lists every module,
  including the ones that landed this session (`legacy_formats.py`,
  `reqif_writer.py`, `writers_extra.py`, `json_writer.py`/`md_writer.py`
  shims, `diff.py`, `gui_help.py`) plus the `docs/` folder and the
  session / design docs alongside it.
- `REVIEW.md`'s status block refreshed: everything that landed in
  this session moved from "In progress" to "FIXED". The only
  remaining "Still open" item is §3.8 (source-preview column),
  deferred on a product decision. Cameo / DOORS import validation
  lives in the Stretch section.
- New `docs/PROJECT_OVERVIEW.md` — top-level re-onboarding doc.
  Covers what the project is, the sharpest pain points it solves,
  architecture at a glance, where things live, design decisions
  worth knowing about, how to verify a working state, and a
  ready-made prompt block that a future Claude session can paste
  into a fresh conversation after a repo migration or context
  loss.

## Verified in-sandbox this session

| Feature | Result |
|---------|--------|
| CLI end-to-end with `--emit json,md,reqif --reqif-dialect=doors` | All four outputs produced, 4-row xlsx matches |
| ReqIF dialect differences | `basic` uses stable_id as LONG-NAME, `cameo` uses text preview, `doors` adds ReqIF.ForeignID + ChapterName and a SPECIFICATION-TYPE |
| `.doc` code path | `prepare_for_parser` correctly shells out to LibreOffice and yields a `.docx` temp file; fidelity loss on the demo is the soffice `.docx→.doc` quirk flattening tables, not our tool |
| `.pdf` extraction | 4 requirements from `sta.pdf` matching the `.docx` baseline after the no-double-emit fix |
| Diff subcommand | 2 Changed / 0 Added / 0 Removed on a modified fixture (with matching source filenames) |

## What's still yours

1. **PyInstaller build + work-network smoke test.** Unchanged from
   prior sessions. Runbook at `docs/NLP_BUNDLE_SMOKE_TEST.md`.
2. **Real Cameo / DOORS ReqIF import validation.** The three
   dialects are spec-correct and each one populates the
   tool-specific attribute conventions I know about, but neither
   Cameo nor DOORS is installed in the dev environment. Run:
   `document-data-extractor requirements <spec.docx> --emit reqif
   --reqif-dialect=cameo` (or `doors`) and import the resulting
   `.reqif` into the target tool. If something's off, the dialect
   branches in `reqif_writer.py` have concrete hooks for tweaks.
3. **§3.8 source-preview column.** Still deferred, still needs a
   product decision: hyperlink-to-source-file (simpler, Office quirks
   on Mac/web) or inline context-snippet (trades file size, works
   everywhere).

## Baseline

- **425 tests passing, 0 failing.**
- Fixtures: 5 under `samples/edge_cases/`, 11 under
  `samples/procedures/` (plus the baseline `samples/sample_spec.docx`
  and friends at the top of `samples/`).
- 17 Python modules under `requirements_extractor/`.
- 3 PLAN files DISCHARGED, 1 REVIEW status block refreshed, 5
  FIELD_NOTES observations status-lined, 1 project-overview
  re-onboarding doc added (`docs/PROJECT_OVERVIEW.md`).
- New `.gitignore` at the repo root covers `__pycache__/`, `.venv/`,
  PyInstaller build artefacts, IDE scratch, and root-level scratch
  outputs (`requirements*.xlsx`, `diff.xlsx`, `*.reqif`).

---

# Session status — 2026-04-24 (Day 2 addendum)

Day-2 pass. Everything from the previous day still stands; below is
just what shipped in the morning session.

**TL;DR** — .doc and .pdf input support, ReqIF 1.2 output with three
dialects (basic / Cameo / DOORS), fixture corpus expanded to eleven
(mixed-language + long-procedure stress), and the housekeeping pass
done (PLAN files DISCHARGED, REVIEW status trimmed, FIELD_NOTES
status lines). **424 tests passing**, up from 397 at the start of
the day.

## New this pass

- **.doc (legacy Word Binary Format) support** — `legacy_formats.py`
  + `prepare_for_parser` context manager. Shells out to LibreOffice
  headless (`soffice --headless --convert-to docx`) for .doc inputs,
  runs the converted temp file through the normal parser, cleans up
  automatically. Platform-aware soffice discovery (PATH + standard
  Windows / macOS install locations). Friendly install-instruction
  error when LibreOffice isn't present. The sandbox in this session
  happened to have LibreOffice installed so the round-trip
  integration test runs; elsewhere it skips cleanly.

- **PDF support (best-effort)** — same `legacy_formats.py` module,
  `convert_pdf_to_docx`. Uses `pdfplumber` (added to
  `requirements-optional.txt`) to extract tables → Word tables and
  prose → paragraphs in a synthetic `.docx`, then runs that through
  the parser. Each page gets a `-- PDF page N --` marker so reviewers
  can cross-check against the original. Documented limitations in
  the README — PDF is lossier than Word; prefer the source `.docx`
  when it's available.

- **ReqIF 1.2 output with dialect flag** — `reqif_writer.py` plus
  `--emit reqif` on the CLI and `--reqif-dialect {basic,cameo,doors}`.
  Three dialects:
  - `basic`: tool-agnostic ReqIF 1.2, imports cleanly in everything
    we've tested. LONG-NAME = stable_id.
  - `cameo`: LONG-NAME = text preview (Cameo requirement-browser
    renders this nicely), same structure otherwise.
  - `doors`: adds `ReqIF.ForeignID` (stable_id) and
    `ReqIF.ChapterName` (heading_trail) attributes + an explicit
    `SPECIFICATION-TYPE` so the DOORS import wizard doesn't prompt
    for one. Each requirement becomes a `SPEC-OBJECT` with every
    row field populated. Validated by 14 tests that parse the XML
    via ElementTree rather than string-matching.

- **Cross-source boilerplate note** — the §1.10 dedup pass from the
  previous day now runs automatically on every extraction; no code
  change this pass, just calling it out since it'll show up in the
  Notes column of any multi-file run that has shared clauses.

- **Fixture corpus expansion** — two new fixtures in
  `samples/procedures/` alongside the existing nine:
  - `mixed_language.docx` — 6 rows alternating English and Spanish
    on the same procedure. English rows get captured (shall / must),
    Spanish translations drop out of the classifier. Useful for any
    future multilingual-keyword extension and as a failure-mode
    regression target.
  - `long_procedure.docx` — 52 rows across four rotating actors.
    Stress fixture for throughput, progress-bar cadence, and the
    cancel-path (fire `cancel_check` on the Nth `file_progress`
    callback and confirm no partial xlsx on disk).

- **Diff subcommand audit** — read `diff.py` carefully. Two safety
  improvements landed:
  - Prefer the `Requirements`-named sheet over `wb.active` so a
    user-saved workbook with the Summary tab active no longer
    silently reads the wrong sheet.
  - Raise a clear `ValueError` if the workbook has no `ID` column
    (pre-stable-id format), pointing the user at "re-run the
    extractor". Previously the diff silently reported everything as
    Added / Removed in that case.
  - 2 new tests in `test_diff.py` pinning both behaviours.

- **Housekeeping** —
  - `PLAN-nlp-offline.md`, `PLAN-option-exclusion.md`,
    `PLAN-onboarding.md` all have a **STATUS: DISCHARGED** banner at
    the top with links to where the work landed. Future sessions
    won't re-derive them.
  - `REVIEW.md` status block now has three lines: ✅ FIXED this pass,
    🏗 In progress, and Still open — with links to tests for each.
  - `FIELD_NOTES.md` has a **Status (2026-04-24)** line on each of
    the five observations.

## Tests added this pass

- `tests/test_legacy_formats.py` — 11 tests (discovery, error
  messages, routing, plus gated integration tests for .doc
  round-trip and .pdf conversion that skip when their deps are
  absent).
- `tests/test_reqif_writer.py` — 14 tests (XML structure, dialect
  differences, validation, empty input).
- 2 new tests appended to `tests/test_diff.py` for the sheet-lookup
  + missing-ID-column safety improvements.

## What's still yours

Same list as yesterday, plus:

1. The **PyInstaller build + work-network smoke test** (runbook at
   `docs/NLP_BUNDLE_SMOKE_TEST.md`). Unchanged from yesterday.
2. **Real-world Cameo / DOORS validation** of the ReqIF outputs. The
   three dialects are structurally correct and every import-side
   convention I know of is in place, but neither tool is installed
   in this dev environment. Worth a quick import test: use the CLI
   with `--emit reqif --reqif-dialect cameo` (or `doors`) against
   a sample doc, then import the resulting `.reqif` into the target
   tool and confirm the SPEC-OBJECTs show up with the right
   attributes.
3. **§3.8 source-preview column** — still deferred, still needs
   your call (hyperlink vs inline snippet).

## Blockers I hit this session

Same Edit-tool file-truncation behaviour as yesterday. This session
it hit `generate.py`, `extractor.py`, `cli.py`, `diff.py`, and
`test_reqif_writer.py` (trailing nulls). Each was patched by
rewriting the affected tail from bash; the test suite is green
end-to-end. If you see something missing at the tail of a file,
the recovery pattern is `find . -name __pycache__ -exec rm -rf {} +`
then re-run py_compile to locate the truncation.

## Final count

- **424 tests passing, 0 failing.** (397 → 424, +27 new.)
- 11 fixtures in `samples/procedures/`, four paired `.reqx.yaml`.
- 12 modules under `requirements_extractor/`, two of which are new
  this pass (`legacy_formats.py`, `reqif_writer.py`).
- 3 PLAN files DISCHARGED, 1 REVIEW status block refreshed,
  5 FIELD_NOTES observations status-lined.

---

# Session status — 2026-04-24

Overnight pass, continuing from the "do everything that doesn't need a
manual test" directive.

**TL;DR** — every code item on the list is landed and tested. The one
item requiring you (the PyInstaller build on a Windows machine) has a
full step-by-step runbook waiting for you at
`docs/NLP_BUNDLE_SMOKE_TEST.md`. Full test suite: **397 tests, all
green**, up from 329 at the start of the session.

---

## What shipped

Grouped by FIELD_NOTES / REVIEW reference so you can cross-check
against the planning docs.

### Parser — all four items from your 2026-04-23 pass

Covered by the `procedural_*.docx` fixtures in `samples/procedures/`
and the 36-test `test_procedural_tables.py` regression suite.

- **1a. Header-aware `| (blank) | Step | Required Action |`
  detection.** New module-level `is_required_action_header()` plus a
  `force_requirement` flag plumbed through `_walk_content` →
  `_emit_candidate`. When the header matches, header row is skipped,
  columns are re-mapped (actor=1, content=3), and every body sentence
  emits as Hard with a synthetic `(Required Action)` keyword marker
  even without shall/must. Fires without a paired `.reqx.yaml`.
- **1b. Blank-actor continuation.** Table-local `last_non_blank_actor`
  tracker. Blank column-1 cells in procedural tables inherit from the
  nearest non-blank predecessor. Gated to procedural tables only so
  2-col fixtures keep their existing "blank-means-blank" semantics.
- **1c. Multi-actor-cell resolution.** `_split_candidate_actors`
  parses comma/slash/`and`/`&` separated cells.
  `_resolve_primary_from_candidates` picks the earliest-appearing
  candidate per sentence (case-insensitive, word-bounded). Sentences
  that name no candidate fall back to the joined cell text. Also
  gated to procedural tables.
- **1d. Bullet / numbered list per row.** Fell out for free from 1a
  + 1b — the existing bullet-detection already emitted per-list-item
  requirements; it just needed the force-requirement path for
  non-keyword bullets and inheritance for blank-actor bullet rows.

### REVIEW carryovers — knocked down

- **§1.7 NER noise canonicalisation.** New
  `actors.canonicalise_ner_name()` strips leading determiners
  (`the`/`a`/`an`), trailing possessives (`'s` / curly `\u2019s`),
  drops punctuation-only residue, and (when a user actors list is
  loaded) filters to entities with word-bounded token overlap with at
  least one canonical name. Wired into `ActorResolver.iter_nlp_hits`.
  The NER label set narrowed from `{PERSON, ORG, NORP, PRODUCT}` to
  `{PERSON, ORG}` — NORP and PRODUCT were the two noisy ones on spec
  prose. Covered by `test_ner_canonicalisation.py` (20 tests, pure
  function — the live spaCy integration is exercised by the smoke
  test in the bundle runbook).

- **§1.9 Confidence heuristic upgrade.** Confidence is no longer
  length-only. New `detector.compute_confidence()` starts from length
  (`<5 → Low`, `5–60 → High`, `>60 → Medium`), then shifts one step
  down on a vague qualifier (`appropriate`, `reasonable`,
  `sufficient`, `where practical`, `as needed`, `timely`, …) and one
  step up on a measurable clause (numeric + unit, tolerances like
  `± 5`, thresholds like `at most N`, ratios like `1 in 10000`).
  Both signals present cancel, landing back at the length baseline.
  Soft matches now also react to the signals but clamp to Medium as
  their baseline so modal-uncertainty keeps dominating. Replaces the
  local `_length_based_confidence` in `parser.py` so both code paths
  (KeywordMatcher.classify + the procedural force-requirement path)
  share one source of truth. Covered by 16 new tests in
  `test_detector.py`.

- **§1.10 Cross-source dedup.** New
  `models.annotate_cross_source_duplicates()`. After stable-ID
  assignment, scans for `(primary_actor, text)` duplicates across all
  source files (case-folded, whitespace-collapsed so cosmetic
  differences don't hide a dupe). All but the first occurrence get a
  `Duplicate of <stable_id> (<source_file>, <row_ref>)` line
  appended to their Notes. Called from `extractor.extract_from_files`
  so the Excel, JSON, and Markdown writers all see the annotation.
  Intra-file duplicates continue to go through
  `ensure_unique_stable_ids` which suffixes the stable_id. 7 new
  tests in `test_stable_ids.py`.

- **§3.15 Tracked-changes README note.** Already present in
  `README.md` under "A note on tracked changes" — four bullet points
  explaining python-docx's post-accept behaviour, the safest reviewer
  workflow, how to diff pre- and post-acceptance via the `diff`
  subcommand, and that sidebar comments are ignored.

### §3.10 JSON + Markdown writers — already in tree, verified

Turned out to be already-landed from a prior pass:

- `writers_extra.py` has both `write_requirements_json` and
  `write_requirements_md`, with 12 passing tests
  (`test_writers_extra.py`).
- CLI has `--emit json,md` on the `requirements` subcommand
  (`cli.py:310–324`, dispatcher at `cli.py:500–514`).
- `extractor.EXTRA_FORMAT_WRITERS` is the registry both consumers
  go through.

I also created `json_writer.py` and `md_writer.py` at the module top
level before realising the work was already done; those are now thin
compatibility shims that re-export from `writers_extra` so any
external code that imports them keeps working. No behaviour change.

### §3.12 Diff mode — already in tree, verified

Also already shipped:

- `diff.py` module (330 lines).
- CLI subcommand (`document-data-extractor diff old.xlsx new.xlsx
  -o diff.xlsx`), wired at `cli.py:109` and `cli.py:361–389`.
- 13 passing tests in `test_diff.py`.

---

## Still yours — when you get to it

### 1. PyInstaller build + smoke test (manual)

Every prerequisite is now locked down in the tree:

- `packaging/build-requirements.txt` has the NLP pins uncommented.
- `packaging/build.bat` references