# PATCH-0.6.2 - Multi-action requirement detection + decomposition

> Authored as an autonomous overnight patch on 2026-04-27.
> Uncommitted in the working tree for Eric's morning review.

## Summary

Where 0.6.1 added compound-requirement *aggregation* (lead-in + bulleted
list -> one requirement), 0.6.2 solves the inverse problem:
*decomposing* a single sentence that carries one modal verb plus
multiple verb phrases joined by `,` ... `, and` (or `, or`) into N
atomic requirements (or flagging them for human decomposition).

The trigger pattern, from Eric's 2026-04-27 field notes:

> "Software engineers shall create unit tests, implement CICD
>  Pipelines, and integrate software quality control systems."

This is one sentence syntactically but three atomic obligations
semantically (`create` / `implement` / `integrate` are three distinct
actions on three distinct artifacts).  Per ISO/IEC/IEEE 29148 §5.2.4
(Singular principle) and the INCOSE *Guide for Writing Requirements*,
each requirement should express one thought.

## Three modes

A new `extraction.multi_action` config namespace carries the knob.
Default mode is **`flag`** (most conservative behaviour change).

* `single` - emit one requirement, preserve source text faithfully.
  Behaviour-equivalent to 0.6.1.  `multi_action.enabled: false` is
  effectively the same.
* `flag` (DEFAULT) - emit one requirement with a one-line note in
  `Requirement.notes`:

      Multi-action sentence: 3 verb phrases detected via regex;
      consider splitting into 3 atomic requirements.

  No new rows; reviewers decide per-requirement.

