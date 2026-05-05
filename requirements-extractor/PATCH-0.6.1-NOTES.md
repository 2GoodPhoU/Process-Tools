# PATCH-0.6.1 — Compound-requirement detection

> Authored as an autonomous overnight patch on 2026-04-27.
> Uncommitted in the working tree for Eric's morning review.

## Summary

Adds an additive parser pre-pass that detects modal-verb paragraphs
ending with `:` followed by a bulleted / dashed / numbered / lettered
list of conditions, and aggregates them into ONE compound requirement
instead of dropping the lead-in (fragmentary) and the bullets (no modal
verbs).

The trigger pattern, from the field gap that motivated this patch:

> Programs shall comply with this document if they:
> - Domestic US-Based program, and
> - exceed 12 months in duration, and
> - Pre-preliminary design review &lt;MRL 5 overall maturity, and
> - design and/produce hardware content

In 0.6.0 this paragraph emitted **zero** requirements (lead-in ends with
`:` so detector treated it as fragmentary; bullets had no modal verbs).
In 0.6.1 it emits **one** compound requirement whose text aggregates
the lead-in plus all four AND-joined conditions, with a `Compound
requirement: lead-in + N and-joined item(s).` note for reviewer triage.

## Cases handled

1. **Core compound detection** — modal+colon lead-in followed by a
   contiguous run of list items.  Items can be Word-styled bullets
   (`numPr` element / `List Bullet` / `List Number` style) OR
   plain-text-marker paragraphs (dashes, asterisks, numbered, lettered,
   Roman numerals — see `compound._LIST_MARKER_RE`).
2. **and / or / unless connector preservation** — inferred from items'
   trailing connector words.  Priority: `unless` > `or` > `and`.  The
   synthetic compound text is rendered with an explicit clause
   (`(all of)` / `(any of)` / `(unless any of)`) so reviewers see the
   polarity at a glance.
3. **Mixed markers** — bullets, dashes (`—`, `–`, `-`), asterisks (`*`),
   numbered (`1.`, `2.`, `3)`), lettered (`a.`, `b)`, etc.), and Roman
   numerals (`i.`, `iv)`).  All recognised; lists may mix marker styles.
4. **`where:` exclusion** — a lead-in whose last word before `:` is
   `where` introduces a glossary / definitions block.  Compound
   detection skips it; the legacy walker handles each paragraph
   individually so definitions still flow into actor extraction.
5. **`unless:` connector** — aggregation fires; connector inferred as
   `unless`; rendered text uses `(unless any of)` to flag exclusion
   semantics.

## Files changed

| File | Lines (before → after) | Change |
|------|------------------------|--------|
| `requirements_extractor/__init__.py` | 7 → 7 | Version bump 0.6.0 → 0.6.1. |
| `requirements_extractor/compound.py` | NEW | 320-line module.  Pure helpers; no docx dependency. |
| `requirements_extractor/config.py` | 456 → 548 | New `CompoundConfig` dataclass; `_normalise_extraction_namespace` collapses `extraction.compound` to flat `compound` shape; section registered. |
| `requirements_extractor/parser.py` | 749 → 914 | `_walk_content` runs compound pre-pass before the legacy paragraph walk; lead-in / item indices claimed; aggregated requirement emitted with a `(compound)` block_ref suffix. |
| `samples/procedures/compound/generate.py` | NEW | Generator for the five compound fixtures. |
| `samples/procedures/compound/fixture_*.docx` | NEW (5 files) | Synthetic compound fixtures. |
| `tests/test_compound.py` | NEW | 45 tests across pure helpers, end-to-end fixtures, and config wiring. |
| `tests/test_regression_baseline.py` | NEW | 3 tests assert every existing top-level procedure fixture still matches the 0.6.0 baseline JSON byte-for-byte. |
| `tests/baselines/procedures_baseline_0_6_0.json` | NEW | 60 KB JSON snapshot of the 0.6.0 row-level output for the 11 existing fixtures. |
| `CHANGELOG.md` | (Unreleased) | New `[0.6.1]` section. |

