# Document Data Extractor

A small Python tool that pulls structured data out of Word documents (`.docx`).

It has two modes:

- **Requirements mode** (the original use case) — reads one or more specs and pulls out anything that looks like a requirement — shall/must/required statements (plus softer should/may/can/will items flagged for human review) — into a single tidy Excel workbook. It also flags **negative requirements** ("shall not", "must not", "can't") so prohibitions don't get lost in a long list of obligations.
- **Actors mode** — skips requirement detection entirely and harvests a canonical actors list from the document corpus, producing an `.xlsx` that can be fed straight back into the requirements run as `--actors`.

In requirements mode, each row in the output workbook is one requirement, with columns for traceability (file, section, table/row), the primary actor (from the first column of the 2-column table), any secondary actors referenced in the text, the requirement itself, and the matched keywords.

(The Python package is still called `requirements_extractor` internally — the rename is surface-level so existing imports and scripts keep working.)

---

## What this tool expects from your documents

- A header region at the top of the document.
- One or more large **2-column tables**, where:
  - Column 1 contains the section title, topic, or actor.
  - Column 2 contains the content — paragraphs, nested tables, bullet lists.
- Standard Word heading styles (Heading 1, Heading 2, …) are captured as a "heading trail" so you can find each requirement in the original doc.

The tool won't catch 100% of requirements — wording varies and some items genuinely need a human eye — so soft-language matches are highlighted in yellow for review. You can tune the keyword lists in `requirements_extractor/detector.py`.

---

## Setup from the ground up

Aimed at teammates who haven't done much Python before. You only need to do this once.

### 1. Install Python

- Download Python 3.10 or newer from https://www.python.org/downloads/
- On Windows, during install, **tick "Add python.exe to PATH"** on the first screen. This matters.
- Verify: open a new terminal (Command Prompt / PowerShell on Windows, Terminal on macOS) and run
  ```
  python --version
  ```
  You should see something like `Python 3.12.0`.

### 2. (Recommended) Install a code editor

Visual Studio Code is a good free choice: https://code.visualstudio.com/
Install the **Python extension** from Microsoft once VS Code is open (Extensions sidebar → search "Python").

You don't strictly need an editor to run the tool, but it helps when peeking at the source or tweaking keyword lists.

### 3. Get the tool

Copy the whole `requirements-extractor/` folder into your working area. If you're using Git, you can clone the parent `work-tools/` repo instead.

### 4. Create a virtual environment (one-time, per machine)

A virtual environment ("venv") keeps this tool's libraries separate from anything else on your machine.

Open a terminal **inside the `requirements-extractor/` folder** and run:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

Once activated, your prompt will show `(.venv)` at the start. Every time you open a new terminal to work on this tool, repeat the `activate` step.

### 5. Install the required libraries

With the venv active:
```
pip install -r requirements.txt
```

That installs `python-docx` (for reading Word files), `openpyxl` (for writing Excel files), and `PyYAML` (for optional config files).

### 6. (Optional) Install the NLP add-on

Only needed if you want the tool to auto-detect secondary actors via spaCy's named-entity recognition:
```
pip install -r requirements-optional.txt
python -m spacy download en_core_web_sm
```

---

## Running the tool

There are two ways to run it. Both do the same work under the hood — pick whichever is easier.

### A. The GUI (easier for non-developers)

From the `requirements-extractor/` folder, with the venv active:
```
python run_gui.py
```

A window opens. Pick **Extraction mode** (Requirements or Actors) at the top, add one or more `.docx` files (or a whole folder), optionally point at an actors list, choose where to save the output, and click **Run**. A determinate progress bar tracks the per-file progress and a **Cancel** button can stop the run between files. When it finishes, the output file opens automatically (disable via the "Open output file when the run finishes" checkbox). The statement-set section is only active in Requirements mode and greys out automatically when you switch to Actors mode.

**Bonus conveniences:**

