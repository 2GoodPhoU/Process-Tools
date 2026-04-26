# Plan: Unified Process-Tools GUI

**Status:** APPROVED, awaiting execution.
**Drafted:** 2026-04-25.
**Owner:** Eric (kicks off in a fresh session).
**Estimated effort:** 4-6 focused sessions across Phases 1-4.
**Prerequisites:** working tree from 2026-04-25 refactor pass committed
(see `COMMIT_PLAN.md`); 600 tests green via `.\scripts\test_all.ps1`.

---

## Why this plan exists

The four Process-Tools components form a clear pipeline -- DDE feeds
Compliance Matrix and Nimbus Skeleton, both of which produce
deliverables Eric hands to customers -- but only DDE has a GUI today.
Compliance Matrix and Nimbus Skeleton are CLI-only, which means a
process modeler running the full pipeline has to manually copy xlsx
paths between three command invocations. That friction is the target
of this work.

Architecture goals (the "seamless UX" requirements from the design
discussion):

1. **Pipeline awareness** -- when DDE finishes, the other tabs offer
   to use that xlsx with one click.
2. **Stale-output detection** -- if a DDE input changes after a
   downstream tab consumed it, the tab surfaces "input has changed".
3. **Single shared log pane** -- everything that happens this session
   shows up in one log, not three.
4. **Single PyInstaller exe** -- one bundle replacing three for
   restricted-network distribution.
5. **Independent tab usability** -- a reviewer who only wants
   Compliance Matrix shouldn't see DDE's options.

---

## Architecture decisions (locked, do not re-litigate)

These were chosen via AskUserQuestion on 2026-04-25 with full
trade-off context. If a fresh session hits a blocker that would
require revisiting one of these, ask Eric explicitly before
deviating.

| Decision                     | Choice                                          | Why                                                                 |
|------------------------------|-------------------------------------------------|---------------------------------------------------------------------|
| GUI location                 | Stay in `requirements-extractor/`               | Zero migration cost; PyInstaller spec keeps working with extension. |
| Tool-run mechanism           | In-process via `cli.main([...])` from worker    | No 0.5-1s startup; consistent with existing DDE GUI; shared log.    |
| Refactor scope               | Aggressive -- full split into widgets + workflows | Smaller net diff over Phases 1-4; cleaner copy-pattern for new tabs. |

---

## Target file layout (post-Phase-1)

```
requirements-extractor/requirements_extractor/
  gui.py                           ← slim app shell (~150 lines):
                                     ProcessToolsApp class, builds Tk root,
                                     ttk.Notebook, menu, shared log pane,
                                     adds DDEWorkflow as the first tab.
                                     main() entry point preserved at this
                                     name so the existing PyInstaller spec
                                     keeps working.

  gui_widgets.py                   ← reusable widgets (~250 lines):
                                     FileListPicker (multi-file picker
                                     with optional drag-drop), LogPane
                                     (ScrolledText wrapper with .log() /
                                     .clear()), RunBar (Run + Cancel +
                                     status label + progress bar),
                                     OptionRow (label + control + tooltip).

  gui_workflow_dde.py              ← DDE-specific tab (~700 lines):
                                     class DDEWorkflow(parent: ttk.Frame).
                                     This is most of the current
                                     ExtractorApp body, restructured to
                                     compose the widgets from gui_widgets.py.
                                     All the _build_*_section methods live
                                     here; the run/cancel logic lives here;
                                     mode-handling lives here.

  gui_workflow_compliance.py       ← (new in Phase 2) Compliance Matrix tab.
  gui_workflow_nimbus.py           ← (new in Phase 3) Nimbus Skeleton tab.

  gui_state.py                     ← unchanged in Phase 1; extended in
                                     Phase 4 with cross-workflow recent-
                                     outputs (RecentOutputsTracker).

  gui_help.py                      ← unchanged; the Help menu / tooltips /
                                     first-run modal stay as-is.
```

---

## Phase 1 -- gui.py refactor (prerequisite)

Splits 1119-line `gui.py` into shared-widgets + per-workflow + app-shell.
**No user-visible change.** All 511 DDE tests stay green.

### Phase 1a -- Make ExtractorApp embeddable

**Goal:** ExtractorApp accepts a `ttk.Frame` parent instead of owning
the Tk root, so it can live inside a notebook tab.

**Changes:**
- `class ExtractorApp.__init__` signature changes from
  `(self, root: Tk, *, settings=...)` to
  `(self, parent: ttk.Frame, *, settings=...)`.
