# Process-Tools — Consolidated Action Items

**Last updated:** 2026-04-25 (overnight session)
**Status:** All work uncommitted; Eric reviews and commits in the morning.

---

## Top-of-doc summary

| Unit                   | Status today                                            | Tests added |
|------------------------|---------------------------------------------------------|-------------|
| nimbus-skeleton        | BPMN 2.0 emitter shipped (--bpmn flag); 33 tests pass   | +14 tests   |
| requirements-extractor | Rule-based actor-extraction fallback shipped (10 rules) | +36 tests   |
| requirements-extractor | Cross-tool integration test (prior session, retained)   | n/a         |
| compliance-matrix      | Fuzzy-ID matcher (prior session, retained)              | n/a         |
| nimbus-skeleton        | Review-writer source-text enhancement (prior, retained) | n/a         |
| **Total green tests**  | requirements-extractor 505 / nimbus-skeleton 33         |             |

**Highest-leverage item this pass:** `nimbus-skeleton` BPMN 2.0 XML emitter. Triggered by the alternatives-survey finding that TIBCO Nimbus on-prem retired Sept 1, 2025 — BPMN 2.0 is the recommended interchange path forward.

**Biggest concern surfaced:** the `compliance-matrix/`, `nimbus-skeleton/`, and `process-tools-common/` directories are **entirely untracked in git** with no nested `.git/` and no `.gitignore` rule excluding them. This is most likely "never `git add`-ed yet", not "intentionally separate repos". Eric should decide what to do (see below).

---

## Phase 0 — Integrity / git tracking findings (no fixes applied)

`git status` at repo root shows:

- **Tracked + modified:** `requirements-extractor/README.md`, `requirements-extractor/requirements_extractor/__init__.py` (plus three deleted PLAN-*.md files staged in working tree).
- **Untracked entirely:** `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`, `requirements-extractor/CHANGELOG.md`, `requirements-extractor/archive/`, `requirements-extractor/docs/INTEGRATION.md`, `requirements-extractor/research/`, `requirements-extractor/scripts/`, `requirements-extractor/tests/integration/`, `ACTION_ITEMS.md`, `README.md`.

Checks:

- No nested `.git/` directory in any of `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`. They are not separate repos.
- `.gitignore` does not exclude any of those directories. Their untracked status is "never added", not "deliberately ignored".
- `compliance-matrix/compliance_matrix/loader.py` is **clean** post the prior session's null-byte fix: 2339 bytes, zero null bytes, ends in valid Python (`load_dde_xlsx(procedure_path, side="procedure"),\n    )\n`), and `py_compile` passes. The fix held.

**Recommendation for Eric:** decide one of (a) `git add` all three top-level dirs and commit them as part of the monorepo, or (b) explicitly add `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/` to `.gitignore` if they're meant to be separate repos / vendored copies. Either is fine; the current state is just ambiguous.

---

## Phase 1 — BPMN 2.0 emitter for `nimbus-skeleton` (THIS SESSION)

**Why:** the research note `requirements-extractor/research/2026-04-25-stack-alternatives-survey.md` flagged that TIBCO Nimbus's on-premise product retired Sept 1, 2025 (no new subscriptions, no renewals). BPMN 2.0 is the open-standard process-modelling interchange and the recommended migration path.

**What shipped:**

- `nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py` (~270 lines). Full element coverage:
  - `<bpmn:definitions>` root with proper namespaces (BPMN, BPMNDI, DC, DI, XSI)
  - `<bpmn:collaboration>` + `<bpmn:participant>` (single-pool wrapper)
  - `<bpmn:process>` with `<bpmn:laneSet>` / `<bpmn:lane>` per actor (swimlanes)
  - `<bpmn:task>` per Activity (with `<bpmn:documentation>` for flagged ones)
  - `<bpmn:exclusiveGateway>` per Gateway (XOR — closest 1:1 for the single-condition Skeleton model)
  - `<bpmn:startEvent>` / `<bpmn:endEvent>` bracketing
  - `<bpmn:sequenceFlow>` edges; each node also declares its `<bpmn:incoming>` / `<bpmn:outgoing>` (Camunda Modeler is strict about this)
  - `<bpmn:textAnnotation>` + `<bpmn:association>` for free-text Notes
