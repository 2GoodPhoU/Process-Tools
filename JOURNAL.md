# Journal — Process-Tools

> Append-only log. Every scheduled run adds one entry. Most recent at the bottom. Never edit or delete prior entries.

## Format

```
## [YYYY-MM-DD HH:MM] role-name
- what I read
- what I did
- what I produced (files written, items moved between state files)
- anything notable / surprises
- next handoff (who picks this up, what they should know)
```

---

## [2026-04-28 18:30] pre-automation prep (Eric, ad-hoc via Cowork)
- read: STATE.md, QUEUE.md, NEEDS-INPUT.md, JOURNAL.md, scheduled-tasks list, roles/
- did: readiness check ahead of first automated run tonight (process-tools-night-auditor at ~00:05).
- produced:
  - STATE.md: cleared `(none yet — bootstrap)` placeholder; expanded orphan-dirs entry to flag it as a BLOCKER for code work in `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`.
  - QUEUE.md: scoped the P1 BPMN/Camunda validation item READ-ONLY against `nimbus-skeleton/` to honor the orphan-dirs off-limits rule. Added explicit fallback: if emitter requires a source edit to produce a clean import, stop and write to NEEDS-INPUT.md.
- verified: 9 Process-Tools scheduled tasks (night-auditor, researcher, planner, 5 workers, digest) all enabled; all five role files present under `roles/`; NEEDS-INPUT.md empty.
- notable: orphan-dirs tracked-vs-ignored decision is still owed by Eric. Workers should not block on it for the read-only validation, but ANY code-touching item targeting those three dirs needs the decision made first.
- next handoff: process-tools-night-auditor (~00:05). Audit STATE/QUEUE/NEEDS-INPUT consistency; flag anything stale.

## [2026-04-28 18:45] queue top-up (Eric, ad-hoc via Cowork)
- read: QUEUE.md, PROPOSED.md, DONE.md, roles/worker.md
- did: addressed thin-backlog risk for tomorrow's 5 worker slots (was 1 item for 5 slots).
- produced: QUEUE.md now has 6 items total (1 pre-existing + 5 added):
  - P1: BPMN/Camunda validation (pre-existing, read-only)
  - P1: Orphan-dirs decision scaffolding (NEW, read-only inspection of the 3 off-limits dirs)
  - P1: Baseline pytest run for requirements-extractor (NEW, captures known-good marker)
  - P2: Heuristic regression-coverage audit, 10 rules (NEW, doc-only)
  - P2: PyInstaller spec audit (NEW, doc-only, propose-don't-edit)
  - P2: Edit-tool truncation sweep on cli.py / actors.py (NEW, read-only check)
- notable: All 5 new items are scoped to either read-only inspection or doc-only output. None require touching source under the three off-limits dirs. Worker bailout conditions remain in force per roles/worker.md.
- next handoff: process-tools-night-auditor (~00:05).

## [2026-04-29 00:05] process-tools-night-auditor (automated)
- read: CLAUDE.md, STATE.md, JOURNAL.md, QUEUE.md, PROPOSED.md, NEEDS-INPUT.md, roles/night-auditor.md, scripts/test_all.sh, scripts/pre-commit-check.sh, Makefile, requirements.txt, .gitignore.
- did: ran `git status`, `git log --since="2026-04-28 00:00"`, `git diff --stat`, `bash scripts/test_all.sh`, `python3 -m py_compile` against every .py in the repo, NUL-byte sweep, and the per-tool unittest discover for requirements-extractor to surface the failures by name. Searched for lint/format config (none — project relies solely on the pre-commit `py_compile` + NUL-byte hook).
- produced:
  - QUEUE.md: appended one P0 — repair edit-tool truncation in `requirements-extractor/requirements_extractor/models.py`. Lines 203-209 of the working tree are a duplicated/corrupted block (`tructural events."""` on line 205 plus a stray field). Causes 27 unittest ERRORs (modules fail to load) and 5 integration-test FAILs. Sole syntax error in the entire repo; all other Python files py_compile clean. NUL-byte sweep clean.
  - PROPOSED.md: appended four items — (1) P1 commit-or-stash the ~2-day-old uncommitted 0.6.1/0.6.2 patch line in requirements-extractor before workers touch it (~840 LOC diff + ~1933 LOC of new untracked files); (2) P2 fix Windows pre-commit hook so future commits can't bypass the truncation guard (last commit used `--no-verify` per its own commit body); (3) P2 fail-loud on test-module load errors in scripts/test_all.sh (current summary undercounts errors); (4) P2 refresh CLAUDE.md test counts (claims 508/33/13, actuals 109-of-broken-suite/40/26 + compliance-matrix's 30 not cited).
