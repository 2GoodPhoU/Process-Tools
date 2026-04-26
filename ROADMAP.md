# Process-Tools — Roadmap

**Last updated:** 2026-04-25

A unified view of what's shipped, what's in flight, and what's
queued across the four tools in this workshop. Highlights only —
each tool's `CHANGELOG.md` has the full release detail.

---

## Strategic context

The most load-bearing recent finding sits behind the rest of this
roadmap: **TIBCO Nimbus on-premise retired on 2025-09-01** (no new
subscriptions, no renewals). The original premise of `nimbus-skeleton`
— "emit something Nimbus can import" — has shifted to "emit BPMN 2.0,
the open-standard interchange format that every modern process-modelling
tool reads." The Visio path is still useful for any Nimbus instance
still in operation, but BPMN 2.0 is now the forward direction. The
research note `requirements-extractor/research/2026-04-25-stack-alternatives-survey.md`
covers the full alternatives survey across NLP, parsers, NER, packaging,
GUI, and tabular interchange that informed this pivot.

Workshop-wide test count today: **570 tests passing** (DDE 505 +
nimbus-skeleton 33 + compliance-matrix 23 + process-tools-common 9).

---

## Cross-cutting items

These span all four tools and are worth resolving before any of the
tool-specific items.

### Now

- **Decide git tracking for the three untracked top-level dirs.** As of
  2026-04-25, `compliance-matrix/`, `nimbus-skeleton/`, and
  `process-tools-common/` are entirely untracked, with no nested `.git/`
  and no `.gitignore` rule excluding them. Either `git add` them as
  part of the monorepo or add them to `.gitignore` if they're meant to
  live separately. Right now their state is ambiguous.
- **Commit the overnight 2026-04-25 work** (BPMN emitter, actor
  heuristics, fuzzy-ID matcher, review-writer enhancement, integration
  test, ACTION_ITEMS) once tracking is decided.

### Next

- **Replace the `sys.path` bootstrap in `process-tools-common` consumers**
  with a real packaging convention. As soon as any tool in the repo
  picks up `pyproject.toml`, the others can declare
  `process-tools-common` as an editable dependency and the bootstrap
  goes away.
- **PyInstaller bundles for compliance-matrix and nimbus-skeleton**, so
  they run on the same restricted-network Windows machine DDE targets.
  DDE's `packaging/` spec is the template.
- **Address the file-tail truncation hazard.** Past sessions saw silent
  Edit/Write truncation and one null-byte corruption case on
  `nimbus-skeleton/` files. Mitigation today is "verify with
  `wc` / `tail` / `py_compile` after every edit" — worth formalising
  into a pre-commit hook.

### Later

- **Cross-tool integration test suite at the repo root.** Today,
  `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py`
  covers DDE→compliance-matrix. The DDE→nimbus-skeleton path has
  ad-hoc smoke tests but no pinned integration test.
- **Top-level CI** that runs all four test suites in one shot.
- **Repo-wide `pyproject.toml`** for shared lint / type-check / format
  configuration once the tools converge on tooling.

---

## Document Data Extractor (DDE)

**Path:** `requirements-extractor/`
**Version:** 0.5.0
**Tests:** 505 passing

### Shipped (highlights)

- **Multi-format input.** `.docx`, legacy `.doc` (via headless
  LibreOffice), and `.pdf` (via pdfplumber, with table-aware
  double-emit suppression).
- **Multi-format output.** `xlsx` (primary), plus `json`, Markdown,
  and ReqIF 1.2 with three dialect variants (`basic` / `cameo` /
  `doors`).
- **`diff` subcommand.** Stable-ID-aware spec drift detection with a
  3-colour Added / Removed / Changed workbook and CI-friendly exit
  codes.
- **Stable IDs.** `REQ-<8hex>` hashed from
  `(source_file, primary_actor, text)` — the canonical interchange
  ID across the workshop.
- **Smart boilerplate auto-skip.** 25 default section titles
  (Glossary, Acronyms, References, Revision History, …) skipped out
  of the box.
- **Inline source-preview Context column** (REVIEW §3.8). Up to 280
  chars of surrounding paragraph text per row.
- **Rule-based actor-extraction fallback** (overnight 2026-04-25):
  10 heuristics (`by`-agent, `send-to`, possessive, compound subject,
  conditional subject, `for` beneficiary, implicit-passive,
  hyphenated role, `between`, appositive). Opt-in via
  `ActorResolver(use_heuristics=True)`. Plumbed as a third pass after
  regex and NLP.
