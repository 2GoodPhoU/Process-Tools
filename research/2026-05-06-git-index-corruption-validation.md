# 2026-05-06 -- .git/index corruption: empirical validation of auditor 2026-05-06 P1 PROPOSED

## Question

Is the night-auditor 2026-05-06 PROPOSED P1 entry's diagnosis of `.git/index` corruption empirically correct, and is the recommended fix sequence (`rm -f .git/index .git/index.lock && git read-tree HEAD`) actually safe and complete? The same auditor role has produced 5 confabulation-pattern findings in the running window (per STATE.md "Audit-quality concern"), so a P1 recommendation that touches `.git/` warrants verification before Eric approves.

(Verbatim from PROPOSED.md line 153, auditor 2026-05-06: ".git/index is structurally corrupt, not merely stale -- escalates the still-open P1 from 2026-04-30." Recommendation: "from a non-locked git state, `rm -f .git/index .git/index.lock` then `git read-tree HEAD` (or equivalently `git reset --mixed HEAD`).")

## What I checked

Sources / commands (all read-only; no `.git/` writes):

- `git rev-parse HEAD`, `git rev-parse origin/main`, `git rev-list --count` (both directions) -- HEAD vs remote.
- `git status --short` -- live (corrupt) index view.
- `git fsck --no-progress` -- live index validation.
- `git ls-files -u` -- live unmerged-entries enumeration.
- `ls .git/{MERGE,CHERRY_PICK,REBASE}_HEAD .git/rebase-{merge,apply}` -- merge / rebase state probe.
- `stat .git/index .git/index.lock` -- lock-file existence + mtime.
- `head -c 16 .git/index | xxd` -- index header inspection (DIRC magic + version + entry count).
- Python: `hashlib.sha1` over the live index body, compared against the trailer 20 bytes.
- `GIT_INDEX_FILE=/tmp/idx-fresh.$$ git read-tree HEAD` then `git fsck --no-dangling --no-reflogs` against the fresh index -- non-destructive equivalent of the auditor's recommended fix; uses a temp-file index so the live `.git/index` is never written.
- Same temp-index: `git diff --stat HEAD`, `git status --short`, `git ls-files -u` -- post-fix expected state.
- Python: re-validate the temp-file index trailer SHA1 self-consistency.
- `git ls-tree -r HEAD | wc -l` -- HEAD blob count vs index entry count.
- `stat -c%s` on each working-tree file the fresh index flags as modified -- confirm legitimate, file present.

## What I found

**1. Corrupt-index symptoms reproduce exactly as the auditor reported.**

```
$ git fsck --no-progress
error: bad index file sha1 signature
fatal: index file corrupt
```

```
$ git ls-files -u
000000 590000006c0100006c0400006c0a00006c0a0000 2  "l\020"
15000000000 6c0000006d0000006e0000006f00000070000000 3 r
23200000000 9e0000009f000000a0000000a1000000a2000000 2 ./
```

Three phantom unmerged stage entries with control-character paths (`"l\020"`, `r`, `./`) and impossibly-long mode strings (`000000`, `15000000000`, `23200000000` -- valid git modes are 6 octal characters). No merge / cherry-pick / rebase in progress: `.git/MERGE_HEAD` / `.git/CHERRY_PICK_HEAD` / `.git/REBASE_HEAD` / `.git/rebase-{merge,apply}` all absent. `.git/index.lock` exists, 0 bytes, mtime 2026-04-29 17:10:14 UTC (~4 minutes after the live `.git/index` mtime of 2026-04-29 17:06).

**2. Refinement on the corruption mechanism.**

- The index header is structurally intact: first 12 bytes `4449524300000002000000ea` decode to `DIRC` magic + v2 + 234 entries. The header is fine; the body looks parseable up to a point.
- The trailing 20-byte SHA1 is wrong:
  - Stored trailer:   `680000000000000000000081a400000000000000`
  - Computed SHA1:    `00c08ebf83dee1378d4b78b473095e4370a8ce04`
- The trailer bytes `81a4` are git's encoded mode for a regular 0644 file. The trailer is leaking raw stat data from a partial entry write -- consistent with a git process that started writing the new index, made it partway through entries, then died before writing the trailing checksum and renaming the temp file into place. The 0-byte `.git/index.lock` (mtime 4 min after `.git/index`) is consistent with that timeline: a Windows-side git started a write, took the lock, wrote partial data, died before the rename, never released the lock.
- Net: the corruption is confined to `.git/index`. The object database is fine.

**3. Object database is intact; fresh index reconstruction is structurally clean.**

```
$ TMPIDX=/tmp/idx-fresh.$$
$ GIT_INDEX_FILE=$TMPIDX git read-tree HEAD     # exit 0
$ GIT_INDEX_FILE=$TMPIDX git fsck --no-dangling --no-reflogs    # exit 0, no errors
```

Fresh index: 27959 bytes (vs live corrupt 23103 -- 1 entry lost in the corrupt write), 235 entries, trailer SHA1 self-consistent (`computed == stored`). `git ls-tree -r HEAD | wc -l` = 235, matching the fresh index entry count.

**4. Working-tree state under a fresh index is the expected legitimate dirty list.**