- Internally:
  - `self.parent = parent`
  - `self.root = parent.winfo_toplevel()` (cached for windowing ops
    like `update_idletasks`, `after`, `protocol`)
  - All widget-creation calls that used `self.root` as parent now
    use `self.parent`.
- `_make_root` stays in `gui.py`; not called by ExtractorApp anymore.
- `_fit_window_to_content` moves to `ProcessToolsApp` (window-level
  concern, not workflow-level).

**Add ProcessToolsApp class to gui.py:**

```python
class ProcessToolsApp:
    """Top-level app shell: Tk root + ttk.Notebook + shared menu."""
    def __init__(self, root: Tk):
        self.root = root
        self.settings = GuiSettings.load()
        root.title("Process Tools")
        root.geometry(self.settings.window_geometry)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Phase 1a: just the DDE tab.
        dde_frame = ttk.Frame(self.notebook)
        self.notebook.add(dde_frame, text="Document Data Extractor")
        self.dde_workflow = ExtractorApp(dde_frame, settings=self.settings)

        self._build_menu()  # moved from ExtractorApp
        self._fit_window_to_content()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        # Persist any settings each workflow updated, then quit.
        self.dde_workflow.persist_settings_for_close()  # new helper
        self.settings.save()
        self.root.destroy()
```

**Update `main()`:**

```python
def main() -> None:
    root = _make_root()
    ProcessToolsApp(root)
    root.mainloop()
```

**Tests:** existing GUI tests target `gui_state.py`, which is
unchanged. Run `.\scripts\test_all.ps1` to confirm nothing breaks.
Manually launch the GUI to confirm the DDE workflow still works
as a tab.

**Estimated time:** 1 session.

### Phase 1b -- Extract shared widgets

**Goal:** Pull the four reusable widgets out of ExtractorApp into a
new `gui_widgets.py` module. Each widget is a small `ttk.Frame`
subclass (or callable that builds and returns a frame).

**Widgets:**

1. `FileListPicker(parent, *, label, allow_dnd=True, on_change=None)`:
   - The Treeview + Add file(s)/Add folder/Remove/Clear button row.
   - Optional drag-drop via tkinterdnd2 (degrade if missing).
   - `on_change(paths: list[Path])` callback when the list mutates.
   - Owned attribute `paths: list[Path]`.
2. `LogPane(parent, *, height=10)`:
   - ScrolledText wrapper with `.log(msg: str)`, `.clear()`,
     `.copy_to_clipboard()`.
   - Auto-scroll to end on log.
3. `RunBar(parent, *, on_run, on_cancel)`:
   - Run button + Cancel button + status label + Progressbar.
   - Methods: `.set_running(bool)`, `.set_status(str)`,
     `.set_progress(current, total)`.
4. `OptionRow(parent, *, label, control, tooltip=None)`:
   - Label + control widget side-by-side. Optional tooltip.

**Migration:** ExtractorApp's `_build_input_section`,
`_build_run_section`, the `_log()` method, the various tooltip-aware
checkboxes all collapse into widget instantiations.

**Tests:** add a `tests/test_gui_widgets.py` for any pure-logic
methods (e.g. drag-drop payload parsing currently in `_on_drop` --
extract the parser into a free function and unit-test it without Tk).

**Estimated time:** 1-2 sessions.

### Phase 1c -- Rename ExtractorApp to DDEWorkflow

**Goal:** Final naming cleanup. The class moves to
`gui_workflow_dde.py` under the name `DDEWorkflow`. `gui.py` becomes
the slim app shell.

**Changes:**
- Move `ExtractorApp` body to `gui_workflow_dde.py` and rename to
  `DDEWorkflow`.
- Keep an `ExtractorApp = DDEWorkflow` alias in `gui.py` for one
  release for backward compat.
- Update PyInstaller spec hidden-imports list:

  ```python
  hiddenimports=[
      "requirements_extractor.gui",
      "requirements_extractor.gui_help",
      "requirements_extractor.gui_state",
      "requirements_extractor.gui_widgets",       # new
      "requirements_extractor.gui_workflow_dde",  # new
  ]
  ```

**Tests:** `.\scripts\test_all.ps1`; manual GUI launch.

**Estimated time:** 0.5 sessions.

---

## Phase 2 -- Compliance Matrix tab

**File:** `gui_workflow_compliance.py`.

**Class:** `ComplianceMatrixWorkflow(parent: ttk.Frame, settings: GuiSettings)`.

