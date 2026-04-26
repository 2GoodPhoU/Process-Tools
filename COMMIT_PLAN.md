# Suggested commit plan -- 2026-04-25 (refreshed post-execution)

The working tree has grown substantially since the original draft.
This document supersedes the earlier version. Execute on your end;
nothing here has been git-staged or committed.

## ACTION_ITEMS Phase 0 -- RESOLVED, doc is stale

`ACTION_ITEMS.md` flagged `compliance-matrix/`, `nimbus-skeleton/`,
and `process-tools-common/` as **entirely untracked**. They are not --
git log shows them already committed in `76b4993`, `aac5728`, and the
`cfc8ef7` series. Phase 0 was already resolved by the time of this
refactor pass.

## Current working-tree state (2026-04-25, post-refactor)

```
 M .gitignore                                                  (new venv pattern + test_output.txt)
 M ACTION_ITEMS.md                                              (Phase 0 marked RESOLVED in-place)
 M README.md                                                    (full doc-truth refresh + tooling pointers)
 M WHEN_YOU_RETURN.md                                           (repointed at ROADMAP / REFACTOR / COMMIT_PLAN)
 M compliance-matrix/CHANGELOG.md                               (Unreleased: fuzzy-id + shared CLI + loader)
 M compliance-matrix/README.md                                  (5 matchers, 30 tests, layout fix)
 M compliance-matrix/compliance_matrix/cli.py                   (uses cli_helpers from process-tools-common)
 M compliance-matrix/compliance_matrix/combiner.py              (S1: fuzzy_id weight 0.95)
 M compliance-matrix/compliance_matrix/loader.py                (D4: load_into helper)
 M nimbus-skeleton/CHANGELOG.md                                 (Unreleased: BPMN + review writer + shared loader)
 M nimbus-skeleton/README.md                                    (BPMN section, 6 outputs, layout fix)
 M nimbus-skeleton/nimbus_skeleton/cli.py                       (uses cli_helpers)
 M nimbus-skeleton/nimbus_skeleton/loader.py                    (D4: load_into helper)
 M process-tools-common/CHANGELOG.md                            (Unreleased: cli_helpers + loader helpers)
 M process-tools-common/process_tools_common/dde_xlsx.py        (D3+D4: load_into + find_sidecar)
 M requirements-extractor/CHANGELOG.md                          (Unreleased: heuristics, integration, T1, fix)
 M requirements-extractor/README.md                             (actor_heuristics in layout)
 M requirements-extractor/requirements_extractor/actors.py      (Windows file-handle close)
 M requirements-extractor/requirements_extractor/diff.py        (Windows file-handle close)
 M requirements-extractor/requirements_extractor/json_writer.py (T1: now raises ImportError)
 M requirements-extractor/requirements_extractor/md_writer.py   (T1: now raises ImportError)
 M requirements-extractor/tests/test_writers_extra.py           (T1: TestRemovedShimsRaise replaces TestCompatibilityShims)

?? COMMIT_PLAN.md                                               (this file)
?? Makefile                                                     (test-all, install-hooks)
?? REFACTOR.md                                                  (refactor punch list with status)
?? ROADMAP.md                                                   (unified by-tool roadmap)
?? requirements.txt                                             (workshop-wide runtime deps)
?? compliance-matrix/tests/test_combiner.py                     (S1: 7 regression tests)
?? process-tools-common/process_tools_common/cli_helpers.py     (D1+D2: shared --quiet + logger)
?? process-tools-common/tests/test_cli_helpers.py               (9 tests)
?? process-tools-common/tests/test_helpers.py                   (8 tests for load_into + find_sidecar)
?? requirements-extractor/tests/integration/test_extractor_to_nimbus_skeleton.py  (S5: 6 tests)
?? samples/bpmn_validation/                                     (S3: real .bpmn for modeler validation)
?? scripts/                                                     (test_all.sh, test_all.ps1, install-hooks.sh, install-hooks.ps1, pre-commit-check.sh)
?? PLAN-gui-unification.md                                      (kickoff plan for next-session GUI work)

NOT to commit:
  ?? requirements-extractor/test_output.txt   (now in .gitignore)
  ?? .venv-workshop/                          (now in .gitignore)
  ?? nimbus-skeleton/sample-output/           (already in .gitignore)
```

## Suggested commit grouping

Five focused commits, each independently revertable. Run
`.\scripts\test_all.ps1` between each to confirm green.

### Commit 1 -- gitignore tightening + ACTION_ITEMS resolution

