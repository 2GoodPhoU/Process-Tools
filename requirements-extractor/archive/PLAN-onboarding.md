> **STATUS: DISCHARGED (2026-04-24).**
> All three surfaces shipped: Help menu ("Getting started…", "Open
> README", "About"), first-run modal (dismissible-forever via
> `GuiSettings.onboarding_seen`), and hover-tooltips on the
> NLP / dry-run / auto-actors / statement-set checkboxes. Dialog and
> tooltip helper live in the new `gui_help.py` module so the Tk
> surface stays legible. Tests cover the persistence flag in
> `tests/test_gui_state.py::TestOnboardingSeen` (4 tests).
> Kept in-tree for the design rationale; the implementation won't
> be re-derived.

---

# Plan — onboarding and in-app help

FIELD_NOTES §5. The GUI has no startup guide, tooltips, or in-app
help — first-time users, and returning users after a break, have to
reconstruct intent from the README.

Three surfaces, in escalating effort / payoff:

1. **Help menu** — persistent, cheap, always discoverable.
2. **Tooltips on each option** — tiny per-widget explanations for the
   options most commonly misunderstood (NLP dependency, auto-actors,
   statement-set).
3. **First-run modal** — a single "getting started" dialog the very
   first time the app launches on a machine.

Do all three in that order. Each is independently landable.

## 1. Help menu

Add a menubar to the Tk root with a single "Help" cascade. Three
entries: "Getting started…" (opens the first-run modal on demand),
"README online" (falls back to a local path inside the bundled exe),
and "About".

Patch against `requirements_extractor/gui.py`:

```python
# Add these imports at the top alongside the other tkinter imports.
# (BooleanVar / Tk / ttk / messagebox are already imported.)
from tkinter import Menu, Toplevel

# Add to ExtractorApp.__init__, right after self._build_ui():
self._build_menu()

# New method on ExtractorApp, next to _build_ui:
def _build_menu(self) -> None:
    """Attach a minimal Help menu to the root window."""
    menubar = Menu(self.root)
    help_menu = Menu(menubar, tearoff=False)
    help_menu.add_command(
        label="Getting started\u2026",
        command=self._show_getting_started,
    )
    help_menu.add_command(
        label="Open README",
        command=self._open_readme,
    )
    help_menu.add_separator()
    help_menu.add_command(label="About", command=self._show_about)
    menubar.add_cascade(label="Help", menu=help_menu)
    self.root.config(menu=menubar)

def _show_getting_started(self) -> None:
    GettingStartedDialog(self.root)

def _open_readme(self) -> None:
    """Open the bundled README.md next to the executable, falling back
    to the source-tree copy for dev runs."""
    # When frozen by PyInstaller, the bundle's data files live under
    # sys._MEIPASS. Otherwise we're running from source.
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "README.md")
    candidates.append(Path(__file__).resolve().parents[1] / "README.md")
    for p in candidates:
        if p.exists():
            _platform_open(p)
            return
    messagebox.showinfo(
        "README not found",
        "Could not locate README.md. See the project repository for "
        "full documentation.",
    )

def _show_about(self) -> None:
    messagebox.showinfo(
        "About Document Data Extractor",
        "Document Data Extractor\n\n"
        "Pulls structured requirements data out of Word (.docx) "
        "specifications.\n\n"
        "See Help \u2192 Getting started\u2026 for a short walkthrough.",
    )
```

The menubar shows on Windows and Linux as a top-of-window bar and on
macOS as an application-menu extension — Tk handles the platform
difference automatically.

## 2. First-run modal

A `Toplevel` (not `messagebox` — we want two-column layout and a
"don't show this again" checkbox) that explains, in three short
sections:
- Two modes: Requirements vs Actors.
- The NLP dependency — what it's for and what happens without it.
- The minimal valid option set (from `PLAN-option-exclusion.md`).

Trigger on startup when `GuiSettings.onboarding_seen` is False. The
"don't show this again" flag persists via the existing settings JSON.

Patch against `requirements_extractor/gui_state.py`:

```diff
     # When True, requirements mode first runs the actor scan on the same
     # inputs and uses its output as the actors list — saves the "maintain
     # a separate actors.xlsx" step for users who just want to go.
     auto_actors: bool = False
+
+    # Onboarding: True once the user has dismissed the first-run modal.
+    # Cleared by deleting settings.json, or via a "Show getting started
+    # on next launch" toggle in the Help menu (future work).
+    onboarding_seen: bool = False
```

New widget class in `gui.py` — or a separate `gui_help.py` module if
you prefer to keep `gui.py` from growing further. Sketch:

