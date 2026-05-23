# Pre-Phase-4 readiness audit

**Run:** process-tools-researcher (automated), 2026-05-14 ~04:00
**Posture:** READ-ONLY. No source edits this run.

---

## Question

> **(R3) Pre-Phase-4 readiness audit.** Once the `.git/index` thread closes
> and BPMN B1/B2/B3 + orphan-dir 3.7 land, Phase 4 (bundle / cut / tag)
> becomes pickable. A focused readiness check across the four sub-tools
> (CHANGELOG Unreleased depth, version-bump consistency across
> `__init__.py` / spec / README, PyInstaller spec gaps still open per 3.2,
> smoke-test footprint on the offline target) would surface gaps before a
> Worker tries to close 4.1-4.7 and discovers them mid-shift. Value:
> de-risks the v1.0 cut.

Verbatim from `NEEDS-INPUT.md` line 42, `[from: researcher / 2026-05-08 04:00]`,
candidate (R3). R1 (post-fix `.git/index` retro) is gated on the lock
clearing -- not yet done. R2 (Windows-side lock-holder forensics) requires
Windows-side access -- cannot be done from a Linux read-only environment.
R3 is the only candidate from that 6-day-stale menu actionable from this
slot, and it is timely: QUEUE 2.4 + 2.5 are each one Eric action from
closing, after which Phase 2 exits and Phase 4 is next.

---

## What I checked

- `ROADMAP.md` (Phase 4 entry/exit criteria; v1.0 per-sub-tool meaning;
  sub-tool status table; rate-limiter callout).
- `QUEUE.md` Phase-4 items 4.1 / 4.2 / 4.3 / 4.4 / 4.6 / 4.7 -- DoD,
  effort cite, deps, skill assignment.
- All four sub-tool `CHANGELOG.md` files end-to-end: requirements-extractor
  (362 lines), nimbus-skeleton (141 lines), compliance-matrix (107 lines),
  process-tools-common (64 lines).
- Version declarations in each sub-tool's `__init__.py`.
- Packaging spec: `requirements-extractor/packaging/DocumentDataExtractor.spec`
  (the only `.spec` in the repo; `find -name '*.spec'` confirms zero
  results elsewhere).
- Each sub-tool `README.md` for stale version strings.
- `requirements-extractor/docs/NLP_BUNDLE_SMOKE_TEST.md` (the 7-step
  sandbox-side pre-flight checklist + 6-step Windows runbook).
- `sys.path` bootstrap shim in `nimbus-skeleton/nimbus_skeleton/loader.py`
  and `compliance-matrix/compliance_matrix/loader.py`.
- Searched repo-wide for `pyproject.toml` / `setup.py` -- none exist.
- Did NOT run any builds, did NOT touch source, did NOT modify state files
  (those happen below in PROPOSED + JOURNAL).

---

## What I found

### Finding 1: requirements-extractor Unreleased section is EMPTY

`requirements-extractor/CHANGELOG.md` line 9 is `## [Unreleased]`, line 10
is blank, line 11 is `## [0.6.2] -- 2026-04-27`. There is nothing under
Unreleased to promote.

The 0.6.1 (compound) and 0.6.2 (multi-action) patch lines that motivated
the "promote to 0.7.0" framing in QUEUE 4.1 are already in dated entries
(0.6.1 from line 100; 0.6.2 from line 11). They landed in HEAD via Eric's
bundle commit `261a674` (2026-05-05) and the CHANGELOG was authored as if
they had been released at that time.

QUEUE 4.1 DoD says: *"CHANGELOG date stamp + `[0.7.0]` heading; version
bumps consistent across `__init__.py`, `packaging/DocumentDataExtractor.spec`,
README references"*. With Unreleased empty, there is no content to anchor
a `[0.7.0]` heading on -- a Worker following 4.1 verbatim would write a
`[0.7.0]` heading with no body, which violates the project's CHANGELOG
hygiene (Keep-a-Changelog: each version section has at least one bullet).

The current sub-tool status table in `ROADMAP.md` (line 218) lists
requirements-extractor at `0.6.2 (committed)` with Phase-3 status `OPEN --
0.6.1/0.6.2 uncommitted`. The "uncommitted" framing is stale post-`261a674`
(noted in the 2026-05-06 revision-history entry which fixed the row but
left the Phase-3 column language unchanged).

### Finding 2: PyInstaller spec gaps wider than QUEUE 3.2 captures

QUEUE 3.2 DoD: *"spec gains `yaml` in `_bundle()` + `requirements_extractor.actor_heuristics`
in explicit hiddenimports; once 0.6.1/0.6.2 patch line lands, also adds
`requirements_extractor.compound` + `requirements_extractor.multi_action`"*.

