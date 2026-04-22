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
- **Actor-only scan mode** (new capability, complements §1.7 in practice) — ✅ FIXED. A dedicated ``actors`` / ``scan`` CLI subcommand and an **Actors** mode in the GUI run the parser without keyword detection and emit a three-sheet workbook (Actors / Observations / Readme). The Actors sheet's header shape (``Actor`` / ``Aliases``) is directly consumable by ``--actors`` on a subsequent run, so users can bootstrap and iterate on an actors list cheaply. Seeded re-scans preserve canonical spellings verbatim and add only new variants as aliases. Covered by ``tests/test_actor_scan.py`` (23 tests: normalisation, grouping seeded/unseeded, end-to-end round-trip through ``load_actors_from_xlsx``, cancel/progress plumbing).
- **Subcommand CLI + surface rename to `document-data-extractor`** — ✅ FIXED. The tool now presents as ``document-data-extractor`` (window title, packaging spec, README branding) to reflect that it does more than just requirements.  The CLI is git-style: ``document-data-extractor requirements SPECS/`` and ``document-data-extractor actors SPECS/`` (with ``reqs`` / ``scan`` aliases).  Global flags (``--config``, ``-q/--quiet``, ``--no-summary``) live on the root parser.  The legacy ``extract.py`` shim transparently rewrites flag-style argv to a ``requirements`` subcommand so older scripts keep working.  GUI exposes the mode as a top-of-window radio selector; the statement-set section greys out in actors mode; the chosen mode is persisted in ``GuiSettings`` and restored on next launch.  The Python package remains ``requirements_extractor`` internally so existing imports don't break.  Covered by ``tests/test_cli.py`` (23 tests: parser shape, per-subcommand flag parsing, alias passthrough, end-to-end dispatch, shim argv rewriting) plus ``TestGuiSettingsMode`` in ``tests/test_gui_state.py``.

Still open (carried into the roadmap below): §1.6, §1.7, §1.9, §1.10, §2.4, §2.7, §2.8, §2.9, §2.13, §2.14, §3.1, §3.2 (beyond keyword tuning), §3.8, §3.9, §3.10, §3.12, §3.13, §3.15.

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

### 1.6 Preamble requirements lack a primary actor — LOW
`parser.py:251-262` scans prose before the first table with `primary_actor=""`. The Excel workbook is fine with that, but `statement_set.py:109` drops any preamble row from the CSV. If preamble prose is a likely home for high-level requirements, consider letting them into the statement set under a synthetic `Level 2 = "(Preamble)"` bucket rather than silently discarding.

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

### 2.4 `extractor.py` reaches into `ActorResolver._nlp` — LOW
`extractor.py:53`: `if use_nlp and resolver._nlp is None:` accesses a private attribute. Expose a public `has_nlp()` or `nlp_loaded` attribute and use that — otherwise any refactor of `ActorResolver` silently breaks this check.

### 2.5 `-q/--quiet` hides the summary too — MEDIUM
`cli.py:107-119` writes the Summary block through the same `log` callback that progress messages use. With `-q`, a user gets zero output even when the job completes, which is a surprise. Split into `_progress`/`_summary` callbacks, or make `-q` suppress only per-file progress and still print a one-line summary to stdout.

### 2.6 `_MAX_LEVEL = 4` is misleading — LOW
`statement_set.py:41` plus the README line 171 ("raise `_MAX_LEVEL`") imply that deeper hierarchies just work. In reality `_place()` is only ever called with levels 1/2/3 (grep confirms). Bumping `_MAX_LEVEL` only adds empty columns; it does not enable deeper nesting. Either wire `_place` to handle H2/H3 doc headings into L2/L3 and bump the actual level, or simplify the constant and update the README.

### 2.7 `parser.py:79` uses python-docx private API — LOW
`parent._tc` is an implementation detail of `_Cell`. python-docx has historically been stable here, but pin the version tighter in `requirements.txt` (`python-docx>=1.1,<2`) or wrap in a try/except so an upgrade doesn't silently break nested-cell walking.

### 2.8 Heading level-skip edge case — LOW
`parser.py:135-139` `_update_heading_trail`: if a doc jumps H1 → H3, the trail becomes `[H1, H3]` but the H3 occupies the "H2 slot". That's only a cosmetic issue in the Heading Trail column. Consider padding with empty strings so level is preserved: `while len(trail) < level - 1: trail.append("")`.

### 2.9 Bare `except Exception` in multiple places — LOW
`extractor.py:48, 77`, `actors.py:91, 145`, `gui.py:260, 275` all swallow every exception. They're annotated with `# noqa: BLE001` so the decision is intentional, but at least `actors.py:145` (`spacy.load`) hides real version mismatches. Consider narrowing to `(ImportError, OSError, ValueError)` and logging the exception class in a debug mode.

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

