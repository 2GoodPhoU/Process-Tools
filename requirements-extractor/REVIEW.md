# Document Data Extractor — review & improvement suggestions

> Note: this tool was originally named "Requirements Extractor".  The
> user-facing surface (CLI command name, GUI window title, packaging
> artifacts, README branding) has since been rebranded to
> **Document Data Extractor** to reflect the addition of actors mode,
> but the Python package is still `requirements_extractor` internally
> so existing imports and scripts keep working.  References below to
> "Requirements Extractor" in commit-history context are preserved
> verbatim.

A pass through the current codebase (`requirements_extractor/*.py`, `packaging/`, CLI and GUI entry points) and the sample output. Findings are grouped by priority. Each item cites the file and line range so it's easy to jump to.

Verdict up front: the architecture is clean (event stream → writers, pluggable resolver, thin CLI/GUI shells) and the README is excellent. The biggest lifts are (1) tightening the keyword-based detector to cut false positives, (2) removing a couple of latent bugs around the `Requirement` data model, and (3) filling in tests + a few UX niceties that would pay off every time the tool is used.

---

## Status — what's been resolved

The **Today, small** batch plus a **configurable file-format parser** have been implemented. Items below tagged **✅ FIXED** have landed on `main`; items tagged **✅ ADDRESSED BY CONFIG** are not closed as source changes but are now user-tunable via `--config` / per-doc `<stem>.reqx.yaml` without editing code (see the "Config file" section in `README.md` and `samples/sample_config.yaml`).

