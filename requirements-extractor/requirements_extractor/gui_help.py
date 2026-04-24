"""Help surfaces for the Tk GUI.

FIELD_NOTES §5 / PLAN-onboarding.md.  Split out of ``gui.py`` to keep
that module under control as the UI grows.  Contains:

* :class:`GettingStartedDialog` — the first-run modal.  Walks the user
  through the two modes, the NLP dependency, and the minimum valid
  option set.  Persists its "Don't show again" choice via
  :attr:`gui_state.GuiSettings.onboarding_seen`.
* :class:`Tooltip` — a lightweight hover-tooltip helper (no extra
  dependencies) used to decorate the handful of options whose semantics
  aren't obvious from the label alone.

Neither class requires tkinterdnd2 and both degrade politely if the
platform's Tk lacks some of the advanced window-manager hints.
"""

from __future__ import annotations

from tkinter import BooleanVar, Tk, Toplevel, ttk
from typing import Any, Optional


# ---------------------------------------------------------------------------
# First-run modal
# ---------------------------------------------------------------------------


class GettingStartedDialog:
    """Modal 'first-run' dialog.

    A Toplevel window with a short walkthrough, a 'Don't show this
    again' checkbox, and a Close button.  Deliberately plain Tk — no
    images, no extra dependencies — so it ships in the same install
    footprint as the rest of the GUI.

    Pass ``settings`` to have the dialog flip
    :attr:`GuiSettings.onboarding_seen` when the user ticks 'Don't show
    again'.  Omit it when the dialog is opened via Help → Getting
    started… (we only want the auto-trigger at startup to honour the
    preference; a manually-opened dialog should not silently record a
    "don't show" decision on close).
    """

    def __init__(
        self,
        root: Tk,
        *,
        settings: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.top = top = Toplevel(root)
        top.title("Getting started with Document Data Extractor")
        try:
            top.transient(root)
        except Exception:  # pragma: no cover — some WMs refuse this
            pass
        try:
            top.grab_set()
        except Exception:  # pragma: no cover
            pass
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
                "sentence.  Actors mode harvests a canonical actors "
                "list you can feed back in on the next run via the "
                "Actors field.",
            ),
            (
                "NLP dependency",
                '"Use NLP" improves secondary-actor recall via spaCy. '
                "If spaCy isn't installed the run still completes — "
                "you just get fewer actors.  On networks where spaCy "
                "can't be installed, see the Offline workflow section "
                "in the README.",
            ),
            (
                "Minimum valid options",
                "Requirements mode needs at least one secondary-actor "
                "source: an Actors list, the NLP option, or Auto-"
                "harvest.  Without one of these, only the first-column "
                "actor is captured and the output can be misleading.",
            ),
            (
                "Per-run settings persist",
                "Your window size, last-used paths, and checkbox "
                "states are remembered between launches.  Delete "
                "~/.requirements_extractor/settings.json to reset.",
            ),
        ]
        for title, body in sections:
            ttk.Label(frm, text=title, font=("Arial", 10, "bold")).pack(
                anchor="w", pady=(8, 0),
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

        # Centre on the root window.  wait/update so widget sizes are
        # settled before we read them.
        try:
            top.update_idletasks()
            rx = (
                root.winfo_rootx()
                + (root.winfo_width() // 2)
                - (top.winfo_width() // 2)
            )
            ry = (
                root.winfo_rooty()
                + (root.winfo_height() // 2)
                - (top.winfo_height() // 2)
            )
            top.geometry(f"+{max(rx, 0)}+{max(ry, 0)}")
        except Exception:  # pragma: no cover — geometry is nice-to-have
            pass

        top.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self) -> None:
        if (
            self.dont_show.get()
            and self.settings is not None
            and hasattr(self.settings, "onboarding_seen")
        ):
            self.settings.onboarding_seen = True
        try:
            self.top.grab_release()
        except Exception:  # pragma: no cover
            pass
        self.top.destroy()


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------


class Tooltip:
    """Hover-tooltip for a Tk widget.

    Minimal.  Shows the given text in a borderless Toplevel when the
    cursor enters the widget; hides it on leave.  Delay is fixed at
    500 ms so a brief hover doesn't flash content at the user.
    """

    _DELAY_MS = 500

    def __init__(self, widget: Any, text: str) -> None:
        self.widget = widget
        self.text = text
        self._after_id: Optional[str] = None
        self._tip: Optional[Toplevel] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event: Any) -> None:
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _on_leave(self, _event: Any) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:  # pragma: no cover
                pass
            self._after_id = None
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:  # pragma: no cover
                pass
            self._tip = None

    def _show(self) -> None:
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        tip = Toplevel(self.widget)
        try:
            tip.wm_overrideredirect(True)
        except Exception:  # pragma: no cover
            pass
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