```python
class GettingStartedDialog:
    """Modal 'first-run' dialog.

    A Toplevel window with a short walkthrough, a 'Don't show this
    again' checkbox, and a single Close button. Deliberately plain Tk
    — no images, no dependencies — so it works under the same install
    footprint as the rest of the GUI.
    """

    def __init__(self, root: Tk, *, settings: Optional[GuiSettings] = None) -> None:
        self.settings = settings
        self.top = top = Toplevel(root)
        top.title("Getting started with Document Data Extractor")
        top.transient(root)
        top.grab_set()
        top.resizable(False, False)

        frm = ttk.Frame(top, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text="Getting started",
            font=("Arial", 13, "bold"),
        ).pack(anchor="w")

        sections = [
            (
                "Two modes",
                "Requirements mode extracts one row per requirement "
                "sentence. Actors mode harvests a canonical actors "
                "list you can feed back in on the next run.",
            ),
            (
                "NLP dependency",
                "\"Use NLP\" improves secondary-actor recall via "
                "spaCy. If spaCy isn't installed the run still "
                "completes — you just get fewer actors. See README "
                "for the offline workflow.",
            ),
            (
                "Minimum valid options",
                "Requirements mode needs at least one secondary-actor "
                "source: an Actors list, the NLP option, or "
                "Auto-harvest. Without one of these, only the "
                "first-column actor is captured.",
            ),
            (
                "Per-run settings persist",
                "Your window size, last-used paths, and checkbox "
                "states are remembered between launches. Delete "
                "~/.requirements_extractor/settings.json to reset.",
            ),
        ]
        for title, body in sections:
            ttk.Label(frm, text=title, font=("Arial", 10, "bold")).pack(
                anchor="w", pady=(8, 0)
            )
            ttk.Label(
                frm, text=body, wraplength=460, justify="left",
            ).pack(anchor="w", padx=(8, 0))

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(16, 0))
        self.dont_show = BooleanVar(value=True)
        ttk.Checkbutton(
            row,
            text="Don't show this again",
            variable=self.dont_show,
        ).pack(side="left")
        ttk.Button(row, text="Close", command=self._close).pack(side="right")

        # Centre on the root window.
        top.update_idletasks()
        rx = root.winfo_rootx() + (root.winfo_width() // 2) - (top.winfo_width() // 2)
        ry = root.winfo_rooty() + (root.winfo_height() // 2) - (top.winfo_height() // 2)
        top.geometry(f"+{max(rx, 0)}+{max(ry, 0)}")

    def _close(self) -> None:
        if self.dont_show.get() and self.settings is not None:
            self.settings.onboarding_seen = True
        self.top.grab_release()
        self.top.destroy()
```

Wire the trigger at the end of `ExtractorApp.__init__`:

```python
# Trigger the first-run modal only once per machine. "Help → Getting
# started…" opens it again on demand regardless of this flag.
if not self.settings.onboarding_seen:
    # Defer until after the main loop starts so the modal lands on
    # top of the fully-rendered root.
    self.root.after(200, lambda: GettingStartedDialog(
        self.root, settings=self.settings,
    ))
```

## 3. Tooltips

Lightweight — no extra dependencies. A shared `_Tooltip` helper that
binds `<Enter>` / `<Leave>` on a widget and shows a borderless
`Toplevel` near the cursor. Target only the options that have
non-obvious semantics — NLP, auto-actors, statement-set, dry-run.

```python
class _Tooltip:
    """Hover-tooltip for a Tk widget.

    Minimal. Shows the given text in a borderless Toplevel when the
    cursor enters the widget; hides it on leave. Delay is fixed at
    500 ms so a brief hover doesn't flash content at the user.
    """

    _DELAY_MS = 500

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._after_id: Optional[str] = None
        self._tip: Optional[Toplevel] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event) -> None:
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _on_leave(self, _event) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

    def _show(self) -> None:
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        tip = Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        ttk.Label(
            tip,
            text=self.text,
            background="#FFFFE0",
            relief="solid",
            borderwidth=1,
            padding=(6, 3),
            wraplength=320,
            justify="left",
        ).pack()
        self._tip = tip
```

Attach in `_build_options_section` and siblings:

```python
_Tooltip(
    self.auto_actors_cb,
    "Runs the actor scan on the inputs before the requirements pass "
    "and uses its output as the Actors list. Saves you maintaining a "
    "separate actors.xlsx. Requirements mode only.",
)
_Tooltip(
    self.dry_run_cb,
    "Parses and counts without writing any files. Useful for "
    "previewing totals before overwriting an existing output.",
)
# Add similar entries on the NLP checkbox and the statement-set row.
```

## Effort estimate

- Help menu: 30 min.
- First-run modal + settings flag: 1.5 hours.
- Tooltips (shared helper + 4 hook-ups): 1 hour.
- Tests (headless — stub Toplevel): 45 min.

Total ~4 hours. Each layer is independently landable if Eric wants to
stage.

## Open question for Eric

The plan above makes the first-run modal **dismissible-forever** via
the checkbox. The alternative — "re-appear until a real run succeeds"
— was the other option FIELD_NOTES raised. Recommendation: stick with
dismissible-forever. Eric is both the author and the most frequent
user; re-popping the modal on every launch until the first successful
run punishes him specifically while adding nothing for a new user who
is still fiddling with options. The Help menu entry is the
self-service fallback.

## Sequencing with other field-notes items

Land after `PLAN-option-exclusion.md` — the first-run modal's
"minimum valid options" section references rules that only exist once
the option-exclusion logic is in place. Writing the modal first means
rewriting it when §3 ships.
