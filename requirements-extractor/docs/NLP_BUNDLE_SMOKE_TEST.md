# NLP bundle — build & smoke-test procedure

Work-network machines can't install spaCy or its English model through
the network's package path, so the `Use NLP` feature has to be baked
into the frozen executable at build time. Everything in this document
is **manual** — do it on a connected Windows build machine once per
release, then copy the artifact to the restricted network.

Context: see `PLAN-nlp-offline.md` for the design rationale
(FIELD_NOTES §1 — actor-ID accuracy collapses without NLP, and this is
the blocker to real-world use on Eric's target environment). The
build-requirements, spec file, and README build recipe are already
updated for the NLP-bundled path — this document is the runbook that
actually exercises them.

---

## Prerequisites (one-time per build machine)

1. Windows machine with internet access — does not need to be the
   target machine.
2. Python 3.10 or newer installed (tick "Add python.exe to PATH"
   during install).
3. The `requirements-extractor/` source tree checked out locally.
4. ~2 GB free disk for the build venv and PyInstaller intermediates.

No spaCy or model-specific prep is needed beyond what the steps below
do — the pinned model-wheel URL handles the download deterministically.

---

## Build steps

All commands are run from inside the `requirements-extractor/`
directory on the build machine.

### 1. Create and activate a fresh build venv

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

A fresh venv keeps any stray packages in your system Python out of the
bundle. Don't skip this even if you've built before — it prevents
mystery failures where `import pandas` works in your dev shell and the
exe drags 300 MB of extras you never asked for.

### 2. Install the runtime and build dependencies

```bat
pip install -r requirements.txt
pip install -r requirements-optional.txt
pip install -r packaging\build-requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
```

**Why the pinned wheel URL?** `python -m spacy download en_core_web_sm`
funnels through spaCy's download CLI and depends on that CLI reaching
github.com through whatever proxy is on the machine. Installing the
wheel directly pins the exact model version, so two build machines
produce identical bundles. If a future spaCy release requires a newer
model, bump the `3.7.1` in the URL to match.

### 3. Verify the build venv can load NLP *before* you run PyInstaller

```bat
python -c "from requirements_extractor.actors import _try_load_spacy; print('NLP ok:' , _try_load_spacy() is not None)"
```

Must print `NLP ok: True`. If it prints `False`, the venv is
mis-configured — stop here and fix it. Running PyInstaller against a
venv that can't load the model will produce an exe that also can't
load the model, but you'll only find out on the target machine.

### 4. Build the executable

```bat
packaging\build.bat
```

This runs `pyinstaller packaging\DocumentDataExtractor.spec --clean
--noconfirm` after clearing any previous `build/` and `dist/`
directories. Expect 2–5 minutes on a modern machine.

The output lands at:

```
dist\DocumentDataExtractor.exe
```

Expected size: roughly **250–320 MB**. If it comes out closer to 60 MB
the NLP collect_all didn't pick up the dependencies — re-check step 2.

### 5. Record the SHA-256 of the produced exe

```bat
certutil -hashfile dist\DocumentDataExtractor.exe SHA256
```

Write this into the release note / changelog. The work network's
software-approval process may ask for it, and it's useful for
attesting integrity after the artifact hops through internal file
shares.

---

## Smoke test on the build machine

Before copying to the work network, verify the bundle actually loads
NLP when run locally. This catches build-level issues (model not
bundled, pydantic version mismatch, etc.) immediately instead of
discovering them hours later on the restricted machine.

### A. Basic launch

Double-click `dist\DocumentDataExtractor.exe`. The GUI should open
within 5–10 seconds on first launch (PyInstaller unpacks to a temp
directory) and under 2 seconds on subsequent launches.

If the window appears and is cut off on the bottom half: that's
FIELD_NOTES §2 — we already shipped a fix for it
(`_fit_window_to_content` in `gui.py` + bumped default geometry).
Close and re-open to confirm the fix is in the bundle.

First-run behaviour: a "Getting started" modal should appear after
200 ms. Tick "Don't show this again" and close. On the next launch
the modal should not re-appear. The Help menu should still expose it
as "Getting started…".

### B. NLP smoke test against a sample doc

1. Tick the **Use NLP to detect secondary actors** checkbox.
2. Add `samples/procedures/simple_two_actors.docx` as the input.
3. Pick any scratch path for the output.
4. Click **Run**.

In the log text area, look for:

- **Absence** of a line containing `NLP unavailable` or `spaCy model
  not found`. Presence of either means NLP did not load — the bundle
  is broken even though the run completed.
- A line roughly like `Processing simple_two_actors.docx…` followed
  by a successful summary with `N requirements (M hard, K soft)`.

The Excel output should open automatically if "Open output file when
the run finishes" is ticked (it's on by default). Confirm the file
has rows and that the Secondary Actors column is populated (that
column is the direct signal that NER fired).

### C. Procedural fixture smoke test

This exercises the four parser changes from Eric's 2026-04-23 pass
inside the bundled exe:

1. Add all four `samples/procedures/procedural_*.docx` files as inputs.
2. Leave the `samples/procedures/procedural_*.reqx.yaml` files in
   their directory — the per-doc auto-discovery picks them up.
3. Click **Run**.

Expected output row counts (filter to `Row Ref` starting `Table 1`):

| Fixture | Expected body rows |
|---------|-------------------:|
| procedural_no_keywords | 5 |
| procedural_actor_continuation | 5 |
| procedural_multi_actor_cell | 4 |
| procedural_bullet_rows | 9 |

If `procedural_no_keywords` produces **zero** body rows, the
header-aware detection (parser §1a) didn't survive the freeze —
something in `packaging/DocumentDataExtractor.spec` is dropping a
module under `requirements_extractor.parser`. Debug by rebuilding
with `console=True` in the spec and reading the stderr trace on the
next launch.

---

## Deploying to the work network

### D. Copy the exe over

Use whatever internal channel the restricted network accepts — shared
drive, SCCM, signed installer. The exe has no install-time network
dependency, so it doesn't matter if the copy lands on a machine with
no external connectivity.

Don't rename the exe on copy — the PyInstaller bootstrapper uses the
executable's basename when building its temp-extraction path.

### E. First launch on the restricted machine

Same smoke-test steps as A above. The important thing to verify here
is that Windows SmartScreen or the corporate AV doesn't quarantine
the artifact:

- If SmartScreen blocks: right-click the exe → Properties → tick
  **Unblock** → OK. This is a one-time per machine step.
- If corporate AV quarantines: talk to IT. The spec already disables
  UPX (`upx=False`) because that's the #1 AV-false-positive trigger
  for PyInstaller exes; if the AV still flags, the fall-back options
  are (i) buy a code-signing cert, or (ii) rebuild with `--onedir`
  layout instead of `--onefile`.

### F. NLP verification on the restricted machine

This is the test that actually validates the whole plan. Repeat step
B on the restricted machine:

1. Tick **Use NLP**.
2. Run against a real spec document (or
   `samples/procedures/simple_two_actors.docx` if you haven't copied
   any real docs over yet).
3. Confirm the log is clean of `NLP unavailable` warnings.
4. Confirm the Secondary Actors column is populated.

If NLP fails to load on the restricted machine but worked on the build
machine, the most common cause is file-system extraction flakiness
— try running the exe once with admin rights to let it warm the temp
directory, then subsequent runs should work as the current user.

---

## Failure modes and what to do

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Log shows `NLP unavailable` after build succeeded | Build venv didn't have spaCy installed | Re-do step 2, re-run step 3 to verify, rebuild |
| Exe is ~60 MB instead of ~250 MB | `collect_all` didn't find the NLP stack | Same as above |
| Exe crashes on launch with `ValidationError` | spaCy / pydantic / pydantic-core version mismatch | Confirm the pins in `packaging/build-requirements.txt` are uncommented and all installed. Don't bump `spacy` without also re-checking `pydantic` and `pydantic-core` — see the prose note at the top of that file |
| Exe opens but GUI is cut off | `_fit_window_to_content` didn't run | Should not happen with the current `gui.py`; if it does, rebuild and confirm `gui.py` mtime predates the PyInstaller run |
| `procedural_no_keywords` produces zero body rows | `requirements_extractor.parser` module missing from bundle | Add explicit `requirements_extractor.parser` to the `hiddenimports` list in the spec; rebuild |
| AV quarantines the exe | UPX-like packing signature | Spec already disables UPX; fall back to code-signing or `--onedir` layout |
| Windows SmartScreen blocks on first run | Unsigned exe | Unblock via Properties, or code-sign |

---

## Release checklist (for future reference)

Run this after any change to files under `requirements_extractor/`,
`packaging/DocumentDataExtractor.spec`, `requirements.txt`,
`requirements-optional.txt`, or `packaging/build-requirements.txt`:

1. Commit the source change on the connected dev machine.
2. On the build machine, pull and activate the build venv (steps 1–2
   above — pip install is idempotent so repeated runs are fine).
3. Run step 4 (`packaging\build.bat`).
4. Run smoke tests A, B, C.
5. Record the SHA-256 (step 5).
6. Copy to the restricted network and run smoke tests E, F.
7. Tag the release with the SHA-256 and the spaCy / model versions
   (`spacy 3.7.x`, `en_core_web_sm 3.7.1`).

If any smoke test fails, don't ship — fix the issue on the dev
machine, re-run the whole checklist. The bundle's value is entirely
in the NLP path working; a build that doesn't load NLP is strictly
worse than the CLI-only path Eric already has.


---

## Pre-flight checklist (sandbox-side, run on the dev machine before every build)

The runbook above is the manual flow on the build machine.  This
section is the cheap headless pass you can run **before** sitting down
on the Windows box, to catch the failures that don't need a build to
surface.  All commands run from `requirements-extractor/`.

1. **Tests are green.**  `python3 -m unittest discover tests` —
   should report `OK`.  A green suite isn't a guarantee the bundle
   will work, but a red suite always means the bundle won't.

2. **Source-tree modules match the spec's `hiddenimports`.**  When
   we add a new module under `requirements_extractor/`, the
   PyInstaller spec needs to know about it — particularly for modules
   imported via dynamic dispatch (the `EXTRA_FORMAT_WRITERS`
   registry, the `diff` subcommand routing, the JSON/MD shim
   modules).  This one-liner flags any drift:

   ```bash
   diff <(ls requirements_extractor/*.py | xargs -n1 basename | grep -v __init__ | sed 's/\.py$//' | sort) \
        <(grep -oP 'requirements_extractor\.\K[a-z_]+' packaging/DocumentDataExtractor.spec | sort -u)
   ```

   No output = in sync.  Any output = the spec needs an update
   (add the missing module names to the `hiddenimports` list inside
   the `Analysis(...)` block).  Same recipe catches the reverse case
   too — a module deleted but still listed.

3. **Optional-dep bundle list matches `requirements-optional.txt`.**
   The second `for _pkg in (...)` block in the spec lists optional
   GUI / input-format add-ons that we want baked into the exe
   (`pdfplumber`, `pdfminer`, `tkinterdnd2`).  Cross-check:

   ```bash
   grep -oP '^(?!#)[a-z][a-z0-9_-]+' requirements-optional.txt | sort -u
   ```

   Anything in that list that's NOT in either of the spec's
   `for _pkg in (...)` blocks is a candidate to add (or to leave
   intentionally out — `spacy` lives in the first block, drag-and-drop
   is in the second).

4. **`build-requirements.txt` pins are still consistent with the
   spaCy minor we're targeting.**  The pin block is:

   ```
   spacy>=3.7,<3.8
   pydantic>=2.5,<3
   pydantic-core>=2.14,<3
   thinc>=8.2,<9
   ```

   Bumping `spacy` past `<3.8` means re-checking that pydantic and
   pydantic-core still line up with what the new spaCy minor declares
   in its metadata.  The model wheel URL in the README install
   command must match the spaCy minor too — `en_core_web_sm-3.7.1`
   pairs with spaCy 3.7.x.

5. **`run_gui.py` is the entry point referenced by the spec.**
   The spec hardcodes `["../run_gui.py"]` as `Analysis.scripts`.
   If anyone renames the entry script, the spec needs to follow.

6. **Smoke-import the spec file with Python's parser.**  Catches
   any local edit that broke the spec's syntax.  A real PyInstaller
   build would do this anyway, but failing here is much cheaper than
   waiting for the Windows machine to fail it:

   ```bash
   python3 -c "import ast; ast.parse(open('packaging/DocumentDataExtractor.spec').read()); print('spec syntax OK')"
   ```

7. **End-to-end smoke through the CLI.**  This exercises the same
   modules the bundled exe will exercise, just on the dev machine:

   ```bash
   python3 -m requirements_extractor.cli requirements \
       samples/procedures/simple_two_actors.docx \
       -o /tmp/preflight.xlsx --emit json,md,reqif
   ```

   Should produce four files under `/tmp/` and exit `0`.  If this
   fails, the bundle will fail the same way — fix it here first.

If all seven steps pass, the bundle is as ready as a sandbox-side
check can make it.  Ship it to the Windows machine and follow the
build/smoke procedure above.
