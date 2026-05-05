# Push Mystery — How 2026-04-29 commits reached origin/main

## Question

Verbatim from `PROPOSED.md` (night-auditor / 2026-04-30):

> `git rev-parse main origin/main` both return `382ee397...`. `git reflog show origin/main` shows the most recent entry is `382ee39 ... update by push` — i.e., the worker-12pm commit is on the remote. ... Yet the worker-9am, worker-10am, worker-11am, worker-12pm journal entries all say `not pushed per roles/worker.md and CLAUDE.md`. So either (a) the journal claims are wrong (commits were pushed despite the worker not noticing), or (b) someone pushed manually after the workers committed, or (c) there is an out-of-band push hook running.

This research grounds which hypothesis is correct so Eric can pick a policy direction.

## What I checked

- `.git/hooks/` — full directory listing; cat'd every non-sample file
- `.githooks/`, `hooks/` — confirmed neither exists
- `git config core.hooksPath`, `remote.origin.pushurl`, `push.default`, `push.autoSetupRemote`, `credential.helper` — all unset (no overrides)
- `git config remote.origin.url` — `https://github.com/2GoodPhoU/Process-Tools.git` (HTTPS, not SSH)
- `.github/`, `.github/workflows/` — confirmed neither exists (no CI, no Actions)
- `scripts/` — read every file; only `install-hooks.sh`, `install-hooks.ps1`, `pre-commit-check.sh`, `test_all.sh`, `test_all.ps1`. None contain `git push`.
- Repo-wide grep `git push` (excluding `.venv*` and `.git/`) — only two hits: `PROPOSED.md` (the auditor's own entry) and `roles/worker.md` (the policy text).
- `schedule.json` — no `push` references; the 9 scheduled tasks all delegate to `roles/<role>.md`.
- `digests/*.md` — no `push` references.
- `git reflog show --date=iso origin/main` — full output, every push event since 2026-04-22.
- `git reflog show --date=iso main` and `git reflog show --date=iso HEAD` — for cross-reference against commit timestamps.
- `git log --since='2026-04-28' --pretty='%h | %ai | %an <%ae>'` — author attribution for every recent commit.

## What I found

### 1. There was exactly ONE push event on 2026-04-29, not six.

```
$ git reflog show --date=iso origin/main | grep '2026-04-29' | wc -l
1

$ git reflog show --date=iso origin/main | grep '2026-04-29'
382ee39 refs/remotes/origin/main@{2026-04-29 17:55:40 -0600}: update by push
```

That single push fast-forwarded `origin/main` from `18ee238` (the prior tip from 2026-04-27) directly to `382ee39` (worker-12pm's commit), carrying every intermediate worker commit (8am, 9am, 10am×5, 11am, 12pm) in one shot.

This is the load-bearing observation. If each worker had pushed, the reflog would show 8+ "update by push" entries on 2026-04-29; it shows one.

### 2. The push happened ~5h 40m AFTER the last worker commit.

UTC timeline:

| time (UTC) | event |
|---|---|
| 14:33:44 | worker-8am first commit (`45fca26`) |
| 14:34:27 / 14:35:06 | worker-8am amend ×2 (`758bdf5`, `91a05bf`) |
| 15:20:29 | worker-9am commit (`24f1b3d`) |
| 16:11:52 – 16:18:54 | worker-10am commits (5 commits, `76e211b` … `96aab20`) |
| 17:13:49 | worker-11am commit (`4c645ec`) |
| 18:15:26 | **worker-12pm commit (`382ee39`) — last worker commit of the day** |
| ~22:45 (≈16:45 -0600) | digest run wrote `digests/2026-04-29.md` |
| **23:55:40 (= 17:55:40 -0600)** | **single push event lands `382ee39` on `origin/main`** |
| ~06:05 (next day) | night-auditor sees `origin/main = 382ee39` and writes the PROPOSED entry |

The push timestamp (17:55 local) sits AFTER the digest run (16:45 local) and well outside any worker-shift window (workers run 08:00–12:00 local). It's consistent with manual evening review.

### 3. No automation that could have pushed.

- `.git/hooks/` contains exactly one non-sample hook: `pre-commit` (the truncation guard from `scripts/pre-commit-check.sh`). It does not push and is not invoked on push.
- No `post-commit`, `pre-push`, `post-push`, or `post-update` hooks installed.
- No `.git/hooks/post-receive` or server-side hooks (would be irrelevant on the client anyway).
- No `core.hooksPath` redirecting to a custom hook directory.
- No `.github/` directory at all → no GitHub Actions, no scheduled workflow that could call `gh` or push.
- No script in the repo contains `git push`.
- No Cowork scheduled task pushes (per `schedule.json` and the digest).

### 4. Author attribution is mostly Eric, with one anomaly.

```
382ee39 | 2026-04-29 18:15:26 +0000 | Eric Joseph Sy <ericsy99@gmail.com>      worker-12pm
4c645ec | 2026-04-29 17:13:49 +0000 | Eric Joseph Sy <ericsy99@gmail.com>      worker-11am
96aab20 | 2026-04-29 16:18:54 +0000 | process-tools-worker-10am <…>            worker-10am
89b4103 | 2026-04-29 16:17:56 +0000 | process-tools-worker-10am <…>            worker-10am
cd953da | 2026-04-29 16:14:51 +0000 | process-tools-worker-10am <…>            worker-10am
91a240c | 2026-04-29 16:13:31 +0000 | process-tools-worker-10am <…>            worker-10am
76e211b | 2026-04-29 16:11:52 +0000 | process-tools-worker-10am <…>            worker-10am
24f1b3d | 2026-04-29 15:20:29 +0000 | Eric Joseph Sy <ericsy99@gmail.com>      worker-9am
91a05bf | 2026-04-29 14:35:06 +0000 | Eric Joseph Sy <ericsy99@gmail.com>      worker-8am
```

`git config user.name / user.email` returns `Eric Joseph Sy / ericsy99@gmail.com`, so commits made via the standard plumbing-path workaround (which doesn't override `GIT_AUTHOR_*`) inherit Eric's identity. Worker-10am alone explicitly set a custom author. This author-attribution detail is not directly relevant to the push question, but it does mean a future audit cannot use `git log --author` to distinguish worker commits from Eric commits — only `process-tools-worker-10am` is unambiguous.

### Hypothesis verdicts

| Hypothesis | Verdict | Evidence |
|---|---|---|
| (a) Workers pushed silently | **REFUTED** | Only one push event on 2026-04-29 covers all 8 worker commits in one shot. If workers pushed, the reflog would show 6+ separate "update by push" entries through the morning. The push also happened at 23:55 UTC, ~5h after the last worker shift ended. |
| (b) Eric pushed manually | **STRONGLY SUPPORTED** | Single push event at 17:55 -0600 (evening), after digest ran, fast-forwarding through every worker commit. Consistent with a `git push origin main` run during evening review. |
| (c) Out-of-band push hook | **REFUTED** | No hooks installed beyond `pre-commit`. No CI. No script in the repo calls `git push`. No `core.hooksPath` redirect. |

## Recommendation

**Actionable change** — but the action is at the policy/workflow level, not at the code level.

The auditor's PROPOSED entry phrased the question as "policy and practice diverge — pick one of two paths to reconcile." Grounded in the evidence above, the framing should be sharper: **workers are not violating the push policy. They're following it correctly.** The "no push without GitHub MCP" fallback is engaging as designed (no MCP available → workers commit locally, log to NEEDS-INPUT, defer push). The remote drift is from a separate actor — Eric's evening manual push to `main` — that the policy doesn't address.

Concrete options for Eric (any are valid; pick one):

1. **Status quo, documented.** Add one line to `roles/worker.md` and/or `CLAUDE.md`: *"Eric reviews and pushes to `main` directly during evening review. Worker push policy applies only to automated runs."* This makes the observed behaviour the policy. Lowest-cost option; no new tooling.

2. **Install + auth the GitHub MCP** (the auditor's other PROPOSED item). Then workers push to `automation/<role>-<YYYY-MM-DD>-<slot>` branches with draft PRs as the existing policy says, and Eric merges PRs in evening review instead of pushing main. Higher up-front cost; aligns with the originally-written policy.

3. **Drop the branch policy entirely.** Strip the `automation/<role>-...` requirement from `roles/worker.md` and accept that workers commit locally without pushing, with Eric pushing to main directly when he reviews. Same end-state as option 1 but with less doc.

The decision is purely a workflow preference; there is no correctness or security issue here. The narrower point that needed grounding — *"are commits reaching `main` via some mechanism we don't know about?"* — has a clean answer: **no, they're reaching `main` via Eric's hands**.

## Open follow-ups

- The author-attribution anomaly (worker-10am uses a synthetic identity, all other workers inherit Eric's identity) is unrelated to the push question but is worth a one-line note for future auditors. Recommend a small `~/.gitconfig.d/process-tools` or a wrapper that sets `GIT_AUTHOR_NAME=process-tools-worker-<slot>` for every scheduled-task commit so log searches stay legible. Out of scope for this research.
- The night-auditor's PROPOSED #1 (refresh `.git/index` via `git read-tree HEAD`) is independent of the push question. Stale-index ghost diffs are caused by the `GIT_INDEX_FILE=/tmp/...` plumbing-path workaround, not by anything push-related. Whoever resolves the push policy should also act on that PROPOSED separately.
- One detail not covered: the local `main` reflog only goes back to `24f1b3d` (worker-9am) and is missing every later commit because workers 10am-12pm used `printf <sha> > .git/refs/heads/main` to advance `main`, which bypasses the reflog. So `git reflog show main` is a misleading source for "what did `main` point to during 2026-04-29." `origin/main` reflog is correct because pushes always update reflogs. If the team relies on `git reflog main` for audit, that's a separate gap.