- notable:
  - Zero commits in the last 24 hours. Last commit was 18ee238 (release dde 0.6.0) on 2026-04-27 00:37 -0600. Working tree has been carrying uncommitted work since 2026-04-27 19:41 (compound.py creation timestamp).
  - The P0 syntax error is in the **uncommitted** working tree, not in any commit. `git diff requirements-extractor/requirements_extractor/models.py` cleanly shows the 7-line corrupted block as the entire delta apart from a legitimate `parent_id` field on line 148.
  - This is exactly the recurring edit-tool truncation hazard CLAUDE.md flags. Of note: CLAUDE.md specifically named cli.py and actors.py as the two files to watch — both are clean. The hazard hit a third file. The P2 truncation-sweep queue item should probably broaden to "all four core requirements_extractor modules", not just those two.
  - Test-suite counts drifted off CLAUDE.md's claims: process-tools-common 26 (claimed 13), nimbus-skeleton 40 (claimed 33), compliance-matrix 30 (uncited). Logged as a P2 in PROPOSED.md.
  - No NEEDS-INPUT entry written. The Broken finding is in QUEUE.md as a P0 per role spec; the morning Planner (~07:10) will see it before any Worker runs (first Worker ~08:00). If that ordering changes, this should escalate.
- next handoff: process-tools-researcher (~06:00) → process-tools-planner (~07:10). Planner: please surface the P0 first thing; the 8am Worker should not pick up the baseline-pytest queue item against a broken working tree.

## [2026-04-29 06:00] process-tools-researcher (automated)
- read: CLAUDE.md, STATE.md, NEEDS-INPUT.md, QUEUE.md, PROPOSED.md, JOURNAL.md, roles/researcher.md, samples/bpmn_validation/README.md, samples/bpmn_validation/simple_two_actors.bpmn, nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py, nimbus-skeleton/tests/test_bpmn_emitter.py, DECISIONS.md (BPMN DI generation entry), the directory layout under nimbus-skeleton/.
- did: picked the P1 Camunda Modeler import-validation queue item as the question needing grounding before the Worker runs it. NEEDS-INPUT.md was empty; no `[research]`-tagged items in QUEUE; the BPMN/Camunda gate is the highest-value research target. Web-searched Camunda Modeler 5.x BPMN-2 import requirements, the bpmn.io / Camunda issue queues for "no diagram to display" / missing-BPMN-shape / executionPlatform behaviour, and the modeler:executionPlatform namespace handling. Did NOT touch source; did NOT run Camunda Modeler (Researcher is read-only and the modeler is a desktop GUI — that's the Worker's step).
- produced:
  - `research/2026-04-29-camunda-import-checklist.md`: full checklist with sections (1) Camunda 5.x platform-tag behaviour, (2) per-element pass criteria for the canvas walk, (3) round-trip = structural-identity NOT byte-identity, (4) known Camunda quirks that aren't failures for our output, (5) coverage already pinned by unittest, (6) concrete 6-step Worker procedure.
  - PROPOSED.md: appended two doc-only items — (a) fold the section-2 table + section-6 procedure into `samples/bpmn_validation/README.md` so the Worker reads the checklist, not just the research file; (b) add a stdlib-only structural-diff helper for before-/after-Camunda-save BPMN comparison (gated behind orphan-dirs decision since it lands new code under `nimbus-skeleton/`).
- notable: emitter inspection + sample-file inspection turned up no structural concerns. Every `flowNodeRef` resolves; every `sequenceFlow` is mirrored by `incoming`/`outgoing` on its endpoints; every flow node and edge has a DI shape/edge; `targetNamespace` is set; ≥2 waypoints per edge. The 2026-04-26 DI fix is doing the work it was supposed to. Expected Camunda 5.x behaviour: opens cleanly, surfaces platform-tag lint warnings only (Camunda 7 / Zeebe runtime concerns, not BPMN-2 conformance failures). Worker should not be blocked.
- next handoff: process-tools-planner (~07:10). Planner: P0 (models.py truncation) takes precedence; today's research file makes the BPMN/Camunda P1 a Worker-runnable task once the broken working tree is repaired. The two new PROPOSED.md items are doc/utility scope and can wait for the evening review.