**UI sections (in order):**

1. **Inputs:**
   - Contract xlsx (FileListPicker single-mode, or single-file Entry+Browse).
   - Procedure xlsx (same).
   - Optional manual mapping yaml/csv (single-file picker).
2. **Options:**
   - similarity-threshold (default 0.20, slider or entry).
   - keyword-threshold (default 0.15).
   - fuzzy-id-threshold (default 0.85).
   - --no-similarity / --no-keyword-overlap / --no-explicit-id /
     --no-fuzzy-id checkboxes.
3. **Output:**
   - Output xlsx path (Save as...).
4. **Run:**
   - RunBar identical to DDE's.
5. **Log:**
   - Either a per-tab LogPane or write into the shared log pane (Phase 4
     decision -- start with per-tab).

**Run logic:**

```python
def _run(self):
    args = self._build_args()  # converts UI state to argv list
    def worker():
        from compliance_matrix.cli import main as cm_main
        try:
            rc = cm_main(args)
        except SystemExit as e:
            rc = e.code
        # update UI on the main thread via .after()
    self._worker = threading.Thread(target=worker, daemon=True)
    self._worker.start()
```

**Persistent state:** add fields to `GuiSettings` for
`last_compliance_contract_path`, `last_compliance_procedure_path`,
`last_compliance_mapping_path`, `last_compliance_output_path`,
`last_compliance_thresholds: dict`.

**Hook into ProcessToolsApp:**

```python
cm_frame = ttk.Frame(self.notebook)
self.notebook.add(cm_frame, text="Compliance Matrix")
self.compliance_workflow = ComplianceMatrixWorkflow(cm_frame, settings=self.settings)
```

**Tests:**
- `test_compliance_workflow_args.py` -- verify the args-builder
  produces the expected argv list for each combination of options
  (no Tk needed).
- `test_compliance_workflow_settings.py` -- verify settings round-trip.

**Estimated time:** 1 session.

---

## Phase 3 -- Nimbus Skeleton tab

**File:** `gui_workflow_nimbus.py`.

**Class:** `NimbusSkeletonWorkflow(parent: ttk.Frame, settings: GuiSettings)`.

**UI sections:**

1. **Inputs:**
   - Requirements xlsx (single-file picker).
   - Optional actors xlsx (single-file picker).