Files:
- `.gitignore`
- `ACTION_ITEMS.md`
- `WHEN_YOU_RETURN.md`

Suggested message:

```
chore: gitignore venv-* + test_output; mark ACTION_ITEMS Phase 0 RESOLVED

- gitignore: .venv-*/ pattern catches .venv-workshop and friends;
  test_output.txt prevents diagnostic output from being committed.
- ACTION_ITEMS.md Phase 0 -- the three top-level dirs were already
  committed; the doc was the stale piece. Marked RESOLVED in-place.
- WHEN_YOU_RETURN.md repointed at ROADMAP / REFACTOR / COMMIT_PLAN.
```

### Commit 2 -- Doc-truth refresh + new top-level docs + ROADMAP

Files:
- `README.md`
- `compliance-matrix/README.md`
- `compliance-matrix/CHANGELOG.md`
- `nimbus-skeleton/README.md`
- `nimbus-skeleton/CHANGELOG.md`
- `requirements-extractor/README.md`
- `requirements-extractor/CHANGELOG.md`
- `process-tools-common/CHANGELOG.md`
- `ROADMAP.md` (new)
- `COMMIT_PLAN.md` (new)
- `REFACTOR.md` (new)

Suggested message:

```
docs: refresh READMEs + CHANGELOGs to current state; add ROADMAP / REFACTOR

- Top-level README: four tools, 600 tests total, BPMN 2.0 emitter,
  Nimbus retirement context, link to ROADMAP and the new tooling
  scripts.
- compliance-matrix: 5 matchers (fuzzy_id at 0.95 weight), 30 tests,
  layout fix.
- nimbus-skeleton: 6th output (.bpmn, opt-in), 33 tests, BPMN 2.0
  import path section, layout fix.
- requirements-extractor: actor_heuristics in layout, T1 breaking
  removal called out.
- process-tools-common CHANGELOG: documents the new helper modules.
- ROADMAP.md (new): unified by-tool roadmap with risk register.
- REFACTOR.md (new): refactor punch list with sign-off status per item.
- COMMIT_PLAN.md (new): this file.
```

### Commit 3 -- Tooling: requirements.txt + Makefile + scripts/

Files:
- `requirements.txt` (new)
- `Makefile` (new)
- `scripts/test_all.sh` (new)
- `scripts/test_all.ps1` (new)
- `scripts/install-hooks.sh` (new)
- `scripts/install-hooks.ps1` (new)
- `scripts/pre-commit-check.sh` (new)

Suggested message:

```
tooling: workshop-wide test runner, pre-commit hook, requirements.txt

- requirements.txt at repo root: openpyxl + pyyaml + python-docx,
  enough to run all 600 tests across the four tools without per-tool
  installs.
- scripts/test_all.{sh,ps1}: aggregates the four test suites with
  one summary. Exits non-zero on any failure.
- scripts/install-hooks.{sh,ps1}: installs the pre-commit hook into
  .git/hooks/.
- scripts/pre-commit-check.sh: runs py_compile + NUL-byte check on
  every staged .py file. Catches the documented truncation hazard
  at commit time.
- Makefile: thin wrappers (make test-all, make install-hooks).
```

After this commit, run `bash scripts/install-hooks.sh` (or the .ps1
on Windows) so the hook is active for the rest of the commits.

### Commit 4 -- S1: fuzzy_id weight fix + regression tests

Files:
- `compliance-matrix/compliance_matrix/combiner.py`
- `compliance-matrix/tests/test_combiner.py` (new)

(CHANGELOG entry already in Commit 2.)

Suggested message:

```
fix(compliance-matrix): add explicit fuzzy_id weight 0.95 to combiner

The matcher shipped without a DEFAULT_WEIGHTS entry, so its score
multiplied by the 0.5 fallback rather than the documented value.
Tests pin every shipped matcher having an explicit weight to catch
this class of bug at test time.

REFACTOR.md item S1.
```

### Commit 5 -- D1+D2+D3+D4: shared helpers in process-tools-common; thin out consumer loaders + CLIs

Files:
- `process-tools-common/process_tools_common/cli_helpers.py` (new)
- `process-tools-common/process_tools_common/dde_xlsx.py`
- `process-tools-common/tests/test_cli_helpers.py` (new)
- `process-tools-common/tests/test_helpers.py` (new)
- `compliance-matrix/compliance_matrix/cli.py`
- `compliance-matrix/compliance_matrix/loader.py`
- `nimbus-skeleton/nimbus_skeleton/cli.py`
- `nimbus-skeleton/nimbus_skeleton/loader.py`

Suggested message:

