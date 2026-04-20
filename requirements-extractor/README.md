# Requirements Extractor

A small Python tool that reads one or more Word documents (`.docx`) and pulls out anything that looks like a requirement — shall/must/will/required statements (plus softer should/may/can items flagged for human review) — into a single tidy Excel workbook.

Each row in the output workbook is one requirement, with columns for traceability (file, section, table/row), the primary actor (from the first column of the 2-column table), any secondary actors referenced in the text, the requirement itself, and the matched keywords.

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

That installs `python-docx` (for reading Word files) and `openpyxl` (for writing Excel files).

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

A window opens. Add one or more `.docx` files (or a whole folder), optionally point at an actors list, choose where to save the output, and click **Run extraction**. Progress shows in the log area; when it's done you'll see a summary dialog.

> Tip for Windows users: rename `run_gui.py` to `run_gui.pyw` to suppress the background console window when you double-click.

### B. The command line

From the same folder, with the venv active:
```
python extract.py PATH_TO_DOCUMENT.docx -o output.xlsx
```

More examples:
```
# Process every .docx in a folder (recursively)
python extract.py C:\Projects\Specs -o specs.xlsx

# Multiple files, with an actors list
python extract.py spec_a.docx spec_b.docx -o combined.xlsx --actors actors.xlsx

# Include the spaCy NER pass
python extract.py spec.docx -o out.xlsx --nlp

# Also export a statement-set CSV (hierarchical paired-level format)
python extract.py spec.docx -o out.xlsx --statement-set statement_set.csv
```

Run `python extract.py --help` to see every option.

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

## Statement-set CSV (optional second output)

The Excel workbook is the primary output, but the tool can *also* export the extracted content to a "statement set" CSV matching a specific paired-column template (`Level 1, Description 1, Level 2, Description 2, …`). Each row fills exactly one `(Level N, Description N)` pair and leaves the others blank, so the file opens as a pre-order-flattened hierarchy:

| Level     | What it is                                                                                  | Example                                     |
|-----------|---------------------------------------------------------------------------------------------|---------------------------------------------|
| Level 1   | Top document heading (most recent Heading 1 above the section).                             | `System Requirements`                       |
| Level 2   | Section-style row from the 2-col table — title in Level 2, intro paragraph in Description 2. | `3.1 Authentication` / `Access control is…` |
| Level 3   | One row per requirement. `Level 3` = `"<Actor> <N>"`; `Description 3` = `"<Actor>\n\n<text>"`. | `Auth Service 1` / `Auth Service\n\nThe Auth Service shall…` |

A table row is treated as a **section** (Level 2) when its first-column text starts with a numeric prefix like `3.1 …` or `3.1.2 …`. Anything else is treated as an **actor** row, and its requirements become Level 3 children of the most recent section. The `Level 3` counter restarts per `(section, actor)` pair, so you get `Auth Service 1…6` under `3.1 Authentication`, then `Flight Software 1…3` and `Ground Control 1…2` under `3.2 Telemetry`, and so on.

Enable the export:

- **CLI:** add `--statement-set PATH.csv`
- **GUI:** tick "Also export to statement-set CSV" in section 5 and pick a save path

Notes on the statement-set output:

- Preamble prose (content before the document's first Heading 1) is *not* exported to the statement set — it's rarely a real requirement. Those rows still appear in the Excel workbook for review.
- The header includes the final `Level #, Description #` placeholder pair to match the template exactly. If your docs ever nest deeper than four levels, raise `_MAX_LEVEL` in `requirements_extractor/statement_set.py`.
- Text is preserved faithfully from the source. If your H1 is literally `3. System Requirements`, that's what appears at Level 1 — the tool doesn't strip numeric prefixes.

## Output workbook

Two sheets:

**Requirements** — one row per detected requirement:

| Column           | What it is                                                                                  |
|------------------|---------------------------------------------------------------------------------------------|
| #                | Global order of appearance across all processed docs.                                       |
| Source File      | The document filename.                                                                      |
| Heading Trail    | Nearest H1 > H2 > H3 above the requirement.                                                 |
| Section / Topic  | Text from column 1 of the 2-column table row.                                               |
| Row Ref          | e.g. `Table 2, Row 4` — traces back to the row in the doc.                                  |
| Block Ref        | Where inside column 2 it came from (e.g. `Paragraph 2`, `Bullet 3`, `Nested Table 1 R2C1`). |
| Primary Actor    | Same as Section / Topic (i.e., the row's column-1 actor).                                   |
| Secondary Actors | Other known actors mentioned in the requirement text.                                       |
| Requirement      | The requirement sentence or item.                                                           |
| Type             | `Hard` (binding keywords) or `Soft` (advisory — yellow-highlighted).                        |
| Keywords         | Which trigger words matched.                                                                |
| Confidence       | High / Medium / Low — a rough heuristic, not a guarantee.                                   |
| Notes            | Flags for the reviewer (e.g. "verify soft language").                                       |

**Summary** — quick totals and a breakdown by primary actor.

The header row is frozen, autofilters are enabled, and soft rows are shaded yellow so they're easy to batch-review.

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
python -m spacy download en_core_web_sm
pip install -r packaging\build-requirements.txt
```

That installs everything the tool needs plus PyInstaller.

### Build

```bat
packaging\build.bat
```

You'll find the result at:

```
dist\RequirementsExtractor.exe
```

Copy that single file anywhere — desktop, network share, Teams — and double-click to launch. No Python install required on the target machine.

### Rebuilding after code changes

Just re-run `packaging\build.bat`. It cleans the previous `build/` and `dist/` folders before rebuilding, so you always get a fresh artifact.

### Troubleshooting the build

- **"ModuleNotFoundError" at runtime for some spaCy submodule** — add the missing module name to the `_bundle("...")` list at the top of `packaging/RequirementsExtractor.spec` and rebuild.
- **"en_core_web_sm not found" at runtime** — you forgot `python -m spacy download en_core_web_sm` in the build venv. The spec collects the model at build time; if it's not installed, the bundled exe won't have it.
- **Exe is huge** — that's spaCy + its model. If you don't need the NLP feature, remove every entry in the `for _pkg in (...)` block of the spec except the first block; the exe will drop to around 60 MB.
- **Exe launches then closes immediately** — rebuild with `console=True` in the spec so you can see the error traceback, fix it, then switch back to `console=False`.

### macOS / Linux builds

`packaging/build.sh` does the equivalent build on macOS or Linux (produces a `.app` bundle on Mac or a single binary on Linux). Same limitations apply — you must build on the OS you want to target.

## Tuning

- **Keyword lists** live in `requirements_extractor/detector.py` (`HARD_KEYWORDS`, `SOFT_KEYWORDS`). Add your org's house terms.
- **Confidence heuristic** is in the same file — it's intentionally simple and meant to be edited.
- **Output columns / formatting** live in `requirements_extractor/writer.py`.

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
requirements-extractor/
├── README.md                          (this file)
├── requirements.txt                   (core Python deps)
├── requirements-optional.txt          (optional spaCy deps)
├── extract.py                         (CLI shortcut)
├── run_gui.py                         (GUI shortcut)
├── packaging/                         (PyInstaller build config)
│   ├── RequirementsExtractor.spec
│   ├── build.bat                      (Windows build)
│   ├── build.sh                       (macOS/Linux build)
│   └── build-requirements.txt
├── samples/                           (sample files for testing)
└── requirements_extractor/
    ├── __init__.py
    ├── models.py                      (dataclasses + event types)
    ├── detector.py                    (hard/soft keyword classifier)
    ├── actors.py                      (primary + secondary actor resolution)
    ├── parser.py                      (walks the .docx into an event stream)
    ├── writer.py                      (writes the .xlsx output)
    ├── statement_set.py               (writes the statement-set .csv output)
    ├── extractor.py                   (orchestrator)
    ├── cli.py                         (command-line interface)
    └── gui.py                         (Tkinter GUI)
```