2. **Options:**
   - basename (default "skeleton").
   - title (default "Process Skeleton").
   - --bpmn checkbox (default off; helper text: "Recommended for
     post-Nimbus-retirement workflows").
   - --no-xmi checkbox.
   - --no-vsdx checkbox.
3. **Output:**
   - Output directory picker.
4. **Run:**
   - RunBar.
5. **Log:**
   - Per-tab or shared (same decision as Phase 2).

**On run completion:** show a "Files written" summary listing each
emitted path with an "Open" link (uses the same `_platform_open`
helper that DDE has).

**Tests:** mirror Phase 2's pattern.

**Estimated time:** 1 session.

---

## Phase 4 -- Cross-workflow seamless features

This is what turns "three tabs that happen to share a window" into
"seamless pipeline UX."

### 4a -- Recent-outputs tracker

**Component:** `RecentOutputsTracker` in `gui_state.py`.

**Behaviour:**
- Each workflow registers its outputs on successful completion:
  `tracker.register("dde_xlsx", path)`,
  `tracker.register("compliance_matrix_xlsx", path)`,
  `tracker.register("nimbus_skeleton_dir", path)`.
- Tracker stores last 5 of each kind, persisted to settings.
- Each workflow's input pickers query the tracker for recent matches:
  `tracker.recent("dde_xlsx", limit=5) -> list[Path]`.
- File pickers grow a small "Recent..." dropdown next to Browse.

**UI surface:** keep the existing Browse buttons as the primary
control; add a small dropdown-arrow icon next to each Entry that
expands a list of recent paths. One click sets the field.

### 4b -- Stale-output detection

**Component:** `StaleOutputCheck` -- a small helper that compares
mtimes between an input file and a downstream output.

**Behaviour:**
- Each workflow tracks `last_run_inputs: dict[str, Path]`.
- On focus / launch, compare current input mtimes to the snapshot.
- If any input is newer than `last_run_inputs[name]`'s last seen
  mtime, show a non-blocking yellow banner: "Input has changed since
  last run -- click here to re-run."

### 4c -- Shared log pane (decision point)

**Two design options:**
- *A:* keep per-tab logs (simplest; what the workflows do today).
- *B:* single shared log pane below the notebook; tabs write into it
  with `[DDE]` / `[CM]` / `[NS]` prefixes.

**Recommendation:** Start with A. Move to B only if Eric reports the
per-tab log feels disconnected during real workflow use. B is a
small, isolated change once the workflows exist.

### 4d -- Project state file (optional, post-MVP)

If the recent-outputs tracker isn't enough for the seamless ideal,
a `.process-tools-project.json` file in the working directory can
track:
- Which DDE run produced which xlsx (timestamp + source docs).
- Which compliance matrix runs are based on which DDE outputs.
- Which skeleton runs are based on which DDE outputs.

This is the "Option B -- Project-based GUI" from the design
discussion. **Hold off until 4a-c are in real use** -- it's the
right answer if those mechanisms aren't sufficient, but it's a big
add and shouldn't be speculative.

**Estimated time for 4a + 4b:** 1 session.

---

## Testing strategy

The existing tests target `gui_state.py` (pure-Python helpers), which
should keep passing through every phase. The new test surface:

- `tests/test_gui_widgets.py` (Phase 1b) -- pure-logic widget
  helpers; no Tk root.
- `tests/test_compliance_workflow_args.py` (Phase 2) -- argv
  builder.
- `tests/test_nimbus_workflow_args.py` (Phase 3) -- argv builder.
- `tests/test_recent_outputs_tracker.py` (Phase 4a) -- pure logic.
- `tests/test_stale_output_check.py` (Phase 4b) -- pure logic.

**No Tk-driven tests.** Tk doesn't behave consistently in headless
environments. The pattern is: extract every piece of testable logic
into pure functions / dataclasses in `gui_state.py` (or a new
similarly headless module), unit-test those, and trust manual GUI
testing for the actual widget plumbing.

After every phase: run `.\scripts\test_all.ps1` -- expect "ALL GREEN"
with the test count growing.

---

## Risk register

1. **Truncation hazard on large files.** `gui.py` is 1119 lines.
   The pre-commit hook installed in 2026-04-25 catches truncation
   pre-commit, but during the refactor itself, large rewrites should
   use heredocs (single-shot) rather than many small Edits. After
   each rewrite: `wc -l file.py`, `tail -5 file.py`,
   `python -m py_compile file.py`. Verify all three.
2. **Cross-package imports.** `gui_workflow_compliance.py` imports
   `compliance_matrix.cli`, which lives in a sibling top-level dir.
   The same `sys.path` bootstrap that `requirements_extractor` and
   the others use today applies. Plumb it once at the top of
   `gui_workflow_compliance.py` and `gui_workflow_nimbus.py`. The
   bootstrap pattern is already documented in
   `compliance-matrix/compliance_matrix/loader.py`.
3. **Threading + Tk gotchas.** Tk is not thread-safe. The worker
   threads must NEVER touch widgets directly. Use `root.after(0,
   callback)` to marshal updates back to the UI thread. Existing
   ExtractorApp already does this correctly; preserve the pattern.
4. **PyInstaller bundle growth.** Each new workflow adds ~0 MB of
   dependencies (compliance-matrix and nimbus-skeleton are
   pure-stdlib + openpyxl, all already bundled by DDE). The bundle
   should *not* grow meaningfully. If it does, run the T2 audit
   (REFACTOR.md item T2) to identify what's being unintentionally
   pulled in.
5. **Settings file migration.** Adding new fields to GuiSettings is
   safe (they default to empty/zero); removing or renaming fields
   needs a migration step. If it gets messy, bump
   `GuiSettings.SCHEMA_VERSION` and read-with-fallback.
6. **GUI test surface.** Once Phase 1c lands, manually exercise:
   - Launch GUI; confirm window opens, DDE tab is selected by
     default.
   - Run DDE on a sample fixture; confirm output xlsx is produced.
   - Switch tabs (Compliance Matrix once Phase 2 lands).
   - Close and re-launch; confirm last-used tab and last paths
     restored.

---

## PyInstaller spec updates

Each phase adds modules to the spec's `hiddenimports`. The spec
file is `requirements-extractor/packaging/DocumentDataExtractor.spec`.

After Phase 1c:

```python
hiddenimports=[
    "requirements_extractor.gui",
    "requirements_extractor.gui_help",
    "requirements_extractor.gui_state",
    "requirements_extractor.gui_widgets",
    "requirements_extractor.gui_workflow_dde",
]
```

After Phase 2:
```python
    "requirements_extractor.gui_workflow_compliance",
```

After Phase 3:
```python
    "requirements_extractor.gui_workflow_nimbus",
```

The bundled exe also needs to *find* the sibling tools at runtime.
Two options:

A. **Bundle the sibling tools' source into the exe.** Add `datas=`
   entries to the spec for `compliance-matrix/compliance_matrix/`
   and `nimbus-skeleton/nimbus_skeleton/` and
   `process-tools-common/process_tools_common/`. The bootstrap
   sys.path-adjusts to find them at `sys._MEIPASS`.

B. **Pip-install the sibling tools as packages.** Requires each tool
   to gain a `pyproject.toml` (currently none have one).

Recommendation: **A** for the unified bundle (no packaging churn).
The sys.path bootstrap pattern needs a small extension to handle
the bundled case. Document this in the bundle README.

The bundle should be **renamed** from "DocumentDataExtractor.exe" to
"ProcessTools.exe" in Phase 1c -- update the spec's `name=` and any
docs that reference the old name.

---

## Docs / CHANGELOG / README updates

Each phase ships with its own doc updates:

**Phase 1c:**
- `requirements-extractor/CHANGELOG.md`: Unreleased entry: "GUI
  refactored into shell + workflow modules; ExtractorApp renamed
  to DDEWorkflow (alias kept for one release)."
- `requirements-extractor/README.md`: minor update -- "GUI" section
  notes that the same launcher is now the unified workshop UI.
- Top-level `README.md`: tooling section flags
  `python run_gui.py` as the unified launcher.
- `ROADMAP.md`: move "Unified GUI" into Shipped if Phase 1+2+3 land
  together.

**Phase 2:**
- `compliance-matrix/CHANGELOG.md`: Unreleased: "Now reachable via
  unified GUI tab."
- `compliance-matrix/README.md`: GUI section added with screenshot
  (or ASCII diagram).

**Phase 3:**
- `nimbus-skeleton/CHANGELOG.md`: same pattern.
- `nimbus-skeleton/README.md`: GUI section added.

**Phase 4:**
- ROADMAP.md cross-cutting "PyInstaller bundles for compliance and
  nimbus" item closes (the unified bundle subsumes it).

---

## Effort estimate (cumulative)

| Phase | Description                                | Est. sessions |
|-------|--------------------------------------------|---------------|
| 1a    | ExtractorApp embeddable + ProcessToolsApp shell | 1         |
| 1b    | Extract gui_widgets.py                     | 1-2           |
| 1c    | Rename to DDEWorkflow + spec update        | 0.5           |
| 2     | Compliance Matrix tab                      | 1             |
| 3     | Nimbus Skeleton tab                        | 1             |
| 4a    | Recent-outputs tracker                     | 0.5           |
| 4b    | Stale-output detection                     | 0.5           |
| 4c    | Shared log decision (likely defer)         | 0.25          |
| **Total** |                                        | **5.75-6.75** |

Phase 1a alone delivers a usable tabbed shell with one tab; Phases 2+3
each deliver a new working tab; Phase 4 polishes. Eric can stop at
any phase boundary and ship the partial result.

---

## Kickoff prompt for the next session

Drop this into a fresh session to bootstrap context efficiently:

```
I want to execute Phase 1a of PLAN-gui-unification.md in
Process-Tools/. Read PLAN-gui-unification.md first; that has all the
architecture decisions and the target file layout.

Phase 1a only:
- Make ExtractorApp accept a ttk.Frame parent instead of a Tk root.
- Add a ProcessToolsApp class to gui.py that builds the Tk root, a
  ttk.Notebook, and adds DDEWorkflow as the first tab.
- Update main() to build ProcessToolsApp.
- Update PyInstaller spec hidden imports if needed (only if names change).
- Verify: .\scripts\test_all.ps1 (expect ALL GREEN, 600 tests),
  manual GUI launch confirms identical behaviour to before.

Constraints:
- Conservative -- I review each substantive edit before it lands.
- Use heredocs for any rewrite of >100 lines (truncation hazard
  documented in REFACTOR.md / feedback_edit_truncation memory).
- Do NOT touch gui_state.py, gui_help.py, or any tool's
  business logic. Phase 1a is purely UI plumbing.
- Stop at Phase 1a; do NOT roll into 1b without explicit go-ahead.
```

For Phase 1b, 1c, 2, 3, 4: identical pattern -- replace "Phase 1a"
with the target phase, replace the bullet list with that phase's
goals from this doc.
