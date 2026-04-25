# Changelog

All notable changes to **Document Data Extractor** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html). Pre-1.0
behaviour: minor versions may include breaking CLI / config / output-shape
changes — they will always be called out under a **Breaking** subhead.

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

[0.5.0]: #050--2026-04-24
[0.1.0]: #010--initial-scaffold
