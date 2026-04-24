# Project overview and re-onboarding guide

This document exists to bring someone — a new teammate, future-Eric
after a long break, or a fresh Claude session after a repo migration —
back up to speed on the project without having to re-derive everything
from the code. It describes what the tool does, how the code is
organised, where to look for what, and how to verify the project is in
a working state. The last section is a **ready-made prompt** that can
be pasted into a new Claude conversation to get the assistant up to
speed immediately.

---

## What this project is

`requirements-extractor` (surface name: **Document Data Extractor**) is
a Python tool that reads Word specification documents and pulls
structured requirement data out of them. It has two primary extraction
modes:

- **Requirements mode.** Reads one or more `.docx` files and emits a
  row-per-requirement `.xlsx` workbook. Each row carries the source
  file, heading trail, table position, primary actor, any secondary
  actors referenced, the requirement text itself, its type (Hard /
  Soft based on modal keywords), polarity (Positive / Negative for
  shall-not etc.), confidence, and a stable `REQ-<8hex>` identifier.
  Optional additional outputs alongside the workbook: a hierarchical
  statement-set CSV, JSON, Markdown, and ReqIF 1.2 (with dialect
  variants for Cameo and DOORS). `.doc` and `.pdf` inputs are
  converted to `.docx` at runtime via LibreOffice and pdfplumber
  respectively.

- **Actors mode.** Skips requirement detection, instead harvesting a
  canonical actors list from the input corpus. Produces an `.xlsx`
  with an Actor / Aliases shape that can be fed back into a subsequent
  requirements run via `--actors`.

There's also a `diff` subcommand that compares two extractor-produced
workbooks and emits a colour-coded third workbook showing Added /
Removed / Changed rows. It's the tool's native change-tracking
surface.

The codebase ships both a subcommand-style CLI
(`document-data-extractor requirements …` / `actors …` / `diff …`) and
a Tkinter GUI. Both surfaces expose the same extraction options plus
convenience features (drag-and-drop inputs, dry-run mode, actors
template, persistent settings, hover-tooltips).

---

## The sharpest pain points the project solves

Understanding *why* the code looks the way it does is easier if you
know which field problems drove each design decision. The most
load-bearing pains:

1. **Work-network NLP blocker.** Eric's target machine can't install
   spaCy or download its English model through the network's package
   path. Without NLP the actor-identification accuracy collapses. Fix:
   bundle spaCy + `en_core_web_sm` 3.7.1 into a PyInstaller exe so the
   tool works fully offline after a one-time distribution.
   (`PLAN-nlp-offline.md`, `packaging/`, `docs/NLP_BUNDLE_SMOKE_TEST.md`.)

2. **Real docs have tables the default detector won't recognise.** A
   common shape is a 3-column procedural table with a blank column-1
   header, `Step` in column 2, and `Required Action` in column 3.
   Every body row is a requirement by virtue of that header, even
   when the sentence has no shall/must keyword. Fix: header-aware
   detection in `parser.is_required_action_header`, a
   `force_requirement` path that bypasses the keyword gate when the
   table signal fires, blank-actor inheritance within the table, and
   multi-actor cell resolution from sentence subject.
   (`FIELD_NOTES.md` §4, `samples/procedures/procedural_*.docx`.)

3. **Reviewers need to see what changed between doc versions.** A
   plain text diff of the `.xlsx` files is useless. Fix: the `diff`
   subcommand matches rows by stable ID (and by `(source_file,
   row_ref)` as a secondary for text edits at the same position), then
   colour-codes a third workbook. The stable ID scheme is
   deliberately scoped to `(source_file, primary_actor, text)` so
   cosmetic upstream edits don't churn IDs. (`diff.py`, `models.py`
   stable-ID section.)

4. **Non-technical users need a tool that doesn't bleed context.**
   Hence the GUI with its first-run modal, tooltips, persistent
   settings, and hard-disabled option combinations in actors mode.
   (`gui.py`, `gui_help.py`, `gui_state.py`.)

---

## Architecture at a glance

Data flows through roughly five stages:

```
.docx / .doc / .pdf
      ↓
   legacy_formats.prepare_for_parser   (only if .doc / .pdf — else passthrough)
      ↓
   parser.parse_docx_events            (walks the doc, emits an event stream)
      ↓
   detector.KeywordMatcher             (classifies sentences as Hard / Soft)
   actors.ActorResolver                (resolves primary + secondary actors)
      ↓
   models.Requirement                  (one object per captured row)
      ↓
   models.ensure_unique_stable_ids     (collision suffixing)
   models.annotate_cross_source_duplicates  (cross-file dedup note)
      ↓
   writer.write_requirements           (primary .xlsx)
   writers_extra.write_requirements_json / _md  (optional --emit)
   reqif_writer.write_requirements_reqif        (optional --emit reqif)
   statement_set.write_statement_set            (optional --statement-set)
```

The `extractor.extract_from_files` function is the orchestrator that
glues all of this together. Higher-level entry points (`cli.py` and
`gui.py`) call it with user-supplied options.

A parallel actors-mode pipeline lives in `actor_scan.py`; it reuses
the parser but drops the detector and writes a different output
shape.