- Hand-built XML using `xml.sax.saxutils.escape` + `quoteattr`, mirroring the XMI emitter convention. Byte-stable across runs.
- BPMNDI graphical layout intentionally **omitted** — modern BPMN tools auto-layout on import; pixel coordinates would just be wrong.
- Wired into `cli.py` as `--bpmn` flag (additive — existing emitters unchanged). Default off so the standard 5-file output stays unchanged unless explicitly requested.
- 14 tests in `tests/test_bpmn_emitter.py`: structural round-trip (parse-and-assert), byte-stability, ID safety (special-char actor names yield NCName-valid IDs), empty-skeleton case, CLI flag wiring.
- Module docstring captures the design choices explicitly (gateway-collapse rationale, why no DI section, exporter conventions).

**Run:** `nimbus-skeleton --requirements REQS.xlsx --output-dir OUT/ --bpmn` adds `<basename>.bpmn` to the existing 5 outputs.

**Open follow-ups:**
- If/when `Skeleton.Gateway` learns a `kind` field (parallel/inclusive vs exclusive), expand the `bpmn:gateway` switch in `bpmn.py`.
- If a public BPMN 2.0 XSD is available offline at Eric's site, add an XSD-validation test to the suite.

---

## Phase 2 — Rule-based actor-extraction fallback (THIS SESSION)

**Why:** the alternatives survey called out NLP-bundle (GLiNER) gating as not-ready in 2026; the rule-based path stays the offline-network default. Without a seed actors list, secondary-actor extraction was producing nothing — even on sentences that obviously named another actor.

**What shipped:**

- `requirements-extractor/requirements_extractor/actor_heuristics.py` (~460 lines). Ten heuristics, each a pure `str -> List[str]` function with the example sentence inline. Each rule is conservative — false positives are worse than false negatives because reviewers audit the output xlsx and noise costs them time.

  | # | Rule                       | Example                                                              |
  |---|----------------------------|----------------------------------------------------------------------|
  | 1 | `_h_by_agent`              | "The report shall be approved by the **Reviewer**."                  |
  | 2 | `_h_send_to`               | "The System shall forward the alert to the **Notification Service**." |
  | 3 | `_h_possessive`            | "The **Operator**'s screen shall display the alert."                 |
  | 4 | `_h_compound_subject`      | "The **Operator** and the **Supervisor** shall co-sign the release." |
  | 5 | `_h_conditional_subject`   | "If the **Auditor** approves the change, ..."                        |
  | 6 | `_h_for_beneficiary`       | "...generate a report for the **Compliance Officer**."               |
  | 7 | `_h_implicit_passive`      | "Every login attempt shall be logged." → `(implicit System)` flag    |
  | 8 | `_h_hyphenated_role`       | "An **Operator**-initiated abort shall halt the run."                |
  | 9 | `_h_between`               | "Communication between the **Operator** and the **Auth Service**..." |
  |10 | `_h_appositive`            | "The QA Lead, the **Reviewer**, shall countersign..."                |

- Role-shape probe (`_is_role_phrase`) gates every rule's output: head noun must be in a curated role-noun list (Service, System, Manager, ...) OR the token must end in an agent-noun morpheme (-er/-or/-ist/-ant/-ent) with Title-case OR it's a 2-6-letter all-caps acronym. Filters lowercase fragments and capitalised function words ("If", "When") that masquerade as actors.

- Determiner / possessive cleanup mirrors the existing `canonicalise_ner_name` helper so heuristics output is comparable to NER hits without re-canonicalising.

- Wired into `ActorResolver` via opt-in `use_heuristics=True` constructor flag. New `iter_heuristic_hits()` method, plumbed through `iter_matches()` as a third pass with source label `"rule"`. Order is regex → nlp → rule (highest-confidence first; cross-source dedup).

- Default off so existing test fixtures (which depend on no-secondary-actor behaviour without seed list/NLP) stay green. Caller opts in via flag.

- 36 tests in `tests/test_actor_heuristics.py`: per-rule positive + negative tests (most rules have a "fires on the case it covers" test paired with a "does NOT fire on a near-miss" test, since false-positive control is the real failure mode), end-to-end through `extract_actor_candidates`, and three integration tests for `ActorResolver(use_heuristics=True)`.

