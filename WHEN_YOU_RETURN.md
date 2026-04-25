# When you return — start here

**Open `ACTION_ITEMS.md` first.** It's the consolidated overnight log.

## Top-priority decision (5 min)

Three top-level dirs are **untracked in git** with no nested `.git/` and no
`.gitignore` rule excluding them: `compliance-matrix/`, `nimbus-skeleton/`,
`process-tools-common/`. Most likely "never `git add`-ed yet". Decide:
either `git add` them as part of the monorepo, or add them to
`.gitignore` if they're meant to live separately. See Phase 0 in
`ACTION_ITEMS.md` for the integrity check details.

## What shipped overnight

- `nimbus-skeleton`: **BPMN 2.0 emitter** (`--bpmn` flag, +14 tests)
- `requirements-extractor`: **rule-based actor-extraction fallback**
  (10 heuristics, opt-in, +36 tests)
- Two files were truncation-recovered earlier (`cli.py`, `actors.py`) —
  diff carefully before committing.

## Suggested order

`ACTION_ITEMS.md` → review diffs → run the three test suites
(`requirements-extractor` 505, `nimbus-skeleton` 33, `compliance-matrix`
23) → commit when satisfied.