- §1.1 (`will` as a hard keyword) — ✅ FIXED. `will` moved from `HARD_KEYWORDS` to `SOFT_KEYWORDS` in `detector.py`. Future-tense prose now registers as Soft (yellow-highlighted for reviewer inspection) instead of being treated as a binding requirement. Projects whose house style treats "will" as equivalent to "shall" can reverse this with `keywords: {hard_add: [will], soft_remove: [will]}`. Regression-guarded by `TestKeywordMatcherConfig.test_will_is_soft_by_default` and `TestBuiltInKeywordSets.test_will_is_soft_not_hard`.
- §1.2 (`requirement(s)` noun matches) — ✅ FIXED. The bare nouns were never in the default keyword sets, and `TestBuiltInKeywordSets.test_nouns_not_in_hard` now regression-guards that fact. The adjective form `required` remains in HARD.
- §1.4 (negation not flagged) — ✅ FIXED. `KeywordMatcher.is_negative()` detects modal+negation pairs ("shall not", "must not", "may never", "can't", "won't") including contraction forms with either ASCII `'` or curly `\u2019` apostrophes, and allows 0–1 filler words between the modal and the negation. Polarity is surfaced as a new **Polarity** column in the output workbook (`Positive` / `Negative`); Negative rows are shaded light red so prohibitions don't hide among obligations. Covered by the ten tests in `TestNegationDetection` plus `TestParserDefaults.test_polarity_field_populated` and `test_default_polarity_is_positive`.
- §1.5 (section detection misses alphanumeric schemes) — ✅ FIXED. Default `section_prefix` regex in `config.py` now matches `A.1`, `SR-1.2`, `REQ-042`, `5.1.1a`; overridable per-doc via `tables.section_prefix`. Covered by `TestTablesConfig.test_section_re_matches_alphanumeric`.
- §1.8 (`_cell_text` flattens nested-table prose) — ✅ FIXED. Parser is now recursive and walks nested tables of arbitrary depth, emitting dotted block refs like `Nested Table 1 R2C1 > Paragraph 3`. Toggleable via `parser.recursive`.
- §2.1 (`section_topic` duplicates `primary_actor`) — ✅ FIXED. Parser carries the nearest `SectionRowEvent.title` into `Requirement.section_topic`. Regression-guarded by `TestParserDefaults.test_section_topic_is_distinct_from_actor`.
- §2.2 (dead `source` property) — ✅ FIXED. Property removed from `models.py`.
- §2.3 (unused imports) — ✅ FIXED. `field` removed from `extractor.py`, `Optional` removed from `models.py`.
- §2.5 (`-q` hides summary too) — ✅ FIXED. Split into `progress`/`summary` callbacks; new `--no-summary` added for fully-silent scripted runs.
- §2.6 (`_MAX_LEVEL = 4` is misleading) — ✅ FIXED. Renamed to `_HEADER_LEVEL_PAIRS` with a docstring note that only L1–L3 are functionally populated.
- §2.10 (GUI cannot be cancelled mid-run) — ✅ FIXED. ``extract_from_files`` now accepts a ``cancel_check`` callback and ``file_progress(i, n, name)`` callback. GUI has a **Cancel** button that sets a ``threading.Event`` which the extractor polls between files; a cancel before any write raises ``ExtractionCancelled`` and no half-written output lands on disk. Covered by ``TestCancelCheck`` (3 tests) and ``TestFileProgress`` (1 test) in ``tests/test_extractor_cancel.py``.
- §2.11 (duplicate-file detection uses identity, not resolved path) — ✅ FIXED. All dedup goes through ``gui_state.dedupe_paths`` / ``is_duplicate_of_any``, which normalise with ``Path.resolve()`` so ``./a/../a/spec.docx`` and ``a/spec.docx`` collapse. A final dedup pass runs just before Run, catching any entries that slipped in via drag-and-drop. Covered by ``TestPathDedup`` in ``tests/test_gui_state.py``.
- §2.12 (no tests) — ✅ PARTIALLY FIXED. `tests/` now ships with 174 unit/integration tests across `test_detector.py`, `test_config.py`, `test_parser.py`, `test_edge_cases.py`, `test_gui_state.py`, `test_extractor_cancel.py`, `test_actor_scan.py`, and `test_cli.py`. Run with `python -m unittest discover tests`. Pytest not required.
- §3.4 (progress bar in GUI) — ✅ FIXED. ``ttk.Progressbar`` in determinate mode, advanced per-file via the new ``file_progress`` extractor callback.
- §3.5 (open output file from the "done" dialog) — ✅ FIXED. Default is now 'open on success' (toggleable via a checkbox in §4 Options); when disabled the completion dialog offers a yes/no prompt. Cross-platform open via ``os.startfile`` / ``open`` / ``xdg-open``.
- §3.6 (persistent settings) — ✅ FIXED. ``gui_state.GuiSettings`` dataclass round-trips to ``~/.requirements_extractor/settings.json`` on window close and reloads on launch. Defensive against missing / malformed / future-schema files — always launches cleanly. Covered by ``TestGuiSettingsRoundtrip`` (6 tests).
- §3.7 (drag-and-drop inputs) — ✅ FIXED. Optional ``tkinterdnd2`` dependency enables drag-and-drop onto the input list; absent, the UI falls back to the existing buttons without warning. Added to ``requirements-optional.txt``.
- §3.14 (GUI "Open actors template" button) — ✅ FIXED. New **Save template…** button in the Actors section calls ``gui_state.write_actors_template`` which emits a ready-to-fill .xlsx (with a Readme sheet) using the exact "Actor" / "Aliases" headers that ``load_actors_from_xlsx`` expects. Covered by ``TestActorsTemplate`` (round-trip test confirms the template parses back without error).
- §2.4 (``extractor.py`` reaches into ``ActorResolver._nlp``) — ✅ FIXED. ``ActorResolver`` now has a public API: ``has_nlp() -> bool``, ``iter_regex_hits(text, primary="")``, ``iter_nlp_hits(text, primary="")``, and ``iter_matches(text, primary="")`` which yields ``(name, source)`` tuples across both passes with cross-source dedup. ``resolve()`` is now a thin wrapper over ``iter_matches``, and ``extractor.py`` / ``actor_scan.py`` use ``not resolver.has_nlp()`` and ``resolver.iter_matches(...)`` instead of reaching into ``_nlp`` / ``_actor_re`` / ``_alias_to_canonical``. All three ``# noqa: SLF001`` comments were removed. Covered by ``TestActorResolverPublicApi`` (9 tests) in ``tests/test_encapsulation.py``.
- §2.7 (``parser.py`` uses python-docx private API) — ✅ FIXED. New ``_cell_element(cell)`` and ``_paragraph_element(p)`` helpers in ``parser.py`` centralise the ``_Cell._tc`` / ``Paragraph._p`` accesses so a future python-docx upgrade that exposes a public attribute can be absorbed in one place. Each helper walks ``_tc``/``_p`` → ``_element`` → ``element`` and raises a descriptive ``AttributeError`` if the library's internal shape ever changes. The ``python-docx`` pin in ``requirements.txt`` was tightened to ``>=1.1,<2`` (and ``openpyxl`` / ``PyYAML`` got matching upper bounds) so surprise majors can't sneak in. Covered by ``TestParserPrivateAttrWrappers`` (2 tests) in ``tests/test_encapsulation.py``.
- §2.8 (heading level-skip edge case) — ✅ FIXED. ``_update_heading_trail`` in ``parser.py`` now pads the trail with empty strings for any skipped level, so an H1 → H3 jump produces ``["H1", "", "H3"]`` instead of ``["H1", "H3"]`` — the depth of every heading can be recovered from its list index. ``trail_str`` continues to filter empties so the visible "Heading Trail" column reads ``Chapter > Detail`` without stray separators. Covered by ``TestHeadingTrailPadding`` (6 tests) in ``tests/test_logging_and_trail.py``.
- §2.13 (no logging module) — ✅ FIXED. New ``requirements_extractor._logging`` module exposes a ``requirements_extractor`` logger with a ``NullHandler`` attached (standard-library library-author recommendation) plus ``make_progress_logger(progress)`` which returns a callback that forwards every message to both the existing progress callback AND the logger at an appropriate level (``ERROR:`` → ERROR, ``WARNING:`` → WARNING, anything else → INFO). ``extractor.py`` and ``actor_scan.py`` both construct their ``log`` via ``make_progress_logger`` now, so scripted callers can do ``logging.getLogger('requirements_extractor').setLevel(logging.DEBUG)`` and attach their own handler to capture progress without having to supply a callback. CLI and GUI behaviour is unchanged because the callback still runs and no stream handler is attached by default. Covered by ``TestProgressLogger`` (5 tests) in ``tests/test_logging_and_trail.py``.
- §2.9 (bare ``except Exception`` in multiple places) — ✅ FIXED. Three catches in ``extractor.py`` (config load, per-doc config, keywords load) and their parallels in ``actor_scan.py`` narrowed from ``Exception`` to ``(OSError, ValueError, ImportError)`` — covering file-not-found/permission, YAML parse and schema validation, and "PyYAML not installed for a .yaml file". Actors-file loaders narrowed to ``(OSError, ValueError, KeyError)``. ``actors._try_load_spacy`` narrowed to ``(ImportError, OSError, ValueError, TypeError)`` with a comment explaining each case (model missing, incompatible pickled config, pydantic v1/v2 TypeError). The three ``# noqa: BLE001`` comments where the catch is genuinely broad-on-purpose (per-file parse failures must not abort the batch) are kept with explicit comments saying so. Covered by ``NarrowedCatchSoftFails`` (4 tests) in ``tests/test_error_handling.py`` — missing actors file, missing config, invalid config contents, missing keywords file — all confirm the run completes with a recorded warning in ``stats.errors``.
- §2.14 (PyInstaller spec's pydantic hazard) — ✅ FIXED. ``packaging/build-requirements.txt`` now carries documented pin ranges for the NLP stack (``spacy>=3.7,<3.8``, ``pydantic>=2.5,<3``, ``pydantic-core>=2.14,<3``, ``thinc>=8.2,<9``) plus a header note explaining the pydantic v1/v2 compatibility hazard: spaCy's pydantic requirement has flipped between majors across minor releases, and bundling a mismatched pair has historically caused runtime ``ValidationError``s that only surface on the target machine. PyInstaller itself is now pinned to ``pyinstaller>=6.0,<7`` to match. The NLP pins are commented out by default (so CLI-only builds don't get forced into an NLP install) with clear guidance for when to uncomment them.
- **Module-size refactors / de-duplication** — ✅ FIXED. Two duplication hazards removed: (1) ``extract.py`` used to hand-maintain its own ``_KNOWN_SUBCOMMANDS = {"requirements", "reqs", "actors", "scan"}`` set, which would silently go stale the next time a subcommand was added/renamed.  It now imports ``SUBCOMMAND_NAMES`` from ``requirements_extractor.cli`` — a single source of truth next to the argparse wiring.  A regression test in ``tests/test_cli_refactors.py::SubcommandCatalogueTests`` pins the set against the parser's actual registered choices in both directions, so drift becomes a test failure. (2) The ``cli._run_requirements`` function mixed its auto-actors pre-pass inline with the main extraction dispatch; the pre-pass has now been factored into ``_harvest_auto_actors(args, inputs, output_path, progress)`` which returns the sidecar path.  The parent function dropped from ~70 lines to ~50 and ``_harvest_auto_actors`` is now directly testable — covered by ``HarvestAutoActorsTests.test_harvest_writes_sidecar_and_returns_path``.
- **Actor-only scan mode** (new capability, complements §1.7 in practice) — ✅ FIXED. A dedicated ``actors`` / ``scan`` CLI subcommand and an **Actors** mode in the GUI run the parser without keyword detection and emit a three-sheet workbook (Actors / Observations / Readme). The Actors sheet's header shape (``Actor`` / ``Aliases``) is directly consumable by ``--actors`` on a subsequent run, so users can bootstrap and iterate on an actors list cheaply. Seeded re-scans preserve canonical spellings verbatim and add only new variants as aliases. Covered by ``tests/test_actor_scan.py`` (23 tests: normalisation, grouping seeded/unseeded, end-to-end round-trip through ``load_actors_from_xlsx``, cancel/progress plumbing).
- **Subcommand CLI + surface rename to `document-data-extractor`** — ✅ FIXED. The tool now presents as ``document-data-extractor`` (window title, packaging spec, README branding) to reflect that it does more than just requirements.  The CLI is git-style: ``document-data-extractor requirements SPECS/`` and ``document-data-extractor actors SPECS/`` (with ``reqs`` / ``scan`` aliases).  Global flags (``--config``, ``-q/--quiet``, ``--no-summary``) live on the root parser.  The legacy ``extract.py`` shim transparently rewrites flag-style argv to a ``requirements`` subcommand so older scripts keep working.  GUI exposes the mode as a top-of-window radio selector; the statement-set section greys out in actors mode; the chosen mode is persisted in ``GuiSettings`` and restored on next launch.  The Python package remains ``requirements_extractor`` internally so existing imports don't break.  Covered by ``tests/test_cli.py`` (23 tests: parser shape, per-subcommand flag parsing, alias passthrough, end-to-end dispatch, shim argv rewriting) plus ``TestGuiSettingsMode`` in ``tests/test_gui_state.py``.
- §1.6 (preamble requirements dropped from statement set) — ✅ FIXED. ``statement_set.py`` now routes any `RequirementEvent` whose `row_ref == "Preamble"` under a synthetic ``(preamble)`` Level-2 bucket so preamble prose stays visible in the CSV instead of being silently dropped. The bucket's description explicitly tells reviewers to promote preamble items into real sections manually. Also handles the degenerate empty-hierarchy case (no H1, no H2, no section-row table) so every extracted row still reaches the output.
- §3.2 (editable keyword lists) — ✅ FIXED. A new ``--keywords PATH`` global flag loads a standalone keywords file (``.yaml``/``.yml`` or ``.txt``/``.kw``) that tweaks just the HARD/SOFT lists without forcing users to author a full ``--config``. Two schemas are supported: "replace" (``hard: [shall, must]`` replaces the bucket wholesale via a ``"*"`` sentinel in the remove list) and "tweak" (``hard_add: [is to]`` / ``hard_remove: [will]`` adjusts the defaults). Mixing ``hard`` with ``hard_add``/``hard_remove`` in the same file is rejected with a clear error. The GUI exposes a matching "Keywords" field next to "Config" and persists ``last_keywords_path``. A sample file lives at ``samples/sample_keywords.yaml``.
- §3.9 (statement-set respects H2/H3 doc headings) — ✅ FIXED. ``statement_set.py`` now tracks ``current_h2`` and ``current_h3`` alongside the old H1/section-row state and routes each event to its natural depth: H2 at L2, H3 at L3 (or L2 if the document skips H2), section rows at ``_depth_below_headings()``, requirements one level below the deepest structural anchor. The header width was bumped from 4 to 5 level pairs to accommodate the deeper nesting. Printed-anchor deduping lets a given heading emit its own row exactly once per ancestor context.
- §3.13 (CLI UX polish) — ✅ FIXED. The CLI now has a ``RawDescriptionHelpFormatter`` with an epilog listing exit codes (``0/1/2/130`` for ok/runtime-error/usage-error/SIGINT) and per-subcommand Examples blocks. Named constants ``EXIT_OK``, ``EXIT_RUNTIME``, ``EXIT_USAGE`` replace bare integers. ``main()`` wraps dispatch in ``try/except`` for ``FileNotFoundError``/``ValueError``/``OSError`` (runtime errors return 1) and ``KeyboardInterrupt`` (returns 130). An ``_is_tty()`` helper is exposed for future compact-mode wiring. The module docstring now shows usage examples that cover ``--keywords`` and ``--auto-actors``.
- **Auto-harvest actors before requirements extraction** (new feature) — ✅ FIXED. A new ``--auto-actors`` flag on the ``requirements`` subcommand (and a matching GUI checkbox in Options) runs the actor scan on the input docs first, writes the harvested list as ``<output_stem>_auto_actors.xlsx`` next to the requirements output, and uses that list as the ``--actors`` source for the requirements pass. Any explicit ``--actors`` is used to seed the scan and survives verbatim into the harvested list. Saves the "maintain a separate actors.xlsx" step for users who just want to get going; the sidecar file is deterministic and ready for inspection / tidy-up / reuse on subsequent runs.

Status as of 2026-04-24 (end of day):

- ✅ FIXED: §1.7 (NER canonicalisation in `actors.canonicalise_ner_name`, 20 tests in `test_ner_canonicalisation.py`), §1.9 (`detector.compute_confidence` with vague/measurable signal offsets, 16 tests in `test_detector.py`), §1.10 (`models.annotate_cross_source_duplicates` wired into the extractor, 7 tests in `test_stable_ids.py`), §3.1 (`.doc` via LibreOffice shell-out **plus** `.pdf` via pdfplumber — both live in `legacy_formats.py`, 12 tests in `test_legacy_formats.py`, routed through `prepare_for_parser`), §3.8 (inline context snippet via `parser._build_context` + a "Context" column in the xlsx writer + a matching ReqIF attribute; the JSON writer carries it for free via `dataclasses.asdict`; 13 tests in `test_source_preview.py`), §3.10 full (JSON + Markdown in `writers_extra.py`, ReqIF 1.2 with `basic`/`cameo`/`doors` dialects in `reqif_writer.py`; CLI `--emit json,md,reqif` + `--reqif-dialect=…`; 26 tests across `test_writers_extra.py` and `test_reqif_writer.py`), §3.12 (`diff.py` + `diff` subcommand with sheet-by-name lookup and pre-stable-id rejection, 15 tests in `test_diff.py`), §3.15 (README "A note on tracked changes" section).
- Stretch / future: Cameo and DOORS import validation of the produced ReqIF files on real installs of those tools (structure is spec-correct; behaviour in the import wizards still needs a real-world run).

---

## 1. Extraction accuracy

### 1.1 `will` as a hard keyword produces heavy false positives — HIGH — ✅ FIXED
`requirements_extractor/detector.py:17` used to list `"will"` in `HARD_KEYWORDS`. Future-tense prose like *"We will see improvements in Q3"* or *"This document will serve as a guide"* was flagged as a binding requirement.

**Resolution.** `will` was moved from `HARD_KEYWORDS` to `SOFT_KEYWORDS`. Future-tense prose now registers as Soft (still captured, shown yellow for reviewer inspection) instead of Hard. Organisations whose house style treats "will" as equivalent to "shall" can reverse the default with `keywords: {hard_add: [will], soft_remove: [will]}`. Regression-guarded by `TestKeywordMatcherConfig.test_will_is_soft_by_default` and `TestBuiltInKeywordSets.test_will_is_soft_not_hard`.

### 1.2 `requirement`/`requirements` noun matches are false positives — HIGH — ✅ FIXED
`detector.py` used to leave open the question of whether the bare nouns `requirement` / `requirements` belonged in `HARD_KEYWORDS`.

**Resolution.** The bare nouns are explicitly **not** in either keyword set; only the adjective/participle form `required` (useful in "is required to respond within 5s") stays in HARD. The comment in `detector.py` now documents the choice, and `TestBuiltInKeywordSets.test_nouns_not_in_hard` regression-guards it.

### 1.3 Sentence splitter breaks on abbreviations — MEDIUM — ✅ FIXED
`split_sentences` no longer terminates a sentence on common abbreviations or enumeration prefixes. The naïve "split on .!? + whitespace + capital/digit" pass still runs first (Python's `re` can't do variable-width lookbehind cleanly), but a post-merge step now glues any fragment whose tail is a known non-terminal token back to the following fragment. The abbreviation set (`_COMMON_ABBREVS`) covers titles (`Dr.`, `Mr.`, `Mrs.`, `Ms.`, `St.`, `Sr.`, `Jr.`, `Prof.`), Latin glosses (`e.g.`, `i.e.`, `etc.`, `vs.`, `viz.`, `cf.`), document references (`Fig.`, `Eq.`, `Ref.`, `Sec.`, `Ch.`, `No.`, `Vol.`, `pp.`, `p.`), and corporate suffixes (`Inc.`, `Ltd.`, `Corp.`, `Co.`). A separate regex `_ENUMERATION_SUFFIX_RE` handles `Step N.`/`Item N.`/`Note N.`-style preambles. Token matching is case-insensitive and strips leading punctuation, so `(e.g.` and `"Dr.` both merge correctly. Covered by nine regression tests in `TestSplitSentences` (title/multi-title/Latin/reference/enumeration/parenthetical/case-insensitivity, plus a "real sentence after abbreviation still splits" guard).

### 1.4 Negation not flagged — MEDIUM — ✅ FIXED
`"shall not"`, `"must not"`, `"may not"` used to classify correctly as Hard/Soft but the polarity was discarded, so prohibitions hid among obligations.

**Resolution.** `KeywordMatcher.is_negative()` detects modal+negation pairs in three forms: spaced (`shall not`, `may never`), short-filler (`shall clearly not`, `may sometimes never` — at most one intervening word, length-capped to keep it precise), and contraction (`can't`, `shouldn't`, `won't` — both ASCII and curly apostrophes). Polarity is plumbed from `detector.py` → `parser.py::_emit_candidate` → `Requirement.polarity` → a new **Polarity** column in the Excel writer. Negative rows get a light-red fill that beats the Soft yellow, so prohibitions stand out during review. Covered by the ten tests in `TestNegationDetection` plus `TestParserDefaults.test_polarity_field_populated` and `test_default_polarity_is_positive`.

### 1.5 Section detection misses alphanumeric schemes — MEDIUM — ✅ FIXED
The section-prefix recogniser had already been broadened during the config refactor to accept letter-prefixed labels (`A.1`, `SR-1.2`, `REQ-042`, `H1.2`). The remaining gap was letter-*suffix* subdivisions (`5.1.1a`, `5.1.1b`, `3.1b)`), common in IEEE/ISO specs: they fell through as "actor" rows and polluted statement-set output. The default pattern is now `^\s*(?:[A-Z]{1,4}[-.]?)?\d+(?:\.\d+)*[a-z]?[.)]?\s+\S` — a single optional lowercase letter after the last digit group, with the mandatory trailing whitespace keeping it off typos like `3.1abc` (no space) or legit title text like `3.1 a new feature` (where the lookbehind/adjacency rule correctly treats `a` as the start of the title, not part of the prefix). The config.py block has an expanded doc-comment enumerating exactly what the default matches, doesn't match, and how to override via YAML. Covered by four new tests in `TestTablesConfig`: letter-suffix acceptance, typo rejection, unstructured-title rejection, and paren-style retention; the original alphanumeric-prefix test is kept as a regression guard.

### 1.6 Preamble requirements lack a primary actor — LOW — ✅ FIXED
`parser.py` used to emit preamble prose with `primary_actor=""` and `row_ref="Preamble"`. The Excel workbook handled that cleanly, but `statement_set.py` silently dropped any preamble row from the CSV, making important high-level requirements invisible when the reviewer worked from the statement-set rather than the workbook.

**Resolution.** `statement_set.events_to_rows()` now routes any `RequirementEvent` whose `row_ref == "Preamble"` under a synthetic `Level 2 = "(preamble)"` bucket (constants `_PREAMBLE_L2_TITLE` / `_PREAMBLE_L2_DESC` in `statement_set.py`). The bucket's description explicitly tells reviewers to promote preamble items into a real section manually. The same `(preamble)` bucket also catches the degenerate no-H1/no-H2/no-section-row case so every extracted row reaches the output regardless of document structure.

### 1.7 Secondary-actor NER returns noisy raw text — LOW
`actors.py:79-93` feeds `ent.text` directly into the output. spaCy NER readily returns determiners (`"the Auth Service"`), possessives, or ORG labels that aren't actors (`"ISO"`, `"USA"`). If the user-supplied actor list is present, consider gating NER to skip entities that don't have a lexical overlap with *any* canonical actor; otherwise restrict NER to just `PERSON`/`ORG` and canonicalise (strip leading `the`, trim trailing `'s`).

### 1.8 `_cell_text` flattens nested-table prose — LOW
`parser.py:116-118`: `_cell_text` uses only `cell.paragraphs`, losing bullet structure and nested tables. When this feeds `_collect_from_cell`'s nested-table branch (`parser.py:180-191`), a cell with bullets or its own sub-table becomes a single blob before sentence splitting. Consider calling `iter_block_items(cell)` recursively and preserving bullet boundaries — bullets are generally one requirement per bullet, and folding them loses that boundary.

### 1.9 Confidence heuristic over-rewards length alone — LOW
`detector.py:79-85` only uses sentence length. Easy upgrades: downgrade to Medium when the sentence also contains vague qualifiers (`appropriate`, `reasonable`, `sufficient`, `where practical`), and upgrade toward High when the sentence contains a measurable clause (numbers, units, tolerances). These are mostly regex — no NLP needed.

### 1.10 No dedup across sources — LOW
If the same requirement appears verbatim in two docs (common for shared boilerplate) the tool emits it twice. A simple hash of `(text.lower().strip(), primary_actor)` with a "Duplicate of #" note would help triage.

---

## 2. Code quality & bugs

### 2.1 `Requirement.section_topic` duplicates `primary_actor` — MEDIUM
`parser.py:213` sets `section_topic=primary_actor`. `writer.py:60-73` then emits both columns. Every row in `samples/sample_output.xlsx` will have these two columns identical, wasting space and confusing reviewers. Either (a) drop `Section / Topic` from `COLUMNS`, or (b) track the real section title (nearest `SectionRowEvent`) during `_collect_from_cell` and pass it through as a distinct value.

### 2.2 `Requirement.source` property is dead code — LOW
`models.py:27-38` defines a `source` property composing file + headings + row + block. Nothing calls it (grep shows only `req.source_file`). Either use it in the workbook (a single "Source" column could replace four) or delete it.

### 2.3 Unused imports — LOW
- `extractor.py:5` imports `field` from `dataclasses` but never uses it.
- `models.py:6` imports `Optional` but never uses it (the dataclass has no optional-typed fields).
- `actors.py:16` imports `Sequence` only once (OK) and `Optional` (used) — fine. (For posterity, worth running `ruff check --select F401`.)

### 2.4 `extractor.py` reaches into `ActorResolver._nlp` — LOW — ✅ FIXED
`extractor.py` used to do `if use_nlp and resolver._nlp is None:` to decide whether to warn about a missing spaCy model; `actor_scan.py::_resolver_hits` additionally reached into `_actor_re` and `_alias_to_canonical` to rebuild the resolve pipeline with source attribution (`regex` / `nlp`). Three `# noqa: SLF001` comments marked the violation as deliberate but it still meant any refactor of `ActorResolver` would silently break both call sites.

**Resolution.** `ActorResolver` got a proper public API: `has_nlp() -> bool`, `iter_regex_hits(text, primary="") -> Iterator[str]`, `iter_nlp_hits(text, primary="") -> Iterator[str]`, and `iter_matches(text, primary="") -> Iterator[Tuple[str, str]]` which yields `(name, source)` pairs with cross-source dedup. `resolve()` became a one-liner wrapper over `iter_matches`, and the NLP entity-label set moved to a named `_NLP_ACTOR_LABELS` class constant so it lives next to the behaviour that owns it. The two warning checks (`extractor.py:95`, `actor_scan.py:609`) now use `not resolver.has_nlp()`; `actor_scan._resolver_hits` collapsed from a 40-line re-implementation to a single `return list(resolver.iter_matches(text, primary))`. All three `# noqa: SLF001` comments were removed. Regression-guarded by `TestActorResolverPublicApi` (9 tests) in `tests/test_encapsulation.py`, which pins the contract of every public method including dedup across primary/secondary passes.

### 2.5 `-q/--quiet` hides the summary too — MEDIUM
`cli.py:107-119` writes the Summary block through the same `log` callback that progress messages use. With `-q`, a user gets zero output even when the job completes, which is a surprise. Split into `_progress`/`_summary` callbacks, or make `-q` suppress only per-file progress and still print a one-line summary to stdout.

### 2.6 `_MAX_LEVEL = 4` is misleading — LOW
`statement_set.py:41` plus the README line 171 ("raise `_MAX_LEVEL`") imply that deeper hierarchies just work. In reality `_place()` is only ever called with levels 1/2/3 (grep confirms). Bumping `_MAX_LEVEL` only adds empty columns; it does not enable deeper nesting. Either wire `_place` to handle H2/H3 doc headings into L2/L3 and bump the actual level, or simplify the constant and update the README.

### 2.7 `parser.py` used python-docx private API — LOW — ✅ FIXED
`iter_block_items` reached into `_Cell._tc` (the underlying `<w:tc>` element) and `_is_bullet` reached into `Paragraph._p`. Both are implementation details; historically stable on python-docx 1.x, but a silent breakage vector if 2.x ever renames them.

**Resolution.** Two helpers (`_cell_element(cell)` and `_paragraph_element(p)`) in `parser.py` centralise the access. Each walks a fallback chain — the current private attr (`_tc` / `_p`), then `_element`, then `element` — so if python-docx promotes one of the public candidates to an official attribute the helper picks it up without code changes. A descriptive `AttributeError` fires if all candidates disappear, giving a clear upgrade signal. The two call sites in `parser.py` now call the helpers; nothing else in the codebase touches python-docx privates. The `python-docx` pin in `requirements.txt` was tightened to `>=1.1,<2` (and `openpyxl` to `>=3.1,<4`, `PyYAML` to `>=6.0,<7`) so major-version drift can't sneak in via `pip install --upgrade`. Regression-guarded by `TestParserPrivateAttrWrappers` (2 tests) in `tests/test_encapsulation.py` — one confirms both helpers return correctly-tagged lxml elements against real `python-docx` objects, the other confirms the `AttributeError` path fires on a non-docx object.

### 2.8 Heading level-skip edge case — LOW — ✅ FIXED
`_update_heading_trail` used to do `while len(trail) >= level: trail.pop(); trail.append(text)`. If a document jumped H1 → H3 with no intervening H2, the H3 text landed at index 1 (the "H2 slot"), which meant the depth of each stored heading couldn't be recovered from its list index.

**Resolution.** After the pop-loop we now pad with empty strings until `len(trail) == level - 1` before appending, so the H1 → H3 case produces `["H1", "", "H3"]`. The `trail_str()` presentation helper already filtered empty strings with `if h`, so the "Heading Trail" column still reads `Chapter > Detail` without stray ` > ` separators — the fix only matters for any future consumer that indexes into the list by depth. Covered by `TestHeadingTrailPadding` (6 tests in `tests/test_logging_and_trail.py`): sequential-no-padding, H1→H3 padding, trail-str-skips-padding, new-H1-clears-subtree, new-H2-replaces-earlier-H2, starting-at-H2-pads-from-zero.

### 2.9 Bare `except Exception` in multiple places — LOW — ✅ FIXED
Several catches in `extractor.py`, `actor_scan.py`, and `actors.py` swallowed every `Exception`. The intent was correct — soft-fail on optional inputs — but the breadth meant genuine bugs (type errors in our own code, NLP pickle version mismatches, etc.) were being silently logged as user-facing warnings.

**Resolution.** The catches now name their expected failure modes:

- **Actors-file loading** (`extractor.py`, `actor_scan.py`) → `(OSError, ValueError, KeyError)`: OSError covers FileNotFound/Permission, ValueError covers the "Actor header missing" guard in `load_actors_from_xlsx`, KeyError catches empty header lookups that openpyxl can propagate.
- **Config / keywords loading** (three sites in `extractor.py`, three in `actor_scan.py`) → `(OSError, ValueError, ImportError)`: OSError for missing/locked files, ValueError for YAML parse failures and `_validate_raw` schema errors, ImportError for PyYAML missing.
- **`actors._try_load_spacy`** → `(ImportError, OSError, ValueError, TypeError)`: ImportError for missing model package, OSError for missing model directory, ValueError for incompatible pickled configs, TypeError for pydantic v1/v2 metaclass mismatches (the exact bug §2.14 addresses at the build level).

The three remaining `# noqa: BLE001` sites (per-file parse loops) are deliberately broad — one bad docx must not stop the whole batch — and now carry an inline comment saying so rather than a bare pragma. Covered by `NarrowedCatchSoftFails` (4 tests) in `tests/test_error_handling.py`: missing actors file, missing config file, invalid YAML contents, missing keywords file all soft-fail with a recorded warning and let the run continue.

### 2.10 GUI cannot be cancelled mid-run — MEDIUM — ✅ FIXED
`gui.py` used to spawn a daemon thread with no stop hook; big spec folders left the user stuck waiting.

**Resolution.** `extract_from_files` now accepts a `cancel_check` callback (polled before each file) and a `file_progress(i, n, name)` callback (fired once per file). The GUI owns a `threading.Event` cancel flag, exposes a **Cancel** button that flips it, and catches the new `ExtractionCancelled` exception to tidy up without writing a partial output. Covered by `tests/test_extractor_cancel.py`.

### 2.11 GUI duplicate-file detection uses identity, not resolved path — LOW — ✅ FIXED
`gui.py` used to compare `Path` objects via `==`, so symlink-vs-real or ``./a/../a/spec.docx`` vs ``a/spec.docx`` both slipped into the input list.

**Resolution.** All dedup now goes through `gui_state.dedupe_paths` / `is_duplicate_of_any`, which normalise via `Path.resolve()` (with a safe fallback to `.absolute()` for files that don't exist yet). A final dedup pass runs right before Run so even entries added through drag-and-drop get normalised. Covered by `TestPathDedup` in `tests/test_gui_state.py`.

### 2.12 No tests — MEDIUM
Zero unit tests are shipped. For a tool whose value depends on detection quality, this is the most cost-effective investment. Recommended minimum:
- `test_detector.py` — golden-file keyword classification on a curated set of 30–50 sentences (including known false positives from §1.1/1.2).
- `test_parser.py` — a fixture `.docx` with one of each structure (table row, nested table, bullet, preamble) and an assertion on the event stream.
- `test_statement_set.py` — round-trip against `samples/sample_statement_set.csv`.
Add a `tests/` folder, one `pytest.ini`, and a 20-line GitHub Action to run it.

### 2.13 No logging module — LOW — ✅ FIXED
All user-visible progress messages used to flow through a `progress: Callable[[str], None]` callback — practical for the GUI text area and CLI `print`, but opaque to scripted callers who want to route through the stdlib `logging` plumbing (filters, handlers, formatters, rotating files).

**Resolution.** New `requirements_extractor/_logging.py` module defines a single `logger = logging.getLogger("requirements_extractor")` with a `NullHandler` attached on import (the library-author standard-library recipe, so importing the package never adds noise to a host app's root logger). A `make_progress_logger(progress)` helper returns a callback that forwards each message to **both** the original callback and the logger at a level inferred from the message prefix: `ERROR: …` → `logger.error`, `WARNING: …` → `logger.warning`, anything else → `logger.info`. `extractor.py::extract_from_files` and `actor_scan.py::scan_actors_in_files` both construct their internal `log` via `make_progress_logger` instead of the old `progress or (lambda msg: None)` idiom. Behaviour for existing CLI and GUI callers is unchanged — the callback still fires and no stream handler is attached by default. Advanced callers can now do:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requirements_extractor").setLevel(logging.DEBUG)
```

…and capture the full progress stream with no other changes.  Covered by `TestProgressLogger` (5 tests in `tests/test_logging_and_trail.py`): info-routing, WARNING-prefix routing, ERROR-prefix routing, callback-still-invoked, NullHandler-attached-by-default.

### 2.14 PyInstaller spec's pydantic hazard — LOW — ✅ FIXED
`packaging/DocumentDataExtractor.spec` bundles both `pydantic` and `pydantic_core` into the frozen executable for NLP support. spaCy's pydantic major-version pin has flipped between v1 and v2 across minor releases, and a mismatched (spaCy, pydantic, pydantic-core) trio surfaces only as a runtime `ValidationError` on the target machine, typically the first time "Use NLP" is toggled.

**Resolution.** `packaging/build-requirements.txt` now carries documented pin ranges for the whole NLP stack:

```
pyinstaller>=6.0,<7

# Uncomment if bundling NLP:
# spacy>=3.7,<3.8
# pydantic>=2.5,<3
# pydantic-core>=2.14,<3
# thinc>=8.2,<9
```

A prose header calls out the v1/v2 hazard explicitly and tells future maintainers to re-check the trio whenever spaCy's minor version is bumped. The NLP pins are commented out by default so CLI-only builds don't pay the spaCy install tax; the spec file's `collect_all(...)` calls continue to silently no-op when those packages aren't present (graceful degradation path, unchanged). PyInstaller itself is now pinned to `>=6.0,<7` as well, so surprise majors can't break the spec file's `collect_all` hook shape.

---

## 3. Features & UX

### 3.1 `.doc` (legacy) support — MEDIUM
`extractor.py:69-72` rejects non-.docx files with a one-line error. Teams often have `.doc` specs lingering. Options: (a) detect `.doc` and shell out to `libreoffice --headless --convert-to docx` when available, or (b) use `antiword`/`textract` as a softer fallback for text-only extraction.

### 3.2 Editable keyword lists without code changes — MEDIUM — ✅ FIXED
`detector.py` holds the word lists in code. For a non-technical audience, editing Python is a non-starter; the prior `--config` path let them tune keywords only as part of a larger config dict, which felt heavy for a single-knob change.

**Resolution.** A new global `--keywords PATH` flag loads a **standalone** keywords file that tweaks just the HARD/SOFT buckets without forcing a full `--config`. Two schemas are supported:

- **Tweak the defaults** (most common): `hard_add: [is to]` / `hard_remove: [will]` / `soft_add: [anticipated]` / `soft_remove: []`. Stacks on top of the built-in lists.
- **Replace a bucket wholesale**: `hard: [shall, must]` / `soft: [should, may]`. Internally this translates into an add+remove shape using a `"*"` sentinel in the remove list, so the existing add/remove pipeline in `detector._apply_add_remove` handles both schemas on one code path.

Mixing `hard` with `hard_add` / `hard_remove` in the same file is rejected with a clear error — the two intents contradict each other. The text format (`.txt` / `.kw`) uses `[hard]` / `[soft]` / `[hard_add]` section markers for non-YAML-comfortable users. The GUI exposes a matching "Keywords" field next to "Config" in the config section, persists `last_keywords_path` across restarts, and supports browsing for `*.yaml *.yml *.txt *.kw`. A fully-documented example lives at `samples/sample_keywords.yaml`.

### 3.3 Dry-run / preview mode — MEDIUM — ✅ FIXED
`requirements --dry-run` runs the full parse + detect + ID-assignment pipeline and prints the usual summary, but skips writing both the Excel workbook and any `--statement-set` CSV. `--show-samples N` additionally prints the first N detected requirements (stable ID, type, primary actor, text preview) so users can eyeball what was matched before spending disk on it. Plumbed through as a `dry_run` kwarg on `extract_from_files`; existing callers (GUI, legacy tests) pick up the default `False` without change. Covered by `TestDryRunEndToEnd` (extractor-level) and `TestDryRunCLI` (argparse wiring + end-to-end `main()` invocation) in `tests/test_stable_ids.py`, plus updated flag coverage in `tests/test_cli.py`.

### 3.4 Progress bar in GUI — LOW — ✅ FIXED
A `ttk.Progressbar` in determinate mode now lives below the Run/Cancel row, advanced per-file via the new `file_progress(i, n, name)` callback the extractor emits. The status label alongside shows `"Parsing i/n: <filename>"`.

### 3.5 Open output file from the "done" dialog — LOW — ✅ FIXED
On successful completion the output file opens automatically (default on, toggleable via **Options → "Open output file when the run finishes"**). When the auto-open is off, the done dialog offers a yes/no prompt instead of just a static info box. Cross-platform open through `os.startfile` / `open` / `xdg-open`.

### 3.6 Persistent settings — LOW — ✅ FIXED
`gui_state.GuiSettings` persists window geometry, last-used paths (output, actors, config, statement-set, input-dir), checkbox states (NLP, statement-set, open-on-done), and a capped MRU list of recent inputs to `~/.requirements_extractor/settings.json` on window close and restores them on launch. Defensive against missing, malformed, non-dict, and wrong-type JSON — the GUI always launches. Covered by `TestGuiSettingsRoundtrip` + `TestRememberInputs` in `tests/test_gui_state.py`.

### 3.7 Drag-and-drop inputs — LOW — ✅ FIXED
Optional dependency on `tkinterdnd2` (listed in `requirements-optional.txt`). When installed, users can drop `.docx` files or whole folders onto the input list; the drop handler recursively discovers `.docx` files in any dropped directory, respects the `~$` temp-lock prefix, and dedupes via the same resolved-path path as the Add buttons. When `tkinterdnd2` is absent the GUI degrades silently — the label drops the "drag-and-drop supported" hint but nothing crashes.

### 3.8 Source-preview column — LOW — ✅ FIXED
The current `Row Ref`/`Block Ref` string tells you *where* the requirement is in the doc but you still have to open Word to confirm.

**Resolution.** New **Context** column on the Requirements sheet (16th and rightmost — placed at the end so existing column indexing in user formulas / scripts is unaffected). Implementation lives in `parser._build_context` and is fed by every `_emit_candidate` caller (paragraph, bullet, legacy nested-table flatten, preamble). The snippet is the requirement's enclosing block text — paragraph for paragraph-derived rows, bullet for bullets, cell text for nested tables, source paragraph for preamble. Suppression is built in: when the surrounding text equals the requirement (single-sentence paragraph), the column collapses to empty so it doesn't waste horizontal space. Snippets are whitespace-collapsed to a single line and capped at 280 chars with a sentence-friendly truncation (cut at the last whitespace, append `…`). The hyperlink-to-source-file approach was considered and rejected: Excel's external hyperlink behaviour is flaky on Office-for-Mac and Excel-on-the-web, while a snippet works the same way everywhere. The Context value also propagates into the JSON output (free via `dataclasses.asdict`) and into ReqIF (added to `_BASE_ATTRIBUTES` so all three dialects expose it). Markdown intentionally omits the column to keep PR-review tables compact. Covered by 13 tests in `test_source_preview.py`: pure-function `_build_context` (empty/redundant/whitespace-normalised/casefolded/short/cap/no-whitespace edge case), Requirement model default, writer column placement / ordering invariants, and end-to-end paragraph → populated context vs single-sentence → suppressed.

### 3.9 Statement-set: respect H2/H3 — MEDIUM — ✅ FIXED
`statement_set.py` used to drop `HeadingEvent` levels ≥ 2. For docs that use Heading 2 / Heading 3 as genuine structure (not just table-based sections), this flattened the tree and lost important reviewer context.

**Resolution.** `statement_set.events_to_rows()` now tracks `current_h2` and `current_h3` alongside the existing H1 / section-row state, and routes each event to its natural depth: H2 anchors at L2, H3 at L3 (or L2 if the document skipped H2 — we don't invent a missing level), section rows at `_depth_below_headings()` (which shifts based on what H2/H3 context is in scope), and requirements land one level below the deepest structural anchor. The header width was bumped from 4 to 5 level pairs to accommodate the deeper nesting, with the requirement level clamped at `_HEADER_LEVEL_PAIRS` so a runaway document doesn't blow past the CSV template. Printed-anchor deduping (a `set[Tuple[str, ...]]` keyed by ancestor chain) lets a given heading emit its own row exactly once per context — so if the same H2 appears under two different H1s, both get their own anchor row. A new H1 resets the whole subtree.

### 3.10 Additional output formats — LOW
Common requests once a team has this running:
- ReqIF XML (standard interchange format for requirements tools — JAMA, DOORS, Polarion).
- JSON for programmatic consumers / CI checks.
- Markdown table for lightweight review PRs.

Each is a 50-line writer; the event stream already exposes enough to build them.

### 3.11 Stable requirement IDs — MEDIUM — ✅ FIXED
Every requirement now gets a `REQ-<8hex>` identifier written to a new **ID** column (column 2, right after `#`). The hash inputs are `(source_file, primary_actor, text)` — whitespace-collapsed and case-folded first so cosmetic reformatting doesn't churn IDs. Row/block/heading references and global appearance order are *deliberately excluded* so inserting an unrelated paragraph upstream does not renumber downstream IDs. Duplicate `(file, actor, text)` rows in a single corpus get `-1`, `-2`, … suffixes in first-seen order via `ensure_unique_stable_ids()`, preserving the shared prefix for `grep`. The ID is computed in `parser.py::_emit_candidate` and finalised in `extractor.py` just before writers run, so every output consumer sees the same values. Decision log: the original §3.11 sketch suggested including `row_ref`/`block_ref` in the hash — that was dropped because it makes IDs brittle under exactly the upstream edits this feature is meant to survive. Covered by `TestComputeStableId`, `TestEnsureUniqueStableIds`, and `TestWriterIdColumn` in `tests/test_stable_ids.py` (format check, determinism, whitespace/case normalisation, collision suffixing, xlsx column placement, cross-run stability).

### 3.12 Diff mode — LOW
`requirements-extractor diff old.xlsx new.xlsx` that colour-codes added/removed/changed rows in a third workbook would be a killer feature for change-control meetings.

### 3.13 CLI UX polish — LOW — ✅ FIXED
The CLI previously returned an undifferentiated `0`/`2`, had no usage examples visible to `--help`, and relied on argparse's default error surface for every failure mode.

**Resolution.** Named exit-code constants (`EXIT_OK=0`, `EXIT_RUNTIME=1`, `EXIT_USAGE=2`) replace bare integers everywhere in `cli.py`. The parser and both subparsers use `RawDescriptionHelpFormatter` so a new epilog with per-command **Examples** blocks and (on the root parser) an **Exit codes** block is visible to `--help`. `main()` now wraps dispatch in `try/except`: `FileNotFoundError`/`ValueError`/`OSError` bubble up as `Error: ...` on stderr and return `EXIT_RUNTIME` (the "user can fix it" set — corrupt docx, bad config, permission denied); `KeyboardInterrupt` prints `Interrupted.` and returns `130` to match the CLI-as-script convention for SIGINT. An `_is_tty()` helper is exposed for future compact-mode callers. The module docstring now includes worked examples for `--keywords` and `--auto-actors`.

Not yet implemented (deferred to a future pass): `-v/--verbose` escalation, non-zero on recorded `stats.errors` for CI use, `--summary-json PATH` for machine-readable stats. The exit-code ladder is now large enough to accept a fourth code (e.g. `3 = completed with warnings`) without breaking the existing contract.

### 3.14 GUI "Open actors template" button — LOW — ✅ FIXED
Non-technical users often struggle to get the actors file started. A "Download actors template" button that copies `samples/actors.sample.xlsx` to a user-chosen location would remove that friction.

**Resolution:** Added a **Save actors template…** button next to the Actors field in the GUI. It calls the new `gui_state.write_actors_template()` helper, which builds a fresh `.xlsx` in-memory (headers `Actor` / `Aliases` matching what `actors.load_actors_from_xlsx` expects, four worked example rows, plus a Readme sheet explaining the format). After saving, the GUI offers to open the file and auto-fills the Actors path so the next run picks it up. Covered by `TestActorsTemplate` in `tests/test_gui_state.py`, including a round-trip test (`test_template_is_loadable_by_actor_loader`) that parses the generated file back through the real actor loader.

### 3.15 Document the environment expectations — LOW
`README.md` doesn't mention that `.docx` files with tracked changes accepted/unaccepted behave differently (python-docx reads the post-accept text from the XML). Worth a sentence under "What this tool expects" so reviewers know to accept tracked changes first (or run the tool twice — before and after acceptance — to see the delta).

---

## Suggested order of attack

If you want a concrete roadmap:

1. **Today, small**: fix §2.1 (duplicate column), §2.2 (dead property), §2.3 (unused imports), §2.5 (quiet+summary), §2.6 (`_MAX_LEVEL` doc). *(All done.)*
2. **This week**: §1.1 and §1.2 (high-signal detector fixes), §2.12 (add pytest + 10 golden tests so you can safely refactor the detector), §1.4 (negation), §3.3 (`--dry-run`). *(All done.)*
3. **Next**: §1.3 (sentence splitter — done), §1.5 (alphanumeric sections — done), §3.2 (external keyword file — done), §3.11 (stable IDs — done), §3.9 (statement-set heading-style — done), §1.6 (preamble bucket — done), §3.13 (CLI UX polish — done), auto-harvest actors (done).
4. **Nice-to-have**: §3.5–3.7 (GUI polish — done), §3.1 (.doc support), §3.10 (extra output formats), §3.12 (diff mode), §3.13 finish-up (``-v/--verbose``, ``--summary-json``), §1.7 (NER canonicalisation), §1.9 (confidence heuristic upgrade), §1.10 (cross-source dedup).

Items §1.1, §1.2, §2.1, and §2.5 are all one-liners or near-one-liners and would materially improve the user-facing quality right away.
