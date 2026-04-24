> **STATUS: DISCHARGED (2026-04-24).**
> Option (a) — bundled PyInstaller exe with spaCy + en_core_web_sm
> baked in — was selected after IT sign-off on a ~250–300 MB
> single-file exe. The build recipe is live in
> `packaging/build-requirements.txt` (NLP pins uncommented),
> `packaging/DocumentDataExtractor.spec` (collect_all already wired),
> `packaging/build.bat` / `build.sh` (prereq comments updated), and
> `README.md` (pinned model-wheel URL in the Packaging section).
> The manual step-by-step smoke-test runbook lives at
> `docs/NLP_BUNDLE_SMOKE_TEST.md` — run it on your Windows build
> machine when you're ready to produce the artifact. Option (c) is
> also documented as the fallback in the README's "Bundling for a
> restricted network" subsection.
> This plan is kept in-tree for historical context; don't re-derive
> it. Flip a fresh plan if a later requirement (e.g. macOS / Linux
> bundles, different model) warrants a new approach.

---

# Plan — making the NLP path work on the work network

FIELD_NOTES §1. Actor-ID accuracy collapses without NLP, and the work
network's package path will not install spaCy or download its English
model. This is the only blocker to real-world use. Everything else on
the field-notes list is noise until this one ships.

## What the tool actually depends on

- **Library:** `spacy >= 3.7` (listed in `requirements-optional.txt`).
- **Model:** `en_core_web_sm` preferred; `_try_load_spacy` in
  `requirements_extractor/actors.py` also tries `_md` and `_lg` as
  fallbacks.
- **Load path:** `spacy.load("en_core_web_sm")` at `ActorResolver.__init__`
  time, not at import time — so spaCy's cost is only paid when the user
  ticks the NLP checkbox.
- **Failure behaviour:** `_try_load_spacy` swallows `ImportError` /
  `OSError` / `ValueError` / `TypeError` and returns `None`. The
  extractor logs a warning and proceeds without NLP. The run completes,
  but secondary-actor recall drops to whatever the seed xlsx + regex
  layer can carry.
- **Why the network matters:** both the pip install of `spacy` *and*
  the `python -m spacy download en_core_web_sm` step make outbound HTTP
  calls (PyPI + GitHub releases). Either the proxy blocks them, or
  no proxy is reachable, or the approved package channel doesn't carry
  spaCy / the model wheel. Result: fresh installs on a work laptop
  simply don't get an NLP-capable build.
- **Size budget (model artefacts):**
  - `en_core_web_sm` — ~12 MB wheel, ~45 MB unpacked.
  - `en_core_web_md` — ~40 MB wheel, ~160 MB unpacked.
  - `en_core_web_lg` — ~400 MB wheel, ~560 MB unpacked.
- **Licence:** spaCy is MIT. The three English models are MIT. No
  redistribution blocker; no copyleft.

Important datapoint already in the repo: `packaging/DocumentDataExtractor.spec`
already lists `spacy`, `en_core_web_sm`, and the full pydantic/thinc
dependency graph in its `collect_all` block. The bundling path is
partially built out already.

## Options, with implementation sketch and hour estimate

### (a) Bundle spaCy + the model inside the installer

Finish what `DocumentDataExtractor.spec` was designed to do: produce a
PyInstaller exe with spaCy and `en_core_web_sm` pre-baked. The work
network never needs to fetch anything.

**Sketch.**
1. On a connected build machine (one per target OS), set up a build
   venv: `pip install -r packaging/build-requirements.txt` plus the
   commented-out NLP stack in that file (`spacy>=3.7,<3.8`,
   `pydantic>=2.5,<3`, `pydantic-core>=2.14,<3`, `thinc>=8.2,<9`).
2. Install the model directly from its wheel URL (no CLI fetch needed):
   ```
   pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
   ```
   Pinning the wheel URL rather than using `spacy download` keeps the
   build reproducible; also useful if the only connected build machine
   is behind its own proxy.
3. Run `./packaging/build.sh` (macOS/Linux) or `packaging\build.bat`
   (Windows). The spec already bundles spaCy + the model via `collect_all`.
