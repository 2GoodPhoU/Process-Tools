"""A small Tkinter GUI so non-technical teammates can run the extractor.

The UI surface is deliberately thin — all the state (window geometry,
last-used paths, checkbox values) and the tricky-to-test helpers (path
dedup, actors template generation) live in
:mod:`requirements_extractor.gui_state` so they can be unit-tested
without spinning up a Tk root.

Features:

* Run / Cancel a multi-file extraction without freezing the UI.
* Indeterminate-to-determinate progress bar driven by ``file_progress``.
* "Open output file" button on completion.
* Optional drag-and-drop of .docx files / folders if ``tkinterdnd2``
  is installed (pure-Tk fallback otherwise — no crash).
* "Save actors template\u2026" button writes a ready-to-fill .xlsx.
* Persistent settings: window size, last-used paths, and checkbox
  states round-trip through ``~/.requirements_extractor/settings.json``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional
from tkinter import (
    BooleanVar,
    END,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    ttk,
)
from tkinter.scrolledtext import ScrolledText

from .actor_scan import ActorScanCancelled, scan_actors_from_files
from .extractor import ExtractionCancelled, extract_from_files
from .gui_state import (
    GuiSettings,
    dedupe_paths,
    is_duplicate_of_any,
    write_actors_template,
)


# ---------------------------------------------------------------------------
# Optional drag-and-drop — degrade to plain Tk if tkinterdnd2 is missing.
# ---------------------------------------------------------------------------


try:  # pragma: no cover - import guard
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    _DND_AVAILABLE = True
except Exception:  # noqa: BLE001
    DND_FILES = None  # type: ignore[assignment]
    TkinterDnD = None  # type: ignore[assignment]
    _DND_AVAILABLE = False


def _make_root() -> Tk:
    """Return the Tk root, preferring the DnD-aware subclass if available."""
    if _DND_AVAILABLE:
        return TkinterDnD.Tk()  # type: ignore[union-attr]
    return Tk()


# Default output filenames per mode.  Kept in sync with the CLI's
# defaults in ``requirements_extractor.cli``.
_DEFAULT_OUTPUT_NAMES = {"requirements.xlsx", "actors_scan.xlsx"}


def _default_output_name(mode: str) -> str:
    """Return the default output filename for the given mode."""
    return "actors_scan.xlsx" if mode == "actors" else "requirements.xlsx"


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class ExtractorApp:
    def __init__(self, root: Tk, *, settings: Optional[GuiSettings] = None) -> None:
        self.root = root
        self.settings: GuiSettings = settings if settings is not None else GuiSettings.load()
        root.title("Document Data Extractor")
        root.geometry(self.settings.window_geometry)

        # Input state ---------------------------------------------------- #
        self.input_files: list[Path] = []
        self.mode = StringVar(value=self.settings.mode)
        self.actors_file = StringVar(value=self.settings.last_actors_path)
        self.config_file = StringVar(value=self.settings.last_config_path)
        self.output_file = StringVar(
            value=self.settings.last_output_path
            or str(Path.cwd() / _default_output_name(self.settings.mode))
        )
        self.use_nlp = BooleanVar(value=self.settings.use_nlp)
        self.export_statement_set = BooleanVar(value=self.settings.export_statement_set)
        self.statement_set_file = StringVar(
            value=self.settings.last_statement_set_path
            or str(Path.cwd() / "requirements_statement_set.csv")
        )
        self.open_output_on_done = BooleanVar(value=self.settings.open_output_on_done)

        # Run state ------------------------------------------------------ #
        self._cancel_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._last_output_path: Optional[Path] = None

        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------------------------------------------- #
    # UI construction
    # ----------------------------------------------------------------- #

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        self._build_mode_section(frm, pad)
        self._build_input_section(frm, pad)
        self._build_actors_section(frm, pad)
        self._build_config_section(frm, pad)
        self._build_options_section(frm, pad)
        self._build_output_section(frm, pad)
        self._build_statement_set_section(frm, pad)
        self._build_run_section(frm, pad)
        # Apply initial mode-dependent state (enables/disables ss section
        # and adjusts output default for the current mode).
        self._on_mode_change()

    # --- section: mode --- #

    def _build_mode_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(parent, text="Extraction mode")
        frame.pack(fill="x", **pad)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Radiobutton(
            row,
            text="Requirements  \u2014  one row per requirement sentence",
            variable=self.mode,
            value="requirements",
            command=self._on_mode_change,
        ).pack(anchor="w")
        ttk.Radiobutton(
            row,
            text="Actors  \u2014  canonical actors list (feeds --actors)",
            variable=self.mode,
            value="actors",
            command=self._on_mode_change,
        ).pack(anchor="w")

    # --- section: input files --- #

    def _build_input_section(self, parent: ttk.Frame, pad: dict) -> None:
        label = "1. Input .docx files"
        if _DND_AVAILABLE:
            label += " (drag-and-drop supported)"
        frame = ttk.LabelFrame(parent, text=label)
        frame.pack(fill="x", **pad)

        self.listbox = ttk.Treeview(
            frame, columns=("path",), show="headings", height=6
        )
        self.listbox.heading("path", text="File path")
        self.listbox.column("path", anchor="w")
        self.listbox.pack(fill="x", padx=4, pady=4)

        if _DND_AVAILABLE:
            self.listbox.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

        btns = ttk.Frame(frame)
        btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(btns, text="Add file(s)\u2026", command=self._add_files).pack(side="left")
        ttk.Button(btns, text="Add folder\u2026", command=self._add_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove selected", command=self._remove_selected).pack(side="left")
        ttk.Button(btns, text="Clear", command=self._clear_files).pack(side="left", padx=4)

    # --- section: actors --- #

    def _build_actors_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(parent, text="2. Actors list (optional Excel file)")
        frame.pack(fill="x", **pad)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Entry(row, textvariable=self.actors_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse\u2026", command=self._browse_actors).pack(side="left", padx=4)
        ttk.Button(row, text="Save template\u2026", command=self._save_actors_template).pack(
            side="left"
        )
        ttk.Button(row, text="Clear", command=lambda: self.actors_file.set("")).pack(
            side="left", padx=4
        )

    # --- section: config --- #

    def _build_config_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(
            parent, text="3. Config file (optional YAML \u2014 document format hints)"
        )
        frame.pack(fill="x", **pad)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Entry(row, textvariable=self.config_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse\u2026", command=self._browse_config).pack(side="left", padx=4)
        ttk.Button(row, text="Clear", command=lambda: self.config_file.set("")).pack(side="left")
        ttk.Label(
            frame,
            text=(
                "Tip: place <docname>.reqx.yaml next to any .docx and it "
                "will be auto-loaded for that file."
            ),
            foreground="#555",
        ).pack(anchor="w", padx=4, pady=(0, 4))

    # --- section: options --- #

    def _build_options_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(parent, text="4. Options")
        frame.pack(fill="x", **pad)
        ttk.Checkbutton(
            frame,
            text="Use NLP to detect secondary actors (requires spaCy)",
            variable=self.use_nlp,
        ).pack(anchor="w", padx=4, pady=2)
        ttk.Checkbutton(
            frame,
            text="Open output file when the run finishes",
            variable=self.open_output_on_done,
        ).pack(anchor="w", padx=4, pady=2)

    # --- section: output --- #

    def _build_output_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(parent, text="5. Output .xlsx")
        frame.pack(fill="x", **pad)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Entry(row, textvariable=self.output_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Save as\u2026", command=self._browse_output).pack(side="left", padx=4)

    # --- section: statement-set --- #

    def _build_statement_set_section(self, parent: ttk.Frame, pad: dict) -> None:
        frame = ttk.LabelFrame(
            parent, text="6. Statement-set CSV (optional \u2014 paired-level hierarchy)"
        )
        frame.pack(fill="x", **pad)
        self.ss_checkbox = ttk.Checkbutton(
            frame,
            text="Also export to statement-set CSV (requirements mode only)",
            variable=self.export_statement_set,
            command=self._toggle_statement_set,
        )
        self.ss_checkbox.pack(anchor="w", padx=4, pady=(4, 0))
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=4, pady=4)
        initial_state = "normal" if self.export_statement_set.get() else "disabled"
        self.ss_entry = ttk.Entry(
            row, textvariable=self.statement_set_file, state=initial_state
        )
        self.ss_entry.pack(side="left", fill="x", expand=True)
        self.ss_browse_btn = ttk.Button(
            row,
            text="Save as\u2026",
            command=self._browse_statement_set,
            state=initial_state,
        )
        self.ss_browse_btn.pack(side="left", padx=4)

    # --- section: run + log --- #

    def _build_run_section(self, parent: ttk.Frame, pad: dict) -> None:
        run_row = ttk.Frame(parent)
        run_row.pack(fill="x", **pad)
        # One Run button; its behaviour depends on the selected mode.
        self.run_btn = ttk.Button(run_row, text="Run", command=self._run)
        self.run_btn.pack(side="left")
        self.cancel_btn = ttk.Button(
            run_row, text="Cancel", command=self._cancel, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=4)

        self.status_var = StringVar(value="Ready.")
        ttk.Label(run_row, textvariable=self.status_var).pack(side="left", padx=12)

        # Determinate progress bar — zeroed until a run starts.
        self.progress = ttk.Progressbar(
            parent, orient="horizontal", mode="determinate", maximum=1
        )
        self.progress.pack(fill="x", padx=8, pady=(0, 4))

        log_frame = ttk.LabelFrame(parent, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

    # ----------------------------------------------------------------- #
    # File-list management
    # ----------------------------------------------------------------- #

    def _add_files(self) -> None:
        initial = self.settings.last_input_dir or str(Path.cwd())
        files = filedialog.askopenfilenames(
            title="Select .docx files",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
            initialdir=initial,
        )
        for f in files:
            self._add_path(Path(f))
        if files:
            self.settings.last_input_dir = str(Path(files[0]).parent)

    def _add_folder(self) -> None:
        initial = self.settings.last_input_dir or str(Path.cwd())
        folder = filedialog.askdirectory(
            title="Select folder containing .docx files", initialdir=initial
        )
        if not folder:
            return
        self.settings.last_input_dir = folder
        for p in sorted(Path(folder).rglob("*.docx")):
            if not p.name.startswith("~$"):
                self._add_path(p)

    def _add_path(self, path: Path) -> None:
        # REVIEW §2.11: compare resolved paths so different spellings of the
        # same file (./a/b.docx, /abs/a/b.docx, …) don't sneak in twice.
        if is_duplicate_of_any(path, self.input_files):
            return
        self.input_files.append(path)
        self.listbox.insert("", END, values=(str(path),))

    def _on_drop(self, event) -> None:  # pragma: no cover - requires DnD
        """tkinterdnd2 delivers dropped paths as a brace-quoted string."""
        raw: str = event.data or ""
        # The payload uses Tcl list syntax: {path with spaces} path_no_spaces …
        parts: list[str] = []
        token = []
        inside = False
        for ch in raw:
            if ch == "{":
                inside = True
            elif ch == "}":
                inside = False
                parts.append("".join(token))
                token = []
            elif ch == " " and not inside:
                if token:
                    parts.append("".join(token))
                    token = []
            else:
                token.append(ch)
        if token:
            parts.append("".join(token))
        added = 0
        for s in parts:
            p = Path(s)
            if p.is_dir():
                for d in sorted(p.rglob("*.docx")):
                    if not d.name.startswith("~$"):
                        before = len(self.input_files)
                        self._add_path(d)
                        added += len(self.input_files) - before
            elif p.suffix.lower() == ".docx":
                before = len(self.input_files)
                self._add_path(p)
                added += len(self.input_files) - before
        self.status_var.set(f"Added {added} file(s) via drag-and-drop.")

    def _remove_selected(self) -> None:
        selected = self.listbox.selection()
        for item in selected:
            path = Path(self.listbox.item(item, "values")[0])
            # Match by resolved path for the same §2.11 reasons as _add_path.
            self.input_files = [
                p for p in self.input_files
                if not is_duplicate_of_any(p, [path])
            ]
            self.listbox.delete(item)

    def _clear_files(self) -> None:
        self.input_files.clear()
        for item in self.listbox.get_children():
            self.listbox.delete(item)

    # ----------------------------------------------------------------- #
    # File dialogs
    # ----------------------------------------------------------------- #

    def _browse_actors(self) -> None:
        f = filedialog.askopenfilename(
            title="Select actors .xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if f:
            self.actors_file.set(f)

    def _save_actors_template(self) -> None:
        """REVIEW §3.14: let the user generate an actors template without CLI."""
        f = filedialog.asksaveasfilename(
            title="Save actors template as",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="actors_template.xlsx",
        )
        if not f:
            return
        try:
            out = write_actors_template(Path(f))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Failed to write template", str(e))
            return
        # Helpfully pre-fill the actors field so the next Run uses it.
        self.actors_file.set(str(out))
        self._log(f"Wrote actors template to {out}.")
        if messagebox.askyesno(
            "Template saved",
            f"Actors template saved to:\n{out}\n\nOpen it now to customise?",
        ):
            _platform_open(out)

    def _browse_config(self) -> None:
        f = filedialog.askopenfilename(
            title="Select config .yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if f:
            self.config_file.set(f)

    def _browse_output(self) -> None:
        f = filedialog.asksaveasfilename(
            title="Save output as",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=_default_output_name(self.mode.get()),
        )
        if f:
            self.output_file.set(f)

    def _browse_statement_set(self) -> None:
        f = filedialog.asksaveasfilename(
            title="Save statement-set CSV as",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="requirements_statement_set.csv",
        )
        if f:
            self.statement_set_file.set(f)

    def _toggle_statement_set(self) -> None:
        """Enable the statement-set path widgets only if the checkbox
        is ticked AND we're in requirements mode."""
        enabled = (
            self.export_statement_set.get() and self.mode.get() == "requirements"
        )
        state = "normal" if enabled else "disabled"
        self.ss_entry.config(state=state)
        self.ss_browse_btn.config(state=state)

    def _on_mode_change(self) -> None:
        """React to a mode radio change.

        * Disables the statement-set section in actors mode (it's
          requirements-only).
        * Swaps the default output file name when the current output
          still matches the other mode's default (no stomp on
          user-customised paths).
        """
        mode = self.mode.get()
        # Statement-set section: only meaningful in requirements mode.
        self._toggle_statement_set()
        if hasattr(self, "ss_checkbox"):
            self.ss_checkbox.config(
                state="normal" if mode == "requirements" else "disabled"
            )
        # Swap default output name if the user hasn't picked a custom path.
        current = self.output_file.get().strip()
        current_name = Path(current).name if current else ""
        if current_name in _DEFAULT_OUTPUT_NAMES:
            parent = Path(current).parent if current else Path.cwd()
            self.output_file.set(str(parent / _default_output_name(mode)))

    def _log(self, msg: str) -> None:
        self.log.insert(END, msg + "\n")
        self.log.see(END)
        self.root.update_idletasks()

    # ----------------------------------------------------------------- #
    # Run / Cancel
    # ----------------------------------------------------------------- #

    def _run(self) -> None:
        """Mode-aware dispatcher: runs requirements or actor-scan."""
        if self._worker is not None and self._worker.is_alive():
            return  # already running — no-op
        if self.mode.get() == "actors":
            self._run_actors_scan()
            return
        if not self.input_files:
            messagebox.showwarning("No inputs", "Please add at least one .docx file.")
            return
        out_path = self.output_file.get().strip()
        if not out_path:
            messagebox.showwarning("No output", "Please choose an output .xlsx path.")
            return

        actors_path = self.actors_file.get().strip()
        actors = Path(actors_path) if actors_path else None

        config_raw = self.config_file.get().strip()
        config = Path(config_raw) if config_raw else None

        ss_path: Optional[Path] = None
        if self.export_statement_set.get():
            ss_raw = self.statement_set_file.get().strip()
            if not ss_raw:
                messagebox.showwarning(
                    "No statement-set path",
                    "Statement-set export is enabled but no CSV path is set.",
                )
                return
            ss_path = Path(ss_raw)

        # Final dedup pass — removes any duplicates that slipped in pre-fix.
        self.input_files = dedupe_paths(self.input_files)

        self._cancel_event.clear()
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status_var.set("Running\u2026")
        self.log.delete("1.0", END)
        self.progress.config(value=0, maximum=max(1, len(self.input_files)))

        inputs_snapshot = list(self.input_files)

        def worker() -> None:
            try:
                result = extract_from_files(
                    input_paths=inputs_snapshot,
                    output_path=Path(out_path),
                    actors_xlsx=actors,
                    use_nlp=self.use_nlp.get(),
                    statement_set_path=ss_path,
                    config_path=config,
                    progress=lambda m: self.root.after(0, self._log, m),
                    file_progress=lambda i, n, name: self.root.after(
                        0, self._on_file_progress, i, n, name
                    ),
                    cancel_check=self._cancel_event.is_set,
                )
            except ExtractionCancelled as e:
                self.root.after(0, self._log, f"Cancelled: {e}")
                self.root.after(0, self._finish_run, "Cancelled.", None)
                return
            except Exception as e:  # noqa: BLE001
                self.root.after(0, self._log, f"ERROR: {e}")
                self.root.after(0, self._finish_run, "Error.", None)
                self.root.after(0, messagebox.showerror, "Error", str(e))
                return

            msg_lines = [
                f"Done. {result.stats.requirements_found} requirements "
                f"({result.stats.hard_count} hard, "
                f"{result.stats.soft_count} soft).",
                f"Excel:        {result.output_path}",
            ]
            if result.statement_set_path is not None:
                msg_lines.append(f"Statement set: {result.statement_set_path}")
            msg = "\n".join(msg_lines)
            self.root.after(0, self._log, "")
            self.root.after(0, self._log, msg)
            self.root.after(0, self._finish_run, "Done.", result.output_path)
            self.root.after(0, self._show_done_dialog, msg, result.output_path)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _on_file_progress(self, i: int, n: int, name: str) -> None:
        self.progress.config(value=i, maximum=max(1, n))
        self.status_var.set(f"Parsing {i}/{n}: {name}")

    def _cancel(self) -> None:
        self._cancel_event.set()
        self.cancel_btn.config(state="disabled")
        self.status_var.set("Cancelling\u2026")
        self._log("Cancel requested. Finishing current file and stopping\u2026")

    def _finish_run(self, status: str, output_path: Optional[Path]) -> None:
        self.run_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.status_var.set(status)
        self._last_output_path = output_path

    # ----------------------------------------------------------------- #
    # Actor-only scan
    # ----------------------------------------------------------------- #

    def _run_actors_scan(self) -> None:
        """Scan inputs for actors and write an Actor/Aliases .xlsx.

        Called from :meth:`_run` when mode == "actors".  The Run-section
        output field doubles as the destination path in actors mode, so
        we don't pop an extra file-picker here anymore — the user picks
        the path once via the normal "5. Output" browse button.
        """
        if not self.input_files:
            messagebox.showwarning("No inputs", "Please add at least one .docx file.")
            return
        out_raw = self.output_file.get().strip()
        if not out_raw:
            messagebox.showwarning("No output", "Please choose an output .xlsx path.")
            return
        out_path = Path(out_raw)

        actors_path = self.actors_file.get().strip()
        seed = Path(actors_path) if actors_path else None

        config_raw = self.config_file.get().strip()
        config = Path(config_raw) if config_raw else None

        self.input_files = dedupe_paths(self.input_files)
        inputs_snapshot = list(self.input_files)

        self._cancel_event.clear()
        self.run_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status_var.set("Scanning actors\u2026")
        self.log.delete("1.0", END)
        self.progress.config(value=0, maximum=max(1, len(inputs_snapshot)))

        def worker() -> None:
            try:
                result = scan_actors_from_files(
                    input_paths=inputs_snapshot,
                    output_path=out_path,
                    seed_actors_xlsx=seed,
                    use_nlp=self.use_nlp.get(),
                    config_path=config,
                    progress=lambda m: self.root.after(0, self._log, m),
                    file_progress=lambda i, n, name: self.root.after(
                        0, self._on_file_progress, i, n, name
                    ),
                    cancel_check=self._cancel_event.is_set,
                )
            except ActorScanCancelled as e:
                self.root.after(0, self._log, f"Cancelled: {e}")
                self.root.after(0, self._finish_run, "Cancelled.", None)
                return
            except Exception as e:  # noqa: BLE001
                self.root.after(0, self._log, f"ERROR: {e}")
                self.root.after(0, self._finish_run, "Error.", None)
                self.root.after(0, messagebox.showerror, "Error", str(e))
                return

            msg = (
                f"Done. {result.stats.groups} actor group(s) from "
                f"{result.stats.observations} observation(s).\n"
                f"Output: {result.output_path}"
            )
            self.root.after(0, self._log, "")
            self.root.after(0, self._log, msg)
            self.root.after(0, self._finish_run, "Done.", result.output_path)
            self.root.after(0, self._show_done_dialog, msg, result.output_path)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _show_done_dialog(self, msg: str, output_path: Optional[Path]) -> None:
        """REVIEW §3.5: offer an Open-output-file action on success."""
        if output_path is not None and self.open_output_on_done.get():
            _platform_open(output_path)
            return
        if output_path is None:
            messagebox.showinfo("Extraction complete", msg)
            return
        if messagebox.askyesno(
            "Extraction complete",
            msg + "\n\nOpen the output file now?",
        ):
            _platform_open(output_path)

    # ----------------------------------------------------------------- #
    # Persistence
    # ----------------------------------------------------------------- #

    def _snapshot_settings(self) -> GuiSettings:
        try:
            geom = self.root.winfo_geometry()
        except Exception:  # noqa: BLE001
            geom = self.settings.window_geometry
        self.settings.window_geometry = geom or self.settings.window_geometry
        self.settings.last_actors_path = self.actors_file.get().strip()
        self.settings.last_config_path = self.config_file.get().strip()
        self.settings.last_output_path = self.output_file.get().strip()
        self.settings.last_statement_set_path = self.statement_set_file.get().strip()
        self.settings.use_nlp = bool(self.use_nlp.get())
        self.settings.export_statement_set = bool(self.export_statement_set.get())
        self.settings.open_output_on_done = bool(self.open_output_on_done.get())
        self.settings.mode = self.mode.get()
        self.settings.remember_inputs(self.input_files)
        return self.settings

    def _on_close(self) -> None:
        try:
            self._snapshot_settings().save()
        except Exception as e:  # noqa: BLE001
            # Don't block shutdown on a failed settings write; surface it
            # in stderr so it's debuggable but not user-blocking.
            print(f"[gui] Could not save settings: {e}", file=sys.stderr)
        self.root.destroy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _platform_open(path: Path) -> None:
    """Open ``path`` in the OS's default handler.

    Swallows exceptions — a failure to open shouldn't tank the app.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:  # noqa: BLE001
        print(f"[gui] Could not open {path}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    root = _make_root()
    # Use the native theme where possible.
    try:
        ttk.Style().theme_use("vista" if os.name == "nt" else "clam")
    except Exception:  # noqa: BLE001
        pass
    ExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
