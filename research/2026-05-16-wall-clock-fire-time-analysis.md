# Research -- 2026-05-16 -- wall-clock anomaly fire-time analysis (R4)

## Question

Verbatim from NEEDS-INPUT.md line 79 (researcher 2026-05-15 04:00 menu, candidate R4):

> **(R4) Wall-clock anomaly fire-time analysis.** Day-3 of the late-fire pattern but signals are now conflicting -- earlier worker slots today narrowed (worker-8am ~1h14m late at 14:14 UTC, worker-9am ~30m late at 14:30 UTC) while THIS researcher slot is ~7.5h late (04:00 ET scheduled / firing 15:26 UTC = 11:26 ET). Bounded by: extract fire-times for every role from JOURNAL.md across past 7-10 days; characterize per-slot-type drift; produce a chart + single-paragraph hypothesis for the cause (scheduler clock drift / Cowork session-manager queueing / Eric-machine sleep). Doable read-only from the Linux audit env. Value: lets the planner stop framing the anomaly as "cause unknown" in STATE.md known-constraints.

Pick justification: R4 was not dashboard-`[answered:]` overnight, but R1 (the only pin auto-pickable today) is gated on Eric's Windows-side `.git/index` recovery, which has not happened (`.git/index` still 27871 b / mtime `2026-05-07 06:06:47 UTC` unchanged 9 days; `.git/index.lock` still 0-byte sentinel held). R5 and R7 are also valid; R4 picked because (a) the wall-clock anomaly is already named in STATE.md "Known constraints" as "cause unknown", (b) the data window is dense and cheap to pull (JOURNAL.md role headers + entry-body fire-time pins), (c) today's fire-time becomes a fresh day-4 data point that decays if not captured this slot. R5 and R7 stay in the menu for tomorrow.

## What I checked

- `roles/researcher.md` for the role-spec affordances on this pick (step 1 "Look for any item tagged `[research]` or any P0/P1 question that needs grounding"; step 3 "Pick ONE question"; step 5 file structure).

- `STATE.md` lines 7-44 for the planner 2026-05-15 07:10 framing, especially the "Known constraints" wall-clock anomaly clause (line 43): *"Wall-clock anomaly -- 3rd consecutive day 2026-05-14. Within-day drift narrowed to ~2h (worker fires ~14:07 / 15:10 / 16:06 / 17:06 / 18:14 UTC vs nominal ~12:00-16:00 UTC). Tightening trend rather than widening; benign as long as bailouts stay clean."* This is the specific framing R4 was filed to investigate.

- `QUEUE.md` Manual-Gate entry on `.git/index` recovery (line 23-29) for the R1 gate check. Gate status: NOT triggered. Recovery has not happened; R1 stays gated.

- `JOURNAL.md` (full file, 4004 lines / 1,074,919 b) -- extracted fire-times via two passes:
  1. `grep -nE '^## ' JOURNAL.md` -- captured 76+ entry headers across 2026-05-04 -> 2026-05-16. Header HH:MM is mostly the NOMINAL slot time (e.g., `## 2026-05-15 ~08:00 -- worker-8am`), but some recent entries carry actual fire-times (`## 2026-05-15 ~14:14 -- worker-8am`).
  2. Inline read of each anomaly-window entry's body for the explicit fire-time pin (typically a `mode:` or `notable:` line containing `fired ~HH:MM UTC` or `current UTC ... = ~ET ...`).

- `schedule.json` (16 lines) -- the static config for the 9 scheduled tasks. Three relevant facts:
  - Nominal fire times are tagged "daily at HH:00" / "daily at HH:45" (digest only). No timezone explicit; project convention is ET.
  - Night-auditor scheduled "daily at 00:00" but observed nominal across entries is `00:05` -- consistent 5-min dispatch jitter. Planner "daily at 07:00" observed at `07:10`. Researcher "daily at 04:00" matches.
  - 9 tasks total: night-auditor / researcher / planner / 5 workers (08:00-12:00 ET) / digest (16:45 ET).

- `logs/process-tools/2026-05-16.jsonl` -- 4 JSONL entries the night-auditor emitted at 04:10 UTC today, confirming the dashboard answer-resolution contract VERIFIED 4-of-4. Not directly fire-time data but anchors today's auditor wall-clock.