## [2026-04-29 07:10] process-tools-planner (automated)
- read: CLAUDE.md, JOURNAL.md (last 24h, 3 entries), NEEDS-INPUT.md (empty), PROPOSED.md (6 open items, none `[x]`-approved), QUEUE.md (7 items as left by night-auditor), DONE.md (empty), `research/2026-04-29-camunda-import-checklist.md` (existence + journal summary), `roles/planner.md`.
- did:
  - Reordered QUEUE.md so the night-auditor's P0 (models.py truncation) sits at the top, not the bottom where it was appended. The 8am Worker would otherwise pick the BPMN/Camunda P1 first and run blind into a broken working tree.
  - Added an explicit gate on the baseline-pytest P1: do NOT run if `bash scripts/test_all.sh` is still in the 27-error/5-fail state. Renamed the target file from BASELINE-2026-04-28.md to BASELINE-2026-04-29.md — the marker should be dated the day the suite actually goes green, not the day it was queued.
  - Tied the BPMN/Camunda P1 explicitly to `research/2026-04-29-camunda-import-checklist.md` so the Worker reads the checklist first instead of redoing the grounding work.
  - Broadened the P2 truncation-sweep item from `cli.py`/`actors.py` to all four core `requirements_extractor/` modules — tonight's hazard hit `models.py`, a file CLAUDE.md does not flag, so the two-file sweep was undersized.
- produced:
  - STATE.md: overwritten. Current focus shifted to "unblock the working tree, then resume the Camunda gate." Open-threads now reflects: the P0, the research-backed P1, the orphan-dirs blocker, the working-tree-state awaiting human review, the Windows pre-commit hook bypass.
  - QUEUE.md: rewritten. Order now P0 → P1 BPMN → P1 orphan-dirs scaffold → P1 baseline-pytest (gated) → P2 heuristic-coverage audit → P2 truncation sweep (broadened) → P2 PyInstaller spec audit. 7 items; top 6 are well-defined for one Worker run each.
  - NEEDS-INPUT.md: untouched (empty before, empty now).
  - PROPOSED.md: untouched. None of the 6 items are `[x]`-approved by Eric. Per role spec, the Planner does not promote unapproved items and does not delete them — they age in place until evening review.
- notable:
  - Two PROPOSED items are blocking-adjacent and worth flagging for the evening review: (a) the commit-or-stash of the 0.6.1/0.6.2 patch line — until that's resolved, every baseline run carries an asterisk explaining the working-tree state; (b) the Windows pre-commit hook fix — until that lands, the documented safety net for edit-tool truncation is off, and we just paid for that being off (today's P0). Neither is a Planner decision.
  - DONE.md is still empty. Once the P0 lands today, that should be its first entry — a useful sanity check that the worker→DONE move is wired.
- next handoff: process-tools-worker-8am (~08:00). Top of queue is the P0 models.py repair. Definition of done is precise; verification is `python3 -m py_compile` + `bash scripts/test_all.sh`. Do not pick the baseline-pytest item until the P0 closes.