```
refactor: hoist --quiet flag, logger, loader pattern to process-tools-common

- New process_tools_common.cli_helpers: add_quiet_flag(parser),
  make_logger(quiet). Both consumer tools' CLIs now use these
  instead of hand-rolling identical boilerplate.
- New process_tools_common.dde_xlsx.load_into(path, factory, fields):
  centralises the iterate-and-filter loop both consumer loaders had.
- New process_tools_common.dde_xlsx.find_sidecar(input_path, suffix):
  the "look for actors xlsx beside input" convention.
- Both loader.py files are now ~5-line wrappers.
- 17 new tests in process-tools-common (9 cli_helpers + 8 helpers).
- No user-visible behaviour change.

REFACTOR.md items D1, D2, D3, D4.
```

### Commit 6 -- S5: DDE -> nimbus-skeleton integration test

Files:
- `requirements-extractor/tests/integration/test_extractor_to_nimbus_skeleton.py` (new)

Suggested message:

```
test: end-to-end integration test for DDE -> nimbus-skeleton

Mirrors test_extractor_to_compliance_matrix.py. 6 tests covering:
- the 5-default-output shape (no --bpmn)
- the 6-output shape with --bpmn
- manifest content shape
- review xlsx well-formedness
- BPMN XML well-formedness

REFACTOR.md item S5.
```

### Commit 7 -- T1: remove writer compatibility shims (BREAKING)

Files:
- `requirements-extractor/requirements_extractor/json_writer.py`
- `requirements-extractor/requirements_extractor/md_writer.py`
- `requirements-extractor/tests/test_writers_extra.py`

Optional follow-up: physically `git rm` the two shim files (they
currently exist with `raise ImportError` bodies; the placeholder
form was used because the dev sandbox can't delete files). Either
leave the placeholder or remove on commit.

Suggested message:

```
remove(BREAKING): writer compatibility shims (json_writer, md_writer)

The shims have re-exported from writers_extra since the writer
consolidation. Eric confirmed (REFACTOR.md item T1) no external
scripts use the old import path. Importing either module now
raises ImportError with a pointer to writers_extra.

Migration: from requirements_extractor.writers_extra import
    write_requirements_json, write_requirements_md, requirement_to_dict.
```

### Commit 8 -- Windows file-handle close fix (real production bug)

Files:
- `requirements-extractor/requirements_extractor/actors.py`
- `requirements-extractor/requirements_extractor/diff.py`

Suggested message:

```
fix: close openpyxl workbooks in actors and diff loaders

actors.load_actors_from_xlsx and diff._read_requirements_workbook
both opened the workbook with load_workbook but never called close.
On Linux the leaked handle was harmless; on Windows it caused
PermissionError [WinError 32] when callers using
tempfile.TemporaryDirectory tried to clean up.

Surfaced by running the test suite on Windows for the first time --
7 tests erroring on Windows but passing on Linux all funneled through
these two loaders. Pure cleanup; no behavioural change.
```

### Commit 9 -- S3: BPMN modeler validation samples

Files:
- `samples/bpmn_validation/`

Suggested message:

```
samples: add BPMN modeler validation set

Real DDE + nimbus-skeleton output produced from
samples/procedures/simple_two_actors.docx. Use simple_two_actors.bpmn
as the artefact to validate against Camunda Modeler / bpmn.io.

REFACTOR.md item S3 -- ready for Eric to do the visual validation.
```

## After Commit 9

Run `make test-all` (or `.\scripts\test_all.ps1`) -- expect
`ALL GREEN -- 600 tests across 4 tools`. If anything errors,
the per-commit grouping makes bisection trivial.

## What NOT to commit

- `requirements-extractor/test_output.txt` -- diagnostic file from
  the Windows debugging session. Now gitignored.
- `.venv-workshop/` -- workshop-wide venv. Now gitignored.
- `nimbus-skeleton/sample-output/` -- already gitignored.
- Anything in `__pycache__/`, `.pytest_cache/`, or `dist/` -- already
  gitignored.

## Items still on Eric's plate (post-refactor)

- **S3** -- open `samples/bpmn_validation/simple_two_actors.bpmn` in
  Camunda Modeler / bpmn.io and confirm visual correctness.
- **S4** -- if a public BPMN 2.0 XSD is available offline at your
  site, add a test that validates emitter output against it.
- **T2** -- run the PyInstaller bundle audit per the runbook in
  REFACTOR.md.
- **T3** (deferred to major bump) -- prune JSON / Markdown / ReqIF
  writers when ready for a 0.6.0 / 1.0.0 release.
