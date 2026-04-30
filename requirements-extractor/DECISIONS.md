# Decisions — requirements-extractor

> Decision-doc voice. One entry per architectural call or audit finding. Append-only — supersede with a later entry rather than rewriting an old one.

---

## 2026-04-29 — Actor-extraction heuristic regression coverage audit

**Context.** The rule-based actor heuristics in `requirements_extractor/actor_heuristics.py` are the offline-network fallback when neither a user-supplied actors list nor spaCy NER is available. They are load-bearing on the air-gapped target. CLAUDE.md flags edit-tool truncation as a recurring hazard and the night-auditor / 8am-Worker incident on 2026-04-29 confirmed it can hit core modules silently. We need to know which heuristics are exposed if a future change breaks them without tripping a test.

**Method.** Walked the 10 heuristics in `actor_heuristics.py` against the test set in `tests/test_actor_heuristics.py` (36 tests, all green as of this audit). For each rule: identified the pure function that owns it, listed the named tests that pin its behaviour (positive + negative cases), and assigned a coverage verdict. No new tests written — this is an audit, not a remediation.

**Test count.** `python3 -m unittest tests.test_actor_heuristics` reports `Ran 36 tests in 0.001s — OK`. No other test module references `actor_heuristics` or `extract_actor_candidates` (`grep -l` across `tests/` and `tests/integration/` returns only `tests/test_actor_heuristics.py`). All heuristic coverage lives in this one file.

### Per-heuristic coverage table