Confirmed missing from `packaging/DocumentDataExtractor.spec` (verified
against the source-tree module list):

| Module | Required by | In spec? |
|---|---|---|
| `yaml` (PyYAML) | `config.py`, `keywords_loader.py`, nimbus-skeleton YAML emitter | NO |
| `requirements_extractor.actor_heuristics` | 0.6.0 actor-heuristics fallback (the offline-network load-bearing layer per CLAUDE.md) | NO |
| `requirements_extractor.compound` | 0.6.1 compound-requirement detection | NO |
| `requirements_extractor.multi_action` | 0.6.2 multi-action decomposition | NO |
| `requirements_extractor.procedural` | 0.5.0 procedural-table subsystem | YES (line 115) |

The "once 0.6.1/0.6.2 patch line lands" hedge in 3.2 DoD is now stale --
the patch lines landed in `261a674`, so 3.2 should already cover all four
hiddenimport additions in a single commit. The current spec gap is **4
missing entries**, not the 2 the DoD reads as primary.

### Finding 3: Bundle-version source-of-truth is currently CONSISTENT

| Sub-tool | `__init__.py` | Latest CHANGELOG dated | Match? |
|---|---|---|---|
| requirements-extractor | `__version__ = "0.6.2"` (line 6) | `[0.6.2]` 2026-04-27 | YES |
| nimbus-skeleton | `__version__ = "0.1.0"` (line 13) | `[0.1.0]` 2026-04-24 | YES |
| compliance-matrix | `__version__ = "0.1.0"` (line 19) | `[0.1.0]` 2026-04-24 | YES |
| process-tools-common | `__version__ = "0.1.0"` (line 9) | `[0.1.0]` 2026-04-24 | YES |

No version mismatches detected. READMEs carry no stale version strings.
This means the version-bump portion of 4.1 / 4.2 / 4.3 / 4.4 is mechanically
trivial -- the source-of-truth surface is small (one `__init__.py` line
per sub-tool, plus the CHANGELOG header).

### Finding 4: No PyInstaller spec for the other three sub-tools

`find -name '*.spec' -type f` returns exactly one path:
`requirements-extractor/packaging/DocumentDataExtractor.spec`. There is
no spec for `nimbus-skeleton`, `compliance-matrix`, or `process-tools-common`.

QUEUE 4.6 DoD: *"`dist/DocumentDataExtractor.exe` produced clean (mandatory);
nimbus-skeleton equivalent if customer needs offline BPMN emission (optional
per ROADMAP.md Phase 4 exit)"*. ROADMAP confirms this is optional ("at
minimum requirements-extractor; nimbus-skeleton if customer needs the
emitters offline"). The "is nimbus-skeleton in scope or out?" question is
an Eric decision before 4.6 -- and if in-scope, a brand-new spec file +
build verification is roughly a half-day of work on its own, not the small
delta the 4.6 effort cite ("~3-4h") implies for a build-and-validate of a
spec that already exists.

### Finding 5: process-tools-common is NOT pip-installable today

Both consumer loaders still carry the `sys.path` bootstrap shim:

- `nimbus-skeleton/nimbus_skeleton/loader.py` lines 16-22.
- `compliance-matrix/compliance_matrix/loader.py` lines 15-21.

Identical shape in both: `_COMMON_ROOT = Path(__file__).resolve().parents[2] / "process-tools-common"` then `sys.path.insert(0, str(_COMMON_ROOT))` if the dir exists.

No `pyproject.toml` exists anywhere in the repo (`find -name 'pyproject.toml'`
returns zero). No `setup.py` exists either. QUEUE 4.4 DoD: *"consumers
(compliance-matrix + nimbus-skeleton) pip-install or PyInstaller-bundle
cleanly without the `sys.path` bootstrap shim per ROADMAP.md 1.0 criteria"*.

This is the largest hidden-iceberg item in Phase 4. The 4.4 effort cite
("medium ~2h; bootstrap-removal verification is the load-bearing step")
implicitly assumes the packaging plumbing (a `pyproject.toml` for
process-tools-common, then editable installs in the two consumers, then
shim removal, then verification) is mostly already in place. It is not.
Realistic effort to satisfy 4.4 DoD from current state: ~4-6h, broken
into (a) author `process-tools-common/pyproject.toml` (~30 min), (b)
verify both consumers can `pip install -e ../process-tools-common`
(~30 min), (c) remove both bootstrap blocks + run full suites to confirm
no regression (~1h), (d) verify the requirements-extractor PyInstaller
spec still bundles `process_tools_common` correctly via the new pip-install
path -- this likely requires another `collect_all('process_tools_common')`
call in the spec (~1-2h test build + smoke), (e) author DECISIONS.md
entry covering the packaging contract change (~30 min).