- **NLP bundle.** PyInstaller spec that bundles spaCy +
  `en_core_web_sm-3.7.1` + pdfplumber + `tkinterdnd2` directly into
  the exe so restricted-network machines never have to download
  anything. Documented runbook in `docs/NLP_BUNDLE_SMOKE_TEST.md`.
- **GUI polish.** Drag-and-drop, hover tooltips, first-run modal,
  persistent settings, cancellable runs, fit-to-content geometry.

### In progress

Nothing actively in flight; main backlog is below.

### Next

- **CLI flag for the new actor heuristics** (`--actor-heuristics`,
  default off). Currently only available via Python API.
- **GUI checkbox** for the same.
- **PyInstaller smoke test on Eric's restricted Windows network.**
  Spec is preflight-green in the dev sandbox; needs a real-target
  validation.
- **Real Cameo / DOORS ReqIF round-trip validation.** Blocked on
  hardware/software access.

### Later

- **Configurable role-noun whitelist** (`_ROLE_HEAD_NOUNS` in
  `actor_heuristics.py`) once corpus feedback shows whether the
  default list is too tight or too loose.
- **GLiNER as an alternative NER backend.** Zero-shot NER would let
  defense-spec actor vocabulary become a config decision rather than
  a training task. Tracked in the alternatives survey; not committed.
- **Source-preview hyperlink-vs-snippet decision** (REVIEW §3.8
  carryover).

---

## Compliance Matrix Generator

**Path:** `compliance-matrix/`
**Version:** 0.1.0
**Tests:** 23 passing

### Shipped (highlights)

- **End-to-end pipeline.** Two DDE xlsx inputs (contract + procedure)
  → 3-sheet coverage workbook (Matrix / Detail / Gaps).
- **Five matchers** running in parallel with weighted-max combination:
  `explicit_id` (regex citations, weight 1.0), `manual_mapping`
  (operator yaml/csv, weight 1.0), `fuzzy_id` (Levenshtein on
  citations, weight 0.95, default threshold 0.85), `similarity`
  (TF-IDF cosine, pure-stdlib, weight 0.85), `keyword_overlap`
  (token Jaccard, weight 0.65).
- **Pure-stdlib similarity matcher.** TF-IDF in ~50 lines without
  pulling scikit-learn or numpy — keeps the eventual PyInstaller
  bundle lean.
- **Manual mapping format.** YAML (`REQ-AB12: [PROC-9F33, PROC-104A]`)
  or CSV (`contract_id,procedure_id,note`), auto-detected by
  extension.
- **Loader on shared `process-tools-common`.** Local `loader.py` is a
  thin wrapper that just attaches the `side="contract"|"procedure"`
  discriminator.

### In progress

Nothing actively in flight.

### Next

- **Threshold tuning against a real spec/procedure pair.** Defaults
  (similarity 0.20, keyword 0.15, fuzzy_id 0.85) are placeholders.
- **HTML output alongside the xlsx**, faster to skim during review.
- **Weighted coverage scoring.** Today coverage is binary
  ("≥1 match = covered"); a weighted version would surface
  weakly-covered requirements.

### Later

- **PyInstaller bundle** (see cross-cutting backlog).
- **Web/SPA review surface** for the Detail sheet — easier triage
  than scrolling an xlsx.

---

## Nimbus Skeleton Mapper

**Path:** `nimbus-skeleton/`
**Version:** 0.1.0
**Tests:** 33 passing

### Shipped (highlights)

- **Pipeline.** DDE xlsx (+ optional actors xlsx) → classified
  `Skeleton` (activity / gateway / note + swimlanes per actor +
  sequence flows) → six output formats.
- **Six output formats per run.** `.puml` (PlantUML), `.skel.yaml`
  (tool-neutral pivot manifest), `.xmi` (UML 2.5 OMG-spec),
  `.vsdx` (Visio, native Nimbus import path with shape NameUs that
  match Nimbus's default Visio import rules), `.bpmn` (BPMN 2.0,
  the new strategic interchange format — opt-in via `--bpmn`),
  and `.review.xlsx` (flagged-items audit side-car).