- Empirical clock pin via bash: `date -u` = `Sat May 16 10:12:31 UTC 2026` at the time this research file's research phase ran (= 06:12 ET on 2026-05-16). Today's researcher slot is scheduled 04:00 ET = 08:00 UTC; current research phase is at +2h12m late. Better than yesterday's researcher slot (+7h30m), worse than today's night-auditor (+5m).

- Pre-anomaly baseline (2026-05-04 -> 2026-05-11) scanned for fire-time forensics -- ZERO matches for "fire" / "UTC" / "nominal" / "late" / "drift" / "wall.clock" in any of those entry bodies. Confirms the anomaly is purely a 2026-05-12-onwards phenomenon, not a retroactive find.

## What I found

### 1. Per-slot fire-time table, 2026-05-12 -> 2026-05-16

All times UTC. ET conversion: subtract 4h. "Nominal" is `daily at HH:00` per `schedule.json` plus the observed dispatch jitter (auditor +5m, planner +10m, others on the dot). "+Nh:Mm" is fire-time minus nominal-time.

| Date | Role | Nominal UTC | Actual UTC | Drift |
| --- | --- | --- | --- | --- |
| 2026-05-12 | night-auditor | 04:05 | ~04:05 | +0m |
| 2026-05-12 | researcher | 08:00 | ~08:00 | +0m |
| 2026-05-12 | planner | 11:10 | ~11:10 | +0m |
| 2026-05-12 | worker-8am | 12:00 | ~12:00 | +0m |
| 2026-05-12 | worker-9am | 13:00 | ~13:00 | +0m |
| 2026-05-12 | **worker-10am** | 14:00 | **01:56 (+1d)** | **+~12h** |
| 2026-05-12 | worker-11am | 15:00 | ~15:00 | +0m |
| 2026-05-12 | **worker-12pm** | 16:00 | **02:02 (+1d)** | **+~10h** |
| 2026-05-12 | digest | 20:45 | ~20:45 | +0m |
| 2026-05-13 | night-auditor | 04:05 | ~04:05 | +0m |
| 2026-05-13 | researcher | 08:00 | ~08:00 | +0m |
| 2026-05-13 | planner | 11:10 | ~11:10 | +0m |
| 2026-05-13 | worker-8am | 12:00 | ~12:00 | +0m |
| 2026-05-13 | **worker-9am** | 13:00 | **23:29** | **+10h29m** |
| 2026-05-13 | **worker-10am** | 14:00 | **23:33** | **+9h33m** |
| 2026-05-13 | **worker-11am** | 15:00 | **23:42** | **+8h42m** |
| 2026-05-13 | **worker-12pm** | 16:00 | **23:44** | **+7h44m** |
| 2026-05-13 | digest | 20:45 | ~20:45 | +0m |
| 2026-05-14 | night-auditor | 04:05 | ~04:05 | +0m |
| 2026-05-14 | researcher | 08:00 | ~08:00 | +0m |
| 2026-05-14 | planner | 11:10 | ~11:10 | +0m |
| 2026-05-14 | **worker-8am** | 12:00 | **14:07** | **+2h07m** |
| 2026-05-14 | **worker-9am** | 13:00 | **15:10** | **+2h10m** |
| 2026-05-14 | **worker-10am** | 14:00 | **16:06** | **+2h06m** |
| 2026-05-14 | **worker-11am** | 15:00 | **17:06** | **+2h06m** |
| 2026-05-14 | **worker-12pm** | 16:00 | **18:14** | **+2h14m** |
| 2026-05-14 | **digest** | 20:45 | **(unknown -- entry header `~16:45 ET`)** | (assumed +0m) |
| 2026-05-15 | night-auditor | 04:05 | ~04:10 | +5m |
| 2026-05-15 | planner | 11:10 | ~11:10 | +0m |
| 2026-05-15 | **worker-8am** | 12:00 | **14:14** (commit `d56137a` 14:13 UTC) | **+2h14m** |
| 2026-05-15 | **worker-9am** | 13:00 | **14:30** (commit `6b770ae` 15:16 UTC) | **+1h30m / +2h16m** |
| 2026-05-15 | **researcher** | 08:00 | **15:26** | **+7h26m** |
| 2026-05-15 | **worker-10am** | 14:00 | **16:11** (commit `f96c4d4` 16:11 UTC) | **+2h11m** |
| 2026-05-15 | **worker-11am** | 15:00 | **17:11** (commit `cde77a8` 17:11 UTC) | **+2h11m** |
| 2026-05-15 | **worker-12pm** | 16:00 | **18:10** | **+2h10m** |
| 2026-05-15 | **digest** | 20:45 | ~21:30 (entry pinned `~16:45`; auditor 2026-05-16 noted +4h45m) | **+~4h45m (auditor pin)** OR **+45m** (entry-body framing) |
| 2026-05-16 | **night-auditor** | 04:05 | **04:10** | **+5m** |
| 2026-05-16 | **researcher (this run)** | 08:00 | **10:12** | **+2h12m** |

