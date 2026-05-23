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

## Manual-Gate / eric-action

> Items requiring Eric attended action (not Worker-pickable). Scheduled Workers skip per `roles/worker.md` step 2 -- the dashboard answer-resolution contract is the route to closure. Promotion of new items here requires either a dashboard `**[answered:]**` marker on a NEEDS-INPUT question OR a PROPOSED `[x]`-approval.

- [in-progress] [P1] [manual-gate / eric-action] Refresh `.git/index` from HEAD -- one Windows-side command retires the 8-day chronic stale-index state.
  - Status: promoted by planner 2026-05-15 07:10 from PROPOSED line 65 (auditor 2026-04-30 P1) + 4 successor entries (auditor 2026-05-06 P1 line 153 + auditor 2026-05-07 RISKY P1 lines 160 + 167 + RISKY P2 line 174). Promotion ground: NEEDS-INPUT line 36 `**[answered: B 2026-05-15 via dashboard]**` -- Eric approved "promoting the two P1 blocking-adjacent items"; one of the two (commit-or-stash 0.6.1/0.6.2) was already DONE by `261a674` 2026-05-05 so is moot; this entry covers the other (`.git/index` recovery).
  - Definition of done: from a Windows-side shell at the repo root, run `rm -f .git/index .git/index.lock && git read-tree HEAD`. Verify `git fsck --no-progress` exits 0 and `git ls-files -u` is empty. Verify `git status -s` no longer shows the staged-delete `D  RELEASE-NOTES-1.0.md` nor the `D  nimbus-skeleton/scripts/bpmn_structural_diff.py` + `D  nimbus-skeleton/tests/test_bpmn_structural_diff.py` ghost-delete entries (joined by the legitimate working-tree edits + untracked items). File a one-line DECISIONS.md entry (decision-doc voice) citing the recovery.
  - Why Eric-only: `.git/index.lock` (0-byte sentinel, mtime 2026-05-07 06:07:44 UTC) is held by a Windows-side process; Linux workspace bash returns `Operation not permitted` on `unlink('.git/index.lock')`. Scheduled Workers running on the Linux side cannot release the lock.
  - Time-box: ~2 minutes attended.
  - On completion: 5 grouped PROPOSED entries retire (lines 65 / 153 / 160 / 167 / 174 -- mark `[resolved by Eric 2026-05-15-or-later]` in evening review); destructive staged-delete data-loss vector on `RELEASE-NOTES-1.0.md` retires; 2 invisible-new-files from `9ca814d` stop surfacing as `??` in `git status -s`; vanilla `git commit -a` becomes safe again. The Workers' `GIT_INDEX_FILE=/tmp/...` plumbing-path workaround stays available as a fallback but is no longer load-bearing.
  - Follow-up note for researcher: forensic signal on the 2026-05-06 trailer-SHA1 mismatch decays as soon as `git status` re-stats the new index. If R1 (post-fix retro) is still wanted, researcher 2026-05-16 04:00 should run it the night of the recovery, not later.

---

- [in-progress] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import. **REQUIRES ATTENDED WORKER ONLY -- scheduled Workers must skip.**
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler 5.x desktop, walk the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, drag-drop into demo.bpmn.io, save in Camunda and structural-diff the saved file. Record findings (and any waiver removal) in `nimbus-skeleton/DECISIONS.md`.
  - Constraint: READ-ONLY against `nimbus-skeleton/` source. Emit BPMN artifacts to your run's scratch dir; record findings in `nimbus-skeleton/DECISIONS.md` (file may be created -- doc, not source). If the emitter run requires a code change to produce a clean import, stop and write to NEEDS-INPUT.md.
  - Computer-use waiver: CLAUDE.md "Task-specific waivers" authorizes Camunda Modeler 5.x desktop + Chrome MCP for demo.bpmn.io, scoped to this queue item only. Orphan-dirs read-only constraint still applies. Waiver self-sunsets when this item closes.
  - Status (2026-05-11 cowork-session): Eric picked **option (a) -- run the Camunda Modeler walkthrough manually himself** (equivalent to option B2). NEEDS-INPUT entry `[eric-action / 2026-05-11]` captures the open work (~15 min: open `samples/bpmn_validation/simple_two_actors.bpmn` in Camunda Modeler 5.x, walk the section-2 table in `research/2026-04-29-camunda-import-checklist.md`, drop into demo.bpmn.io, save + structural-diff, file findings in `nimbus-skeleton/DECISIONS.md`). The unattended `request_access` skip pattern still applies for any scheduled Worker -- this item closes when Eric completes the manual walk, not when a Worker picks it up. **New helper available 2026-05-12**: `nimbus-skeleton/scripts/bpmn_structural_diff.py` (worker-9am `9ca814d` / QUEUE 2.1) -- run `python3 nimbus-skeleton/scripts/bpmn_structural_diff.py <emitter-output.bpmn> <camunda-resaved.bpmn>` for step 4 of the walk; returns 0 on equivalent / 1 on delta; format_report() prints the per-dimension delta if non-empty.
  - Prior progress (worker-9am 2026-04-29): programmatic structural validation 24/24 PASS (`/tmp/bpmn_run/validate_bpmn_structural.py`); section-5 unittest pins 40/40 PASS in nimbus-skeleton; full pass/fail table in `research/2026-04-29-bpmn-structural-validation.md`. The remaining work is GUI-only.

