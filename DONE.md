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


- [P1] Baseline pytest run for `requirements-extractor/` — done by process-tools-worker-11am at 11:00. Outcome: produced `requirements-extractor/BASELINE-2026-04-29.md` (renamed from -28 per planner gate; marker dated the day the suite actually went green). Suite: 606 / 0 / 0 / 0 (pass / fail / error / skip), zero flakies across two consecutive verbose runs (test-id projection diff was empty), wall-clock 6.855–7.045 s across four runs (mean ~6.95 s; variance under 200 ms). Environment captured: Python 3.10.12, openpyxl 3.1.5, PyYAML 6.0.3, python-docx 1.2.0, pdfplumber 0.11.9. **spaCy and en_core_web_sm are NOT installed** — this is the offline-network configuration; the rule-based heuristic fallback covers the entire failure surface. The 0.6.1/0.6.2 patch line is uncommitted in the working tree (4 modified tracked files, +639/−21 LOC; 16 untracked items in `requirements-extractor/`); per the QUEUE definition-of-done, the baseline is captured as "tree as it stands today" and the doc records both the HEAD SHA (`96aab20`) and the working-tree delta. Wording note: queue title and commit message read "pytest" but the harness is `unittest discover` — flagged separately in PROPOSED.md (night-auditor 2026-04-29).
  - Commit: `baseline: requirements-extractor pytest snapshot 2026-04-29` — see commit log; not pushed per `roles/worker.md` and `CLAUDE.md`. Used the same `.git/index.lock` plumbing-path workaround the 9am/10am Workers had to use (Windows file-lock blocks `git`'s own unlink, plus the previously-noted `.git/HEAD.lock` — see flagged-for-evening-review).
  - Tests: pass — `bash scripts/test_all.sh` ALL GREEN, 702 tests across 4 too


- [P2] Audit regression coverage for the 10 actor-extraction heuristics — done by process-tools-worker-12pm at 12:00. Outcome: created `requirements-extractor/DECISIONS.md` (file did not exist; opened with the audit as its first entry). Per-heuristic table maps each rule to its owning function (`_h_by_agent` … `_h_appositive` in `actor_heuristics.py`) and its named tests in `tests/test_actor_heuristics.py`. Verdict: all 10 heuristics have at least one positive test (no rule is uncovered); 5 of 10 are fully covered (rules 1, 2, 4, 5, 6 have negative tests); 5 of 10 are partially covered (rules 3, 7, 8, 9, 10 — positives only, no false-positive negative). Three rules (5, 7, 8) carry alternation lists where most branches are unexercised: rule 5 pins 2 of 6 conditional triggers, rule 7 pins 1 of 9 passive verbs and 1 of 5 modal forms, rule 8 pins 2 of 7 hyphen suffixes. Out-of-scope code finding logged in DECISIONS.md, not actioned: `_h_appositive` has a redundant unreachable `elif` branch. Recommendations section spells out what a future remediation would do (~5 negative fixtures + ~14 alternation fixtures) but no new tests written — DoD said audit, not remediate.
  - Commit: `worker-12pm: heuristic regression-coverage audit (DECISIONS.md)` — see commit log; not pushed per `roles/worker.md` and `CLAUDE.md`.
  - Tests: pass — `python3 -m unittest tests.test_actor_heuristics` reports 36 / 36 ok in 0.001 s. `bash scripts/test_all.sh` reports ALL GREEN, 702 tests across 4 tools — no regression vs. the 11am Worker's run (audit is doc-only; no code touched).
