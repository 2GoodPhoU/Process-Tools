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