## Defensive design

- **Additive** — compound detection runs as a pre-pass.  When it finds
  no groups, behaviour is byte-identical to 0.6.0.  The regression test
  suite (`tests/test_regression_baseline.py`) pins this against a
  captured baseline of all 11 existing top-level fixtures.
- **Wrapped** — both the pre-pass scan and the per-group emit are
  wrapped in `try / except Exception` blocks that log a warning via
  the existing `_logging.logger` and fall back to the legacy
  per-paragraph behaviour.  One bad parent never aborts a run.
- **Config-flagged** — new `compound.enabled` (or
  `extraction.compound.enabled` in YAML) flag, default ON.  Set False
  in any `--config` or per-doc `<stem>.reqx.yaml` to revert to legacy
  behaviour without rebuilding the binary.

## Test results

```
$ python3 -m unittest discover tests
....... (559 tests) .......
Ran 559 tests in 6.19s
OK
```

Breakdown:
- 511 pre-existing tests — all green, no edits to existing tests.
- 45 new tests in `test_compound.py` — pure-helper detection rules,
  end-to-end fixture parses, config-flag wiring.
- 3 new tests in `test_regression_baseline.py` — count + per-row
  content match against the 0.6.0 JSON baseline for every fixture in
  `samples/procedures/`.

## Known limitations / deferred cases

Out of scope for 0.6.1; design call needed before implementation:

- **Nested lists** — a sub-bullet inside a bullet item.  Today the
  pre-pass treats the sub-bullet as a sibling of the parent's list,
  which would produce a malformed compound.  The current detector
  guards against this conservatively by only claiming items whose
  styling / marker matches at the same level (no depth tracking) —
  in practice this means nested lists land back in the legacy walker.
- **List items with their own modal verbs** — e.g. a bulleted list of
  sub-requirements that each say "shall...".  These are arguably
  *sub-requirements within a compound* and need a design call: do we
  emit one row per sub-requirement (today's behaviour, since each
  modal-bearing bullet is captured by the legacy walker's bullet
  path), or aggregate as a single compound?
- **Tables of conditions** — different pipeline (the parser walks
  table rows separately).  Separate patch.

## Migration notes

None.  Additive only.  No CLI surface changed; no output schema changed
(the new compound rows use the existing `Requirement` dataclass — only
their `block_ref` carries a `(compound)` suffix and their `notes`
column has a `Compound requirement: lead-in + N {connector}-joined
item(s).` line for reviewer triage).

## Autonomous design call — please sanity-check

The compound pre-pass is **disabled** when `force_requirement=True`
(i.e. inside procedural required-action tables).  Reasoning: those
tables already aggregate every row as an atomic binding requirement by
virtue of the `Required Action` column header; aggregating a
lead-in + bullets there would *drop* atomic requirements rather than
capture additional ones.

Concretely, the existing `procedural_bullet_rows.docx` fixture has
exactly the modal+colon+bullets shape the patch was authored for, but
the existing test `TestProceduralBulletRows` expects one row per
bullet (10 total).  Disabling compound in force-requirement mode keeps
that fixture at 10 rows and preserves the `(Required Action)` header
contract.

This is the right call for the procedural table case I can see, but it
means a compound pattern *inside* a procedural required-action table
will silently fall through to the per-bullet path.  If real procedural
tables contain compound patterns we'd want aggregated, this needs a
follow-up: probably an in-table signal (e.g. lead-in in a separate
sub-table cell) rather than running the pre-pass blindly inside
`force_requirement` walks.

The toggle is in `parser._walk_content`:

```python
if force_requirement:
    compound_enabled = False
```

Flip-and-test: setting that to `if False:` re-enables compound inside
procedural tables and produces the `1 != 4` / `4 != 10` test failures
in `TestProceduralBulletRows`.
