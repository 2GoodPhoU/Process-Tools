# Proposed — Process-Tools

> Things scheduled runs want to do but need human approval before execution. Triaged in the evening review window. Approved items graduate to QUEUE.md by the next Planner run.

## How approval works

- Check the box `[x]` to approve. The next Planner run will move it to QUEUE.md with appropriate priority.
- Strike through (or delete) to reject.
- Annotate with `[needs-discussion]` if you want to talk it through before deciding.

## Format

```
- [ ] [proposed-by: role / YYYY-MM-DD] Title
  - Why: ...
  - What it would do: ...
  - Risk / blast radius: ...
  - Suggested priority: P0 | P1 | P2
```

---

- [ ] [proposed-by: night-auditor / 2026-04-29] Commit (or stash) the ~2-day-old uncommitted patch line in `requirements-extractor/` before any worker touches it.
  - Why: working tree contains 13 modified tracked files (~840 LOC diff against HEAD: CLAUDE.md, QUEUE.md, STATE.md, schedule.json, the four sample bpmn-validation outputs, requirements-extractor's CHANGELOG and four core modules) plus 12 untracked items (~1933 LOC: `compound.py`, `multi_action.py`, four new test files, `PATCH-0.6.1-NOTES.md`, `PATCH-0.6.2-NOTES.md`, two new sample-procedures dirs, a `tests/baselines/` dir, and `build.log`). Last commit was 18ee238 on 2026-04-27 — automation went live 2026-04-28 and the baseline-pytest queue item explicitly captures "known-good" against today's working tree. With models.py in a syntax-error state (see today's P0), the patch line is on top of broken code; capturing a baseline against it pollutes the marker.
  - What it would do: have Eric review the 0.6.1/0.6.2 patch notes, repair the models.py truncation, run the full suite, and either (a) commit the patch line as one or more focused commits, or (b) stash it so the baseline runs against 0.6.0 (commit 18ee238). Either is fine — the point is the working tree should be a deliberate state before workers consume it.
  - Risk / blast radius: low if done now; rising. Each automated worker run that hits a broken working tree adds a JOURNAL entry and blocks the queue without producing useful output.
  - Suggested priority: P1

- [ ] [proposed-by: night-auditor / 2026-04-29] Fix the Windows pre-commit hook's Python discovery so future commits can't bypass the truncation guard.
  - Why: the most recent commit (a07224b) was made with `--no-verify` because the pre-commit hook picks up the MS Store Python stub instead of pyenv. The hook's `py_compile` check is exactly what would have caught the models.py truncation now sitting uncommitted in the working tree. Until the hook works on Eric's Windows setup, the documented "load-bearing layer against edit-tool truncation" is off.
  - What it would do: make `scripts/pre-commit-check.sh` robust to Windows Python discovery — e.g. honor `PYTHON` env var (it already does — but the hook needs to be invoked with it set), prefer `py -3` on Windows over bare `python3`, or add a `pyenv shims` lookup. Re-validate by re-enabling the hook and committing a known-clean file.
  - Risk / blast radius: small. Bash script change only; no shipped-binary impact.
  - Suggested priority: P2

- [ ] [proposed-by: night-auditor / 2026-04-29] Make `scripts/test_all.sh` fail-loud on test-module load errors.
  - Why: tonight's audit caught 27 `unittest.loader._FailedTest` ERRORs in requirements-extractor — but the per-tool `tail -3` summary only shows the final "Ran N tests / FAILED (failures=5, errors=27)" line, and the workshop-wide summary reports "Total ran: 205 tests" without mentioning that 27 modules never loaded. A future run with, say, only load-errors and 0 numeric failures could pass the eyeball test even though half the suite never executed.
  - What it would do: extend the suite-level summary to print error+failure counts alongside ran-counts, and make the workshop-wide summary line surface aggregate error counts (not just suite pass/fail). Optional: add a "modules failed to load" count parsed from the unittest output.
  - Risk / blast radius: scripts only; no source-tree or shipped-binary impact. ~20 LOC of bash.
  - Suggested priority: P2

- [ ] [proposed-by: researcher / 2026-04-29] Fold the Camunda Modeler import checklist into `samples/bpmn_validation/README.md`.
  - Why: the README's current "How to validate" section says "Verify visually: two lanes, four tasks, no errors at import" — three lines. The 2026-04-29 research pass found the import-failure surface is more specific than that (which lint warnings are platform-tag noise vs. real problems, what to expect on Camunda's auto-rewrite during save, what a structural-not-byte round-trip diff means in practice). The checklist exists in `research/2026-04-29-camunda-import-checklist.md` sections 2 and 6 — it should live in the README the validator actually reads, not in a research file they may or may not find.
  - What it would do: replace the current 3-bullet "Verify visually" list with the section-2 table (pool / lanes / tasks / events / flows / gateways / annotations + pass criterion per row) and append the section-6 procedure (open in Modeler, walk the table, repeat in bpmn.io, re-save and structural-diff, document outcome in DECISIONS.md). Keep the file ≤2 pages — anti-sprawl rule.
  - Risk / blast radius: doc-only. No source-tree or shipped-binary impact.
  - Suggested priority: P2

- [ ] [proposed-by: researcher / 2026-04-29] Add a small structural-diff helper for BPMN before/after Camunda re-save.
  - Why: the validator step "open in Camunda, save, confirm structural identity" is currently eyeball work. Camunda reformats XML on save (attribute ordering, indent), so a byte diff is useless; the meaningful diff is at (element-id, parent-lane, sequence-flow source/target, BPMNShape coverage) level. A 50-line stdlib script would make this repeatable and put it in CI for future emitter changes.
  - What it would do: small Python script that takes two `.bpmn` files and prints a structured diff: missing/added ids, lane-membership changes, sequence-flow source/target deltas, flow-node-without-shape count. No third-party deps (stdlib `xml.etree.ElementTree`).
  - Risk / blast radius: new file under `nimbus-skeleton/scripts/` or a new top-level utility — touches the orphan-dirs constraint, so the call has to wait until the orphan-dirs decision lands.
  - Suggested priority: P2

- [ ] [proposed-by: worker-8am / 2026-04-29] Broaden the truncation/NUL-byte sweep to actually catch trailing NUL bytes on tracked Python files.
  - Why: today's P0 had two distinct corruption modes sitting in the working tree, not one. The QUEUE definition-of-done called out only the duplicated-block + truncated docstring. The OTHER hazard — 192 trailing NUL bytes at EOF (rendered in `git diff` as one whitespace line followed by `\ No newline at end of file`) — was invisible to the Read tool (which silently filters NULs) and survived the night-auditor's "NUL-byte sweep clean" line. The cascade made `python3 -m py_compile` fail with `SyntaxError: unterminated triple-quoted string literal` (which the auditor saw) AND with `ValueError: source code string cannot contain null bytes` (which only surfaced after the duplicate block was removed). Without a NUL-aware check, future runs will keep losing time to this same shape.
  - What it would do: add a `grep -lP '\x00' <files>` pass (or equivalent — Python `open(rb).count(b'\x00')` is portable) to `scripts/pre-commit-check.sh` so the hook fails on any tracked `.py` file that contains a NUL byte. Mirror the same check in the night-auditor's audit pass so the audit doesn't claim "NUL-byte sweep clean" when grep's default behavior is treating the file as binary. Optional: extend the worker-side bailout in `roles/worker.md` so a worker that hits a NUL-byte read knows to fall back to a binary-mode rewrite rather than re-running Edit.
  - Risk / blast radius: scripts + role doc. No shipped-binary impact. ~30 LOC bash + a paragraph in `roles/worker.md`.
  - Suggested priority: P2

- [ ] [proposed-by: night-auditor / 2026-04-29] Refresh the test-count claims in CLAUDE.md to match reality.
  - Why: CLAUDE.md says "pytest (~508 tests in requirements-extractor + 33 in nimbus-skeleton + 13 in process-tools-common)". Tonight's discovery: nimbus-skeleton runs 40, process-tools-common runs 26, compliance-matrix runs 30 (uncited). requirements-extractor's 508 figure is unverifiable until the syntax error is fixed (109 ran tonight, 27 modules failed to load). Counts also drifted because new tests were added in the uncommitted 0.6.1/0.6.2 patch line. Also: the script uses `unittest discover`, not pytest — minor wording inconsistency.
  - What it would do: after the models.py P0 is fixed and the patch line is committed/stashed, re-run the suite and update the counts in CLAUDE.md. While there, change "pytest (~N tests)" to "unittest discover" to match the actual harness.
  - Risk / blast radius: doc-only.
  - Suggested priority: P2