4. Expected exe size: ~250–300 MB (single-file). Startup on cold cache
   ~5–10 s because PyInstaller unpacks the spaCy data to a temp dir on
   first run.
5. Smoke test: copy the exe to the restricted network, tick "Use NLP",
   run against one sample doc, confirm `ActorResolver.has_nlp()` is
   True in the log.
6. Distribute the exe via whatever internal channel the work network
   accepts (shared drive, SCCM, signed installer). The exe has no
   install-time network dependency.

**Effort:** 2–4 hours of real work. ~1 hour setting up the build venv
and resolving whichever pydantic pin the current spaCy release actually
wants (`build-requirements.txt` has notes about this being fragile
across spaCy minor bumps). ~1 hour for a clean build + smoke test per
target OS. Remaining time absorbs the "why does the exe fail to load
the model on target" debugging cycle that historically hits bundled
spaCy apps once (see the spec comment).

**Risks.**
- pydantic major-version mismatch between build-venv and runtime is
  the classic failure mode. Already flagged in `build-requirements.txt`.
  If the current `spacy>=3.7` line in `requirements-optional.txt` ever
  shifts to a spaCy release requiring pydantic 1.x, the bundle will
  throw a `ValidationError` on load. Mitigation: pin `spacy` to a
  specific `~=3.7.2` in `build-requirements.txt` and smoke-test after
  every bump.
- Windows Defender occasionally flags PyInstaller single-file exes
  because of UPX-style packers. The spec already disables UPX
  (`upx=False`) for this reason. If the work network's AV still
  quarantines the exe, fall back to code-signing (buying a cert) or
  the `--onedir` PyInstaller layout — `--onefile` self-extracts to a
  temp directory which some AV treats as suspicious.
- Software-approval policy: a 250 MB exe is within normal footprints,
  but the policy might still flag "bundled Python runtime" as a
  category. Worth confirming with IT before committing. This is
  FIELD_NOTES' open question #1.

### (b) Non-NLP heuristic fallback — stronger rule-based actor extraction

Invest in the regex/heuristic path so the `use_nlp=False` run produces
trustworthy output on its own. Already partially supported via the
actors xlsx + regex match; the gap is discovering actors that aren't
in the seed list.

**Sketch.**
1. Add a `_heuristic_hits(text, primary)` method to `ActorResolver`
   that looks for agent-style noun phrases:
   - Title-case head nouns with a role-suffix set:
     `r"\bThe ([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,3}\s(?:Service|System|Manager|Controller|Gateway|Interface|Module|Subsystem|Handler|Processor|Engine|Agent|Node|Client|Server|Daemon|Operator|Collector|Scheduler))\b"`.
   - "Subject of shall" lift: match the noun phrase immediately before
     a modal verb (`shall`, `must`, `should`, `may`). Stop at
     determiners / prepositions.
   - Ignore-list to suppress generic terms ("The Document", "The
     User", "The System" unless explicitly opted in).
2. Wire into `iter_matches` as a `source="heuristic"` pass after
   `regex` and before `nlp`. Gate behind a new `use_heuristic=True`
   flag (default True when `use_nlp=False`) so it's a visible choice,
   not an invisible behaviour change.
3. Tune against the fixture corpus from §4 of FIELD_NOTES. Iterate
   until recall is >= 70% of the NLP pass on the same corpus with
   false-positive rate < 15%.
4. Expose in the GUI as a third option under "Use NLP" — e.g. a
   "Heuristic actor detection" checkbox that's on by default. In the
   CLI, a `--heuristic` / `--no-heuristic` pair.

**Effort:** 6–10 hours. Pattern authoring is ~1 hour; the tuning loop
is the slog. Needs the fixtures (§4) to iterate against or the numbers
are made-up.

**Accuracy ceiling.** Typical spec-style English with consistent naming
conventions: **60–75% of NLP recall** at a tunable false-positive rate.
Prose-heavy or inconsistently-capitalised corpora: lower, maybe 40–55%.
Worth saying out loud: a heuristic that overfits to the fixture corpus
will look great in tests and worse on new documents. Plan to re-tune
each time a new document family shows up.

**Risks.**
- False-positive storm on tables whose first cells are non-actors
  ("Revision History", "Section 4.1"). Already partially handled by
  the existing skip_sections machinery but new surface for bugs.
- Tuning costs forever. Every new document family costs an evening.

### (c) Pre-process elsewhere, import actors

Already mechanically supported today: run `document-data-extractor
actors` on a connected machine, tidy the output xlsx, copy it to the
restricted machine, run with `--actors`. Formalise it as the
documented offline path.

**Sketch.**
1. Add a short section to `README.md` titled "Offline (restricted
   network) workflow" that walks through the three steps (scan on
   connected machine → tidy → copy → run on restricted machine).