### Finding 6: compliance-matrix 4.3 has a real-spec dependency

QUEUE 4.3 DoD: *"default thresholds (similarity 0.20 / keyword 0.15 /
fuzzy_id 0.85) validated against one real spec/procedure pair per
ROADMAP.md 1.0 criteria"*. ROADMAP 1.0 criteria for compliance-matrix
(line 75-76): *"fuzzy-id matcher committed; default thresholds...
validated against one real spec/procedure pair"*.

The 4.3 effort cite hedges this honestly: *"small if thresholds already
validated (~30 min); medium if validation has to be done this shift
(~3-4h)"*. Whether the validation has been done is not visible from
this read-only audit -- no `DECISIONS.md` entry, no research file, no
JOURNAL entry covering it. Assume NOT DONE until evidence surfaces.
Eric needs to either (a) supply a real spec/procedure pair for an
automation slot to validate against, OR (b) waive the validation
criterion (and document that in the ROADMAP).

### Finding 7: Smoke-test runbook is solid

`requirements-extractor/docs/NLP_BUNDLE_SMOKE_TEST.md` exists and is
well-formed. 7-step sandbox-side pre-flight checklist + 6-step Windows
runbook. Two items are worth flagging for the 4.1 / 4.6 chain:

- Pre-flight step 2 (line 278-288): one-liner diff of `requirements_extractor/*.py`
  module list vs spec hiddenimports. **Today's diff would flag 4 missing
  entries** (per Finding 2). The pre-flight already catches the issue --
  the question is whether a Worker running 4.1 will remember to run
  the pre-flight before bumping the version.
- Post-build step D-F (lines 108-220): copy exe to work network +
  first launch + NLP verification on restricted machine. This is
  load-bearing for the v1.0 ship signal and requires Eric's restricted-
  network Windows machine. Workers cannot do this slot.

### Finding 8: Test counts drift vs ROADMAP

ROADMAP.md (last updated 2026-05-06) line 222: *"Workshop total = 702"*.
Current green baseline per night-auditor 2026-05-13 00:05 is **708**
(607 requirements-extractor + 45 nimbus-skeleton + 30 compliance-matrix
+ 26 process-tools-common). The +6 delta comes from `9ca814d` worker-9am
2026-05-12 (BPMN stdlib structural-diff helper, +5 nimbus-skeleton tests)
plus a +1 in requirements-extractor (origin unclear; likely a single
new test added by Eric in `bdc9e04` or a sibling commit). Any new
CHANGELOG entry written under 4.1-4.4 needs to update the per-tool
test count.

This is already on the PROPOSED chain (CLAUDE.md numeric-fact auto-update
authorization per cowork-session 2026-05-04). Worth surfacing here only
because Phase 4 CHANGELOG entries are exactly where the doc-stale numbers
will bite.

### Finding 9: Phase-4 entry criteria gates currently NOT met

ROADMAP Phase 4 entry (line 189-191): *"Phase 2 exit (Camunda gate closed)
AND Phase 3 exit (commit hygiene clean). v1.0-shape decision now locked
(bundle, 2026-05-04)"*. Current state:

- **Phase 2 exit:** NOT MET. QUEUE 2.5 (Camunda Modeler GUI gate) still
  `[in-progress]` waiting on Eric manual walk per `[eric-action / 2026-05-11]`.
  QUEUE 2.3 (Camunda-saved fixture regression test) gated behind 2.5.
  QUEUE 2.4 (BPMN XSD validation) `[in-progress]` waiting on Eric `[x]`
  of researcher 2026-05-13 D1/D2/D3 PROPOSED bundle. All three close-paths
  are Eric-side, not Worker-side.
- **Phase 3 exit:** NOT MET. Per QUEUE.md Phase-3 section, items 3.2 / 3.5 /
  3.6 are open and all depend on PROPOSED approvals. The `.git/index`
  structural-staleness (load-bearing for 4 commits) is the canonical
  Phase-3 hygiene debt and still requires the Windows-side recovery
  command.
- **v1.0-shape decision:** MET (bundle, locked 2026-05-04).

Phase 4 cannot start in the next several Worker shifts under current
state. The readiness audit's value is **calibration**, not unblocking.

---

## Recommendation

**Actionable change.** Update QUEUE Phase-4 item DoD/effort cites and add
two prep items to QUEUE Phase-3 to prevent mid-shift surprises when
Phase 4 becomes pickable. Specifically (filed to PROPOSED -- humans
decide):

1. **(P2) Update QUEUE 3.2 DoD** to explicitly list all four missing
   hiddenimports (`yaml`, `actor_heuristics`, `compound`, `multi_action`)
   plus `yaml` in `_bundle()`. Remove the "once 0.6.1/0.6.2 patch line
   lands" hedge -- they have landed. This is a one-line CHANGELOG edit
   on QUEUE.md, not a code change.