- **Drag-and-drop** — drop `.docx` files or folders directly onto the input list. Requires `pip install tkinterdnd2` (optional — the UI degrades to buttons if it isn't installed).
- **Save actors template\u2026** — click this button in the Actors section to generate a ready-to-fill `actors_template.xlsx` instead of hand-rolling one.
- **Auto-actors** — in Options, tick "Run actor scan first and use its output as the actors list" to harvest actors from the same inputs before the requirements pass, without having to maintain a separate `actors.xlsx`. The harvested list is written as a sidecar next to your output (`<output_stem>_auto_actors.xlsx`) so you can inspect and reuse it later.
- **Keywords field** — next to **Config file**, the Options section now has a **Keywords** field for a standalone keywords file (`.yaml` / `.yml` / `.txt` / `.kw`) that tweaks just the HARD/SOFT lists. See "Keywords file" below.
- **Actors mode** — switch the top radio to "Actors" to run the parser across your inputs and produce a ready-to-use actors workbook from what the documents actually contain. See the "Actors mode" section below.
- **Remembered settings** — window size, last-used paths (including the Keywords field), checkbox states (including auto-actors), and the last-used mode are persisted to `~/.requirements_extractor/settings.json` and restored next launch.

> Tip for Windows users: rename `run_gui.py` to `run_gui.pyw` to suppress the background console window when you double-click.

### B. The command line

The CLI is subcommand-based: `document-data-extractor <MODE> [args]`.  The entry point is `extract.py` for the moment; the legacy flag-style invocation still works — it's transparently routed to the `requirements` subcommand.

From the same folder, with the venv active:

```
# Requirements mode (explicit subcommand)
python extract.py requirements PATH_TO_DOCUMENT.docx -o output.xlsx

# Requirements mode (legacy flag-style — auto-routed for backward compatibility)
python extract.py PATH_TO_DOCUMENT.docx -o output.xlsx
```

More examples:
```
# Process every .docx in a folder (recursively)
python extract.py requirements C:\Projects\Specs -o specs.xlsx

# Multiple files, with an actors list
python extract.py requirements spec_a.docx spec_b.docx -o combined.xlsx --actors actors.xlsx

# Include the spaCy NER pass
python extract.py requirements spec.docx -o out.xlsx --nlp

# Also export a statement-set CSV (hierarchical paired-level format)
python extract.py requirements spec.docx -o out.xlsx --statement-set statement_set.csv

# Dry-run — parse and count without writing anything, great for
# iterating on a config or previewing a new corpus
python extract.py requirements spec.docx --dry-run --show-samples 5

# Auto-actors — harvest the actors list from the same inputs first,
# then use it for the requirements run.  Saves maintaining a
# separate actors.xlsx.  The harvested list is written as a sidecar
# <output_stem>_auto_actors.xlsx next to your output.
python extract.py requirements C:\Projects\Specs --auto-actors -o out.xlsx

# Tweak just the HARD/SOFT keyword buckets via a standalone YAML,
# without writing a full --config.  See "Keywords file" below.
python extract.py --keywords house_style.yaml requirements spec.docx

# Actors mode — build an actors list from a corpus instead of
# extracting requirements.  Output round-trips into --actors.
python extract.py actors C:\Projects\Specs -o actors_scan.xlsx

# Aliases: `reqs` for requirements, `scan` for actors.
python extract.py reqs spec.docx -o out.xlsx
python extract.py scan C:\Projects\Specs -o actors.xlsx
```

Run `python extract.py --help` to see every option, or `python extract.py requirements --help` / `python extract.py actors --help` for mode-specific flags (each has its own Examples block in the help output).

**Exit codes** — scripted callers can rely on:

- `0` — success (also returned for a clean `--dry-run`).
- `1` — runtime error the user can fix (corrupt `.docx`, bad config, I/O error, permission denied on the output path).
- `2` — usage error (missing inputs, unknown flags, no subcommand given).
- `130` — interrupted by the user (SIGINT / Ctrl-C).

---

## Actors mode

The requirements run detects requirements as its main job and tracks actors as a side effect. If you're bootstrapping an actors list — or auditing an existing corpus for the actors it actually mentions — you can skip requirement detection entirely and just harvest actors.

CLI:
```
python extract.py actors C:\Projects\Specs -o actors_scan.xlsx

# With a seed — preserves your canonical names verbatim and only
# adds new spellings discovered in the corpus as aliases.
python extract.py actors C:\Projects\Specs --actors seed.xlsx -o actors_scan.xlsx
```

GUI: switch the top radio to **Actors**, choose an output path in section 5, then click **Run**.

What you get: an `.xlsx` with three sheets. The **Actors** sheet has the exact `Actor` / `Aliases` column layout that `--actors` consumes on a requirements run, plus diagnostic columns (count, files, first seen, sources) that the loader ignores. The **Observations** sheet lists every raw sighting so false positives are easy to audit. The **Readme** sheet explains the workflow.

The typical flow is:

1. Run actors mode on your corpus.
2. Open the output, rename canonicals, delete rows for false positives, merge aliases.
3. Save it and pass it as `--actors your_actors.xlsx` on the next requirements run.
4. Optionally: re-run actors mode with `--actors your_actors.xlsx` as a seed as the corpus grows — the seeded canonicals are preserved verbatim and only new spellings get added as aliases.

This complements the **Save actors template…** button in the GUI: *template* creates a blank file to fill in by hand; *actors mode* creates one pre-populated from your documents.

---

## The actors list (optional)

Secondary actors — characters/roles/teams/systems that are referenced in a requirement but aren't the row's primary actor — are found by looking for known names in the requirement text.

Create a simple Excel file with one row per actor:

| Actor                | Aliases                                |
|----------------------|----------------------------------------|
| Ground Control       | GCS, Mission Control                   |
| Payload Operator     | Payload Op, PL Op                      |
| Flight Software      | FSW, Onboard Software                  |

- **Actor** (required) — the canonical name you want to see in the output.
- **Aliases** (optional) — a comma-separated list of alternate spellings.

Pass it with `--actors actors.xlsx` (CLI) or via the "Actors list" field in the GUI. Matching is case-insensitive and word-boundary aware, so "Ground Control" won't accidentally match "ground-controlled approach".

---

## Config file (optional) — hint at the document format

The extractor makes reasonable guesses by default (2-column tables, numeric section prefixes, a fixed keyword list). A YAML config file lets you tailor those guesses per project or per document when the defaults grab garbage. Nothing is mandatory — every field falls back to a built-in default if omitted.

### How configs are loaded

There are two loading modes and they stack:

1. **Per-run** — one config applies to the whole batch.
   - CLI: `python extract.py spec.docx -o out.xlsx --config my.yaml`
   - GUI: "Config file" field (section 3).
2. **Per-document** — automatic. Drop a file named `<docstem>.reqx.yaml` (or `.reqx.yml`) next to a `.docx` and the tool picks it up for just that file.
   ```
   specs/
     payload.docx
     payload.reqx.yaml    ← auto-loaded when payload.docx is processed
     flight.docx
   ```

When both exist, the per-doc config overrides the per-run config key-by-key. Mappings merge; lists and scalars replace wholesale. (So a per-doc `skip_sections.titles: [Glossary]` *replaces* the per-run list — it does not append.)

### Supported keys

See `samples/sample_config.yaml` for a fully commented example. At a glance:

```yaml
version: 1

skip_sections:
  titles: [Revision History, References, Glossary]
  table_indices: [1]          # 1-based

tables:
  actor_column:   1
  content_column: 2
  min_columns:    2
  max_columns:    2
  section_prefix: '^\s*(?:[A-Z]{1,4}[-.]?)?\d+(?:\.\d+)*[.)]?\s+\S'

keywords:
  hard_add:    [is responsible for]
  hard_remove: [will]         # drop noisy future-tense matches
  soft_add:    []
  soft_remove: []

content:
  skip_if_starts_with: ["Note:", "Example:", "See also:"]
  skip_pattern: null          # optional regex; matches -> drop
  require_primary_actor: false

parser:
  recursive: true             # walk nested tables of arbitrary depth
```

What each section does:

- **skip_sections** — drop whole rows (by first-column text match) or whole tables (by 1-based index) before parsing.
- **tables** — where the actor and content columns live, what counts as a requirements table, and the regex that flags a section-header row. The default `section_prefix` handles numeric (`3.1`), dotted (`3.1.2`), and alphanumeric (`SR-1.2`, `A.1`, `REQ-042`) schemes.
- **keywords** — add house terms (multi-word phrases are fine) or remove built-ins that misfire. `will` is SOFT by default (future-tense prose trips it easily, so matches are yellow-highlighted for review rather than treated as binding). If your house style treats "will" as equivalent to "shall", use `keywords: {hard_add: [will], soft_remove: [will]}`; if you want "will" ignored entirely, use `keywords: {soft_remove: [will]}`.
- **content** — drop candidate sentences by leading text, by regex, or when no primary actor is available.
- **parser.recursive** — when `true` (default) the walker descends into nested tables of any depth and emits dotted block refs. Flip to `false` for the legacy one-level-deep behaviour.

Unknown keys are rejected up front with a clear error message so typos don't silently do nothing.

---

## Keywords file (optional) — tune the HARD/SOFT lists without a full config

Sometimes all you want to change is which modal words count as binding ("hard") vs advisory ("soft"). Authoring a whole `--config` for that is overkill, so the tool also accepts a **standalone keywords file** via `--keywords PATH` (CLI) or the "Keywords" field in the GUI. `.yaml`, `.yml`, `.txt`, and `.kw` extensions are all accepted.

Two schemas are supported — mix them across buckets freely, but don't combine the "replace" and "tweak" forms for the *same* bucket:

**Tweak the built-ins (most common):**

```yaml
hard_add:    [is to, are to]    # extra hard keywords beyond the defaults
hard_remove: [will]             # drop noisy hard matches
soft_add:    [anticipated, expected to]
soft_remove: []
```

The built-in HARD list is `shall`, `must`, `required`, `mandatory`. The built-in SOFT list is `should`, `may`, `might`, `can`, `could`, `will`, `recommended`, `preferred`, `ought to`.

**Replace a bucket wholesale** (for house styles narrower than the defaults):

```yaml
hard: [shall, must]
soft: [should, may]
```

Anything not listed collapses to "not a requirement". Mixing `hard` with `hard_add`/`hard_remove` in the same file is rejected with a clear error since the two intents contradict each other.

The text format (`.txt` / `.kw`) uses `[section]` markers for non-YAML users:

```
[hard_add]
is to
are to
[hard_remove]
will
```

A fully-commented example lives at `samples/sample_keywords.yaml`. The keywords file layers *on top of* `--config` if both are provided; a per-doc `<stem>.reqx.yaml` still wins over both.

---

## Statement-set CSV (optional second output)

The Excel workbook is the primary output, but the tool can *also* export the extracted content to a "statement set" CSV matching a specific paired-column template (`Level 1, Description 1, Level 2, Description 2, …`). Each row fills exactly one `(Level N, Description N)` pair and leaves the others blank, so the file opens as a pre-order-flattened hierarchy.

The writer maps your document structure onto paired columns like this:

| Level     | What it is                                                                                  |
|-----------|---------------------------------------------------------------------------------------------|
| Level 1   | Most recent **Heading 1** above the section.                                                |
| Level 2   | Most recent **Heading 2** — or, if the doc has no H2, a section-style row from the 2-col table that sits directly under an H1. |
| Level 3   | Most recent **Heading 3** (when H2 is also present) — or a section-style 2-col-table row (when an H2 was seen) — or the requirement itself (degenerate case). |
| Level 4+  | Deeper structure and the requirement row as the document demands.                           |

A table row is treated as a **section** when its first-column text starts with a recognised prefix like `3.1 …` or `3.1.2 …` (see the `tables.section_prefix` regex in the config docs). Anything else is treated as an **actor** row, and its requirements become children one level below the deepest structural anchor. The requirement's level counter restarts per `(section_scope, actor)` pair, so you get `Auth Service 1…6` under `3.1 Authentication`, then `Flight Software 1…3` and `Ground Control 1…2` under `3.2 Telemetry`, and so on.

Enable the export:

- **CLI:** add `--statement-set PATH.csv`
- **GUI:** tick "Also export to statement-set CSV" in section 5 and pick a save path

Notes on the statement-set output:

- **Preamble prose** (content before any recognised section / heading) is now routed into a synthetic `(preamble)` Level-2 bucket rather than being dropped, so every extracted requirement still reaches the CSV. Review those rows and promote them into a real section as part of your workflow. Requirements that have *no* structural context at all (a document with no H1, no H2, no section rows) also land under `(preamble)` so nothing is silently lost.
- **H2/H3 plumbing**: if your spec uses Heading 2 / Heading 3 as structure (instead of only H1 + table sections), the writer now respects that — H2 lands at L2, H3 at L3. If the document skips H2 and goes straight to H3, the H3 is emitted at L2 directly rather than inventing a missing level.
- The header row spans five `Level N / Description N` pairs plus a final `Level # / Description #` placeholder pair to match the template exactly. The requirement level is clamped at five so a runaway nesting doesn't blow past the template width.
- Text is preserved faithfully from the source. If your H1 is literally `3. System Requirements`, that's what appears at Level 1 — the tool doesn't strip numeric prefixes.

## Output workbook

Two sheets:

**Requirements** — one row per detected requirement:

| Column           | What it is                                                                                  |
|------------------|---------------------------------------------------------------------------------------------|
| #                | Global order of appearance across all processed docs.                                       |
| ID               | Stable requirement identifier (`REQ-<8hex>`) — survives unrelated upstream churn. See "Stable requirement IDs" below. |
| Source File      | The document filename.                                                                      |
| Heading Trail    | Nearest H1 > H2 > H3 above the requirement.                                                 |
| Section / Topic  | Text from column 1 of the 2-column table row.                                               |
| Row Ref          | e.g. `Table 2, Row 4` — traces back to the row in the doc.                                  |
| Block Ref        | Where inside column 2 it came from (e.g. `Paragraph 2`, `Bullet 3`, `Nested Table 1 R2C1`). |
| Primary Actor    | Same as Section / Topic (i.e., the row's column-1 actor).                                   |
| Secondary Actors | Other known actors mentioned in the requirement text.                                       |
| Requirement      | The requirement sentence or item.                                                           |
| Type             | `Hard` (binding keywords) or `Soft` (advisory — yellow-highlighted).                        |
| Polarity         | `Positive` or `Negative` — whether a modal keyword is immediately negated ("shall not", "must not", "may never", "can't"). Negative rows are shaded light red and win over the Soft yellow so prohibitions stand out during review. |
| Keywords         | Which trigger words matched.                                                                |
| Confidence       | High / Medium / Low — a rough heuristic, not a guarantee.                                   |
| Notes            | Flags for the reviewer (e.g. "verify soft language").                                       |

**Summary** — quick totals and a breakdown by primary actor.

The header row is frozen, autofilters are enabled, soft rows are shaded yellow, and negative (prohibition) rows are shaded light red so both categories are easy to batch-review. A negative-polarity soft row is still shown red — prohibitions take priority because missing one is higher-risk than missing an advisory.

---

## Stable requirement IDs

Every requirement gets a stable `REQ-<8hex>` identifier (column **ID** in the workbook). It's derived from three fields that define the requirement's identity: the source filename, the primary actor, and the requirement text itself (whitespace-collapsed and case-folded first, so cosmetic reformatting doesn't churn the ID). Inserting a paragraph upstream, re-numbering a section, or renaming a table won't change anyone's ID — the three inputs are unchanged.

If two rows somehow end up with identical `(file, actor, text)` — real corpora do have duplicated boilerplate — the second and later occurrences get a numeric suffix (`REQ-abc12345-1`, `REQ-abc12345-2`) in first-seen order so every row still has a unique handle while the shared prefix stays greppable.

The ID is only meant for cross-document referencing in reviews and change-tracking; it's intentionally not a global registry. If you rename the source file or edit the requirement's wording, the ID changes — that's working as intended (the two versions really are different requirements).

---

## Dry run

`--dry-run` on a requirements invocation runs the full parse + detect + ID-assignment pipeline and prints the usual summary, but skips writing the Excel workbook and any statement-set CSV. It pairs well with `--show-samples N`, which prints the first N detected requirements as a one-line preview:

```
python extract.py requirements spec.docx --dry-run --show-samples 5
```

Use it when you're iterating on a YAML config, evaluating a new corpus, or just want to know how many requirements a new file will produce before you overwrite a previous result.

The GUI surfaces the same behaviour as a **Dry run — parse & count but don't write any files** checkbox in section 4 (Options). When ticked, the Run button still parses and reports counts in the log/done dialog, but no files are written and the auto-open-on-done step is skipped.

---

## Packaging to a Windows .exe (optional)

If you want to hand this tool to a non-technical teammate without making them install Python at all, you can package it into a single-file Windows executable using **PyInstaller**. A ready-to-use spec file and build scripts live in the `packaging/` folder.

**Important up front:**

- A Windows `.exe` has to be built **on a Windows machine**. You can't cross-build from macOS or Linux.
- The bundle includes Python + python-docx + openpyxl + spaCy + the English model + Tkinter. Expect the final exe to be around 300–450 MB.
- Single-file exes take a few seconds to start on first launch (Windows unpacks them into a temp folder on each run). Subsequent launches are faster.
- Windows SmartScreen or corporate antivirus may flag the exe because it's unsigned. This is a known PyInstaller issue, not a problem with your code. Options: (a) right-click → Properties → Unblock, (b) add an exclusion in your AV, or (c) buy a code-signing certificate for production distribution.

### One-time setup on the Windows build machine

From inside the `requirements-extractor/` folder:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -r requirements-optional.txt
pip install -r packaging\build-requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
```

That installs everything the tool needs plus PyInstaller and the English spaCy model.

> **Why the explicit model wheel?** `python -m spacy download en_core_web_sm` works fine on a connected developer machine, but it funnels through spaCy's download CLI and depends on that CLI being able to reach `github.com` through whatever proxy the build machine has. Installing the wheel directly (the URL above) skips that layer and pins the exact model version, so builds on two different machines produce byte-identical NLP data. If a future spaCy version requires a newer model, bump the `3.7.1` in the URL to match.

### Build

```bat
packaging\build.bat
```

You'll find the result at:

```
dist\DocumentDataExtractor.exe
```

Copy that single file anywhere — desktop, network share, Teams — and double-click to launch. No Python install required on the target machine.

### Rebuilding after code changes

Just re-run `packaging\build.bat`. It cleans the previous `build/` and `dist/` folders before rebuilding, so you always get a fresh artifact.

### Troubleshooting the build

- **"ModuleNotFoundError" at runtime for some spaCy submodule** — add the missing module name to the `_bundle("...")` list at the top of `packaging/DocumentDataExtractor.spec` and rebuild.
- **"en_core_web_sm not found" at runtime** — you forgot the `pip install https://.../en_core_web_sm-3.7.1-py3-none-any.whl` step in the build venv (see the "One-time setup" block above). The spec collects the model at build time; if it's not installed, the bundled exe won't have it.
- **Exe is huge** — that's spaCy + its model. If you don't need the NLP feature, remove every entry in the `for _pkg in (...)` block of the spec except the first block; the exe will drop to around 60 MB.
- **Exe launches then closes immediately** — rebuild with `console=True` in the spec so you can see the error traceback, fix it, then switch back to `console=False`.

### macOS / Linux builds

`packaging/build.sh` does the equivalent build on macOS or Linux (produces a `.app` bundle on Mac or a single binary on Linux). Same limitations apply — you must build on the OS you want to target.

### Bundling for a restricted network (no spaCy install on the target)

If the machine where the tool actually runs can't install spaCy — common on corporate or air-gapped networks — the bundled exe is the supported path. The build machine needs internet once (to fetch spaCy + the model wheel into its build venv), after which the produced exe is fully self-contained and has no install-time network dependency on the target.

The flow is the same as the "One-time setup" above; the things worth calling out specifically:

1. **Pin the model wheel URL, don't use `spacy download`.** The URL in the setup block above pins `en_core_web_sm-3.7.1` so two build machines produce identical bundles. If the target-network software-approval process asks for a SHA-256 attestation, hash the produced exe after the build and record it alongside the release.
2. **Verify `ActorResolver.has_nlp()` returns True in the bundled exe before shipping.** A silent NLP downgrade is the worst failure mode because the tool appears to work. Smoke test: run the bundled exe against one sample doc with "Use NLP" ticked and grep the log for `NLP unavailable`; if it's absent, NLP loaded cleanly.
3. **Distribute the exe via whatever channel the target network accepts.** The bundle has no install-time network calls, so a shared drive or signed installer both work.
4. **AV / SmartScreen.** The spec already disables UPX (`upx=False`) because that's the #1 trigger for AV quarantine on PyInstaller single-file exes. If the target network's AV still flags the artifact, fall back to `--onedir` layout (edit the spec) or buy a code-signing certificate.
5. **Rebuild cadence.** Regenerate the bundle whenever `requirements-optional.txt`, `packaging/DocumentDataExtractor.spec`, or any file under `requirements_extractor/` changes. Without CI this is a manual gate, so add it to the release checklist.

## Tuning

Most tuning should happen through a **config file** (see the "Config file" section above) so you don't have to edit source. When that's not enough:

- **Default keyword lists** live in `requirements_extractor/detector.py` (`HARD_KEYWORDS`, `SOFT_KEYWORDS`). Config `keywords.hard_add`/`hard_remove` are layered on top of these.
- **Confidence heuristic** is in the same file — it's intentionally simple and meant to be edited.
- **Output columns / formatting** live in `requirements_extractor/writer.py`.
- **Config schema** lives in `requirements_extractor/config.py` — add a new key there if you need one that isn't already supported.

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'docx'`** — you forgot to activate the venv, or forgot `pip install -r requirements.txt`.
- **"NLP requested but spaCy … is not available"** — install the optional deps (step 6).
- **A requirement was missed** — check the wording. If your team uses different modal words, add them to the keyword lists.
- **A non-requirement was picked up** — it probably contained one of the keywords in passing. You can delete the row in Excel, or make the keyword list stricter.
- **Word lock files (`~$something.docx`)** — these are skipped automatically.

---

## Project layout

```
requirements-extractor/                (folder name — Python pkg kept for compat)
├── README.md                          (this file)
├── requirements.txt                   (core Python deps)
├── requirements-optional.txt          (optional spaCy deps)
├── extract.py                         (CLI shortcut — legacy flag-style still works)
├── run_gui.py                         (GUI shortcut)
├── packaging/                         (PyInstaller build config)
│   ├── DocumentDataExtractor.spec
│   ├── build.bat                      (Windows build)
│   ├── build.sh                       (macOS/Linux build)
│   └── build-requirements.txt
├── samples/                           (sample files for testing)
└── requirements_extractor/            (Python package — import path unchanged)
    ├── __init__.py
    ├── models.py                      (dataclasses + event types)
    ├── detector.py                    (hard/soft keyword classifier)
    ├── actors.py                      (primary + secondary actor resolution)
    ├── actor_scan.py                  (actors-only extraction mode)
    ├── parser.py                      (walks the .docx into an event stream)
    ├── writer.py                      (writes the .xlsx output)
    ├── statement_set.py               (writes the statement-set .csv output)
    ├── extractor.py                   (orchestrator for requirements mode)
    ├── cli.py                         (subcommand CLI — document-data-extractor)
    ├── gui.py                         (Tkinter GUI)
    └── gui_state.py                   (Tk-free settings/helpers)
```
