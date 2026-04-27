# Process-Tools — Automation Standing Orders

> This file is read at the start of every automated run. If you are reading this as a scheduled task, you are operating under the constraints below. Read this fully before doing anything else.

## What this project is

Defense-contract Nimbus process modeling toolkit. Sub-tools: requirements-extractor (extracts requirements + actors from procedure docs), compliance-matrix (scaffolds traceability matrices), nimbus-skeleton (emits process models in BPMN 2.0, PlantUML, YAML, XMI, .vsdx), process-tools-common (shared utilities). Air-gapped target — bundles all dependencies via PyInstaller for offline-network deployment.

## Stack & conventions

Python 3.x, PyInstaller offline-bundle (with `collect_all` for spacy + en_core_web_sm). spaCy NLP for actor extraction with rule-based heuristic fallback (10 conservative rules) for offline use. Tkinter GUI. pytest (~508 tests in requirements-extractor + 33 in nimbus-skeleton + 13 in process-tools-common).

## Off-limits

- Do not introduce network-dependent code in shipped binary paths — air-gapped target.
- Do not modify archived `PLAN-*.md` files in `requirements-extractor/archive/` — historical reference.
- Do not break the BPMN 2.0 emitter — Nimbus retired Sept 2025; this is the migration path.
- Do not modify the three sibling top-level dirs (`compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`) until tracked-vs-ignored is decided (currently untracked — see `ACTION_ITEMS.md` Phase 0 finding).
- Do not push to remote unless explicitly approved.
- Do not register scheduled tasks during Eva validation week (active through ~2026-05-03).

## Definition of done (project-wide)

- All pytest tests pass for the affected sub-tool.
- PyInstaller spec includes any new spaCy/transformer/etc. submodules via `collect_all` or `hiddenimports`.
- New emitter output validates against the target tool's import (Camunda Modeler for BPMN, etc.) when applicable.
- Decision-doc-voice DECISIONS.md entry for emitter or architectural changes.
- No network calls in shipped-binary code paths.

## Project-specific notes

- Three sibling top-level dirs (`compliance-matrix`, `nimbus-skeleton`, `process-tools-common`) are entirely untracked in git as of 2026-04-26 — Eric to decide tracked-vs-ignored before more code lands.
- BPMN 2.0 emitter just shipped on `nimbus-skeleton`; next gate is Camunda Modeler import validation (the current focus).
- Rule-based actor-extraction fallback (10 heuristics: passive-by-agent, send-to, possessive, compound subject, conditional subject, for-beneficiary, implicit-passive, hyphenated role, between-X-and-Y, role appositive) is the offline-network load-bearing layer. Any heuristic change should be regression-tested.
- Edit-tool truncation is a recurring hazard — verify file contents post-edit, especially for `cli.py` and `actors.py`.

---

# How automation works in this project

This project runs on a "shift worker" model. Each scheduled run is a different role with one job. You are NOT working on the project all day — you are doing one specific shift, then handing off via the state files.

## State files (read these every run)

- `STATE.md` — current state of the world; 1 page; overwritten by the Planner each morning
- `JOURNAL.md` — append-only log; every run adds an entry
- `QUEUE.md` — prioritized work waiting to be done by Workers
- `PROPOSED.md` — things runs want to do but need human approval first
- `NEEDS-INPUT.md` — questions and blockers waiting for the human
- `DONE.md` — completed items

## Your role

The scheduled task that invoked you specified a role in the prompt. Find your role's instructions in `roles/<role>.md` and follow them. Do not do work outside your role.

Roles available: `night-auditor`, `researcher`, `planner`, `worker`, `digest`.

## Universal rules

1. Read STATE.md and JOURNAL.md first.
2. Append to JOURNAL.md when finished.
3. If ambiguous, write to NEEDS-INPUT.md and stop.
4. Never modify code unless your role explicitly allows it.
5. Stay in your lane.
6. Time-box yourself.
7. No silent failures.

## Working style (Eric's, applies everywhere)

- Operator voice. No cheerleading. Direct, no hedging.
- Anti-sprawl: don't create files unless they earn it.
- Ship-one-validate-next.
- Decision-doc voice in all DECISIONS.md entries.

## Don't

- No emoji unless asked.
- No status reports without an action.
- No new dashboards/files without explicit ask.
- No README/docs proactively.
- Do not register scheduled tasks during Eva validation week.
- Do not propagate the pre-commit hook beyond Sabrina-Local-AI in Phase 1.
