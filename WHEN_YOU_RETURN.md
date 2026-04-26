# When you return — start here

The current canonical entry points are:

1. **[`ROADMAP.md`](./ROADMAP.md)** — unified roadmap across all four
   tools (Shipped / In Progress / Next / Later, plus risk register).
2. **[`REFACTOR.md`](./REFACTOR.md)** — refactor punch list with
   sign-off per item. Stability + dedup + trim findings, sized and
   risk-rated.
3. **[`COMMIT_PLAN.md`](./COMMIT_PLAN.md)** — current working-tree
   state and suggested commit grouping.

`ACTION_ITEMS.md` is the historical overnight log (2026-04-25);
its Phase 0 finding has been resolved and its open items migrated
into `ROADMAP.md` / `REFACTOR.md`.

## Workshop state at a glance

- **570 tests across the workshop** — DDE 505, nimbus-skeleton 33,
  compliance-matrix 30 (after S1's regression test addition),
  process-tools-common 9.
- **Strategic context:** TIBCO Nimbus on-prem retired 2025-09-01;
  BPMN 2.0 is the forward-target interchange format. The
  `nimbus-skeleton` tool ships both `.vsdx` (legacy Nimbus) and
  `.bpmn` (Camunda / bpmn.io / etc.) emitters.
- **Run all tests:** `cd <tool>/ && python -m unittest discover tests`
  for each of the four tools.
