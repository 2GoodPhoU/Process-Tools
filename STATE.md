# State — Process-Tools

> Overwritten by the Planner each morning. One page max. Reflects the current state of the world as of the last Planner run.

## Last updated

(none yet — bootstrap)

## Current focus

Validate BPMN 2.0 emitter output against Camunda Modeler import.

## Open threads

- Orphan-dirs decision: `compliance-matrix`, `nimbus-skeleton`, `process-tools-common` are entirely untracked in git — Eric to decide tracked-vs-ignored before more code lands.
- Nimbus → BPMN 2.0 migration path validation (Camunda Modeler import is the gate).
- Rule-based actor-extraction fallback hardened with 10 heuristics — load-bearing for offline-network use.

## Recent decisions

- Three discharged `PLAN-*.md` files archived to `requirements-extractor/archive/`.
- Fuzzy-ID matcher (Levenshtein) shipped on `compliance-matrix`.
- BPMN 2.0 emitter shipped on `nimbus-skeleton`.

## Known constraints

- Eva validation week active through ~2026-05-03 — do NOT register scheduled tasks.
- Air-gapped target — no network calls in shipped binaries.