### 2.13 No logging module — LOW
All output is raw `print`. Switch the progress callback internals to `logging.getLogger("requirements_extractor")` so users can dial verbosity without changing the public API.

### 2.14 PyInstaller spec's pydantic hazard — LOW
`packaging/DocumentDataExtractor.spec` bundles both `pydantic` and `pydantic_core`. spaCy's version pin has flipped between pydantic v1 and v2 across minor releases — bundling the wrong pair causes runtime `ValidationError`s that only surface on the target machine. Suggest pinning `spacy`, `pydantic`, and `pydantic-core` in a `packaging/build-requirements.txt` stack and calling them out in the build instructions.

---

## 3. Features & UX

### 3.1 `.doc` (legacy) support — MEDIUM
`extractor.py:69-72` rejects non-.docx files with a one-line error. Teams often have `.doc` specs lingering. Options: (a) detect `.doc` and shell out to `libreoffice --headless --convert-to docx` when available, or (b) use `antiword`/`textract` as a softer fallback for text-only extraction.

### 3.2 Editable keyword lists without code changes — MEDIUM
`detector.py` holds the word lists in code. For a non-technical audience, let them live as an editable YAML/TXT next to the exe (or in `%APPDATA%` / `~/.config`), with fallbacks to defaults. `--keywords path.yaml` on the CLI and a "Keywords…" button in the GUI would make per-project tuning possible without rebuilds.

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

### 3.8 Source-preview column — LOW
The current `Row Ref`/`Block Ref` string tells you *where* the requirement is in the doc but you still have to open Word to confirm. Consider:
- A hyperlink in the Excel cell that opens the source .docx (writer can set `cell.hyperlink = str(path)`).
- A short context snippet — 1–2 lines before/after — as a separate `Context` column.

### 3.9 Statement-set: respect H2/H3 — MEDIUM
`statement_set.py:89-92` drops `HeadingEvent` levels ≥ 2. For docs that use `Heading 2` and `Heading 3` as genuine structure (not just table-based sections), this flattens the tree. Either map H2 → L2 and move section-row topics to L3 (and actors to L4), or add a CLI flag `--statement-set-style={table, heading}` to let users pick.

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

### 3.13 CLI UX polish — LOW
- Add `-v/--verbose` (currently only `-q`).
- Exit codes beyond 0/2: consider non-zero when any `stats.errors` is recorded, so CI can fail on parse errors.
- `--summary-json PATH` for machine-readable stats.

### 3.14 GUI "Open actors template" button — LOW — ✅ FIXED
Non-technical users often struggle to get the actors file started. A "Download actors template" button that copies `samples/actors.sample.xlsx` to a user-chosen location would remove that friction.

**Resolution:** Added a **Save actors template…** button next to the Actors field in the GUI. It calls the new `gui_state.write_actors_template()` helper, which builds a fresh `.xlsx` in-memory (headers `Actor` / `Aliases` matching what `actors.load_actors_from_xlsx` expects, four worked example rows, plus a Readme sheet explaining the format). After saving, the GUI offers to open the file and auto-fills the Actors path so the next run picks it up. Covered by `TestActorsTemplate` in `tests/test_gui_state.py`, including a round-trip test (`test_template_is_loadable_by_actor_loader`) that parses the generated file back through the real actor loader.

### 3.15 Document the environment expectations — LOW
`README.md` doesn't mention that `.docx` files with tracked changes accepted/unaccepted behave differently (python-docx reads the post-accept text from the XML). Worth a sentence under "What this tool expects" so reviewers know to accept tracked changes first (or run the tool twice — before and after acceptance — to see the delta).

---

## Suggested order of attack

If you want a concrete roadmap:

1. **Today, small**: fix §2.1 (duplicate column), §2.2 (dead property), §2.3 (unused imports), §2.5 (quiet+summary), §2.6 (`_MAX_LEVEL` doc).
2. **This week**: §1.1 and §1.2 (high-signal detector fixes), §2.12 (add pytest + 10 golden tests so you can safely refactor the detector), §1.4 (negation), §3.3 (`--dry-run`). *(All done.)*
3. **Next**: §1.3 (sentence splitter — done), §1.5 (alphanumeric sections — done), §3.2 (external keyword file), §3.11 (stable IDs — done), §3.9 (statement-set heading-style option).
4. **Nice-to-have**: §3.5–3.7 (GUI polish), §3.1 (.doc support), §3.10 (extra output formats), §3.12 (diff mode).

Items §1.1, §1.2, §2.1, and §2.5 are all one-liners or near-one-liners and would materially improve the user-facing quality right away.
