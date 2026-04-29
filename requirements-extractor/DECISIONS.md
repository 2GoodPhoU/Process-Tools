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
