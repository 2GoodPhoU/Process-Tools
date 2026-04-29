# BPMN structural validation — programmatic pass

> Worker run, 2026-04-29 09:00 (process-tools-worker-9am). Companion to
> `2026-04-29-camunda-import-checklist.md`. This file captures the part of
> the QUEUE.md P1 BPMN/Camunda validation that does NOT need Camunda Modeler
> desktop. The GUI step itself is bailed out to NEEDS-INPUT.md.

## What I did

Walked `samples/bpmn_validation/simple_two_actors.bpmn` against the
section-2 pass-criteria table from
`research/2026-04-29-camunda-import-checklist.md` programmatically: parsed
the file with `xml.etree.ElementTree` (stdlib only, air-gap-safe), checked
every assertion in the table that's verifiable from the file alone, and
re-ran the nimbus-skeleton unittest suite (the section-5 list).

Did NOT open the file in Camunda Modeler 5.x desktop. Did NOT drop the file
on demo.bpmn.io. Did NOT re-save in Camunda and structural-diff. Those are
the section-6 steps 1, 3, and 4, and they require either a human or a
computer-use Worker — see NEEDS-INPUT.md entry from this run.

## Test suite (section 5 of the checklist)

`bash scripts/test_all.sh`: ALL GREEN, 702 tests across 4 tools, 0 errors,
0 failures. nimbus-skeleton specifically: 40/40 pass, including the full
`test_bpmn_emitter.py` set:

- `test_root_is_bpmn_definitions`
- `test_has_collaboration_and_process`
- `test_lane_per_actor`
- `test_tasks_match_activities`
- `test_start_and_end_events`
- `test_sequence_flows_form_a_chain`
- `test_exclusive_gateway_for_conditional`
- `test_flagged_activity_has_documentation`
- `test_note_becomes_text_annotation`
- `test_two_renders_equal` (byte-stability across two emitter runs)
- `test_plane_references_collaboration` (DI)
- `test_shape_count_matches_semantic_counts` (DI)
- `test_edge_count_matches_sequence_and_association_count` (DI)
- `test_every_edge_has_at_least_two_waypoints` (DI)
- `test_every_shape_has_integer_bounds` (DI)
- `test_shape_and_edge_bpmnelement_refs_resolve` (DI)
- `test_empty_skeleton_still_emits_diagram` (DI)
- ID-safety, CLI-flag, and empty-skeleton tests.

That accounts for the section-5 ~80% of the failure surface.

## Programmatic walk of the section-2 table

Validator script: `/tmp/bpmn_run/validate_bpmn_structural.py` (scratch,
stdlib-only, ~180 LOC). Walks 24 checks against the file. **Result: 24/24
PASS, 0 FAIL.**

| # | Check                                                              | Status |
| - | ------------------------------------------------------------------ | ------ |
|  1 | `definitions/@targetNamespace` is set                              | PASS   |
|  2 | Exactly one `bpmn:participant` (pool)                              | PASS   |
|  3 | Pool labelled "Process Skeleton"                                   | PASS   |
|  4 | Exactly one `bpmn:process`                                         | PASS   |
|  5 | Two lanes: "Operator" and "Supervisor"                             | PASS   |
|  6 | Operator lane contains 2 `flowNodeRef`s                            | PASS   |
|  7 | Supervisor lane contains 2 `flowNodeRef`s                          | PASS   |
|  8 | 4 `bpmn:task` elements                                             | PASS   |
|  9 | Exactly one `bpmn:startEvent`                                      | PASS   |
| 10 | Exactly one `bpmn:endEvent`                                        | PASS   |
| 11 | 0 gateways (per fixture spec)                                      | PASS   |
| 12 | 0 text annotations (per fixture spec)                              | PASS   |
| 13 | 6 `bpmn:sequenceFlow` elements                                     | PASS   |
| 14 | Every `flowNodeRef` resolves to a real flow node id                | PASS   |
| 15 | Every `sequenceFlow/@sourceRef` resolves                           | PASS   |
| 16 | Every `sequenceFlow/@targetRef` resolves                           | PASS   |
| 17 | `<incoming>` refs mirror `sequenceFlow/@targetRef`                 | PASS   |
| 18 | `<outgoing>` refs mirror `sequenceFlow/@sourceRef`                 | PASS   |
| 19 | `<bpmndi:BPMNDiagram>` present                                     | PASS   |
| 20 | `<bpmndi:BPMNShape>` for every pool / lane / flow-node             | PASS   |
| 21 | `<bpmndi:BPMNEdge>` for every `sequenceFlow`                       | PASS   |
| 22 | Every `BPMNEdge` has ≥2 waypoints                                  | PASS   |
| 23 | All `BPMNShape` bounds are integer-pixel                           | PASS   |
| 24 | Cross-lane edges have ≥4 waypoints (right-angle elbow)             | PASS   |

Rows 14–18 are the ones the research file flagged as "what would actually
block import" (section 1: `flowNodeRef` to a non-existent id surfaces an
unresolved-reference warning; `incoming`/`outgoing` mismatch with
`sequenceFlow` source/target makes Camunda Modeler reject the file). All
clean.

Rows 19–24 are the BPMNDI requirements from section 2 of the checklist
(2026-04-26 DI fix). All clean.

## What this does NOT cover

The remaining ~20% per the research file is "the modeler refuses for a
subtle reason" — i.e. things only a real renderer can surface:

- Whether Camunda Modeler 5.x **actually opens** the file without throwing
  an `unmarshalling failed` / `no diagram to display` modal.
- Whether the rendered **canvas** matches the section-2 visual table
  (rendering position of tasks within lanes, edge routing, label
  truncation).
- Whether **demo.bpmn.io** (the bpmn.io reference renderer) accepts the
  file and renders it identically.
- Whether a **save round-trip** in Camunda Modeler preserves the
  structure (ids, lane membership, source/target). Camunda reformats XML
  on save — byte diff is meaningless, structural diff is the meaningful
  check.
- Which of Camunda's **lint warnings** actually surface against this
  fixture (the research file lists likely-noise: platform-tag warnings,
  `executionPlatform` missing, Zeebe runtime hints; all expected non-fatal
  per section 1).

These are section-6 steps 1, 3, and 4 of the procedure. They cannot be
exercised by an unattended Worker.

## Recommendation

Based on the programmatic checks + the unittest suite, **there is no
pre-import structural reason to expect the file to fail to load in either
Camunda Modeler 5.x or demo.bpmn.io.** The 2026-04-26 DI fix is the load-
bearing change; this validator confirms it's still doing its job. The
researcher's section-1 forecast — "opens cleanly with platform-tag lint
warnings only" — looks accurate based on the file.

Worker-9am is bailing out to NEEDS-INPUT.md per worker bailout rule
("the task is larger than you thought and would clearly take more than
one Worker run") — the GUI step legitimately cannot be done from an
unattended scheduled run. See NEEDS-INPUT entry for the two paths to
unblock.

## Validator script

Saved to `/tmp/bpmn_run/validate_bpmn_structural.py` for this run. It's
~180 LOC of stdlib Python and would make a clean addition to
`nimbus-skeleton/scripts/` once the orphan-dirs decision lands and writes
under that tree are unblocked. The PROPOSED.md item from the researcher
("Add a small structural-diff helper for BPMN before/after Camunda
re-save") covers the after-Camunda half of this; this validator covers
the before-Camunda half.