### Event stream rationale

The parser doesn't emit `Requirement` objects directly — it emits a
mixed stream of `HeadingEvent`, `SectionRowEvent`, and
`RequirementEvent` values. This matters because the statement-set CSV
exporter needs structural context (where did this requirement sit in
the heading hierarchy?) that a flat requirement list doesn't carry.
The Excel writer filters the stream down to `RequirementEvent` and
doesn't care about the rest; the statement-set exporter consumes the
whole thing.

---

## Where things live

| Area | Primary file(s) | Tests |
|------|-----------------|-------|
| Input routing (`.docx` / `.doc` / `.pdf`) | `legacy_formats.py` | `test_legacy_formats.py` |
| Parsing (walker, event stream, procedural-table detection) | `parser.py` | `test_parser.py`, `test_procedural_tables.py` |
| Classification (Hard / Soft / confidence) | `detector.py` | `test_detector.py` |
| Actor resolution (regex + NLP + NER canonicalisation) | `actors.py` | `test_encapsulation.py`, `test_ner_canonicalisation.py` |
| Stable IDs + cross-source dedup | `models.py` | `test_stable_ids.py` |
| Config (per-run and per-doc YAML) | `config.py` | `test_config.py` |
| Primary output (`.xlsx`) | `writer.py` | covered via `test_stable_ids.py`, end-to-end tests |
| Extra outputs (JSON, Markdown) | `writers_extra.py` + shims in `json_writer.py` / `md_writer.py` | `test_writers_extra.py` |
| ReqIF output (with dialects) | `reqif_writer.py` | `test_reqif_writer.py` |
| Statement-set CSV | `statement_set.py` | `test_logging_and_trail.py` |
| Diff mode | `diff.py` | `test_diff.py` |
| Orchestration | `extractor.py` | `test_extractor_cancel.py`, `test_batch_improvements.py` |
| Shared orchestration helpers | `_orchestration.py` | `test_orchestration.py` |
| CLI | `cli.py`, `extract.py` (shim) | `test_cli.py`, `test_cli_refactors.py` |
| GUI | `gui.py`, `gui_help.py`, `gui_state.py` | `test_gui_state.py` |
| Actors-mode scanner | `actor_scan.py` | `test_actor_scan.py` |
| Logging | `_logging.py` | `test_logging_and_trail.py` |

Fixtures live under `samples/`:

- `samples/edge_cases/` — 5 synthetic `.docx` files for parser/config
  edge cases (nested tables, alphanumeric section prefixes,
  boilerplate skip, wide 4-col tables, noise-prose filters).
- `samples/procedures/` — 11 synthetic `.docx` files for actor-ID and
  procedural-table failure modes. Four of these are the 3-column
  `| | Step | Required Action |` shape that drove the parser
  enhancements in FIELD_NOTES §4.
- `samples/sample_spec.docx` — the original baseline used in some
  end-to-end tests.

Each fixture folder has its own README describing what every file
exercises. Fixture generators are in `generate.py` at each folder.

---

## Design decisions worth knowing about

These all have rationale written down in the PLAN or REVIEW docs;
skimming them saves time if you're evaluating a change.

1. **Stable IDs hash `(source_file, primary_actor, text)`, nothing
   else.** Upstream paragraph insertions don't churn them. Reformatting
   is normalised away (whitespace collapsed, casefold). Renaming the
   source file DOES change the ID — that's by design (the two versions
   are legitimately different requirements in the diff sense). See
   `models.compute_stable_id`.

2. **Confidence is length + vague-qualifier signal + measurable-clause
   signal, composable.** A vague qualifier downgrades one step; a
   measurable clause upgrades one step; both present cancel. Hard
   matches use the signal directly; Soft matches clamp to Medium as
   the baseline so modal-uncertainty dominates. See
   `detector.compute_confidence`.

3. **ReqIF dialects are shallow, not full tool-specific schemas.**
   Enough to import cleanly in each target's default configuration,
   not a full per-tool schema dump. If you hit an edge case in DOORS
   or Cameo import, the fix is usually a small tweak in the dialect
   branch of `reqif_writer.py` rather than a rewrite. See the
   module's docstring.

4. **PDF support is best-effort.** pdfplumber extracts tables as
   tables and prose as prose, but reading order across columns and
   page headers/footers are unreliable. Prefer the source `.docx`
   when it exists. See `legacy_formats.convert_pdf_to_docx`.

5. **The parser has a `force_requirement` kwarg.** Normally a
   sentence only becomes a `Requirement` if it matches a modal
   keyword. In procedural required-action tables the header shape
   itself is the signal, so `force_requirement=True` bypasses the
   keyword gate and emits with a synthetic `(Required Action)`
   keyword marker so reviewers can see which detection path fired.

6. **The GUI's option-exclusion logic is "hard-disable", not
   "warn-and-allow".** Req-only options grey out in actors mode and
   force-reset so flipping modes never silently carries state. See
   `gui._update_option_state`.

7. **Diff requires matching source filenames between the two runs.**
   Because stable IDs depend on the source filename. Documented in
   the diff subcommand's `--help` and the README's Diff mode section.