- **BPMN 2.0 emitter** (overnight 2026-04-25, +14 tests). Triggered
  by the Nimbus retirement finding. Full element coverage:
  `<bpmn:process>` with lane sets per actor, tasks, exclusive
  gateways, sequence flows with `<bpmn:incoming>`/`<bpmn:outgoing>`
  declarations (Camunda Modeler is strict about this), text
  annotations for notes. Hand-built XML, byte-stable across runs.
  BPMNDI graphical layout intentionally omitted — modern BPMN tools
  auto-layout on import.
- **Review-writer enhancement** (prior session). Now takes
  `dde_rows=None` and adds a "Source Requirement" column when
  available.
- **Loader on shared `process-tools-common`.**
- **Byte-stable emitters.** Both `.xmi` and `.vsdx` page1.xml are
  byte-stable across runs — asserted by tests, makes diffs
  meaningful.

### In progress

Nothing actively in flight.

### Next

- **Visual validation of the BPMN output** by opening it in Camunda
  Modeler (or bpmn.io) against a real DDE-derived skeleton. Round-trip
  + structural tests cover ~80% of failure modes; the remaining 20% is
  "the modeler refuses to import for a subtle reason."
- **Phase 3a of the vsdx emitter:** emit cross-functional flowchart
  band shapes for proper swimlane bands. Today, activities sit in the
  right actor *column* but without the rectangular band overlay.
- **Phase 3b of the vsdx emitter:** pre-route connectors so the file
  looks decent before manual cleanup.

### Later

- **Loop / parallel-branch detection in the builder.** Currently
  linear-only — loops, parallel splits, and merge points are explicit
  human-judgment items.
- **`Skeleton.Gateway` `kind` field** (parallel / inclusive / exclusive)
  feeding into the BPMN emitter so gateways aren't all collapsed to
  XOR.
- **XSD validation test** for the BPMN output if a public BPMN 2.0
  XSD is available offline at Eric's site.
- **Classifier flag-rate tuning** against real spec corpora.
- **XMI dialect tweaks** if specific UML tools (Cameo, EA, MagicDraw)
  reject the OMG-spec output. The emitter is hand-built so dialect
  accommodations are a small delta.

---

## process-tools-common

**Path:** `process-tools-common/`
**Version:** 0.1.0
**Tests:** 9 passing

### Shipped (highlights)

- **`process_tools_common.dde_xlsx` module.** Centralises the DDE
  xlsx schema for both downstream tools. Adding a new DDE column is a
  one-line addition to `HEADER_MAP` that compliance-matrix and
  nimbus-skeleton both pick up automatically.
- **Public surface.** `HEADER_MAP`, `iter_dde_records`,
  `load_dde_records`, `iter_actor_records`, `load_actor_aliases`,
  `normalise_header`.
- **Silent degradation** for non-actors-shaped workbooks — returns an
  empty dict rather than raising. Nimbus-skeleton relies on this
  behaviour.

### In progress

Nothing actively in flight.

### Next

- **Extract more shared primitives.** Both consumer tools have similar
  `--quiet` logging patterns and the same "look up the side-car xlsx
  beside the input" convention — both candidates for promotion.

### Later

- **Replace the sys.path bootstrap** in consumers (see cross-cutting
  backlog).
- **Move ID-generation logic here** if a third consumer ever needs
  the `REQ-<8hex>` hash.

---

## Risk register

- **Untracked top-level dirs.** Highest priority — three directories
  of load-bearing code with no version control. Easy to fix once
  decided.
- **BPMN emitter not yet validated against a real modeler.** Mitigation
  is in the "Next" section above.
- **Heuristic false-positive rate unknown on real specs.** Tested
  against tightly-tuned example sentences. Heuristics are off by
  default, opt-in only.
- **TIBCO Nimbus retirement** changes the "what does the user
  ultimately import?" answer over time. BPMN 2.0 is the bet, but
  worth re-checking quarterly.
- **Edit-tool truncation hazard** in this repo — periodic verifier
  step is the current control. A pre-commit hook would make it
  systemic.

---

## Reading order for re-onboarding

1. `Process-Tools/README.md` — workshop overview and quickstart.
2. `Process-Tools/ACTION_ITEMS.md` — most recent overnight log
   (currently 2026-04-25).
3. `requirements-extractor/docs/PROJECT_OVERVIEW.md` — DDE
   architectural deep-dive.
4. Each tool's `CHANGELOG.md` for full release history.
5. `requirements-extractor/research/2026-04-25-stack-alternatives-survey.md`
   for the strategic-direction context.