2. **(P2) Update QUEUE 4.1 framing** to handle the empty Unreleased
   section. Two acceptable shapes: (a) add a one-bullet "Internal release
   alignment for v1.0 cut" entry under Unreleased before promotion, so
   `[0.7.0]` has a body; OR (b) collapse 4.1 into 4.7 (skip the
   intermediate 0.7.0 bump, go straight 0.6.2 -> 1.0.0 since there is no
   intervening work to record). Recommended shape: (b) -- avoids a stub
   CHANGELOG entry and matches the actual code history (the last
   meaningful version is 0.6.2). Eric decision needed before 4.1 runs.

3. **(P1) Add new QUEUE Phase-3 item: process-tools-common pyproject.toml
   authoring.** Promote the implicit packaging plumbing inside 4.4 DoD
   to its own Phase-3 item with clear effort cite (~2h). DoD: author
   `process-tools-common/pyproject.toml` (PEP 621 metadata + version
   pulled from `__init__.py`); verify both consumers can `pip install -e
   ../process-tools-common`; verify the requirements-extractor
   PyInstaller spec still locates `process_tools_common` (likely needs
   `collect_all('process_tools_common')` added); do NOT remove the
   bootstrap shims this item (the shim removal happens in 4.4 itself).
   Sequencing this as a Phase-3 prep item de-risks 4.4's effort cite.

4. **(P2) ROADMAP "compliance-matrix 1.0" criteria reality check.** Eric
   needs to either (a) supply a real spec/procedure pair so an automation
   slot can validate the default thresholds (similarity 0.20 / keyword
   0.15 / fuzzy_id 0.85), or (b) explicitly waive the validation criterion
   in ROADMAP.md and `compliance-matrix/DECISIONS.md`. Without one of
   those, QUEUE 4.3 cannot reach DoD. This is purely an Eric decision;
   no Worker action.

5. **(P2) ROADMAP nimbus-skeleton bundle scope decision.** Eric needs to
   decide whether the customer requires offline BPMN emission, which
   determines whether 4.6 needs a brand-new nimbus-skeleton PyInstaller
   spec. Suggested default: NO bundle for v1.0 (customer can run
   nimbus-skeleton as a Python package on a dev machine; BPMN files are
   then transferred). This avoids ~0.5-day of additional packaging work
   for an unknown demand signal. If customer demand surfaces post-v1.0,
   add as a 1.1 item.

The above are all bundled into ONE PROPOSED entry below (per the
research-2026-05-13 precedent for QUEUE 2.4 D1/D2/D3) so Eric can `[x]`
once rather than answer five separate questions. Adopt-all is the
recommended path; adopt-some is fine with a one-word note on each
sub-item.

---

## Open follow-ups

- **Phase-3 hygiene cleanup remains the critical-path-to-Phase-4.** This
  audit calibrates Phase 4 gaps; it does not move Phase 3 forward. The
  `.git/index` recovery + the 0.6.1/0.6.2 commit-hygiene PROPOSED chain
  + the role-file drift PROPOSED chain are all still on Eric. No
  researcher slot can advance them.

- **Did Eric author any net-new tests since 2026-05-06?** The +1 in the
  requirements-extractor test count (606 -> 607) does not match any of
  the worker commits since 2026-05-11. Best guess: it landed in Eric's
  `bdc9e04` (2026-05-11) but I did not run `git show --stat bdc9e04` to
  confirm. If a Worker is interested in surfacing this in a CHANGELOG
  Unreleased entry for 4.1 path (a), they should run `git log
  --oneline -- requirements-extractor/tests/` over the 2026-05-06 ->
  HEAD window. NOT a research follow-up -- mundane git archeology.

- **R1 still gated; R2 still un-doable from Linux.** Once Eric runs the
  `.git/index` recovery command on Windows, R1 (post-fix retro on the
  2026-05-06 trailer-SHA1 mismatch mechanism) becomes time-critical --
  the forensic signal on the recovered `.git/index` decays as soon as
  `git status` re-stats the working tree. A researcher slot within
  24h of the recovery is high-value. R2 (Windows-side `.git/index.lock`
  holder forensics) remains un-doable from any Linux automation slot --
  needs Eric-attended Process Monitor / Event Viewer review.

- **`.dashboard-enrichment.json`** flagged by night-auditor 2026-05-14
  00:05 (8070b, ~9 min before audit, untracked). Auditor filed P3
  IMPROVABLE PROPOSED. Not in scope for this audit. Worth one Eric look
  to identify the producer (likely Cowork-side dashboard scaffold) and
  decide whether to `.gitignore` it.