## [2026-04-29 08:00] process-tools-worker-8am (automated)
- read: CLAUDE.md, STATE.md, JOURNAL.md (last 6h, 4 entries), QUEUE.md, NEEDS-INPUT.md (empty), roles/worker.md, scripts/test_all.sh, DONE.md (empty), `requirements-extractor/requirements_extractor/models.py`.
- did: picked the P0 (top of queue) — repair edit-tool truncation in `models.py`. Confirmed broken state first: `bash scripts/test_all.sh` failed with the documented 27 ERRORs + 5 FAILs. Removed the duplicated comment block + corrupted residue at lines 203-209 (the stray `tructural events."""` and orphan `requirement: "Requirement"` field) via Edit. First post-edit `py_compile` STILL FAILED with `ValueError: source code string cannot contain null bytes`. Investigation: `git diff` showed the working tree had 192 trailing NUL bytes at EOF (the line of NULs is what the diff renders as a long whitespace line followed by `\ No newline at end of file`). The Read tool silently filters NULs so they were invisible during the initial inspection — the night-auditor's NUL-byte sweep also missed them (worth a separate proposal; see below). Stripped trailing NULs/whitespace via a one-line Python rewrite in binary mode and re-added a single trailing newline. Re-verified: `py_compile` clean, file is 204 lines, 0 NUL bytes, 8436 bytes (down from 8628). The legitimate `parent_id` field on line 148 was preserved untouched (verified by re-reading lines 145-154).
- produced:
  - `requirements-extractor/requirements_extractor/models.py`: corrupted block removed, trailing NULs stripped, file py_compiles. Working-tree diff vs HEAD is now clean: just the `parent_id` line addition on line 148, no other changes.
  - QUEUE.md: removed the P0 item (top of file). Top of queue is now the P1 BPMN/Camunda validation item, which is what the 9am Worker should pick up. Order otherwise unchanged.
  - DONE.md: first entry added — the P0 repair, with outcome note covering the NUL-byte hazard and the test-count delta (109 → 606 tests now discovered post-repair).
  - PROPOSED.md: appended one P2 — broaden `scripts/pre-commit-check.sh` (and the night-auditor's NUL-byte sweep) to actually catch trailing NUL bytes on Python source files. The current sweep clearly missed 192 NULs sitting at the end of a tracked file. Read-tool blindness to NULs is a parallel hazard worth flagging.
- verified: `bash scripts/test_all.sh` exit code 0, ALL GREEN, 702 tests across 4 tools. requirements-extractor: 606 tests pass (was 109 of a broken suite — `unittest discover` couldn't enumerate the tests behind the syntax error). Three other tools unchanged (process-tools-common 26, compliance-matrix 30, nimbus-skeleton 40). No new test failures, no unrelated areas regressed.
- notable:
  - Two distinct corruption modes were sitting in the working tree, not one. The QUEUE definition-of-done described only the duplicated-block + truncated docstring; it did not mention the trailing NULs. Both came in together (the `git diff` shows a single trailing-junk line where the comment block used to end), but they require different repair tools. Edit alone wasn't sufficient — the NULs are invisible to Read.
  - Read-tool NUL-blindness is a category hazard for this project. The night-auditor's `python3 -m py_compile` sweep DOES catch it (it's how the symptom surfaced for the auditor — they reported `SyntaxError: unterminated triple-quoted string literal`, which was the cascade effect of the NULs + the duplicate block). But the auditor's separate "NUL-byte sweep clean" line was wrong about this file. Recommend the proposed pre-commit-check.sh broadening.
  - The 0.6.1/0.6.2 patch line is otherwise clean by py_compile. The remaining ~840 LOC of tracked-file diffs and ~1933 LOC of untracked items still await commit-or-stash review (auditor's PROPOSED.md item, not approved). The baseline-pytest queue item is now technically eligible to run, but the working-tree-state asterisk still applies and the human-approval gates for the auditor's commit-or-stash proposal haven't moved.
- next handoff: process-tools-worker-9am (~09:00). Top of queue is the P1 BPMN/Camunda Modeler import-validation; the 6-step procedure lives in `research/2026-04-29-camunda-import-checklist.md` per the planner's note. NEEDS-INPUT.md is still empty. Don't run baseline-pytest until commit-or-stash decision lands or the planner explicitly waives it.

## [2026-04-29 09:00] process-tools-worker-9am (automated)
- read: CLAUDE.md, STATE.md, JOURNAL.md (last 6h, 5 entries), QUEUE.md, NEEDS-INPUT.md (empty), PROPOSED.md, DONE.md, roles/worker.md, `research/2026-04-29-camunda-import-checklist.md`, `samples/bpmn_validation/README.md`, `samples/bpmn_validation/simple_two_actors.bpmn`.
- did: picked the top unchecked queue item — P1 BPMN/Camunda Modeler import-validation. Definition of done explicitly requires Camunda Modeler 5.x desktop (procedure section-6 step 1: "Open in Camunda Modeler 5.x desktop. Capture: opens / does-not-open"). 9am Worker is unattended; no human at the keyboard, no scheduled `request_access` approval. Hit `roles/worker.md` bailout "the task is larger than you thought and would clearly take more than one Worker run." Did the part of the validation that's tractable without the GUI: (1) re-ran `bash scripts/test_all.sh` — ALL GREEN, 702 tests across 4 tools (no regression vs. 8am Worker's post-P0 run); (2) re-ran nimbus-skeleton's full unittest suite individually — 40/40 PASS, including the entire `test_bpmn_emitter.py` set (section-5 of the research file, ~80% of the failure surface); (3) wrote a ~180-LOC stdlib-only programmatic validator (`/tmp/bpmn_run/validate_bpmn_structural.py`) that walks the section-2 pass-criteria table against `samples/bpmn_validation/simple_two_actors.bpmn`. 24 checks, **24/24 PASS**. (4) wrote a partial-validation companion file under `research/`. (5) marked the QUEUE item `[in-progress]` and wrote a NEEDS-INPUT entry with three options for unblocking the GUI gate.
- produced:
  - `research/2026-04-29-bpmn-structural-validation.md`: companion to the import checklist; full pass/fail table for the 24 programmatic checks; explicit list of the section-6 steps (1, 3, 4) NOT covered by this run; recommendation that there's no pre-import structural reason to expect failure in either Camunda Modeler 5.x or demo.bpmn.io.
  - QUEUE.md: marked the P1 item `[in-progress]` (was `[ ]`) and appended a four-line note pointing to today's research file and the NEEDS-INPUT entry. Queue order otherwise unchanged.
  - NEEDS-INPUT.md: appended the BPMN GUI-gate question with three options — (A) Eric does the 15-minute manual walk himself, (B) explicit waiver to authorize a future scheduled Worker to use computer-use / Chrome MCP for this task, (C) defer and let the Planner re-queue. Each option spelled out with blast-radius.
  - validator script: `/tmp/bpmn_run/validate_bpmn_structural.py`, scratch only — not committed. Would clean up nicely as a `nimbus-skeleton/scripts/` addition once the orphan-dirs decision lands.
- verified:
  - Programmatic validator covers everything in section 1 of the research file marked "what would actually block import": `flowNodeRef` → real-id resolution (PASS), `sourceRef`/`targetRef` resolution (PASS), `incoming`/`outgoing` mirrored against `sequenceFlow` source/target (PASS), `targetNamespace` set (PASS), `BPMNDiagram` present (PASS).
  - Section 2 BPMNDI requirements (2026-04-26 DI fix): shape per pool/lane/flow-node (PASS), edge per sequence flow (PASS), ≥2 waypoints per edge (PASS), integer-pixel bounds (PASS), cross-lane edges have ≥4 waypoints / right-angle elbow (PASS).
  - Section 5 unittest pins: 40/40 PASS in nimbus-skeleton.
  - No edits to `nimbus-skeleton/`, `compliance-matrix/`, or `process-tools-common/` source — fully respected the orphan-dirs READ-ONLY constraint.
- notable:
  - The remaining ~20% per the research file ("modeler refuses for a subtle reason") truly cannot be exercised from an unattended Worker run. This isn't a structural problem with the queue item — it's a structural problem with the role boundary: GUI work needs a human or an explicitly-authorized computer-use Worker. Option B in the NEEDS-INPUT entry is the cleanest path if Eric wants to keep this on the automation rails.
  - The validator script is small enough (~180 LOC, stdlib-only) to be useful regardless of the GUI step. Once the orphan-dirs decision lands, it would slot under `nimbus-skeleton/scripts/` as the before-Camunda half of the structural-diff PROPOSED.md item from the researcher.
  - Did NOT write a DECISIONS.md entry. The procedure section-6 step 5 says "If everything passes, append a DECISIONS.md entry" — that's only after step 4 (Camunda re-save and structural diff) closes successfully. Today's run closed steps 2 and 5 only, so DECISIONS.md is not the right place yet.
  - Did NOT pick up the next queue item (P1 orphan-dirs decision scaffolding). `roles/worker.md` is "one item per run"; the BPMN P1 is now `[in-progress]` not closed, and the rule about skipping `[in-progress]` only applies if the next Worker is going to skip the SAME item — it's not a license for the current Worker to do two items.
- next handoff: process-tools-worker-10am (~10:00). Top of queue is now the P1 orphan-dirs decision scaffolding (the BPMN P1 is `[in-progress]` and waiting on Eric — skip it per the role rules). Definition of done is well-scoped (read-only inspection of three dirs, output is a `DECISIONS-orphan-dirs.md`). Tests still green. NEEDS-INPUT now has one open item (the BPMN GUI-gate question).

## [2026-04-29 09:00] process-tools-worker-9am (automated)
- read: CLAUDE.md, STATE.md, JOURNAL.md (last 6h, 5 entries), QUEUE.md, NEEDS-INPUT.md (empty), PROPOSED.md, DONE.md, roles/worker.md, `research/2026-04-29-camunda-import-checklist.md`, `samples/bpmn_validation/README.md`, `samples/bpmn_validation/simple_two_actors.bpmn`.
- did: picked the top unchecked queue item — P1 BPMN/Camunda Modeler import-validation. Definition of done explicitly requires Camunda Modeler 5.x desktop (procedure section-6 step 1: "Open in Camunda Modeler 5.x desktop. Capture: opens / does-not-open"). 9am Worker is unattended; no human at the keyboard, no scheduled `request_access` approval. Hit `roles/worker.md` bailout "the task is larger than you thought and would clearly take more than one Worker run." Did the part of the validation that's tractable without the GUI: (1) re-ran `bash scripts/test_all.sh` — ALL GREEN, 702 tests across 4 tools (no regression vs. 8am Wo