- Two regex bugs were caught + fixed before shipping: `re.IGNORECASE` was making the `[A-Z]` actor-name anchors match lowercase tokens, causing over-match. Fixed by wrapping each actor-capture group in `(?-i:...)` so the verb-side stays case-insensitive but the actor-shape stays case-sensitive.

**Open follow-ups:**
- CLI flag in `requirements-extractor` to enable heuristics (currently only available via Python API). Recommended: `--actor-heuristics` (default off).
- GUI checkbox for the same. Sketch in `gui.py`.
- If users find the role-noun list too tight, expose it as configurable via `Config`.

---

## Carry-forward from prior overnight session (RETAINED)

These shipped earlier tonight and remain valid. Re-checked: all listed files present, all listed tests still pass.

### Phase 3 (prior) — Cross-tool integration test
- `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py` (243 lines)
- `requirements-extractor/docs/INTEGRATION.md`

### Phase 4b (prior) — Compliance-matrix fuzzy-ID matcher
- `compliance-matrix/compliance_matrix/matchers/fuzzy_id.py` (225 lines, pure stdlib Levenshtein)
- `compliance-matrix/tests/test_fuzzy_id.py` (20 tests)
- CLI: `--fuzzy-id-threshold` (default 0.85), `--no-fuzzy-id`
- README updated

### Phase 4c (prior) — Nimbus-skeleton review-writer enhancement
- `nimbus-skeleton/nimbus_skeleton/review_writer.py` now takes `dde_rows=None`, adds "Source Requirement" column
- `nimbus-skeleton/tests/test_review_writer.py` (3 tests)
- README updated

### Loader corruption fix (prior, verified holding)
- `compliance-matrix/compliance_matrix/loader.py`: 2339 bytes, 0 null bytes, compiles clean. Re-verified 2026-04-25.

### Other prior-session items
- Phase 0–5: docs refresh, test coverage audit, NLP-bundle smoke-test script, cleanup pass (PLAN-*.md archived).
- Honesty audit: prior-prior session's "blocked, needs Eric input" claims were overly conservative; all three were straightforward.

---

## Morning TODO (Eric, est. 5–10 min)

1. **Decide git tracking** for `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`. Either `git add` them or add them to `.gitignore`. Right now they're orphaned in the working tree.
2. **Spot-check the BPMN output** by running:
   `cd nimbus-skeleton && python run_cli.py --requirements <a real REQS.xlsx> --output-dir /tmp/bpmn-test --bpmn`
   then opening the resulting `.bpmn` in Camunda Modeler ([https://camunda.com/download/modeler/](https://camunda.com/download/modeler/)) or bpmn.io. Goal: confirm the tool you'd actually use can read it.
3. **Review the heuristics rule list** in `requirements_extractor/actor_heuristics.py` — the role-noun whitelist (`_ROLE_HEAD_NOUNS`) is the part most likely to need tuning to your actual corpora.
4. **Run all tests:**
   - `cd requirements-extractor && python -m unittest discover -s tests` (505 expected)
   - `cd nimbus-skeleton && python -m unittest discover -s tests` (33 expected)
   - `cd compliance-matrix && python -m unittest discover -s tests` (whatever that suite size is)
5. **Commit** when satisfied. Suggested commit grouping:
   - one commit per directory (compliance-matrix, nimbus-skeleton, process-tools-common) once you decide on tracking
   - one commit for `requirements-extractor` deltas (heuristics + tests + ACTION_ITEMS update)

---

## Risk register

- **Untracked top-level dirs.** Highest priority — they're load-bearing code with no version control. (See Phase 0 above.)
- **BPMN emitter not yet validated against XSD.** Round-trip + structural tests cover ~80% of likely failure modes; the remaining 20% is "the modeler refuses to import it for a subtle reason". Mitigation: open the output in Camunda Modeler before rolling out.
- **Heuristics false-positive rate unknown on real specs.** Tested against tightly-tuned example sentences. Real corpora may show different rates. Mitigation: heuristics are off by default; opt-in only.
- **Rule-based heuristics hard-coded English.** Defense / aerospace specs Eric processes are English-only, so this is fine, but worth flagging.
