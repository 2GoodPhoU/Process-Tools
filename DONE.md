# Done — Process-Tools

> Completed items. Workers move things here when finished. Lets future runs see what's been addressed so they don't re-propose it.

## Format

```
## YYYY-MM-DD
- Title — done by role at HH:MM. Outcome: ...
  - Commit: <sha or "no commit">
  - Tests: pass | fail | n/a
```

---

## 2026-04-29

- [P0] Repair edit-tool truncation in `requirements-extractor/requirements_extractor/models.py` — done by process-tools-worker-8am at 08:00. Outcome: removed the duplicated comment block + corrupted residue (`tructural events."""` on line 205 plus stray `requirement: "Requirement"` field) AND stripped 192 trailing NUL bytes that were silently sitting at EOF (Read tool filters NULs, so the night-auditor's NUL sweep missed them — flagged below). File now py_compiles clean. The legitimate `parent_id` field on line 148 (0.6.2 multi-action work) is preserved untouched.
  - Commit: `fix: repair models.py edit-tool truncation + strip trailing NUL bytes` (latest commit on `main`, recorded by subject not SHA so an amend can't desync this entry). Pre-commit hook ran without `--no-verify` this time (which was unexpected given the auditor's hook-bypass note from this morning — worth noting for the evening review). 1 commit ahead of `origin/main`; NOT pushed per `roles/worker.md` and `CLAUDE.md`.
  - Tests: pass — `bash scripts/test_all.sh` reports ALL GREEN, 702 tests across 4 tools (process-tools-common 26, compliance-matrix 30, nimbus-skeleton 40, requirements-extractor 606). Prior 27 ERRORs + 5 FAILs cleared. Note: requirements-extractor's `Ran N tests` jumped 109 → 606 because the syntax error was preventing module load, which made `unittest discover` undercount.


- [P1] Orphan-dirs decision scaffolding — done by process-tools-worker-10am at 10:00. Outcome: produced top-level `DECISIONS-orphan-dirs.md` (120 lines) with per-dir findings (file count, LOC Python/non-Python, newest mtime, packaging metadata, test pass status, cross-references from `requirements-extractor/`) for each of `compliance-matrix/`, `nimbus-skeleton/`, `process-tools-common/`, plus a 3-option tracked-vs-ignored table. **Premise correction surfaced:** STATE.md / CLAUDE.md / COMMIT_PLAN.md / ACTION_ITEMS.md describe the dirs as "entirely untracked" but `git ls-files` shows all 19/20/8 files tracked since 2026-04-25/26 (initial commits 76b4993, aac5728, 26bc017). Eric's actual decision is "leave / formalize / un-track," not "track or ignore from scratch." Doc explicitly does NOT make the call (per definition of done).
  - Commit: `worker-10am: orphan-dirs decision scaffolding` (76e211b). Plus three follow-ups: `91a240c` strip trailing NUL bytes from QUEUE.md (Edit-tool padded the file with 950 NULs when removing the orphan-dirs item — same hazard the 8am Worker hit on models.py); `cd953da` journal postscript; `89b4103` append the actual 10am journal entry (the Edit-tool calls had failed to persist to disk on the first three commits, masked by Read-tool seeing a different staged version of JOURNAL.md). NOT pushed.
  - Tests: pass — re-confirmed all three orphan-dir suites green individually (compliance-matrix 30/30, nimbus-skeleton 40/40, process-tools-common 26/26). Did not re-run full `scripts/test_all.sh` (gated baseline-pytest item is the place for that). No edits to source under any orphan dir — read-only constraint observed.
