# Queue -- Process-Tools

> Prioritized work waiting to be picked up by Workers. The Planner curates this each morning. Workers pick the top unchecked item.

## Format

Each item:

```
- [ ] [P0|P1|P2] Title -- one-sentence description.
  - Definition of done: ...
  - Notes: ...
```

Use `[in-progress]` instead of `[ ]` if a Worker started but couldn't finish (with a note in NEEDS-INPUT.md about what blocked them).

---

- [in-progress] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import. **REQUIRES ATTENDED WORKER ONLY -- scheduled Workers must skip.**
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler 5.x desktop, walk the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, drag-drop into demo.bpmn.io, save in Camunda and structural-diff the saved file. Record findings (and any waiver removal) in `nimbus-skeleton/DECISIONS.md`.
  - Constraint: READ-ONLY against `nimbus-skeleton/` source. Emit BPMN artifacts to your run's scratch dir; record findings in `nimbus-skeleton/DECISIONS.md` (file may be created -- doc, not source). If the emitter run requires a code change to produce a clean import, stop and write to NEEDS-INPUT.md.
  - Computer-use waiver: CLAUDE.md "Task-specific waivers" authorizes Camunda Modeler 5.x desktop + Chrome MCP for demo.bpmn.io, scoped to this queue item only. Orphan-dirs read-only constraint still applies. Waiver self-sunsets when this item closes.
  - Operational gap (worker-12pm 2026-04-30): unattended scheduled Workers cannot service `request_access` interactive approval dialogs. The 8am-12pm scheduled chain MUST skip this item. Eric's NEEDS-INPUT entry from 2026-04-30 12:00 captures three options to actually close: B1 attended Worker session (Eric kicks off ad-hoc), B2 Eric runs Option A himself (~15 min), B3 defer + drop [in-progress] (lowest cost; weakest gate).
  - Prior progress (worker-9am 2026-04-29): programmatic structural validation 24/24 PASS (`/tmp/bpmn_run/validate_bpmn_structural.py`); section-5 unittest pins 40/40 PASS in nimbus-skeleton; full pass/fail table in `research/2026-04-29-bpmn-structural-validation.md`. The remaining work is GUI-only.

## Decomposed (next-pull-ready)

These two items have no open Eric gate and can be picked up by the next unattended Worker. Pull from this list before scanning the phase sections below.

- 4.5 -- Draft `RELEASE-NOTES-1.0.md` scaffold at repo root (sub-tool sections empty; customer-facing tone). No content commitments yet -- the scaffold gives Phase 4 a target file.
- 5.4 -- Draft DECISIONS.md CUSTOMER_HANDOFF retrospective entry stub (date placeholder, sub-tool versions placeholder, retrospective bullet stubs). Same logic: scaffold ahead of Phase 5 so the entry is ready to fill on tag day.

---

## Decomposed (Phase 2 -- Camunda migration)

> Open phase. Item 2.5 (Camunda Modeler GUI gate) is the existing P1 [in-progress] entry at the top of this file -- B1/B2/B3 pending Eric. Items 2.1-2.4 are queued behind it; 2.1/2.2/2.4 also gated on the orphan-dir tracked-vs-ignored decision (3.7) because they touch `nimbus-skeleton/`.

- [ ] [P1] [phase-2] [code-touching] 2.1 -- Add a stdlib BPMN structural-diff helper script for repeatable Camunda-resave round-trip checks.
  - DoD: `nimbus-skeleton/scripts/bpmn_structural_diff.py` (~50-80 LOC, pure stdlib `xml.etree.ElementTree`); takes two `.bpmn` files and prints (missing/added element ids, lane-membership deltas, sequence-flow source/target deltas, flow-node-without-shape count); 5 unit tests under `nimbus-skeleton/tests/test_bpmn_structural_diff.py`; suite goes from 40 to 45 green.
  - Effort: small (~1.5h, single shift).
  - Deps: 3.7 orphan-dir resolution (touches `nimbus-skeleton/`); originated as PROPOSED researcher 2026-04-29 (P2).
  - Skill: `engineering:system-design` (interchange-format design judgment) -> `engineering:code-review`.

- [ ] [P2] [phase-2] [doc-only] 2.2 -- Fold the Camunda import checklist into `samples/bpmn_validation/README.md`.
  - DoD: README's current 3-bullet "Verify visually" section replaced with the section-2 pass-criterion table + section-6 procedure inline; `research/2026-04-29-camunda-import-checklist.md` retained as provenance; README <= 2 pages.
  - Effort: small (~30 min).
  - Deps: confirm on pull whether `samples/bpmn_validation/` falls under the orphan-dir off-limits rule (path is at root, not under `nimbus-skeleton/`); originated as PROPOSED researcher 2026-04-29 (P2).
  - Skill: `engineering:code-review` (doc-review).