2. Optionally: a CLI convenience `document-data-extractor actors --bundle out.zip`
   that emits `actors.xlsx` alongside a manifest listing source files
   + SHA-256 hashes, so the restricted-network run can warn if the
   source docs diverge from what the scan ran on.
3. Optionally: GUI banner "You don't have NLP — [learn about the
   offline workflow]" with a link into the README section.

**Effort:** 1–3 hours. Zero hours for basic mechanical support — the
flow already works. Documentation is the deliverable.

**Drawbacks.**
- Two-machine workflow with a manual copy step. Every minute of
  friction here compounds; if Eric runs the tool weekly, this adds up.
- The "tidy the xlsx" step assumes a connected machine is always
  available. If Eric is traveling or the connected machine is a
  coworker's laptop, the whole flow breaks.

## Recommendation: ship (a), keep (c) documented, treat (b) as a nice-to-have

Build order:

1. **Finish (a)** — the PyInstaller spec already has the scaffolding;
   it's the cleanest UX and the licensing is clean. This is a one-day
   workstream, not a multi-week one.
2. **Document (c) as the backup** while (a) is going through
   software-approval. If (a) gets blocked on policy grounds, (c)
   becomes the fallback without any code changes.
3. **Defer (b)** unless (a) actually falls through. The heuristic
   path is useful independent work, but it's strictly worse than the
   bundled NLP build and ties up time that's better spent on the
   fixture corpus (§4) and option-exclusion logic (§3 /
   `PLAN-option-exclusion.md`).

Rationale in one sentence: the bundling path is already 80% built
(`DocumentDataExtractor.spec`, `build-requirements.txt`, `build.sh` /
`build.bat`), the remaining work is a build-venv cycle plus one clean
build per target OS, and the network constraint dissolves entirely —
no ongoing workflow tax for Eric, no accuracy compromise.

## Decision checkpoints (before starting implementation)

Three things Eric should confirm before the bundle build runs:

1. **Software-approval scope.** Is a 250–300 MB single-file exe in
   scope for the work network's approval process? If the policy has a
   size cap or excludes bundled Python runtimes, (a) is off the table
   and the plan flips to (c) primary + (b) secondary.
2. **Model choice.** `en_core_web_sm` is the default and the cheapest
   (~45 MB unpacked). `_md` brings word-vector-backed similarity which
   can help NER on domain terms, at ~160 MB. Recommendation: start
   with `_sm` — the accuracy delta for pure NER is small. Keep
   `_try_load_spacy`'s three-model search order as-is so a future
   build that swaps in `_md` picks it up for free.
3. **Build cadence.** Ideally the bundled exe is regenerated whenever
   `requirements-optional.txt` or the spec file changes. Without CI
   this is a manual gate; worth at least adding a note in README.md
   that "run packaging/build.{sh,bat} after touching anything under
   `requirements_extractor/` or the spec".

## Followup tasks (create after Eric signs off)

- Add an NLP smoke test to the CI / pre-commit flow: `python -c
  "from requirements_extractor.actors import _try_load_spacy; assert
  _try_load_spacy() is not None"`. Fails fast if a dep bump breaks
  model loading.
- Capture the exe's SHA-256 into a release note so the distribution
  channel can attest integrity — matters for the work network's
  approval process even if (a) is already green.
- Add a "Build info" panel to the GUI (Help menu, §5) that reports
  `spacy.__version__` and which model loaded. Turns every field bug
  report into self-serving diagnostic data.