## Decomposed (next-pull-ready)

(Today's pull priority is NONE -- the dashboard-marker queue is structurally EMPTY (5/5 paired AND VERIFIED). Worker-8am 2026-05-16 14:12 paired the 5th marker (line 73/74 partial-acceptance: D1=`lxml` accepted; D2 OMG XSD vendor + D3 dev-only confirm still open on parent worker-11am 2026-05-12 entry; QUEUE 2.4 stays `[in-progress]`) via plumbing-path commit `d1500e17`. Night-auditor 2026-05-17 02:12 VERIFIED the pair byte-exact + emitted `logs/process-tools/2026-05-17.jsonl` (1 entry); the 4 prior 2026-05-15-overnight pairs were VERIFIED 2026-05-16 00:10 in `logs/process-tools/2026-05-16.jsonl`. **No unpaired dashboard markers; no next-pull-ready phase-decomposed items; 0 of 34 PROPOSED entries are `[x]`-approved.** Per `roles/worker.md` step 2 + planner role-spec point 5, the 8am-12pm Worker chain today expects empty-queue bailout absent Eric `[x]`-action during evening review. Highest-leverage Eric `[x]` candidates per researcher 2026-05-17 R5 freshness audit (`research/2026-05-17-proposed-backlog-freshness-audit.md`): (a) cowork-session 2026-05-04 P1 numeric-fact auto-update authorization (PROPOSED line 121; retires line 59 by side-effect); (b) researcher 2026-05-14 Pre-Phase-4 readiness 5-sub-item bundle (PROPOSED line 210); (c) researcher 2026-05-13 D2/D3 OMG XSD vendor + dev-only confirm bundle (PROPOSED line 195; D1 already partial-resolved); (d) pair-approve `.gitignore` patches (PROPOSED lines 181 + 203). Remaining unblocks are the two Manual-Gate eric-action items (`.git/index` recovery + Camunda walk; both eric-attended). Wall-clock anomaly day-6; root cause grounded per `research/2026-05-16-wall-clock-fire-time-analysis.md` = Eric-machine sleep + Cowork scheduler-replay; benign as long as bailouts stay clean.)

---

## Decomposed (Phase 2 -- Camunda migration)

> Open phase. Item 2.5 (Camunda Modeler GUI gate) is the existing P1 [in-progress] entry at the top of this file -- waiting on Eric manual walk per `[eric-action / 2026-05-11]`. Items 2.3, 2.4 are queued behind it; 2.4 is now `[in-progress]` waiting on Eric D1/D2/D3 (researcher 2026-05-13 PROPOSED bundle ready for one-click `[x]`). Off-limits constraint on `nimbus-skeleton/` was **lifted 2026-05-12** by `bbcbff5` (QUEUE 3.7 doc-alignment closure). (2.1 closed worker-9am 2026-05-12 `9ca814d`; 2.2 closed worker-12pm 2026-05-05; samples/bpmn_validation/ is at repo root and was never subject to the orphan-dir off-limits rule.)

- [ ] [P1] [phase-2] [code-touching] 2.3 -- Capture the Camunda-saved BPMN as a regression fixture and add a structural-diff pin test against the original emitter output.
  - DoD: `nimbus-skeleton/tests/fixtures/simple_two_actors.camunda-saved.bpmn` checked in (post-2.5 capture); `tests/test_bpmn_camunda_roundtrip.py` adds 1-2 tests asserting structural-diff (via 2.1's helper) is empty between emitter output and Camunda-resave; suite +1-2 / 40+ green.
  - Effort: small (~1h, mostly fixture capture).
  - Deps: 2.5 (GUI gate close). 2.1 helper script DONE 2026-05-12 (`9ca814d`); 3.7 orphan-dir DONE 2026-05-12 (`bbcbff5`).
  - Skill: `engineering:testing-strategy` -> `engineering:code-review`.

- [in-progress] [P2] [phase-2] [code-touching] 2.4 -- Add an offline BPMN 2.0 XSD validation test (vendor the OMG XSD if obtainable air-gapped).
  - DoD: `nimbus-skeleton/tests/schemas/BPMN20.xsd` (or equivalent vendored copy; cite OMG release in comment); `test_bpmn_xsd_validation.py` parses emitter output and asserts schema-clean; suite +1-3 tests.
  - Effort: medium (~2-3h; XSD acquisition + dep-availability check is the slow part -- `xmlschema` is pure-Python and may already be in the bundle, otherwise consider `lxml` cost).
  - Deps: NONE remaining (3.7 orphan-dir DONE 2026-05-12 `bbcbff5`; XSD license/strictness research DONE 2026-05-13 `research/2026-05-13-bpmn-xsd-validator-and-license.md`). Ready to start on Eric `[x]` of researcher 2026-05-13 PROPOSED bundle.
  - Skill: `engineering:system-design` (XSD vs structural-diff coverage tradeoff) -> `engineering:code-review`.
  - Status (worker-11am 2026-05-12 11:00 + researcher 2026-05-13 04:00): worker-11am scoped the dep-availability check (lxml 6.0.2.0 installed / xmlschema not installed / tests dev-only / OMG release identified as 20100524 / 5 XSDs ~100KB) and bailed per role-spec step 6 -- D1/D2/D3 NEEDS-INPUT entry filed. Researcher 2026-05-13 04:00 filed `research/2026-05-13-bpmn-xsd-validator-and-license.md` (~15.7 KB) + ONE PROPOSED P2 bundling D1+D2+D3 (D1->xmlschema for strictness; D2->OK-to-vendor 5 XSDs with sibling SCHEMAS-LICENSE.md; D3->confirmed dev-only) so Eric can one-click `[x]` instead of answering three NEEDS-INPUT lines. ETA ~1.5-2h from `[x]` to DONE; 8-step Worker spec attached to the PROPOSED entry. Failure-mode pre-flagged: if xmlschema rejects existing fixture, treat as emitter spec-gap signal (not setup bug).

- [in-progress] [P1] [phase-2] [attended] 2.5 -- Service the Camunda Modeler GUI gate (existing P1 [in-progress] above).
  - Tracked here only for phase-decomposition completeness. The canonical entry is the P1 [in-progress] at the top of this file. Status: option (a) chosen 2026-05-11 -- Eric runs the manual walkthrough; tracked as `[eric-action / 2026-05-11]` in NEEDS-INPUT.md. Manual-Gate lane.
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
  - Deps: 2.5 (Camunda gate). 3.7 orphan-dir DONE 2026-05-12 (`bbcbff5`).
  - Skill: `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.3 -- Promote `compliance-matrix/CHANGELOG.md` Unreleased -> dated `[0.2.0]` entry; bump version.
  - DoD: CHANGELOG date + `[0.2.0]` heading; fuzzy-id matcher + shared-loader retained; tests still 30 green; default thresholds (similarity 0.20 / keyword 0.15 / fuzzy_id 0.85) validated against one real spec/procedure pair per ROADMAP.md 1.0 criteria.
  - Effort: small if thresholds already validated (~30 min); medium if validation has to be done this shift (~3-4h).
  - Deps: threshold validation against real spec. 3.7 orphan-dir DONE 2026-05-12 (`bbcbff5`).
  - Skill: `engineering:testing-strategy` for threshold validation -> `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.4 -- Promote `process-tools-common/CHANGELOG.md` Unreleased -> dated `[0.2.0]` entry; bump version; verify both consumers install without `sys.path` bootstrap.
  - DoD: CHANGELOG date + `[0.2.0]` heading; cli_helpers + dde_xlsx loader helpers retained; tests still 26 green; consumers (compliance-matrix + nimbus-skeleton) pip-install or PyInstaller-bundle cleanly without the `sys.path` bootstrap shim per ROADMAP.md 1.0 criteria.
  - Effort: medium (~2h; bootstrap-removal verification is the load-bearing step).
  - Deps: 4.1 + 4.2 + 4.3 (consumers cut first; the schema lib stabilises against committed consumers). 3.7 orphan-dir DONE 2026-05-12 (`bbcbff5`).
  - Skill: `engineering:system-design` (sys.path bootstrap removal touches packaging contract) -> `engineering:code-review`.

- [ ] [P2] [phase-4] [code-touching] 4.6 -- Build PyInstaller bundles for the customer-shipping subset; validate on Eric's restricted-network Windows machine.
  - DoD: `dist/DocumentDataExtractor.exe` produced clean (mandatory); nimbus-skeleton equivalent if customer needs offline BPMN emission (optional per ROADMAP.md Phase 4 exit); offline smoke-test green; bundle size + load time recorded in DECISIONS.md.
  - Effort: medium (~3-4h; build + restricted-network roundtrip is the slow part).
  - Deps: 4.1 + 4.2 + 3.2. 3.7 orphan-dir DONE 2026-05-12 (`bbcbff5`) -- option A kept all three sibling dirs tracked as proper packages, so formalizing nimbus-skeleton packaging here is a Phase-4 design call, not a Phase-3 gate.
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
  - Deps: 5.1, RELEASE-NOTES-1.0.md content filled (4.5 scaffolded by worker-10am 2026-05-05; populate during 4.1-4.4).
  - Skill: human attention.

- [ ] [P2] [phase-5] [code-touching] 5.3 -- Open Unreleased sections for 1.1 work; seed ROADMAP.md post-1.0 section.
  - DoD: each of four CHANGELOGs carries a fresh `## [Unreleased]` heading above `[1.0.0]`; ROADMAP.md gains a "Post-1.0 maintenance" section listing carryover items (CLI flags `--actor-heuristics`, GUI checkbox for same, ReqIF decomposition export, threshold tuning, configurable `_ROLE_HEAD_NOUNS`, etc.).
  - Effort: small (~45 min). Picks up "Open follow-ups" already documented in each CHANGELOG.
  - Deps: 4.7.
  - Skill: `engineering:code-review`.
