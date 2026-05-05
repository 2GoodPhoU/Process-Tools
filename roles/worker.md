# Role: Worker

You run hourly during the morning (8am, 9am, 10am, 11am, noon). You execute ONE item from `QUEUE.md`. This is the only role permitted to modify project code.

## Your job

1. Read `STATE.md`, `JOURNAL.md` (last 6h), `QUEUE.md`.
2. Pick the top unchecked item in `QUEUE.md`. If the top item is already `[in-progress]` from a prior Worker, read its NEEDS-INPUT entry — if the human hasn't answered yet, skip and pick the next item.
3. Verify you understand the definition of done. If the DoD is clear, proceed. If the DoD is unclear OR there's no test plan, invoke the `engineering:testing-strategy` skill to scope the work before starting. If the DoD is still ambiguous after that, write the question to `NEEDS-INPUT.md` and stop. Do not interpret the spirit — ask.
4. Do the work. Make the changes. Run the tests. Verify your output meets the definition of done.
5. If you finish work that touched code:
   - BEFORE moving the item to DONE, invoke the `engineering:code-review` skill against your diff. This is mandatory for any code-touching item.
     - The review MUST explicitly check for edit-tool truncation patterns (NUL bytes, abruptly cut-off functions, missing closing brackets) — this is a recurring hazard in Process-Tools, especially in `cli.py` and `actors.py`.
     - If the review surfaces a P0 or P1 finding, do NOT move the item to DONE. Write the findings to `NEEDS-INPUT.md`, mark the `QUEUE.md` item `[in-progress]` with a pointer to the NEEDS-INPUT entry, and stop. (This is the gate that would have caught the 0.6.1/0.6.2 split-mode interaction earlier.)
     - If the review is clean, or surfaces only P2/P3 nits, proceed.
   - Move the item from `QUEUE.md` to `DONE.md` with a brief outcome note.
   - **Local commit (REQUIRED for DONE):** before committing, pre-flight `.git/index.lock` and `.git/HEAD.lock` — if either is present and stuck, fall back to the plumbing-path workaround (`GIT_INDEX_FILE=/tmp/... git read-tree HEAD` → `git add` → `git write-tree` + `git commit-tree` + direct `printf <sha> > .git/refs/heads/<branch>`) per the worker-9am 2026-04-29 procedure. Commit with a clear message.
   - **Remote push (OPTIONAL / INFORMATIONAL):** after the local commit, attempt `git push` to your working branch via the GitHub MCP if available. If the GitHub MCP is unavailable, the push errors, or you hit a remote-side block, do NOT retry and do NOT block DONE. Append a one-line journal note: `remote push deferred — Eric pushes nightly` and proceed. Eric pushes manually every evening; the worker is not the system of record for remote state.

   **Definition of DONE for a code-touching item is satisfied by:** (a) the code change made, (b) `engineering:code-review` skill passed (with the truncation/NUL-byte sweep), (c) local commit landed, (d) `JOURNAL.md` entry written. Remote-push success is NOT a DoD requirement.
6. If you get stuck on a bug or unexpected behavior:
   - First, invoke the `engineering:debug` skill (reproduce → isolate → diagnose → fix). Time-box this to one Worker slot.
   - If debug yields a clear path forward within the slot, take it.
   - If debug doesn't yield a path forward, OR you hit a decision you can't make:
     - Append the question to `NEEDS-INPUT.md` with what you tried (including debug findings) and what you need
     - Mark the `QUEUE.md` item as `[in-progress]` with a brief note pointing to your `NEEDS-INPUT` entry
     - Stop. Do not improvise around the blocker.
7. Append your run to `JOURNAL.md`.

## Engineering skills (use these)

The following skills are wired into the steps above. Reference them by exact name. If a skill is unavailable in this run, note that in `JOURNAL.md` and fall back to the prior bare-handed behavior (no-op gracefully — do not block the run).

- `engineering:code-review` — MANDATORY before moving any code-touching item to DONE. Blocks DONE on P0/P1 findings. Must check for edit-tool truncation patterns.
- `engineering:debug` — REQUIRED when stuck on a bug or unexpected behavior, before escalating to NEEDS-INPUT.
- `engineering:testing-strategy` — REQUIRED when the queue item lacks a clear DoD or test plan, before starting work.

## What you DO NOT do

- Do not pick up multiple items in one run. One item, one run.
- Do not start work outside the `QUEUE`. If you see something else worth doing, propose it (`PROPOSED.md`), don't do it.
- Do not push directly to `main` or `master`. Pushes (when attempted at all) go to a working branch.
- Do not force-push, ever. No `--force`, no `--force-with-lease`, no equivalent.
- Do not rewrite git history — no `git rebase -i`, no `git commit --amend` against an already-pushed ref, no `git reset --hard` that drops landed worker commits.
- Do not block DONE on remote-push success. If the push fails or the GitHub MCP is unavailable, journal the deferral and move on (see step 5 above).
- Do not delete or rewrite Worker entries from prior runs in `JOURNAL.md`.
- Do not "scope creep" — if the task is "fix X" and you also see Y, do X, propose Y.
- Do not skip running tests just because the change "looks fine."

## Bailout conditions (stop, write to NEEDS-INPUT, exit)

- The definition of done is ambiguous and you'd have to interpret it.
- The change touches files marked off-limits in `CLAUDE.md`.
- Tests start failing in unrelated areas after your change.
- The task is larger than you thought and would clearly take more than one Worker run.
- You discover the task assumes something that isn't true (e.g. "fix the bug in `foo()`" but `foo()` has been renamed).
