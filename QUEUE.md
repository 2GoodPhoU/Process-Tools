# Queue — Process-Tools

> Prioritized work waiting to be picked up by Workers. The Planner curates this each morning. Workers pick the top unchecked item.

## Format

Each item:

```
- [ ] [P0|P1|P2] Title — one-sentence description.
  - Definition of done: ...
  - Notes: ...
```

Use `[in-progress]` instead of `[ ]` if a Worker started but couldn't finish (with a note in NEEDS-INPUT.md about what blocked them).

---

- [in-progress] [P1] Validate the new BPMN 2.0 emitter output against Camunda Modeler's import.
  - Definition of done: emit a representative skeleton via the BPMN emitter, import into Camunda Modeler (free desktop), confirm structural integrity (lanes, tasks, gateways, sequence flows, text annotations) round-trips cleanly. Document any failures as DECISIONS doc entries.
  - Constraint: READ-ONLY against `nimbus-skeleton/`. Orphan-dirs tracked-vs-ignored decision is unresolved (see CLAUDE.md off-limits). Do NOT edit source under `nimbus-skeleton/`, `compliance-matrix/`, or `process-tools-common/`. Emit BPMN artifacts to your run's scratch dir; record findings in `nimbus-skeleton/DECISIONS.md` (file may be created — that's a doc, not source). If the emitter run requires a code change to produce a clean import, stop and write to NEEDS-INPUT.md.
  - Notes: Closes the Nimbus → BPMN 2.0 migration-path validation gate. **Read `research/2026-04-29-camunda-import-checklist.md` first** — it has the per-element pass-criterion table (section 2), the round-trip-as-structural-identity rule (section 3), the list of Camunda 5.x lint warnings that are NOT failures (section 4: platform-tag noise, executionPlatform missing, Zeebe runtime hints), and a 6-step Worker procedure (section 6). Use those, don't redo the research.
  - **Worker-9am 2026-04-29:** programmatic structural validation done (24/24 PASS) and section-5 unittest pins re-run green (40/40 in nimbus-skeleton). The remaining ~20% is the GUI gate (Camunda Modeler desktop + demo.bpmn.io drag-drop + save round-trip), which an unattended Worker cannot exercise. See `research/2026-04-29-bpmn-structural-validation.md` for the partial-validation report, and the NEEDS-INPUT entry below for the two paths Eric can pick from to unblock the GUI step.

- [ ] [P1] Orphan-dirs decision scaffolding — assemble the inputs Eric needs to decide tracked-vs-ignored for `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`.
  - Definition of done: a new top-level `DECISIONS-orphan-dirs.md` containing, for each of the three dirs: (a) file count, (b) total LOC (Python + non-Python broken out), (c) last-modified date of newest file, (d) whether a `pyproject.toml`/`setup.py`/`README` exists, (e) any tests present and whether they currently pass, (f) cross-references from `requirements-extractor/` into that dir. Closes with a "tracked vs ignored" options table listing the 2–3 plausible outcomes and the consequences of each. Does NOT make the call — produces the inputs.
  - Constraint: READ-ONLY against all three dirs (no edits, no `git add`, no test fixes). Pure inspection.
  - Notes: Unblocks code-touching work in the three dirs, which is currently gated by CLAUDE.md off-limits.

- [ ] [P1] Baseline pytest run for `requirements-extractor/` and capture results. **GATED on the P0 above.**
  - Definition of done: run the full `requirements-extractor/` test suite. Write a new `requirements-extractor/BASELINE-2026-04-29.md` (renamed from -28; the marker is captured the day the suite is actually green) with: pass/fail/skip counts, list of any failing tests with their error class (one line each), list of any flakies observed across two consecutive runs, total wall-clock time, Python version, spaCy version, en_core_web_sm version. Commit with message "baseline: requirements-extractor pytest snapshot 2026-04-29".
  - Constraint: do NOT run if `bash scripts/test_all.sh` still shows the 27-error / 5-fail pattern from the P0 — capturing a baseline against a broken tree pollutes the marker. If the P0 is not yet done, leave this item unstarted and pick up the next item instead.
  - Notes: Establishes a known-good marker before automated workers start mutating the codebase. The 0.6.1/0.6.2 patch line is uncommitted in the working tree; the auditor's PROPOSED commit-or-stash item has not been approved yet — treat the baseline as covering "tree as it stands today, including the patch line". Note this explicitly in BASELINE-2026-04-29.md.

- [ ] [P2] Audit regression coverage for the 10 actor-extraction heuristics.
  - Definition of done: append a section to `requirements-extractor/DECISIONS.md` (create the file if missing — it's a doc, not source) listing each of the 10 heuristics (passive-by-agent, send-to, possessive, compound subject, conditional subject, for-beneficiary, implicit-passive, hyphenated role, between-X-and-Y, role appositive) with: heuristic name, file/function it lives in, named tests covering it (test names, not just counts), and a coverage verdict (covered / partially covered / uncovered). No new tests written — this is an audit, not a remediation.
  - Notes: The rule-based fallback is offline-network load-bearing. We need to know which heuristics are exposed if a future change breaks them silently.

- [ ] [P2] Edit-tool truncation sweep — broadened to all four core requirements_extractor modules.
  - Definition of done: run `git diff HEAD --` against `requirements-extractor/requirements_extractor/cli.py`, `actors.py`, `models.py`, and `extractor.py` (or whichever four modules are core — confirm by file size + import graph). Compare line counts and `tail -15` against the last commit. If all are clean (no uncommitted truncation), append a one-line note to JOURNAL.md confirming clean state. If truncation is detected on any module, write to NEEDS-INPUT.md with file, expected vs. actual line count, and stop — do NOT attempt to restore.
  - Notes: CLAUDE.md flags edit-tool truncation as a recurring hazard for cli.py and actors.py specifically. Tonight's audit revealed the hazard hit a third file (models.py) — broadening the sweep to the four core modules costs nothing extra and would have caught tonight's P0 a day earlier. Not gated on the P0 (read-only inspection). After the P0 is fixed, the sweep should pass cleanly.

- [ ] [P2] Audit the PyInstaller spec against current imports.
  - Definition of done: compare actual imports in `requirements-extractor/` shipped-binary code paths against the PyInstaller spec's `collect_all` / `hiddenimports` lists. Append findings as a section in `requirements-extractor/DECISIONS.md`: list of imports present in code but missing from the spec, list of entries in the spec that are no longer imported anywhere. Do NOT edit the spec — propose changes via PROPOSED.md if any are warranted.
  - Notes: Air-gapped target. A missing `collect_all` entry shows up as a runtime import error on the offline network, not at build time.