```
$ GIT_INDEX_FILE=$TMPIDX git status --short
 M JOURNAL.md
 M PROPOSED.md
 M requirements-extractor/.gitignore
 M samples/bpmn_validation/simple_two_actors.bpmn
 M samples/bpmn_validation/simple_two_actors.puml
 M samples/bpmn_validation/simple_two_actors.skel.yaml
 M samples/bpmn_validation/simple_two_actors.xmi
?? digests/2026-05-05.md

$ GIT_INDEX_FILE=$TMPIDX git ls-files -u
(empty)
```

All 7 dirty files exist on disk with non-empty sizes (493033 / 42179 / 713 / 6317 / 427 / 804 / 2182 bytes). Each is independently accountable:

- JOURNAL.md, PROPOSED.md -- the night-auditor 2026-05-06 00:05 appends.
- requirements-extractor/.gitignore -- separate pre-existing edit (not in scope of this research).
- samples/bpmn_validation/* -- the 4-file CRLF normalization issue already filed as a separate PROPOSED entry (auditor 2026-05-05).
- digests/2026-05-05.md -- yesterday's digest, untracked, expected.

No phantom `UU` rows. No `AD ./` / `AD "\002"` / `AD "\004"` / `AD "\b"` rows. No control-character paths.

**5. The recommended fix is empirically equivalent to my non-destructive test.**

`rm -f .git/index .git/index.lock && git read-tree HEAD` is structurally identical to what I just did with `GIT_INDEX_FILE=$TMPIDX git read-tree HEAD` -- same `read-tree` invocation, same HEAD as input, same resulting body bytes (proven by my fresh-index trailer SHA1 self-consistency check). The only difference is: the auditor's command writes the fresh index as `.git/index` itself; mine wrote it as `/tmp/idx-fresh.$$` (which I deleted at end of run, leaving live `.git/index` corrupt). Working tree is untouched in both paths.

**6. No surprises.**

- HEAD `f734248813923264886cd30b427ced034803277c` matches origin/main (0 ahead / 0 behind via `git rev-list --count` both directions). Confirms the auditor's STATE.md claim.
- Workers' `GIT_INDEX_FILE=/tmp/...` plumbing-path commit pattern has been shielding commits from the corrupt live index all week; this is why today's chain is clean on `main` despite the index being broken since 2026-04-29 17:06.

## Recommendation

**Actionable change.** Approve auditor 2026-05-06 PROPOSED P1 as written -- the diagnosis is empirically correct on every claim; the fix is empirically validated against a fresh-index reconstruction.

Specifics for Eric (refinements, not corrections):

1. Run from an attended session in a state where no other git process is touching the repo. Close any IDE-side git status watchers, any open terminal `git status` sessions, and (if running from WSL) any concurrent Windows-side `git` invocations on this directory.
2. The exact sequence (verbatim from the PROPOSED entry): `rm -f .git/index .git/index.lock && git read-tree HEAD`. Mine ran the equivalent against a temp file with exit 0 and a self-consistent trailer.
3. Verify with: `git fsck --no-progress` (expect exit 0, no `bad index file` line) and `git ls-files -u` (expect empty). Then `git status --short` should match my temp-index output above (7 modified + 1 untracked, no `UU` / `AD` / control-character rows).
4. The 4 `samples/bpmn_validation/*` `M` markers will persist post-fix -- they're the CRLF normalization, separately filed as auditor 2026-05-05 PROPOSED. Not corruption.
5. After the fix, the auditor's 2026-04-30 P1 (PROPOSED.md line 65, "stale .git/index") is fully resolved by the same action; planner should retire it on the next pass alongside the 2026-05-06 P1.

The "stale" framing in the 2026-04-30 P1 was empirically incomplete -- the index isn't merely out-of-date, it's structurally corrupt with a wrong trailing SHA1 from a partial write. The 2026-05-06 PROPOSED supersedes that framing without contradicting the recommended action; both end at the same `read-tree HEAD` invocation.

## Open follow-ups

1. **Why did the corrupt write happen on 2026-04-29 17:06-17:10?** A Windows-side git process took `.git/index.lock`, wrote a partial index, died before completing the trailer + rename. Was Bitdefender or another Windows AV touching `.git/`? Was an IDE-side git operation killed? The .lock mtime (17:10:14, 4 min after `.git/index`'s 17:06) and the leaked stat-data trailer (`81a4` mode bytes) is a pretty specific failure shape. Worth a brief post-fix retro to identify the trigger so it doesn't recur.

2. **Should the plumbing-path commit workaround (`GIT_INDEX_FILE=/tmp/...`) remain after the fix, or be retired?** Workers have been using it as a defensive default since 2026-04-30 to dodge the corrupt index. Once `.git/index` is structurally sound, the workaround stops being load-bearing -- but it's also been a useful invariant ("Workers do not write to the live index"). Decision: probably retire it post-fix, but flag the question for Eric since two PROPOSED items + STATE.md "Known constraints" reference it as standing practice.

3. **A defensive `git fsck` step in the night-auditor role.** Tonight's auditor caught the corruption on the 7th day after it appeared. A one-line `git fsck --no-progress` in `roles/night-auditor.md` would surface this kind of structural break the morning after it happens, not a week later. Out of scope for this research file; worth a separate PROPOSED if Eric wants the discipline.
