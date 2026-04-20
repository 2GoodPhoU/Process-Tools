"""A small Tkinter GUI so non-technical teammates can run the extractor."""

from __future__ import annotations

import os
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

from .extractor import extract_from_files


class ExtractorApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Requirements Extractor")
        root.geometry("760x560")

        self.input_files: list[Path] = []
        self.actors_file: StringVar = StringVar()
        self.output_file: StringVar = StringVar(value=str(Path.cwd() / "requirements.xlsx"))
        self.use_nlp: BooleanVar = BooleanVar(value=False)
        self.export_statement_set: BooleanVar = BooleanVar(value=False)
        self.statement_set_file: StringVar = StringVar(
            value=str(Path.cwd() / "requirements_statement_set.csv")
        )

        self._build_ui()

    # ---------- UI construction ---------- #

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        # Input files
        input_frame = ttk.LabelFrame(frm, text="1. Input .docx files")
        input_frame.pack(fill="x", **pad)

        self.listbox = ttk.Treeview(
            input_frame, columns=("path",), show="headings", height=6
        )
        self.listbox.heading("path", text="File path")
        self.listbox.column("path", anchor="w")
        self.listbox.pack(fill="x", padx=4, pady=4)

        btns = ttk.Frame(input_frame)
        btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(btns, text="Add file(s)…", command=self._add_files).pack(side="left")
        ttk.Button(btns, text="Add folder…", command=self._add_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove selected", command=self._remove_selected).pack(side="left")
        ttk.Button(btns, text="Clear", command=self._clear_files).pack(side="left", padx=4)

        # Actors file
        actors_frame = ttk.LabelFrame(frm, text="2. Actors list (optional Excel file)")
        actors_frame.pack(fill="x", **pad)
        row = ttk.Frame(actors_frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Entry(row, textvariable=self.actors_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self._browse_actors).pack(side="left", padx=4)
        ttk.Button(row, text="Clear", command=lambda: self.actors_file.set("")).pack(side="left")

        # Options
        opt_frame = ttk.LabelFrame(frm, text="3. Options")
        opt_frame.pack(fill="x", **pad)
        ttk.Checkbutton(
            opt_frame,
            text="Use NLP to detect secondary actors (requires spaCy)",
            variable=self.use_nlp,
        ).pack(anchor="w", padx=4, pady=2)

        # Output
        out_frame = ttk.LabelFrame(frm, text="4. Output .xlsx")
        out_frame.pack(fill="x", **pad)
        row = ttk.Frame(out_frame)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Entry(row, textvariable=self.output_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Save as…", command=self._browse_output).pack(side="left", padx=4)

        # Statement-set CSV (optional)
        ss_frame = ttk.LabelFrame(
            frm, text="5. Statement-set CSV (optional — paired-level hierarchy)"
        )
        ss_frame.pack(fill="x", **pad)
        ttk.Checkbutton(
            ss_frame,
            text="Also export to statement-set CSV",
            variable=self.export_statement_set,
            command=self._toggle_statement_set,
        ).pack(anchor="w", padx=4, pady=(4, 0))
        ss_row = ttk.Frame(ss_frame)
        ss_row.pack(fill="x", padx=4, pady=4)
        self.ss_entry = ttk.Entry(ss_row, textvariable=self.statement_set_file, state="disabled")
        self.ss_entry.pack(side="left", fill="x", expand=True)
        self.ss_browse_btn = ttk.Button(
            ss_row, text="Save as…", command=self._browse_statement_set, state="disabled"
        )
        self.ss_browse_btn.pack(side="left", padx=4)

        # Run button + log
        run_row = ttk.Frame(frm)
        run_row.pack(fill="x", **pad)
        self.run_btn = ttk.Button(run_row, text="Run extraction", command=self._run)
        self.run_btn.pack(side="left")
        self.status_var = StringVar(value="Ready.")
        ttk.Label(run_row, textvariable=self.status_var).pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(frm, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

    # ---------- Helpers ---------- #

    def _add_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select .docx files",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
        )
        for f in files:
            self._add_path(Path(f))

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing .docx files")
        if not folder:
            return
        for p in sorted(Path(folder).rglob("*.docx")):
            if not p.name.startswith("~$"):
                self._add_path(p)

    def _add_path(self, path: Path) -> None:
        if path in self.input_files:
            return
        self.input_files.append(path)
        self.listbox.insert("", END, values=(str(path),))

    def _remove_selected(self) -> None:
        selected = self.listbox.selection()
        for item in selected:
            path = Path(self.listbox.item(item, "values")[0])
            if path in self.input_files:
                self.input_files.remove(path)
            self.listbox.delete(item)

    def _clear_files(self) -> None:
        self.input_files.clear()
        for item in self.listbox.get_children():
            self.listbox.delete(item)

    def _browse_actors(self) -> None:
        f = filedialog.askopenfilename(
            title="Select actors .xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if f:
            self.actors_file.set(f)

    def _browse_output(self) -> None:
        f = filedialog.asksaveasfilename(
            title="Save output as",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="requirements.xlsx",
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
        state = "normal" if self.export_statement_set.get() else "disabled"
        self.ss_entry.config(state=state)
        self.ss_browse_btn.config(state=state)

    def _log(self, msg: str) -> None:
        self.log.insert(END, msg + "\n")
        self.log.see(END)
        self.root.update_idletasks()

    # ---------- Run ---------- #

    def _run(self) -> None:
        if not self.input_files:
            messagebox.showwarning("No inputs", "Please add at least one .docx file.")
            return
        out_path = self.output_file.get().strip()
        if not out_path:
            messagebox.showwarning("No output", "Please choose an output .xlsx path.")
            return

        actors_path = self.actors_file.get().strip()
        actors = Path(actors_path) if actors_path else None

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

        self.run_btn.config(state="disabled")
        self.status_var.set("Running…")
        self.log.delete("1.0", END)

        def worker() -> None:
            try:
                result = extract_from_files(
                    input_paths=list(self.input_files),
                    output_path=Path(out_path),
                    actors_xlsx=actors,
                    use_nlp=self.use_nlp.get(),
                    statement_set_path=ss_path,
                    progress=lambda m: self.root.after(0, self._log, m),
                )
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
                self.root.after(0, self.status_var.set, "Done.")
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Extraction complete",
                        msg
                        + "\n\nOpen the output file to review. Soft (yellow) "
                        "rows may need human verification.",
                    ),
                )
            except Exception as e:  # noqa: BLE001
                self.root.after(0, self._log, f"ERROR: {e}")
                self.root.after(0, self.status_var.set, "Error.")
                self.root.after(0, messagebox.showerror, "Error", str(e))
            finally:
                self.root.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    root = Tk()
    # Use the native theme where possible.
    try:
        ttk.Style().theme_use("vista" if os.name == "nt" else "clam")
    except Exception:  # noqa: BLE001
        pass
    ExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
