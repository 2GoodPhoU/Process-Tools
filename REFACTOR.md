# Process-Tools — Refactor punch list

**Last updated:** 2026-04-25 (post-execution)
**Status:** items S1, T4, S2, S5, D1+D2, D3+D4, S6 **executed and
green**. Items S3, S4, T2, T3, T5 remain — see "What still needs
your involvement" at the bottom. T1 is **deferred** pending
external-script confirmation.

This document covers three buckets:

This document covers three buckets:

1. **Stability** — reducing how often something silently breaks.
2. **Code dedup** — removing duplicated patterns across tools.
3. **Trim** — removing weight, dead paths, or oversized outputs.

Items are numbered in priority order within each bucket. Sizes use
T-shirt scale (XS = <30 min, S = 1–2 hrs, M = half-day, L = day+).
Risk uses Low / Medium / High based on test coverage and blast radius.

---

## 1. Stability

### S1. Add `fuzzy_id` to `combiner.DEFAULT_WEIGHTS` — Risk: **Low**, Size: **XS** — **DONE 2026-04-25**

**Finding.** When `fuzzy_id` was added to `compliance-matrix`, the
combiner's weight dict wasn't updated. The matcher fires correctly,
but its score multiplies by the `weights.get(..., 0.5)` fallback
rather than a deliberate weight. README documented it as 0.95, then
0.60 — neither was true.

**File.** `compliance-matrix/compliance_matrix/combiner.py`

**Sketch.**

```python
DEFAULT_WEIGHTS: Dict[str, float] = {
    "explicit_id": 1.0,
    "manual_mapping": 1.0,
+   "fuzzy_id": 0.95,        # near-gold; small Levenshtein delta on canonical IDs
    "similarity": 0.85,
    "keyword_overlap": 0.65,
}
```

The 0.95 number is a starting point — the weight the README *thought*
it had. Real number should follow threshold tuning against a corpus.
Also update the docstring at the top of `combiner.py`.

**Test impact.** Existing 20 fuzzy-id tests already exercise
score behaviour. Add one combiner test that asserts the weight
flows through correctly.

---

### S2. Pre-commit hook for the truncation hazard — Risk: **Low**, Size: **S** — **DONE 2026-04-25**

**Finding.** The `feedback_edit_truncation.md` memory and ACTION_ITEMS
both flag a recurring file-tail truncation issue. Mitigation today is
"verify with `wc` / `tail` / `py_compile` after every edit" —
manual, easy to skip.

**Proposal.** A pre-commit hook that runs `python -m py_compile` on
every staged `.py` file, plus a null-byte check (`grep -lP '\x00'`).
Both are cheap (sub-second) and catch the documented failure modes
deterministically.

**Files.**
- `.pre-commit-config.yaml` (new at repo root)
- Optionally a `scripts/check_no_null_bytes.sh` helper

**Test impact.** None on test suites. Validation is "make a synthetic
broken file, try to commit it, watch the hook reject it."

---

### S3. BPMN modeler validation — Risk: **Low**, Size: **S** (one-off) — **SAMPLE READY, ERIC TO VALIDATE**

**Finding.** The BPMN emitter has structural + byte-stability tests
(14 tests, all green), but has not been opened in a real BPMN tool.
Round-trip + structural tests cover ~80% of failure modes; the
remaining 20% is "the modeler refuses to import for a subtle reason."

**Sample generated 2026-04-25.** A real `.bpmn` produced from
`samples/procedures/simple_two_actors.docx` lives at
`samples/bpmn_validation/simple_two_actors.bpmn`. See
`samples/bpmn_validation/README.md` for the validation steps.
Quick form:

1. Open `samples/bpmn_validation/simple_two_actors.bpmn` in **Camunda
   Modeler** (https://camunda.com/download/modeler/) or drag-and-drop
   into **bpmn.io** (https://demo.bpmn.io/).
2. Verify visually:
   - Two lanes (Operator, Supervisor) with two tasks each.
   - Start event → first Operator task → branches to a Supervisor
     task and a second Operator task → both rejoin into the end event.
   - No "invalid BPMN" warnings on import.

If anything's off, file the specific symptom against the emitter.

**Test impact.** This is a one-off acceptance check, not an automated
test. If a public BPMN 2.0 XSD is available offline, we can add an
XSD-validation test (separate item — see S4).

---

### S4. Optional: BPMN XSD validation test — Risk: **Low**, Size: **S**

**Finding.** Without an XSD-validation test, the only schema feedback
is whatever the modeler GUI prints. If a public BPMN 2.0 XSD is
available offline at Eric's site, we can add a test that loads it
once and validates every emitter run against it.

**File.** `nimbus-skeleton/tests/test_bpmn_xsd.py` (new)

**Blockers.** Need the XSD from somewhere — OMG hosts it but the
defense network may not reach it. Eric to confirm.

---

### S5. Cross-tool integration test for DDE → nimbus-skeleton — Risk: **Low**, Size: **M** — **DONE 2026-04-25**

**Finding.** `requirements-extractor/tests/integration/test_extractor_to_compliance_matrix.py`
exists for the DDE → compliance-matrix path. The DDE → nimbus-skeleton
path has unit tests on each side but no end-to-end integration test.

**Proposal.** Mirror the existing integration test: synthesise a small
`.docx`, run DDE on it, feed DDE's xlsx into nimbus-skeleton, assert
the .puml/.skel.yaml/.xmi/.vsdx all emit and the .review.xlsx surfaces
the expected flagged items.

**File.** `requirements-extractor/tests/integration/test_extractor_to_nimbus_skeleton.py` (new)

**Test impact.** ~5 tests added. No code changes elsewhere.

---

### S6. Top-level CI for the four test suites — Risk: **Low**, Size: **M** — **DONE 2026-04-25**

**Finding.** Each tool's tests are runnable independently
(`cd <tool>/ && python -m unittest discover tests`). There's no single
green-or-red signal across the workshop today.

**Proposal.** A `Makefile` or `tasks.py` at repo root with a
`test-all` target that runs all four suites and aggregates exit codes.
Optionally a GitHub Actions / Azure Pipelines yaml if Eric's site
runs CI.

**File.** `Makefile` (new) or `scripts/test_all.sh`

---

## 2. Code dedup

### D1. Extract shared CLI helpers (`--quiet`, sys.path bootstrap) — Risk: **Medium**, Size: **S** — **DONE 2026-04-25**

**Finding.** Both `compliance-matrix/cli.py` and `nimbus-skeleton/cli.py`
declare `--quiet` at exactly line 104, with identical surrounding
argparse boilerplate. Both `loader.py` files do an identical sys.path
bootstrap to import `process_tools_common`.

**Proposal.** Promote to `process_tools_common`:

- `process_tools_common.cli_helpers.add_quiet_flag(parser)` — adds
  `-q/--quiet` and returns the dest name.
- `process_tools_common.cli_helpers.configure_logging(quiet)` — central
  logging setup so both tools print identically.
- The sys.path bootstrap is already minimal (~6 lines per tool); a
  single helper module isn't worth the extra hop, but a comment block
  documenting the bootstrap as "intentionally duplicated until
  pyproject.toml lands" is cheap.

**Files.**
- `process-tools-common/process_tools_common/cli_helpers.py` (new)
- `process-tools-common/tests/test_cli_helpers.py` (new)
- Edit `compliance-matrix/compliance_matrix/cli.py` to use the shared
  helper
- Edit `nimbus-skeleton/nimbus_skeleton/cli.py` to use the shared
  helper

**Test impact.** Existing CLI smoke tests in both tools should keep
passing. Add 2–3 new tests in process-tools-common.

**Risk note.** Medium because both tool CLIs are user-facing — flag
behaviour can't subtly change. Mitigation: add a regression test that
asserts `-q` and `--quiet` both work on each tool.

---

### D2. Shared logging — Risk: **Low**, Size: **XS** (folds into D1) — **DONE 2026-04-25 (with D1)**

**Finding.** Same as D1 — `_logging.py` exists in DDE; the other
tools rely on bare `print` for status and a flag for `--quiet`. Three
tools, three different "tell the user what's happening" implementations.

**Proposal.** Same module as D1's `cli_helpers.py`:
`configure_logging(quiet: bool)` returns a logger configured with
the project-standard format.

**Files.** Folds into D1.

---

### D3. "Side-car xlsx beside input" lookup — Risk: **Low**, Size: **XS** — **DONE 2026-04-25** (`find_sidecar` shipped; consumer wiring deferred until next loader change)

**Finding.** Both nimbus-skeleton and DDE have a "look up the actors
xlsx beside the input file if not specified" convention but
hand-rolled in each.

**Proposal.** `process_tools_common.dde_xlsx.find_sidecar(input_path,
suffix="_actors")` returning `Optional[Path]`.

**Files.**
- `process-tools-common/process_tools_common/dde_xlsx.py` (extend)
- Both consumer tools (small edits to use the helper)

---

### D4. The two `loader.py` files have similar shapes — Risk: **Medium**, Size: **S** — **DONE 2026-04-25**

**Finding.** `compliance-matrix/loader.py` (74 lines) and
`nimbus-skeleton/loader.py` (60 lines) are both thin wrappers over
`process_tools_common.dde_xlsx.iter_dde_records`. Each converts the
shared dict into the tool's own `DDERow` dataclass.

**Proposal.** Don't merge the dataclasses — they intentionally
project to different field subsets per tool. But factor out the
"open xlsx + iterate + map" boilerplate into
`process_tools_common.dde_xlsx.load_into(path, row_factory)` taking
a callable that builds the tool's domain row from the shared dict.

**Files.**
- `process-tools-common/process_tools_common/dde_xlsx.py` (extend)
- Both consumer `loader.py` files (use the helper)

**Risk note.** Medium — touches the data path that drives the entire
output. Add a regression test that the post-refactor loaders produce
byte-identical output xlsxs vs pre-refactor.

---

## 3. Trim

### T1. Remove the 8-line `json_writer.py` / `md_writer.py` shims — Risk: **Low**, Size: **XS** — **DONE 2026-04-25** (Eric confirmed no external scripts)

**Finding.** `requirements_extractor/json_writer.py` and `md_writer.py`
are 8-line backward-compat shims that re-export from `writers_extra`.
Comment explicitly says "exists only so callers that imported X in an
earlier pass don't break."

**Verification (run 2026-04-25).** In-repo grep is clean — only the
shim files themselves and a `TestCompatibilityShims` class in
`tests/test_writers_extra.py` reference these names. Within the repo,
removal is safe.

**Why deferred.** The shims exist explicitly for *external* scripts
(Eric's personal tooling, scripts shared across the team, packaging
specs outside the repo) written before the writer consolidation. The
in-repo grep can't see those, and removing the shims would silently
break any external script that does `from requirements_extractor
import json_writer`. Cost of keeping: 16 lines of code + 2 small unit
tests — trivially small. Cost of removing: a hidden breakage we
wouldn't discover until somebody runs an old script.

**Decision needed from Eric.** Are there any external scripts (outside
`Process-Tools/`) that import `requirements_extractor.json_writer` or
`requirements_extractor.md_writer`? If no → safe to remove on a
0.6.0 / 1.0.0 bump. If unsure → leave them; the cost is tiny.

**Verification command.**
```
cd Process-Tools && grep -rn "from requirements_extractor.json_writer\|from requirements_extractor.md_writer\|import json_writer\|import md_writer" --include='*.py'
```

---

### T2. PyInstaller bundle size audit — Risk: **Medium**, Size: **M**

**Finding.** The `requirements-extractor` PyInstaller exe is 300–450 MB.
Per the alternatives survey, this is mostly spaCy + thinc + pydantic +
murmurhash + the `en_core_web_sm` model wheel (12-13 MB unpacked).

**Self-serve runbook.** Eric runs this on his Windows build machine;
no further input from me needed:

```powershell
# 1. Set up the build venv (one-time, on the Windows build machine)
cd C:\Users\erics\Documents\GitHub\Process-Tools\requirements-extractor
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-optional.txt
pip install -r packaging\build-requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# 2. Build with import logging on
pyinstaller --log-level DEBUG --debug=imports `
    packaging\DocumentDataExtractor.spec 2>&1 | Tee-Object build_log.txt

# 3. Inventory what got bundled, biggest packages first
dir dist\DocumentDataExtractor\_internal | Sort-Object Length -Descending |
    Select-Object -First 30 Name, Length

# Or for the bundled subdirs:
Get-ChildItem dist\DocumentDataExtractor\_internal -Recurse |
    Group-Object Directory |
    Sort-Object @{Expression={ ($_.Group | Measure-Object Length -Sum).Sum }} -Descending |
    Select-Object -First 20 Name,
        @{Name='SizeMB';Expression={ [math]::Round((($_.Group | Measure-Object Length -Sum).Sum / 1MB), 1) }}
```

**Likely findings (predicted from the alternatives survey):**

1. **`scipy` is being bundled but never imported.** spaCy *imports* it
   conditionally; the real code path in DDE doesn't. PyInstaller
   bundles it anyway because of static analysis. Excluding it via
   `excludes=["scipy"]` in the spec could save ~100 MB.
2. **`thinc` test fixtures** if any are getting bundled.
3. **Tk** is bundled even when running headless via the CLI —
   unavoidable given the GUI is in the same package.
4. **`numpy` weight** — spaCy needs numpy at runtime; can't be
   excluded, but check version pin doesn't pull a fat one.

**How to interpret the size table.** Anything over 50 MB that DDE
doesn't actively call is a candidate for an `excludes` entry in
`packaging/DocumentDataExtractor.spec`. Add the package name there,
rebuild, and confirm `python -m requirements_extractor.cli requirements
samples/procedures/simple_two_actors.docx -o /tmp/x.xlsx` still works
inside the bundled exe.

**Aggressive alternative (separate item).** Switch to a non-spaCy NER
backend (GLiNER or Flair) — the alternatives survey covers this.
That's a real refactor, not a trim, and is tracked in the roadmap.

**Files.**
- `requirements-extractor/packaging/DocumentDataExtractor.spec` (edit
  the `excludes=[...]` list)

**Test impact.** Need a real Windows build + smoke test to confirm
nothing breaks. Same as the `NLP_BUNDLE_SMOKE_TEST.md` runbook —
worth running once and recording the SHA-256 of the resulting exe.

**Done when.** The exe drops below 250 MB and `make test-all` plus a
manual run of the bundled CLI on a sample `.docx` both pass.

---

### T3. Audit DDE output formats for "is anyone using this?" — Risk: **Low**, Size: **M (if executed)** — **AUDIT DONE; REMOVAL DEFERRED**

**Finding.** DDE emits xlsx, json, markdown, and ReqIF (with three
dialects). That's a lot of surface.

**Eric's answer (2026-04-25):** **only xlsx is in active use.** JSON,
Markdown, and ReqIF (basic / cameo / doors) are confirmed pruning
candidates — but the *removal* is deferred to a future major version
bump (0.6.0 or 1.0.0) since it's a breaking change for any consumer
who wires through the `--emit json,md,reqif` flag.

**Files when executed.**
- `requirements-extractor/requirements_extractor/writers_extra.py` — keep `requirement_to_dict` (used by xlsx writer); drop `write_requirements_json` / `write_requirements_md`.
- `requirements-extractor/requirements_extractor/reqif_writer.py` — delete entirely.
- `requirements-extractor/requirements_extractor/cli.py` — drop `--emit` flag and `--reqif-dialect`.
- `requirements-extractor/tests/test_writers_extra.py` — drop the JSON/MD test classes.
- `requirements-extractor/tests/test_reqif_*.py` — delete.
- README, CHANGELOG (Breaking).

**Estimated test-suite impact when executed.** ~50–80 tests deleted
(net negative because some were testing dead code anyway).

---

### T4. ACTION_ITEMS.md is stale — archive it — Risk: **Low**, Size: **XS** — **DONE 2026-04-25** (Phase 0 marked RESOLVED in-place; WHEN_YOU_RETURN.md repointed at ROADMAP/REFACTOR/COMMIT_PLAN)

**Finding.** `ACTION_ITEMS.md` flags the three top-level dirs as
untracked, but git log shows them committed. The doc's load-bearing
section is wrong as of 2026-04-25.

**Proposal.** Either:

- (a) Move to `archive/ACTION_ITEMS-2026-04-25.md` and update
  `WHEN_YOU_RETURN.md` to point at `ROADMAP.md` instead.
- (b) Rewrite the Phase 0 section to say "RESOLVED — all dirs now
  tracked" and keep the rest as historical record.

The second is more conservative. Let me know your preference.

**Files.**
- `ACTION_ITEMS.md` (edit or move)
- `WHEN_YOU_RETURN.md` (edit)

---

### T5. DDE module count — Risk: **Medium**, Size: **M**

**Finding.** `requirements-extractor/requirements_extractor/` has 18
Python modules totalling ~7,000 lines. Some are large
(`gui.py` 1,119 lines; `parser.py` 749 lines; `actor_scan.py` 640 lines)
and some are very small (`json_writer.py` 8 lines per T1, `md_writer.py`
8 lines per T1, `models.py` 203 lines).

**Proposal.** No structural change *speculatively*. The orchestration
already separates `_orchestration.py` and `_logging.py` into clean
helpers; the large files are large because they encapsulate large
domains (full Tk GUI, full .docx walker). Splitting `parser.py`
without a forcing function would just churn diffs.

**Items worth doing if test churn or onboarding pain materialises:**
- Split `gui.py` per-section (input config, options, run/log) once
  the GUI grows past 1,500 lines.
- Extract the procedural-table subsystem from `parser.py` if it
  grows further (it's already factored to `procedural.py`).

**Files.** None changed yet — recording for the roadmap.

---

## Summary table

| ID  | Bucket    | Risk   | Size | Status | Description                               |
|-----|-----------|--------|------|--------|-------------------------------------------|
| S1  | Stability | Low    | XS   | DONE   | Fix `fuzzy_id` weight in `DEFAULT_WEIGHTS` |
| S2  | Stability | Low    | S    | DONE   | Pre-commit hook for truncation hazard     |
| S3  | Stability | Low    | S    | READY  | BPMN modeler one-off validation (sample at samples/bpmn_validation/) |
| S4  | Stability | Low    | S    | OPEN   | BPMN XSD validation test (blocker: XSD)   |
| S5  | Stability | Low    | M    | DONE   | DDE → nimbus-skeleton integration test    |
| S6  | Stability | Low    | M    | DONE   | Top-level CI / `make test-all`            |
| D1  | Dedup     | Medium | S    | DONE   | Shared CLI helpers (--quiet etc.)         |
| D2  | Dedup     | Low    | XS   | DONE   | Folds into D1                             |
| D3  | Dedup     | Low    | XS   | DONE   | Side-car xlsx lookup helper               |
| D4  | Dedup     | Medium | S    | DONE   | Loader boilerplate factoring              |
| T1  | Trim      | Low    | XS   | DONE   | Remove 8-line writer shims (after grep)   |
| T2  | Trim      | Medium | M    | OPEN   | PyInstaller bundle audit (excludes scipy) |
| T3  | Trim      | Low    | XS   | DEFER  | DDE output-format audit (Eric: only xlsx; removal deferred) |
| T4  | Trim      | Low    | XS   | DONE   | ACTION_ITEMS.md is stale — archive/edit   |
| T5  | Trim      | Medium | M    | OPEN   | DDE module-count audit (no action yet)    |

## Recommended order

If we tackle these, this is the order I'd suggest:

1. **S1** (XS, low risk, fixes a real bug) — first.
2. **T4** (XS) — clears stale guidance that confuses future sessions.
3. **T1** (XS, after grep) — small win, lowers maintenance surface.
4. **D1 + D2** (combine) — biggest dedup payoff for a small change.
5. **S2** (pre-commit hook) — locks in the truncation-hazard fix.
6. **S3** (BPMN modeler validation) — needs a real corpus from Eric.
7. **S5** (integration test) — solidifies the DDE→nimbus path.
8. **D3** + **D4** — finish the dedup pass.
9. **T2** (bundle audit) — biggest payoff but requires a Windows build.
10. **S6** (top-level CI) — only after the above settles.
11. **T3** + **T5** — keep as audit items; no action until forcing
    function arrives.

## What still needs your involvement

These items can't be done from inside the dev sandbox:

- **S3 — BPMN modeler validation.** Open the emitted `.bpmn` in
  Camunda Modeler / bpmn.io against a real DDE-derived skeleton.
  ~5–10 minutes once you have a real spec.
- **S4 — BPMN XSD validation test.** Blocked on whether a public
  BPMN 2.0 XSD is available offline at your site. If yes, drop it
  somewhere local and I'll wire the test.
- **T1 — Remove writer shims.** Need confirmation that no external
  scripts (outside Process-Tools/) import
  `requirements_extractor.json_writer` /
  `requirements_extractor.md_writer`.
- **T2 — PyInstaller bundle audit.** Needs a real Windows build run
  on your machine (`packaging/build.bat`) with `--debug=imports`. The
  alternatives survey suggests `scipy` is the biggest unused
  contributor (~100 MB potential savings).
- **T3 — DDE output-format usage audit.** Just a question for you:
  do you actually consume the json / markdown / ReqIF outputs, or
  is xlsx the only one in real use? If only xlsx, the others are
  candidates for `--no-` flags or removal in 1.0.0.
- **T5 — DDE module-count audit.** No action needed yet; recorded
  as a watch item.

## What I'd hold off on entirely (for now)

- **Switching from spaCy to GLiNER.** Big lift, real value, but the
  alternatives survey already captured the case. Tracked in the
  roadmap as "Later" — separate from this refactor pass.
- **`pyproject.toml` rollout** for the four packages. Worth doing,
  but is its own ~M-sized item with packaging-format decisions
  attached. Tracked in roadmap.
- **Replacing the sys.path bootstrap.** Falls out of the
  `pyproject.toml` work above; pointless to do separately.