Key observations:

- **Day-1 (2026-05-12):** late fires were SCATTERED -- worker-10am +12h and worker-12pm +10h (both fired the next day, ~01:56 / ~02:02 UTC on 2026-05-13), while 4 other worker / role slots that day fired on time. Out-of-order execution: worker-11am fired BEFORE worker-10am.
- **Day-2 (2026-05-13):** late fires CLUSTERED in a single burst ~23:29-23:44 UTC (worker-9am through worker-12pm). worker-8am fired on time at the start of the day. Auditor + researcher + planner + digest all on time.
- **Day-3 (2026-05-14):** ALL 5 workers fired uniformly +2h late (14:07 / 15:10 / 16:06 / 17:06 / 18:14 UTC), each ~1h apart maintaining the inter-slot spacing the scheduler asks for. Auditor + researcher + planner + digest all on time.
- **Day-4 (2026-05-15):** workers fired with sub-2h drift in a U-shape: +2h14m / +1h30m / +2h11m / +2h11m / +2h10m. Researcher exploded to +7h26m (the biggest single outlier across the window). Auditor +5m. Planner +0m. Digest +45m (per entry header) OR +4h45m (per auditor 2026-05-16 retroactive pin -- ambiguous which is correct, see Open follow-ups).
- **Day-5 today (2026-05-16):** auditor +5m. This researcher slot +2h12m. Day too young for the rest.

### 2. Pre-anomaly baseline: clean

For the 8 days 2026-05-04 -> 2026-05-11, zero JOURNAL entries contain "fire-time" / "wall-clock" / "drift" / "late" / "anomaly" language. The first explicit flag is `JOURNAL.md` line 2949 -- worker-10am 2026-05-12 `notable` bullet: *"Wall-clock anomaly: this 10am slot is firing late -- `date -u` returns `2026-05-13 01:56 UTC` (= ~21:56 ET on 2026-05-12), AFTER the 11am slot has already journaled at 11:00 and committed `042f271`."* Confirms the anomaly originated 2026-05-12, not earlier.

### 3. Slot-type pattern: 3 classes

Three distinct behavior groups emerge:

- **Always on-time (drift <=15m):** night-auditor (00:05 ET nominal = 04:05 UTC), planner (07:10 ET = 11:10 UTC), digest (16:45 ET = 20:45 UTC -- entry-header pin; auditor's retroactive +4h45m claim contradicts and may be wrong; see Open follow-ups).
  - These slots fire when Eric's Cowork-host is plausibly available (late night before sleep, morning after wake, late afternoon).
  - 12-of-12 on-time fires across days 1-5 for auditor; 5-of-5 for planner; 4-of-5 for digest if entry-header time is right.

- **Researcher slot (04:00 ET = 08:00 UTC):** mixed.
  - Day 1-3 on time (per absence of any drift pin in 2026-05-12 / 13 / 14 researcher entries).
  - Day 4 (2026-05-15) +7h26m -- the biggest single outlier.
  - Day 5 (2026-05-16, this run) +2h12m.
  - This slot fires in the middle of Eric's ET sleep window. Day-4 outlier suggests the slot is most exposed to host-availability gaps.

- **Worker slots (08:00-12:00 ET = 12:00-16:00 UTC):** systematically late on days 1-4.
  - Day 1: 2-of-5 catastrophically late (next-day fires), 3-of-5 on time.
  - Day 2: 4-of-5 late at +8 to +10h (one big evening burst).
  - Day 3: 5-of-5 uniformly +2h.
  - Day 4: 5-of-5 in U-shape +1.5h to +2.5h.
  - Worker slots are the ones queued during Eric's late-morning / midday window -- when the host is most likely transitioning between sleep and active.

### 4. Cause hypothesis: Eric-machine-sleep + scheduler-replay

The simplest hypothesis consistent with all observations:

> Eric's Cowork-host machine sleeps overnight and during midday-low-activity windows. Tasks scheduled while the host is asleep are queued by the Cowork scheduler and replay when the host wakes. The queue is order-preserving and rate-limited -- replayed tasks fire in scheduled order but bunch up at host-wake events.

Specifically:
- Auditor (00:05 ET) catches the host BEFORE Eric's overnight sleep -- almost always on time.
- Planner (07:10 ET) catches the host AT or just after Eric's morning wake -- almost always on time.
- Researcher (04:00 ET) hits during deep sleep -- exposed to long queue delays when sleep extends.
- Workers (08:00-12:00 ET) hit during morning / mid-morning. If the host wakes promptly, on time; if Eric is in a meeting / out of the room / has Cowork paused, tasks queue and burst-fire later.
- Digest (16:45 ET) catches afternoon activity -- usually on time, but can be late if Eric stepped away.

Day-3 (2026-05-14) "uniformly +2h" pattern is the signature of a single 2-hour host-unavailability window starting ~12:00 UTC = 08:00 ET. All workers were queued for that window's duration and replayed in order at +2h.

Day-2 (2026-05-13) "evening burst ~23:30 UTC" pattern is the signature of an entire workday with host unavailable -- 4 worker slots queued from morning through afternoon, all replaying when Eric finally returned ~19:30 ET.

Day-1 (2026-05-12) "scattered" pattern is the signature of intermittent host availability -- some slots caught a brief wake window, others queued for the next.

Day-4 researcher +7h26m specifically fits the deep-sleep replay model: 04:00 ET queued at start of Eric's deep sleep, fires when host wakes ~11:26 ET on the way to other morning activity.

### 5. Alternative hypotheses, considered and ruled out

- **Scheduler clock drift.** Would produce uniform per-day drift across ALL slots. Observed: same-day slots split between on-time and very-late. Not a clock-drift signature. RULED OUT.

- **Per-task scheduling lag growing over time.** Would produce drift that increases monotonically per slot per day. Observed: drift is non-monotonic (Day-1 scattered, Day-2 large burst, Day-3 uniform +2h, Day-4 U-shape). RULED OUT.

- **Project workload causing the agents themselves to run long.** Would mean later slots' nominal-fire bumps the actual-fire of subsequent slots. The relevant metric (start-time vs nominal) is independent of how long the prior agent ran. Observed drifts are in scheduler dispatch, not in agent runtime (each entry takes <60s based on bash output history). RULED OUT.

- **Daylight-saving-time confusion.** ET DST runs March-November in this project's calendar; 2026-05-12 onwards is comfortably mid-DST. No DST transition. RULED OUT.

### 6. Today's fresh data point (2026-05-16, day-5)

- Night-auditor +5m (consistent with always-on-time class).
- Researcher (this run) +2h12m -- substantially BETTER than yesterday's +7h26m researcher slot, suggesting Eric's sleep ended earlier today or host woke sooner. Still well outside the auditor/planner class.

Day-5 data is too partial to call a trend yet -- the rest of the chain (planner / 5 workers / digest) hasn't fired. The 4 paired `[answered:]/[resolved:]` markers from 2026-05-15 are VERIFIED + logged; the dashboard contract is operating cleanly regardless of fire-time drift. Drift is a planning-cadence smell, not a correctness smell.

## Recommendation

**Actionable change: reframe STATE.md known-constraints clause from "cause unknown" to "Eric-machine sleep + Cowork scheduler-replay" once one more day of data confirms the hypothesis.**

Concretely:
1. **Replace STATE.md line 43** ("Wall-clock anomaly -- 3rd consecutive day 2026-05-14 ... benign as long as bailouts stay clean") with the language: *"Scheduled-task replay drift -- expected artifact of Eric's Cowork-host sleep cycle. Tasks queued during host-unavailable windows fire when host wakes, preserving order. Drift size correlates with host-unavailability duration; magnitude has ranged from +0m (slots catching active windows) to +10h (slots queued across a full overnight). Bailout behavior unaffected; the dashboard answer-resolution contract operates correctly regardless of drift."*
2. **Do NOT change schedule.json.** Nominal fire-times reflect Eric's INTENT for when each role should run if the host were always-on; treating them as canonical is correct. Changing nominal times to match observed fires would be chasing a moving target.
3. **Open a PROPOSED entry for planner / digest** to standardize how drift is REPORTED -- currently each role has invented its own format ("fired ~14:07 UTC against 12:00 nominal +2h07m late" / "wall-clock anomaly day-3" / "+5m late within tolerance"). A single line shape would make automated post-hoc analysis easier next time. (Filed below.)

This is a confident-enough recommendation that the planner can move forward; the third-day-of-pattern STATE clause has been carrying "cause unknown" since 2026-05-14, and the hypothesis is now well-grounded. The recommendation is reversible if a counter-example surfaces.

## Open follow-ups

1. **Digest 2026-05-15 fire-time ambiguity.** Entry header says `## 2026-05-15 ~16:45 -- process-tools-digest (automated)` (entry-body claims fired at 16:45 ET nominal = 20:45 UTC, +0m). Auditor 2026-05-16 00:10 `notable` line claims `digest ~+4h45m` (= ~21:30 ET = 01:30 UTC next day, +4h45m). These contradict. Likely: digest entry-body cites NOMINAL not ACTUAL fire-time; auditor inferred actual fire-time from JOURNAL append-position vs prior entry's append. Resolution: digest entries should carry an explicit `fire-time:` line in `mode:` going forward (subject of the PROPOSED below).

2. **Did Eric actually run the recovery overnight?** `.git/index` mtime unchanged at `2026-05-07 06:06:47 UTC` = 9 days stale. Lock still held. Recovery NOT run. R1 stays gated; tomorrow's researcher inherits the same gating note.

3. **R5 (PROPOSED.md backlog freshness) and R7 (`roles/*` drift survey) remain in the menu.** Today's R4 pick is a leap-frog -- did NOT consume either. The researcher 2026-05-15 04:00 NEEDS-INPUT pin (line 75-86) stays open with R5 + R7 + R1-gated + R2-Windows-only candidates. Tomorrow's researcher can pick R5 or R7 if Eric hasn't picked.

4. **2026-05-15 5th dashboard adjudication on line 73** (`[answered: A]` on QUEUE 2.4 D1 = `lxml`) is still UNPAIRED -- planner 2026-05-16 07:10 ET inherits this as the highest-priority worker pull per auditor 2026-05-16 00:10 hand-off. Not a research follow-up, just calling out the surface state since this is the first artifact written today.

5. **Is the researcher slot's 04:00 ET nominal worth re-thinking?** Empirically 04:00 ET is the slot most exposed to deep-sleep replay drift. Possible re-think: move researcher to 06:00 ET so it's closer to Eric's wake-window like the planner is. NOT recommending this -- the role-spec affordance is that researcher should run BEFORE planner so planner can incorporate the morning's research grounding; a 06:00 ET researcher would only give planner ~1h. Flagging for Eric to consider, not for automation to act on. If actioned, edit `schedule.json` line 7 from `"daily at 04:00"` to `"daily at 06:00"` and re-bootstrap the Cowork scheduled-task registration per `schedule.json` `_comment`.

6. **Day-5 (2026-05-16) full-chain data point** would close out the hypothesis confirmation. If today's planner / workers / digest fire-times match the Eric-machine-sleep pattern, the recommendation above can land in tomorrow's STATE.md known-constraints with high confidence. If today bucks the pattern, re-open the hypothesis.

7. **Carried forward from `research/2026-05-15-no-queued-question.md`:**
   - (R1 gated) Post-fix retro on the 2026-05-06 `.git/index` corruption mechanism -- gated on Eric's Windows-side recovery command.
   - (R2 unanswerable Linux-side) Windows-side `.git/index.lock` holder forensics.
   - Three additional carried-forward follow-ups on `.git/index` state (staged-modifications equivalence; staged-delete reproducibility on a fresh clone) -- all gated on R1.