- [ ] [P1] [phase-2] [code-touching] 2.3 -- Capture the Camunda-saved BPMN as a regression fixture and add a structural-diff pin test against the original emitter output.
  - DoD: `nimbus-skeleton/tests/fixtures/simple_two_actors.camunda-saved.bpmn` checked in (post-2.5 capture); `tests/test_bpmn_camunda_roundtrip.py` adds 1-2 tests asserting structural-diff (via 2.1's helper) is empty between emitter output and Camunda-resave; suite +1-2 / 40+ green.
  - Effort: small (~1h, mostly fixture capture).
  - Deps: 2.1 (helper script), 2.5 (GUI gate close), 3.7 (orphan-dir resolution).
  - Skill: `engineering:testing-strategy` -> `engineering:code-review`.

- [ ] [P2] [phase-2] [code-touching] 2.4 -- Add an offline BPMN 2.0 XSD validation test (vendor the OMG XSD if obtainable air-gapped).
  - DoD: `nimbus-skeleton/tests/schemas/BPMN20.xsd` (or equivalent vendored copy; cite OMG release in comment); `test_bpmn_xsd_validation.py` parses emitter output and asserts schema-clean; suite +1-3 tests.
  - Effort: medium (~2-3h; XSD acquisition + dep-availability check is the slow part -- `xmlschema` is pure-Python and may already be in the bundle, otherwise consider `lxml` cost).
  - Deps: 3.7 (orphan-dir resolution); verify XSD distribution license is air-gap-friendly.
  - Skill: `engineering:system-design` (XSD vs structural-diff coverage tradeoff) -> `engineering:code-review`.

- [in-progress] [P1] [phase-2] [attended] 2.5 -- Service the Camunda Modeler GUI gate (existing P1 [in-progress] above).
  - Tracked here only for phase-decomposition completeness. The canonical entry is the P1 [in-progress] at the top of this file; B1/B2/B3 pending Eric per NEEDS-INPUT worker-12pm 2026-04-30. Manual-Gate lane.
  - Closure unblocks 2.3 + 4.2 (nimbus-skeleton 0.2.0 cut) + waiver removal in CLAUDE.md.

---

## Decomposed (Phase 3 -- hardening + commit hygiene)

> In progress. Several items have PROPOSED siblings awaiting Eric `[x]`; cross-referenced below. Phase-3 next-pull-ready items now exhausted (3.1 closed worker-8am 2026-05-05; 3.3 + 3.4 closed worker-9am 2026-05-05; see DONE.md). Remaining Phase-3 items all need an Eric gate first.

- [ ] [P2] [phase-3] [code-touching] 3.2 -- Patch `requirements-extractor/packaging/DocumentDataExtractor.spec` per worker-10am 2026-04-30 audit.
  - DoD: spec gains `yaml` in `_bundle()` + `requirements_extractor.actor_heuristics` in explicit hiddenimports; once 0.6.1/0.6.2 patch line lands, also adds `requirements_extractor.compound` + `requirements_extractor.multi_action`; `pyinstaller packaging/DocumentDataExtractor.spec --clean --noconfirm` rebuild succeeds; offline smoke-test (YAML config + `use_heuristics=True`) loads in resulting binary.
  - Effort: medium (~2h; build verification is the slow part).
  - Deps: PROPOSED worker-10am 2026-04-30 (P2) `[x]`-approval; companion deps on PROPOSED auditor 2026-04-29 commit-or-stash for the compound/multi_action lines.
  - Skill: `engineering:code-review` (spec-edit + bundle-shape verification).

- [ ] [P1] [phase-3] [code-touching] 3.5 -- Implement the post-edit verification step in `roles/worker.md` + `roles/planner.md`.
  - DoD: `roles/worker.md` step 5 (and `roles/planner.md` step 2) carries the four-check sequence (`wc -c`, `tail -c 80`, `python3 -m py_compile` for .py files, `diff <(cat) <(git show HEAD:)` for content-equiv edits); one JOURNAL entry post-rollout shows a Worker actually following it.
  - Effort: small (~30 min role-doc edit + verify pattern works on a real Edit call).
  - Deps: PROPOSED cowork-session 2026-05-04 (P1) `[x]`-approval. Coupled with the role-file-drift PROPOSED (auditor 2026-05-03 / 2026-05-04) -- pick a path on those before editing, or the new lines get lost in the drift.
  - Skill: `engineering:code-review` (workflow change).

- [ ] [P2] [phase-3] [code-touching] 3.6 -- Extend pre-commit hook with NUL-byte sweep + Windows Python discovery fix.
  - DoD: `scripts/pre-commit-check.sh` rejects any tracked `.py` containing `\x00`; honors `PYTHON` env or prefers `py -3` on Windows; re-validate by re-enabling hook and committing a clean file.
  - Effort: small (~1h bash edit + Windows verify).
  - Deps: PROPOSED night-auditor 2026-04-29 (P2 NUL-byte sweep) + PROPOSED night-auditor 2026-04-29 (P2 Windows hook). Bundle both into one commit.
  - Skill: `engineering:code-review`.

- [ ] [P1] [phase-3] [arch] 3.7 -- Execute the orphan-dir tracked-vs-ignored decision (Option A status-quo / B formalize / C untrack) once Eric picks.
  - DoD per pick: (A) doc cleanup in CLAUDE.md, ACTION_ITEMS.md Phase-0, COMMIT_PLAN.md; off-limits rule lifted. (B) `pyproject.toml` + `README.md` per dir; PyInstaller spec re-validation; off-limits rule lifted. (C) full migration plan filed in PROPOSED, multi-shift.
  - Effort: A small (~30 min); B medium (~1 day); C large (multi-shift).
  - Deps: Eric's pick (DECISIONS-orphan-dirs.md inputs filed 2026-04-29). Unblocks 2.1 / 2.2 / 2.3 / 2.4 + every Phase 4 item that touches the three dirs.
  - Skill: `engineering:system-design` (per planner role -- this is the architectural-ambiguity profile the skill targets; per cowork-session 2026-05-04 PROPOSED P2, this is one of the three pre-staged `[arch]` items).

- [ ] [P2] [phase-3] [doc-only] 3.8 -- Once 0.6.1 + 0.6.2 patch lines land, refresh ROADMAP.md sub-tool status table.
  - DoD: requirements-extractor row reads `0.6.2 (committed)` not `(Unreleased on disk)`; test counts updated if drifted; revision-history append.
  - Effort: trivial (~10 min). Bundles into the same Worker shift that picks up 0.6.1/0.6.2.
  - Deps: PROPOSED auditor 2026-04-29 commit-or-stash (must land first).
  - Skill: `engineering:code-review`.

---

## Decomposed (Phase 4 -- bundle / cut / tag)

> Not started. Entry blocked on Phase 2 exit (Camunda gate close, 2.5) AND Phase 3 exit (commit hygiene clean, 3.1-3.8). Items below assume both have closed.

- [ ] [P2] [phase-4] [code-touching] 4.1 -- Promote `requirements-extractor/CHANGELOG.md` Unreleased -> dated `[0.7.0]` entry; bump `__version__`; one focused commit.
  - DoD: CHANGELOG date stamp + `[0.7.0]` heading; version bumps consistent across `__init__.py`, `packaging/DocumentDataExtractor.spec`, README references; tests still 606 green; offline smoke-test on Eric's restricted-network Windows machine green.
  - Effort: small (~30 min).
  - Deps: 0.6.1 + 0.6.2 patch lines committed (Phase 3); 3.2 (PyInstaller spec patch) landed.
  - Skill: `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.2 -- Promote `nimbus-skeleton/CHANGELOG.md` Unreleased -> dated `[0.2.0]` entry; bump version; one focused commit.
  - DoD: CHANGELOG date + `[0.2.0]` heading; BPMN + review-writer + shared-loader sections retained; tests still 40 green; emitter output validates against Camunda Modeler 5.x (per 2.5).
  - Effort: small (~30 min).
  - Deps: 2.5 (Camunda gate); 3.7 (orphan-dir resolution).
  - Skill: `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.3 -- Promote `compliance-matrix/CHANGELOG.md` Unreleased -> dated `[0.2.0]` entry; bump version.
  - DoD: CHANGELOG date + `[0.2.0]` heading; fuzzy-id matcher + shared-loader retained; tests still 30 green; default thresholds (similarity 0.20 / keyword 0.15 / fuzzy_id 0.85) validated against one real spec/procedure pair per ROADMAP.md 1.0 criteria.
  - Effort: small if thresholds already validated (~30 min); medium if validation has to be done this shift (~3-4h).
  - Deps: 3.7 (orphan-dir resolution); threshold validation against real spec.
  - Skill: `engineering:testing-strategy` for threshold validation -> `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.4 -- Promote `process-tools-common/CHANGELOG.md` Unreleased -> dated `[0.2.0]` entry; bump version; verify both consumers install without `sys.path` bootstrap.
  - DoD: CHANGELOG date + `[0.2.0]` heading; cli_helpers + dde_xlsx loader helpers retained; tests still 26 green; consumers (compliance-matrix + nimbus-skeleton) pip-install or PyInstaller-bundle cleanly without the `sys.path` bootstrap shim per ROADMAP.md 1.0 criteria.
  - Effort: medium (~2h; bootstrap-removal verification is the load-bearing step).
  - Deps: 3.7 (orphan-dir resolution); 4.1 + 4.2 + 4.3 (consumers cut first; the schema lib stabilises against committed consumers).
  - Skill: `engineering:system-design` (sys.path bootstrap removal touches packaging contract) -> `engineering:code-review`.

- [ ] [P2] [phase-4] [doc-only] 4.5 -- Draft `RELEASE-NOTES-1.0.md` scaffold at repo root.
  - DoD: file exists at root; one section per sub-tool; cross-references to per-tool CHANGELOGs; customer-facing tone (no "worker", "queue", or other automation jargon per CLAUDE.md operator voice).
  - Effort: small (~1h scaffold; populate during 4.1-4.4 shifts).
  - Deps: none for the scaffold (next-pull-ready); content fill depends on 4.1-4.4.
  - Skill: `engineering:code-review` (doc-review).

- [ ] [P2] [phase-4] [code-touching] 4.6 -- Build PyInstaller bundles for the customer-shipping subset; validate on Eric's restricted-network Windows machine.
  - DoD: `dist/DocumentDataExtractor.exe` produced clean (mandatory); nimbus-skeleton equivalent if customer needs offline BPMN emission (optional per ROADMAP.md Phase 4 exit); offline smoke-test green; bundle size + load time recorded in DECISIONS.md.
  - Effort: medium (~3-4h; build + restricted-network roundtrip is the slow part).
  - Deps: 4.1 + 4.2 + 3.2; 3.7 (Option B if formalizing nimbus-skeleton packaging).
  - Skill: `engineering:system-design` (bundle-scope decision -- include nimbus-skeleton or not?) -> `engineering:code-review`.

- [ ] [P1] [phase-4] [arch] 4.7 -- Cut bundle v1.0: tag all four sub-tools at `1.0.0` simultaneously.
  - DoD: `git tag -a 1.0.0-requirements-extractor` (and three siblings) on the same HEAD commit; tag annotations cite CHANGELOG date + ROADMAP entry; `git tag -l '1.0.0*'` returns four tags; CHANGELOGs all carry `[1.0.0]` headings cross-referenced to the tag SHAs.
  - Effort: small (~30 min if 4.1-4.6 are all green).
  - Deps: 4.1 + 4.2 + 4.3 + 4.4 + 4.6; Phase 3 commit hygiene clean (no ghost-diffs, working tree faithful to HEAD).
  - Skill: `engineering:system-design` for tag-naming convention -> `engineering:code-review`.

---

## Decomposed (Phase 5 -- v1.0 release)

> Not started. Expected scope: ~1 day of attended work after Phase 4 lands.

- [ ] [P1] [phase-5] [attended] 5.1 -- Push 1.0 tags + bundle commits to `origin/main`.
  - DoD: `git ls-remote --tags origin '1.0.0*'` returns four tags; `git rev-parse origin/main == HEAD` for the bundle commit; reflog confirms push success.
  - Effort: small (~15 min Eric attended; Workers cannot push per current policy).
  - Deps: 4.7. Eric attendance for the push.
  - Skill: human attention; no skill fires.

- [ ] [P1] [phase-5] [attended] 5.2 -- Hand off the customer-deliverable bundle.
  - DoD: customer receives PyInstaller binaries + RELEASE-NOTES-1.0.md + per-tool READMEs + DDE samples; checksum or transfer receipt recorded in DECISIONS.md CUSTOMER_HANDOFF entry; bundle layout documented for re-build.
  - Effort: medium (~2-3h; depends on customer intake form).
  - Deps: 5.1, 4.5 (release notes filled).
  - Skill: human attention.

- [ ] [P2] [phase-5] [code-touching] 5.3 -- Open Unreleased sections for 1.1 work; seed ROADMAP.md post-1.0 section.
  - DoD: each of four CHANGELOGs carries a fresh `## [Unreleased]` heading above `[1.0.0]`; ROADMAP.md gains a "Post-1.0 maintenance" section listing carryover items (CLI flags `--actor-heuristics`, GUI checkbox for same, ReqIF decomposition export, threshold tuning, configurable `_ROLE_HEAD_NOUNS`, etc.).
  - Effort: small (~45 min). Picks up "Open follow-ups" already documented in each CHANGELOG.
  - Deps: 4.7.
  - Skill: `engineering:code-review`.

- [ ] [P2] [phase-5] [doc-only] 5.4 -- Draft DECISIONS.md CUSTOMER_HANDOFF retrospective entry.
  - DoD: one new entry in `DECISIONS.md` (root), decision-doc voice per CLAUDE.md, sections for what shipped + what slipped + what surprised + what to do differently for 1.1; cross-referenced to RELEASE-NOTES-1.0.md and the four CHANGELOGs.
  - Effort: small (~1h; the scaffold is next-pull-ready, content fills on tag day).
  - Deps: scaffold has none (next-pull-ready); content fill depends on 5.2.
  - Skill: `engineering:code-review`.