---

## How to verify the project is in a working state

After pulling a fresh checkout, a repo move, or a Claude-session
migration:

```bash
cd requirements-extractor
python3 -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows
pip install -r requirements.txt
pip install -r requirements-optional.txt  # optional but covers NLP/GUI/PDF
python3 -m py_compile requirements_extractor/*.py  # quick syntax check
python3 -m unittest discover tests                 # should report ~471 passing
```

As of end of 2026-04-24 the baseline is **471 tests passing, 0
failing**. Most tests are headless (no Tk, no spaCy, no LibreOffice,
no pdfplumber required); a few are gated behind `skipUnless` so they
run only when their integration dep is present.

A quick end-to-end smoke test:

```bash
python3 -m requirements_extractor.cli requirements samples/procedures/simple_two_actors.docx -o /tmp/smoke.xlsx --emit json,md,reqif
```

Should produce four files under `/tmp/` (smoke.xlsx, smoke.json,
smoke.md, smoke.reqif) with 4 requirement rows each. If any of these
fail, something regressed.

---

## What's open / deferred

At end of 2026-04-24 the outstanding items are:

1. **PyInstaller build + work-network smoke test** — the full runbook
   is at `docs/NLP_BUNDLE_SMOKE_TEST.md`. Requires a Windows machine
   with internet access to build and a work-network machine to verify.
   No code changes needed; just the manual run.

2. **Real-world Cameo / DOORS ReqIF import validation** — the
   produced `.reqif` files are structurally correct per the spec, but
   the actual import experience in those tools hasn't been tested
   with live installs. Test by producing a `.reqif` via `--emit reqif
   --reqif-dialect=cameo` (or `doors`) and importing into the target.
   If the import wizard complains, the dialect branch in
   `reqif_writer.py` is the right place to tweak.

3. **§3.8 source-preview column** — deferred pending a product
   decision (hyperlink-to-source vs inline context-snippet).

Stretch / future fixture ideas are listed at the bottom of
`samples/procedures/README.md`.

---

## Where to find the history

`docs/SESSION_STATUS.md` is the session-level changelog — it records
what shipped in each working session with cross-links to tests.
Read it in reverse-chronological order (top-of-file is most recent)
to reconstruct what happened when.

`REVIEW.md` is the original architecture review. The "Status as of …"
block at the top tracks which review items have been fixed and which
are still open. Most of it is historical context now; the living
part is the status block.

`FIELD_NOTES.md` is Eric's field-testing observations with a Status
line on each one showing what's been addressed.

The `PLAN-*.md` files are older design plans for features that have
all been discharged. Each one carries a `STATUS: DISCHARGED` banner
at the top with a link to where the work landed. Keep them in-tree
for the design rationale; don't re-derive them.

---

## Re-onboarding prompt for Claude

Paste the block below into a new Claude conversation after a project
migration or context loss. It gives the assistant enough to be
immediately productive without having to explore the codebase blind.

```
I'm picking up work on the Document Data Extractor project
(`requirements-extractor/`). The full overview is at
`docs/PROJECT_OVERVIEW.md` — read that first.

Baseline facts as of the last session:
- 471 tests passing, 0 failing.
- Code lives under `requirements_extractor/`. Tests under `tests/`.
  Fixtures under `samples/edge_cases/` (5 files) and
  `samples/procedures/` (11 files).
- Design docs: REVIEW.md (architecture), FIELD_NOTES.md (field
  observations), PLAN-*.md (all DISCHARGED).
- Session-level changelog: docs/SESSION_STATUS.md (top-of-file is
  most recent).
- Runbook for the PyInstaller / NLP bundle:
  docs/NLP_BUNDLE_SMOKE_TEST.md.
- User-facing guide: README.md.

Outstanding items:
1. PyInstaller build + work-network smoke test (manual, runbook
   linked above).
2. Real Cameo / DOORS ReqIF import validation.
3. §3.8 source-preview column (deferred — needs product decision).

Coding conventions I've observed in prior sessions:
- Tests are `unittest` style, discoverable via
  `python3 -m unittest discover tests`.
- Headless-first: gated integration tests use `skipUnless` so the
  suite stays green when LibreOffice / pdfplumber / spaCy are absent.
- The parser emits an event stream (HeadingEvent / SectionRowEvent /
  RequirementEvent); writers filter what they care about.
- Stable IDs hash (source_file, primary_actor, text) only —
  upstream paragraph edits don't churn them.
- The Edit tool occasionally truncates files mid-function in this
  repo. If a file appears to lose its tail after an edit, verify with
  `wc -l` + `tail`, run py_compile, and rewrite the truncated tail
  from bash if needed. `find . -name __pycache__ -exec rm -rf {} +`
  before re-running tests if behaviour seems stale.

Before making changes:
- `python3 -m py_compile requirements_extractor/*.py` to confirm
  syntax is clean.
- `python3 -m unittest discover tests` to confirm the 471-test
  baseline.

Now, let's [describe the task].
```

Adjust the "last session baseline facts" numbers when reusing — the
test count changes as features and tests land. Keep the rest.