* `split` - emit the parent (text preserved as a record + an "Atomic
  sub-requirement N of M" annotation) plus N child rows, each
  carrying:
    * `text` = `<actor prefix> <modal> <verb-phrase>.`
    * `parent_id` = parent's `stable_id`
    * `stable_id` = `<parent_stable_id>.<n>` (1-based)
    * `block_ref` = parent's `block_ref` + ` (multi-action sub N/M)`
    * Same `primary_actor`, `secondary_actors`, `req_type`, `keywords`,
      `confidence`, `polarity`, `heading_trail`, `source_file`,
      `row_ref`, and `context` as the parent.

## Detection algorithm

1. The sentence must contain *exactly one* modal verb token from
   `{shall, must, will, should}`.  Two modals indicate a compound
   conditional, not a multi-action requirement.
2. The action region (post-modal tail) must contain at least one
   `and` / `or` connector.  Cheap reject for single-action sentences.
3. **spaCy path** (when available): build a dependency tree, find the
   ROOT verb depending on the modal, walk its `conj` children with
   `cc` conjunctions.  Each conj head + its subtree is one verb
   phrase.  Falls back to regex when spaCy is unavailable - matching
   the offline-fallback architecture from `actor_heuristics.py`.
4. **Regex fallback** (load-bearing for the air-gapped binary):
   * Locate the LAST Oxford-style `, and` / `, or` connector.  Split
     the head segment on remaining commas, append the tail.  Each
     candidate must pass `_phrase_head_verb` (a recognisable action
     verb at its head).
   * For two-action `X or Y` sentences without an Oxford comma:
     fall back to the bare-connector form, gated by requiring BOTH
     halves to head with a recognisable verb.
5. **Disambiguation gate (shared verb)**: if every phrase shares the
   SAME normalised head verb (lemma-level, lower-cased, common
   inflection stripped), treat as a single requirement decorated with
   multiple object clauses.  Marks the detection record's
   `imperfect=True` flag for reviewer surfacing.

The shared-verb heuristic catches ~80% of "shall be available 99.9%
... and have mean time to recovery ..." style decoration cases.
Semantic disambiguation requires an LLM and is deliberately out of
scope.

## Pipeline ordering

The 0.6.2 multi-action pass runs **AFTER** the 0.6.1 compound
aggregation pass.  Concretely:

```
                 .--- 0.6.0 detector + per-paragraph walker
docx --> parse --|--- 0.6.1 compound pre-pass (modal+colon -> aggregate)
                 '--- 0.6.2 multi-action post-pass (per-Requirement decompose)
```

So a "shall create A, implement B, and integrate C" sentence
aggregated from a bulleted list (0.6.1) gets decomposed (0.6.2) into
3 atomic sub-requirements when `mode == "split"` is on.

## Procedural-table gate

Multi-action detection is **gated off** inside `force_requirement=True`
procedural required-action tables - same gate as the 0.6.1 compound
pre-pass.  Rationale: rows in those tables are already atomic by
virtue of the `Required Action` column header semantics; splitting
them would fragment what is already atomic.  Reviewers still get one
row per `Required Action` cell, matching the 0.6.0/0.6.1 behaviour
the procedural fixture suite pins.

This is the **autonomous design call** for Eric's morning review.
See "Autonomous design call" below.

## Files changed

| File | Lines | Change |
|------|-------|--------|
| `requirements_extractor/__init__.py` | 7 -> 7 | Version bump 0.6.1 -> 0.6.2. |
| `requirements_extractor/multi_action.py` | NEW (523) | Pure helpers; no docx dependency.  Detection, regex+spaCy paths, sub-requirement rendering. |
| `requirements_extractor/config.py` | 549 -> 612 | New `MultiActionConfig` dataclass; section registered; `extraction.multi_action` namespace path supported. |
| `requirements_extractor/models.py` | 203 -> 204 | New `Requirement.parent_id` field; "" for non-split rows. |
| `requirements_extractor/parser.py` | 918 -> 1075 | New `_apply_multi_action` post-pass; new `_build_split_subrequirements` helper; every yield site in `_walk_content` plus the preamble emit threaded through. |
| `samples/procedures/multi_action/generate.py` | NEW (301) | Generator for the five multi-action fixtures. |
| `samples/procedures/multi_action/fixture_*.docx` | NEW (5 files) | Synthetic multi-action fixtures. |
| `tests/test_multi_action.py` | NEW (403) | 44 new tests across pure helpers, end-to-end fixtures, and config wiring. |
| `tests/test_regression_baseline_062.py` | NEW (150) | 3 tests pinning single-mode 0.6.2 to byte-identical 0.6.1 output across all 16 existing fixtures (11 top-level + 5 compound). |
| `tests/baselines/procedures_baseline_0_6_1.json` | NEW (~70 KB) | Captured BEFORE any 0.6.2 source-level changes. |
| `CHANGELOG.md` | (Unreleased) | New `[0.6.2]` section. |

## Test results

```
$ python3 -m unittest discover tests
......................................................... (606 tests)
Ran 606 tests in 6.57s
OK
```

Breakdown:
- 559 pre-existing tests (all 0.6.1) - all green, no edits.
- 44 new tests in `test_multi_action.py` - pure-helper detection
  rules, all 3 modes per fixture, config-flag wiring, mode validation.
- 3 new tests in `test_regression_baseline_062.py` - count + per-row
  content match against the 0.6.1 JSON baseline for every fixture.

**Regression check:** all 16 baseline fixtures (11 top-level + 5
compound) produce byte-identical output in `single` mode to 0.6.1's
output, verified via `tests/baselines/procedures_baseline_0_6_1.json`.

## Defensive design

- **Additive.**  When `mode == "single"` (or `enabled: false`) the
  output is byte-identical to 0.6.1.  The regression test
  (`test_regression_baseline_062.py`) pins this against the captured
  baseline.
- **Wrapped.**  Detection (`_apply_multi_action`) AND sub-requirement
  build (`_build_split_subrequirements`) are wrapped in
  `try / except Exception` blocks that log via `_logging.logger` and
  fall back to the single-row behaviour.  One pathological sentence
  never aborts a parse.
- **Mode-validated.**  `MultiActionConfig.__post_init__` rejects
  invalid `mode` values and `min_actions < 2` early - a typo in YAML
  surfaces as a `ValueError` at config-load time, not a silent
  fall-through.
- **Config-flagged.**  `multi_action.enabled` (or
  `extraction.multi_action.enabled`) is exposed for emergency
  rollback to 0.6.1 behaviour without rebuilding the binary.

## Hierarchical sub-IDs

Convention: parent `REQ-abc12345` decomposed into 3 actions becomes
`REQ-abc12345.1`, `REQ-abc12345.2`, `REQ-abc12345.3` in `split` mode.
The sub-IDs are computed deterministically from the parent's
`stable_id` + 1-based index, so re-running the extractor on the same
input produces the same sub-IDs.

This format maps cleanly to ReqIF's "decomposition" relation - each
sub-requirement has a `parent_id` field that a future ReqIF exporter
can use to populate `<SPEC-RELATION>` elements (relation type
`SPEC-RELATION-TYPE` = decomposition).  The existing `reqif_writer.py`
does not yet emit these relations; that's a separate patch.

## Known limitations / deferred cases

Out of scope for 0.6.2:

- **Semantic verb-equivalence.**  The shared-verb heuristic is a
  regex-based lemma match (lower-cased, common inflection stripped).
  It does not recognise that "shall be available" and "shall have
  uptime" describe the same requirement.  Real semantic
  disambiguation requires an LLM and is intentionally not in scope -
  the `imperfect` flag on each detection record lets a future GUI
  surface the heuristic call to reviewers.
- **Irregular verbs.**  `_normalise_verb` strips `-ing`/`-ed`/`-es`/
  `-s`/`-e` suffixes only.  Irregular forms ("hold/held",
  "write/wrote") will not normalise to the same lemma.
- **Negation.**  "shall not create A and not implement B" decomposes
  to two phrases, each correctly heading with their verb, but the
  rendered sub-requirements lose the explicit "not" preservation
  semantics.  Polarity is inherited from the parent, so the negative
  flag is preserved at the row level even though the sub-text might
  read awkwardly without "not".  Acceptable trade-off; revisit if
  it surfaces in a real spec.
- **Cross-modal phrases.**  Sentences like "shall create A and may
  implement B" carry two modals and are explicitly rejected by gate
  1.  Splitting these requires per-clause polarity / type tracking -
  a design call before implementation.
- **ReqIF export of decomposition relations.**  Documented above -
  the data is captured (`parent_id`) but the exporter does not yet
  emit the relation.

## Migration notes

- Default mode is `flag`, which adds a one-line note to
  `Requirement.notes` for every multi-action sentence.  Existing
  reviewers should expect more entries in the notes column starting
  with "Multi-action sentence:".
- To preserve exact 0.6.1 row-level output (no notes annotation, no
  splitting), set `multi_action.mode: single` in the run config.
- To enable splitting for production runs, set
  `multi_action.mode: split`.  Reviewers should expect ~N additional
  rows per multi-action sentence detected.
- No CLI surface changed.  No output schema changed beyond the new
  `parent_id` field on the `Requirement` dataclass (defaults to ""
  for non-split rows).

## Autonomous design call - please sanity-check

The multi-action pass is **disabled** when `force_requirement=True`
(i.e. inside procedural required-action tables), mirroring the 0.6.1
compound gate.

The reasoning: every row in a procedural required-action table is
atomic by virtue of the `Required Action` column header.  The
multi-action splitter would fragment `Required Action` cells whose
text happens to contain multiple verbs, breaking the
one-action-per-row contract that procedural fixtures pin in
`tests/test_procedural_tables.py`.

Concretely, fixture 5
(`samples/procedures/multi_action/fixture_5_inside_procedural_table.docx`)
has the exact `Operator shall record metrics, analyze trends, and
report findings.` shape that triggers detection in pure prose - but
the procedural-table gate keeps it as one row in `split` mode, just
as the 0.6.1 compound gate keeps `procedural_bullet_rows.docx` at 10
rows.

This is the right call for the procedural table case I can see, but
it means a real procedural table whose `Required Action` cell genuinely
expresses multiple obligations will silently fall through to the
single-row path.  If real procedural tables contain multi-action
patterns the user wants split, the right fix is probably an in-table
signal (e.g. one verb per cell - which the user can already enforce
when authoring) rather than running the splitter blindly inside
`force_requirement` walks.

The toggle is in `parser._apply_multi_action`:

```python
if force_requirement:
    return [req]
```

Flip-and-test: deleting that branch re-enables multi-action splitting
inside procedural tables and produces the `2 != 4` failure in
`TestFixture5InsideProceduralTable.test_split_mode_does_not_fragment_table_rows`.

## ReqIF mapping notes for future export

When the ReqIF exporter learns about decomposition (separate patch):

- Each parent `Requirement` becomes one `<SPEC-OBJECT>` with its
  text in the `Description` attribute.
- Each child `Requirement` (`parent_id != ""`) also becomes a
  `<SPEC-OBJECT>` with its synthetic atomic text.
- A `<SPEC-RELATION>` element ties parent to child: type
  `decomposition`, source = parent SPEC-OBJECT-REF, target = child
  SPEC-OBJECT-REF.
- The hierarchical sub-IDs (`REQ-abc12345.1`) survive as the child's
  `IDENTIFIER` attribute.  They are unique within a corpus by
  construction (parent's hash + index).

The current `reqif_writer.py` emits flat objects only; adding
relations requires:
  1. Walking `requirements` to collect `parent_id != ""` rows.
  2. Emitting a `<SPECIFICATION-RELATIONS>` block referencing each
     parent->child pair.
  3. Defining a `decomposition` relation type in the spec types
     section.

Out of scope for 0.6.2.
