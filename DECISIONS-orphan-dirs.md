# Decision inputs — orphan dirs (`compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`)

> Compiled by process-tools-worker-10am, 2026-04-29. Read-only inspection. This document does NOT make the call. It assembles the inputs Eric needs to decide whether the three sibling top-level dirs should be tracked, ignored, or restructured.

## TL;DR — premise correction

The framing in `STATE.md`, `CLAUDE.md`, `COMMIT_PLAN.md`, and `ACTION_ITEMS.md` says these three dirs are "entirely untracked." **As of 2026-04-29 that is no longer true.** All three are tracked in git, with their initial commits dated 2026-04-25 (`76b4993`, `aac5728`, `26bc017`) and follow-up work landing through 2026-04-26. `git ls-files` returns 19, 20, and 8 files respectively; `git status -s` shows zero untracked items below them; `.gitignore` does not exclude them (only `nimbus-skeleton/sample-output/` is ignored, and that's regenerable smoke output).

The decision Eric is being asked to make has therefore shifted. It is not "tracked vs ignored from scratch." It is "leave tracked / formalize / un-track." See section 4 below for the three concrete options.

## 1. Per-dir findings

### 1.1 `compliance-matrix/`

| Field | Value |
|---|---|
| (a) File count (excl. `__pycache__`, `.pyc`) | 19 (all 19 tracked in git) |
| (b) Python LOC | 1,735 |
| (b) Non-Python LOC | 269 (CHANGELOG.md + README.md only) |
| (c) Newest file mtime | 2026-04-25 21:44 (`CHANGELOG.md`); newest source file 2026-04-25 21:42 (`compliance_matrix/loader.py`) |
| (d) Packaging metadata | `pyproject.toml` MISSING / `setup.py` MISSING / `setup.cfg` MISSING / `README.md` PRESENT (163 lines) |
| (e) Tests present | 3 test modules (`test_combiner.py`, `test_fuzzy_id.py`, `test_smoke.py`) under `tests/`. Currently passing: 30 / 30 (`python3 -m unittest discover tests` → exit 0, OK) |
| (f) Cross-references from `requirements-extractor/` | 42 hits across 5 files. Load-bearing references: `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py` invokes `python -m compliance_matrix.cli` (lines 118, 176) with `COMPLIANCE_MATRIX_ROOT = REPO_ROOT / "compliance-matrix"`. The other 4 files are docs/research/changelog (`docs/INTEGRATION.md`, `research/2026-04-25-stack-alternatives-survey.md`, `CHANGELOG.md`, `tests/integration/test_extractor_to_nimbus_skeleton.py`'s docstring). |

### 1.2 `nimbus-skeleton/`

| Field | Value |
|---|---|
| (a) File count (excl. `__pycache__`, `.pyc`) | 22 total; 20 tracked. The 2 untracked items are under `nimbus-skeleton/sample-output/` and are excluded by `.gitignore` (regenerable smoke output) |
| (b) Python LOC | 2,712 |
| (b) Non-Python LOC | 803 text-like (CHANGELOG.md + README.md) plus 2 binary/sample artifacts (`sample-output/long_procedure.bpmn`, `sample-output/long_procedure.REQS.xlsx`, both gitignored) |
| (c) Newest file mtime | 2026-04-27 05:26 (`nimbus_skeleton/emitters/bpmn.py` — the BPMNDI fix); newest test 2026-04-27 05:23 (`tests/test_bpmn_emitter.py`) |
| (d) Packaging metadata | `pyproject.toml` MISSING / `setup.py` MISSING / `setup.cfg` MISSING / `README.md` PRESENT (317 lines) |
| (e) Tests present | 3 test modules (`test_bpmn_emitter.py`, `test_review_writer.py`, `test_smoke.py`). Currently passing: 40 / 40 |
| (f) Cross-references from `requirements-extractor/` | 17 hits across 4 files. Load-bearing references: `requirements-extractor/tests/integration/test_extractor_to_nimbus_skeleton.py` invokes `python -m nimbus_skeleton.cli` (line 61) with `NIMBUS_SKELETON_ROOT = REPO_ROOT / "nimbus-skeleton"`. The other 3 are docs/research/changelog. |

### 1.3 `process-tools-common/`

| Field | Value |
|---|---|
| (a) File count (excl. `__pycache__`, `.pyc`) | 8 (all 8 tracked in git) |
| (b) Python LOC | 676 |
| (b) Non-Python LOC | 63 (CHANGELOG.md only — no README) |
| (c) Newest file mtime | 2026-04-25 21:43 (`CHANGELOG.md`); newest source file 2026-04-25 21:42 (`tests/test_helpers.py`) |
| (d) Packaging metadata | `pyproject.toml` MISSING / `setup.py` MISSING / `setup.cfg` MISSING / `README.md` MISSING / `README.rst` MISSING / `README.txt` MISSING — **only** `CHANGELOG.md` |
| (e) Tests present | 3 test modules (`test_cli_helpers.py`, `test_dde_xlsx.py`, `test_helpers.py`). Currently passing: 26 / 26 |
| (f) Cross-references from `requirements-extractor/` | 2 hits across 2 files. References: a single line in `requirements-extractor/docs/INTEGRATION.md` (line 128: "For schema evolution, see `process-tools-common/process_tools_common/dde_xlsx.py`") and a docstring comment in `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py` (line 9: "The output matches the expected xlsx schema (process-tools-common)"). **No `import process_tools_common` anywhere in `requirements-extractor/`.** No CLI invocation. The dir is presented as the schema authority but the integration tests don't load it as a Python package. |

## 2. Aggregate context (what's true across all three)

- **All three are tracked in git as of 2026-04-29.** Initial-commit / latest-commit pairs:
  - `compliance-matrix`: `76b4993` (2026-04-25) → `05b0499` (2026-04-26 02:42).
  - `nimbus-skeleton`: `aac5728` (2026-04-25) → `a07224b` (2026-04-26 23:42, BPMNDI emitter fix).
  - `process-tools-common`: `26bc017` (2026-04-25) → `05b0499` (2026-04-26 02:42).
- **None has packaging metadata.** No `pyproject.toml`, `setup.py`, or `setup.cfg` in any of the three. Each ships a `run_cli.py` wrapper at the dir root for direct-script invocation; none is `pip install`-able from a fresh checkout.
- **All three are wired into `scripts/test_all.sh`.** The script's `TOOLS=(...)` array lists all four sub-tools including these three. Removing any of them from the repo would break `bash scripts/test_all.sh` unless the script is also edited.
- **Two of the three are load-bearing for `requirements-extractor`'s integration test suite.** `compliance-matrix` and `nimbus-skeleton` are invoked via `python -m <pkg>.cli` from `requirements-extractor/tests/integration/`. Those tests assume the dir lives at `REPO_ROOT / <name>` — they will fail if the dirs are removed without a parallel test-suite restructure.
- **`process-tools-common` is the weakest link in the cross-reference graph.** Cited in docs as the schema authority, but `requirements-extractor` does not import it. Worth confirming whether `compliance-matrix` or `nimbus-skeleton` depend on it (out of scope for this read-only doc — flag as a follow-up).
- **All three test suites are currently green.** 30 + 40 + 26 = 96 tests, 0 failures, 0 errors when run today via `python3 -m unittest discover tests`. Combined with `requirements-extractor`, the workshop-wide count is 702 (per the 8am Worker's post-P0 run).

## 3. Cross-references inventory (the precise list)

Files in `requirements-extractor/` that mention any of the three orphan dirs:

| File | Mentions | Load-bearing? |
|---|---|---|
| `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py` | `compliance_matrix.cli` invocation, `COMPLIANCE_MATRIX_ROOT` path constant | YES — test fails if dir absent |
| `requirements-extractor/tests/integration/test_extractor_to_nimbus_skeleton.py` | `nimbus_skeleton.cli` invocation, `NIMBUS_SKELETON_ROOT` path constant | YES — test fails if dir absent |
| `requirements-extractor/docs/INTEGRATION.md` | Documents the DDE → compliance-matrix → nimbus-skeleton flow | NO (doc only) |
| `requirements-extractor/CHANGELOG.md` | Notes about the integration tests added | NO (changelog only) |
| `requirements-extractor/research/2026-04-25-stack-alternatives-survey.md` | Stack-architecture commentary | NO (research only) |

External, top-level-doc references to the three dirs (information only):

- `CLAUDE.md` lines 7, 11, 18 (sub-tools list, test-counts claim, off-limits rule).
- `README.md` lines 38, 63, 81 (architecture diagram + sub-tool sections).
- `ROADMAP.md` lines 15, 25, 37 (Nimbus retirement context, test counts, Phase-0 finding).
- `ACTION_ITEMS.md` lines 21, 24, 25 (Phase-0 progress table — references "33 tests pass" which has since drifted).
- `DECISIONS.md` lines 17, 81, 83 (BPMN emitter context).
- `COMMIT_PLAN.md` lines 9, 10, 22 (treats them as untracked — stale).
- `REFACTOR.md` lines 27, 33, 98 (refactoring history).
- `PLAN-gui-unification.md` lines 260, 340, 341 (GUI plan that imports `compliance_matrix.cli`).

## 4. Options table — tracked vs ignored

This section lays out three plausible outcomes and what each entails. **It does not recommend one.** Eric makes the call.

| Option | What it means | Effort | Consequence for `requirements-extractor` integration tests | Consequence for `scripts/test_all.sh` | Consequence for top-level docs | Consequence for the off-limits rule in `CLAUDE.md` |
|---|---|---|---|---|---|---|
| **A. Status quo — keep tracked, no formalization** | Acknowledge in `CLAUDE.md` and `STATE.md` that the dirs ARE tracked. Update `COMMIT_PLAN.md`'s stale Phase-0 framing. Lift the read-only off-limits rule once docs are aligned. | Doc-only. ~30 minutes. | Continues to work as-is. | Continues to work as-is. | Several files need a one-line correction (CLAUDE.md L18, ACTION_ITEMS.md Phase-0, COMMIT_PLAN.md Phase-0). | Off-limits rule becomes obsolete and should be removed — workers can edit these dirs once lifted. |
| **B. Formalize — keep tracked AND graduate to first-class subpackages** | Add `pyproject.toml` (and a `README.md` for `process-tools-common`) to each dir. Optionally migrate the `run_cli.py` shims to `[project.scripts]` console-script entry points. Wire each into a top-level `pyproject.toml` workspace if desired. | ~1 day per dir to do it carefully. The 3 PyInstaller specs (one per dir? need to check) may need re-validation. | Could simplify to `pip install -e ./compliance-matrix` instead of the `python -m` invocations. Nice-to-have; tests don't require it. | Could remain `unittest discover` based, or migrate to a single root-level `pytest` invocation. Optional. | Doc updates needed in same files as Option A, plus a new section explaining the workspace layout. | Off-limits rule lifted (same as A) once metadata lands. |
| **C. Untrack — remove from this repo, restructure as separate repos / external deps** | `git rm -r --cached compliance-matrix/ nimbus-skeleton/ process-tools-common/`, add to `.gitignore`, push to new repos. Vendor as git submodules or pip dependencies (the latter requires Option B's metadata first). | High. ~3-5 days end-to-end including new-repo plumbing, CI updates, integration-test rewrite. Breaks the air-gapped PyInstaller bundle path until resolved. | **Breaks `test_extractor_to_compliance_matrix.py` and `test_extractor_to_nimbus_skeleton.py`** unless the integration tests are rewritten to point at the new dependency locations or marked as multi-repo. | **Breaks `bash scripts/test_all.sh`** unless the `TOOLS=(...)` array is updated and the missing dirs are skipped. | Major rewrites of CLAUDE.md, README.md, ROADMAP.md, ACTION_ITEMS.md to reflect a multi-repo workshop. | Off-limits rule removed; replaced with a "these are external dependencies" note. |

### Side-table: what stays the same regardless of option

- The four sub-tools' tests are green today. None of these options changes that immediately.
- The BPMN 2.0 emitter (Nimbus → BPMN migration path) lives in `nimbus-skeleton/nimbus_skeleton/emitters/bpmn.py` regardless of which option is picked. The structural-validation and Camunda-Modeler-import gates are unaffected.
- The air-gapped PyInstaller constraint applies to `requirements-extractor`'s shipped binary specifically. Whether the orphan dirs are in this repo, in another repo, or vendored doesn't change that — they are not currently bundled into the DDE binary either way.
- `process-tools-common`'s status as "schema authority" is a documentation claim, not an enforced import constraint. None of the three options resolves that — that's a separate decision about whether to make it a real dependency.

## 5. What this doc does NOT do (out of scope per the queue item)

- Does not recommend an option.
- Does not modify any file under the three dirs (READ-ONLY constraint observed).
- Does not edit `CLAUDE.md`, `STATE.md`, `COMMIT_PLAN.md`, or `ACTION_ITEMS.md` to fix the stale "untracked" premise. That is a follow-up for a Planner or Worker run with explicit permission.
- Does not run `scripts/test_all.sh` end-to-end (that's the gated baseline-pytest item, not this one). The per-dir test runs above were `python3 -m unittest discover tests` against each orphan dir individually.
- Does not investigate whether `compliance-matrix` or `nimbus-skeleton` import `process_tools_common` (would mean entering those source trees with grep, which is in-scope for read-only inspection — but the question deserves its own focused look once the option is chosen, since it informs Option C's scope).
- Does not decide whether `nimbus-skeleton/sample-output/` should remain `.gitignore`'d.

## 6. Suggested next step (procedural, not substantive)

Once Eric picks A, B, or C, the next Planner run should:

1. If **A**: queue a doc-correction Worker item to align CLAUDE.md / COMMIT_PLAN.md / ACTION_ITEMS.md with the actual tracked status, and lift the read-only off-limits rule.
2. If **B**: queue a multi-step plan (one Worker item per dir for `pyproject.toml` + `README.md` additions; one item for top-level workspace wiring; one item for PyInstaller spec re-validation per shipped-binary path).
3. If **C**: stop and write a fuller migration plan; this is too large for a single Worker item.

---

*End of decision inputs. The call is Eric's.*