| # | Rule (CLAUDE.md name) | Function | File | Named tests covering it | Verdict |
|---|---|---|---|---|---|
| 1 | passive-by-agent | `_h_by_agent` | `actor_heuristics.py` | `TestRule1ByAgent.test_approved_by` (pos) · `TestRule1ByAgent.test_recorded_by` (pos) · `TestRule1ByAgent.test_not_by_lowercase` (neg) | covered |
| 2 | send-to | `_h_send_to` | `actor_heuristics.py` | `TestRule2SendTo.test_forward_to` (pos, Form 1 — "to ACTOR") · `TestRule2SendTo.test_notify_actor` (pos, Form 2 — direct-object) · `TestRule2SendTo.test_no_recipient_role` (neg) | covered |
| 3 | possessive | `_h_possessive` | `actor_heuristics.py` | `TestRule3Possessive.test_apostrophe_s` (pos, ASCII) · `TestRule3Possessive.test_curly_apostrophe` (pos, U+2019) · `TestRule3Possessive.test_multi_word` (pos, two-token actor) | partially covered (no negative test — "the report's content" or "the system's value" would slip past role-shape probe but no fixture pins that a non-role possessor is dropped) |
| 4 | compound subject | `_h_compound_subject` | `actor_heuristics.py` | `TestRule4CompoundSubject.test_two_actors` (pos) · `TestRule4CompoundSubject.test_two_services` (pos) · `TestRule4CompoundSubject.test_lowercase_subject_does_not_fire` (neg) | covered |
| 5 | conditional subject | `_h_conditional_subject` | `actor_heuristics.py` | `TestRule5ConditionalSubject.test_if_actor_verb` (pos, "If") · `TestRule5ConditionalSubject.test_when_actor_verb` (pos, "When") · `TestRule5ConditionalSubject.test_no_named_actor` (neg) | partially covered (regex covers six trigger words: `if·when·whenever·once·after·before` — only `if` and `when` have positive fixtures; the other four are unexercised) |
| 6 | for-beneficiary | `_h_for_beneficiary` | `actor_heuristics.py` | `TestRule6ForBeneficiary.test_for_role` (pos) · `TestRule6ForBeneficiary.test_for_lowercase_user_drops` (neg) | covered |
| 7 | implicit-passive | `_h_implicit_passive` | `actor_heuristics.py` | `TestRule7ImplicitPassive.test_shall_be_logged` (pos, "shall be logged") · `TestRule7ImplicitPassive.test_with_explicit_agent_no_fire` (neg, suppression on trailing "by") | partially covered (regex covers nine passive verbs: `logged·recorded·stored·persisted·archived·audited·tracked·captured·monitored·reported` and four modal/aux forms: `shall be · must be · will be · is · are` — only "shall be logged" is exercised; a regex edit dropping any other verb or modal would not be caught) |
| 8 | hyphenated role | `_h_hyphenated_role` | `actor_heuristics.py` | `TestRule8HyphenatedRole.test_actor_initiated` (pos, `-initiated`) · `TestRule8HyphenatedRole.test_reviewer_driven` (pos, `-driven`) | partially covered (regex covers seven hyphen suffixes: `-initiated · -driven · -generated · -owned · -signed · -approved · -requested` — only the first two are exercised; no negative test) |
| 9 | between-X-and-Y | `_h_between` | `actor_heuristics.py` | `TestRule9Between.test_between_two_actors` (pos) | partially covered (single positive case, no negative — the rule's own docstring acknowledges "between the office and the building" should not fire and relies on `_is_role_phrase` to suppress, but no fixture pins that suppression) |
| 10 | role appositive | `_h_appositive` | `actor_heuristics.py` | `TestRule10Appositive.test_role_appositive` (pos) | partially covered (single positive case, no negative — the rule's own comment says "Tight pattern -- only fires when the appositive itself is role-shaped, to avoid grabbing geographical / temporal appositives" but no fixture pins the geographical/temporal suppression) |

### Supporting / shared-machinery coverage

The role-shape probe (`_is_role_phrase`) and the cleanup pass (`_clean`) are shared across all 10 heuristics. They are pinned by:

- `TestRoleShapeProbe.test_head_noun_triggers` — `_ROLE_HEAD_NOUNS` membership ("Auth Service", "Notification Manager")
- `TestRoleShapeProbe.test_role_suffix_triggers` — `_ROLE_SUFFIXES` morpheme match ("Reviewer", "Auditor", "Specialist")
- `TestRoleShapeProbe.test_lowercase_fragment_does_not_trigger` — negative on lowercase head ("the value", "login event")
- `TestRoleShapeProbe.test_acronym_triggers` — single-token uppercase short-form ("API")
- `TestRoleShapeProbe.test_stopword_drops` — `_HEAD_STOPWORDS` filter on `_clean` ("If")

The orchestration entry point (`extract_actor_candidates`) and the `ActorResolver.use_heuristics` wiring are pinned by:

- `TestExtractActorCandidatesIntegration.test_dedupe_across_heuristics` — cross-rule dedupe
- `TestExtractActorCandidatesIntegration.test_primary_excluded` — primary-actor suppression
- `TestExtractActorCandidatesIntegration.test_empty_sentence` — empty-input safety
- `TestExtractActorCandidatesIntegration.test_no_actor_sentence` — pure-data sentence (synthetic-only acceptable)
- `TestExtractActorCandidatesIntegration.test_cleanup_strips_determiners` — leading-determiner strip on output
- `TestActorResolverHeuristicsIntegration.test_off_by_default` — `use_heuristics=False` is the default
- `TestActorResolverHeuristicsIntegration.test_opt_in_finds_role` — `use_heuristics=True` plumbs through, source `"rule"`
- `TestActorResolverHeuristicsIntegration.test_seed_list_takes_priority_over_rule` — regex pass wins over rule pass on cross-source dedupe

### Findings

1. **All 10 heuristics have at least one positive test.** No rule is uncovered. Worst case is partially covered (5 of 10).
2. **Five rules carry a negative test** — rules 1, 2, 4, 5, 6. The other five (3, 7, 8, 9, 10) have only positive cases. False positives are how this whole module gets tuned out by users (per the file's own docstring), so the missing negatives are the more material gap.
3. **Three rules have an alternation that's only partially exercised** — rule 5 (six conditional triggers, only two pinned), rule 7 (nine passive verbs, only one pinned; five modal/aux forms, only one pinned), rule 8 (seven hyphen suffixes, only two pinned). A regex edit could remove an alternation branch without any test failing.
4. **Cross-source dedupe and `ActorResolver` integration are well-covered** (3 tests in `TestActorResolverHeuristicsIntegration`). The integration boundary is not the gap.
5. **Out-of-scope code finding (not a coverage finding).** `_h_appositive` has a redundant `elif` branch: the `if` clause already requires `_is_role_phrase(appos)`, so the `elif` (which also requires it) is unreachable. Behaviour is unaffected — the unreachable branch would have produced the same output as the live branch — but a reader following the dead path will be confused. Not in this audit's scope to fix; logging here so it isn't lost.

### Recommendations (not actions)

These are *what a future remediation would do*, not *what this audit does* — DoD says "no new tests written".

- Add one negative fixture per uncovered rule (3, 7, 8, 9, 10) — five fixtures, ~30 LOC total.
- Add one positive fixture per unexercised alternation branch — 14 fixtures across rules 5, 7, 8 (~80 LOC). The current 36-test suite would grow to ~55. Wall-clock impact is negligible (suite runs in 1 ms).
- Resolve the dead `elif` in `_h_appositive` — either delete or convert to an explicit early-return for clarity.

Whether to act on these is Eric's call. The audit's purpose is to make the gaps visible, not to close them.

---

## 2026-04-30 -- PyInstaller spec audit (DocumentDataExtractor.spec)

**Context.** The spec at `requirements-extractor/packaging/DocumentDataExtractor.spec` defines the air-gapped binary build via PyInstaller. Shipped target has no network access, so a missing `collect_all` entry surfaces as a runtime `ImportError` on the offline network -- not at build time. Last spec-touching commit was `b33be38` ("Extract procedural-table subsystem into procedural.py"); the spec-as-policy-edit commit before it was `2243dfb` ("PyInstaller spec: cover new modules + bundle PDF/dnd extras"). Three modules have entered `requirements_extractor/` since: `actor_heuristics.py` (committed `cfc8ef7`, "Rule-based actor-extraction fallback"), plus `compound.py` and `multi_action.py` (still untracked working-tree files belonging to the 0.6.1/0.6.2 patch line per the night-auditor's PROPOSED commit-or-stash entry).

**Method.** Walked all 25 `.py` files under `requirements_extractor/` plus the entry point `run_gui.py`. Used `ast` to extract every top-level `import X` and absolute `from X import ...` (level == 0; relative imports skipped as internal). Bucketed top-level package names against `sys.stdlib_module_names`, the package's own `requirements_extractor.*` namespace, and the spec's `_bundle()` calls plus tuple-iterated bundle entries. Cross-referenced the explicit internal `hiddenimports` list against the on-disk module set. Stdlib-only audit script; no spec edits.

**State at audit.** `bash scripts/test_all.sh` ALL GREEN, 702/702 across 4 tools. Spec file on disk matches HEAD byte-for-byte. `actor_heuristics.py` is in HEAD (`git ls-tree HEAD`); `compound.py` and `multi_action.py` are untracked (`git status -s` shows `??`).

### Findings

#### A) Third-party imports in shipped-binary code paths but NOT in spec `_bundle` list -- 1 entry

| Top-level package | Used in | Severity |
|---|---|---|
| `yaml` (PyYAML) | `requirements_extractor/config.py:391`, `requirements_extractor/keywords_loader.py:100` | HIGH |

`yaml` is imported lazily inside `_load_yaml_overrides` (config.py) and the YAML branch of the keywords loader (keywords_loader.py), each wrapped in a `try/except ImportError` that falls back to a `"Install with: pip install pyyaml"` user-facing error. On the air-gapped target there is no `pip install`, so the soft message is a hard wall: any user shipping a `*.reqx.yaml` config or a `*.yaml` keywords file gets a runtime failure that looks like a configuration problem but is actually a missing bundle. The repo-root `requirements.txt` and `BASELINE-2026-04-29.md` both list `PyYAML 6.0.3` as a runtime dependency. The spec calls neither `_bundle("yaml")` nor `_bundle("PyYAML")` and lists no PyYAML hidden import. PyInstaller's static analysis MAY pick up the lazy `import yaml` lines via the importedmodule graph, but `collect_all` is the harness this spec uses to drag in package data files (CResolver/CDumper extension binaries, configuration assets); without it those auxiliary files are unreliable across PyInstaller versions and host environments.

#### B) Spec `_bundle` entries NOT directly imported in shipped-binary code -- 24 entries

All 24 are intentional. Grouped by reason:

- **spaCy core transitives** (loaded via spaCy's `catalogue` registry, not by source-level import): `thinc`, `srsly`, `cymem`, `preshed`, `murmurhash`, `blis`, `catalogue`, `wasabi`, `spacy_legacy`, `spacy_loggers`, `confection`.
- **spaCy model + language data**: `en_core_web_sm` (loaded via `spacy.load("en_core_web_sm")` -- string identifier, not Python import), `langcodes`, `language_data`, `marisa_trie`.
- **spaCy CLI / asset-management deps** (used by spaCy itself): `weasel`, `cloudpathlib`, `smart_open`.
- **spaCy v3.7+ schema deps**: `pydantic`, `pydantic_core`, `annotated_types`.
- **CLI dispatch transitives**: `typer`, `click`.
- **pdfplumber backend**: `pdfminer` (pdfplumber depends on it; the spec bundles it independently as belt-and-braces).

The spec's own comments at lines 41-43 ("Optional NLP stack -- bundled so 'Use NLP' works out of the box") and lines 73-75 ("best-effort treatment as the NLP stack ... bundled when installed in the build venv, silently skipped when absent so a CLI-only build isn't forced to drag them in") are the operative policy. **No proposal -- keep all 24.**

#### C) Internal `requirements_extractor.*` modules NOT in explicit `hiddenimports` -- 3 entries

| Module | Tracked? | Import path in code | Verdict |
|---|---|---|---|
| `requirements_extractor.actor_heuristics` | YES (commit `cfc8ef7`) | Lazy import inside `actors.py:252` -- `from .actor_heuristics import extract_actor_candidates` | **gap, shipping now** |
| `requirements_extractor.compound` | NO (untracked) | Top-level static import in `parser.py:271` -- `from . import compound as _compound` | gap, pre-emptive |
| `requirements_extractor.multi_action` | NO (untracked) | Top-level static import in `parser.py:275` -- `from . import multi_action as _multi_action` | gap, pre-emptive |

The spec's stated policy on this list (`DocumentDataExtractor.spec` lines 95-96): "Keep this list in sync with `requirements_extractor/*.py`. Listing them explicitly is belt-and-braces over PyInstaller's static analysis -- a few are imported via dynamic dispatch which static analysis sometimes misses." `actor_heuristics` is exactly the dynamic-dispatch pattern the comment flags -- a deferred `from .X import Y` inside a method body. PyInstaller MAY pick it up via the relative-import graph; the explicit list exists because MAY is not the bar. `compound` and `multi_action` are top-level static imports and would normally be caught, but spec policy says list them anyway. They cannot ship until the 0.6.1/0.6.2 patch line is committed (auditor's PROPOSED P1, unapproved).

#### D) Spec `excludes` -- 13 entries, all confirmed unused

`matplotlib`, `scipy`, `numpy.distutils`, `PIL.ImageTk`, `PyQt5`, `PyQt6`, `PySide2`, `PySide6`, `IPython`, `jupyter`, `notebook`, `pytest`, `sphinx`. None appear as top-level imports in any shipped-binary code path. Excludes are consistent with the code; no action.

### Findings summary

1. **One shipping-now gap: `yaml` is missing from the spec.** Any YAML config or YAML keywords file on the air-gapped target fails with the project's own "Install with: pip install pyyaml" message. Severity HIGH for any user shipping `*.reqx.yaml` or `*.yaml`.
2. **One shipping-now gap: `requirements_extractor.actor_heuristics` is missing from the explicit internal hiddenimports.** Reached only through a lazy-inside-function import -- the exact dynamic-dispatch pattern the spec author flagged.
3. **Two pre-emptive gaps: `compound`, `multi_action`.** Won't ship until the 0.6.1/0.6.2 patch line is committed (auditor's PROPOSED P1, unapproved). Whoever lands that commit must also amend the spec.
4. **Twenty-four `_bundle` entries that look like dead weight are not.** They are spaCy + pdfplumber transitive deps whose `catalogue`/registry-based loading defeats PyInstaller's static analysis. Do not propose removal.
5. **`excludes` list is healthy.** Thirteen entries; all confirmed absent from shipped-binary code paths.

### Recommendations (not actions)

DoD: "Do NOT edit the spec -- propose changes via PROPOSED.md if any are warranted." A PROPOSED.md entry filed in the same run captures these for the evening review.

- Add `"yaml"` to the optional add-ons tuple at lines 76-81 (alongside `pdfplumber`, `pdfminer`, `tkinterdnd2`). One line; the existing best-effort treatment is correct (silently skipped if PyYAML isn't installed in the build venv).
- Add `"requirements_extractor.actor_heuristics"` to the explicit internal hiddenimports list at lines 96-119. One line.
- Bundle the `compound` and `multi_action` additions into whatever commit lands the 0.6.1/0.6.2 patch line -- both modules need to enter the explicit hiddenimports list at the same time the source files become tracked. Two lines; gated on a separate decision.

The audit script and the per-finding cross-reference are in this entry; a future re-audit reproduces by re-running the same `ast`-based walk and re-comparing against the spec's `_bundle()` and `hiddenimports` extracted via `re`. No new tooling needed.
