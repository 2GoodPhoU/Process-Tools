> **STATUS: DISCHARGED (2026-04-24).**
> The hard-disable variant shipped in `gui.py` — centralised
> `_update_option_state()` helper, delegated through from
> `_on_mode_change`, and the pre-run validation messagebox in `_run`
> that hard-blocks a requirements run with no secondary-actor source.
> The pure guard lives in `gui_state.has_secondary_actor_source` so
> it's unit-testable without a Tk root. Tests in
> `tests/test_gui_state.py::TestHasSecondaryActorSource` (6 tests).
> Kept in-tree for the design rationale; the implementation won't
> be re-derived.

---

# Plan — option-exclusion and pre-run validation

FIELD_NOTES §3. The GUI currently lets the user launch a run that cannot
produce useful output — specifically, a requirements run with no
secondary-actor source at all (no actors.xlsx, no NLP, no auto-harvest).
Actors mode has its own smaller trap where requirements-only options
(auto-actors, statement-set CSV, dry-run) remain live even though they
do nothing.

Two enforcement layers, in order of preference:

1. **Widget-level disable.** Grey out an option the moment its
   prerequisites disappear. Cheaper failure mode; the user never gets
   to a bad combination.
2. **Pre-run validation.** A short check inside `_run` / `_run_actors_scan`
   that blocks the extraction and explains *why* when the combination
   still slips through (e.g. the user typed a path into the actors field
   and then cleared it without re-running mode-change logic).

Messages should be diagnostic, not patronising — tell the user what's
missing and what to pick, not that their choice was wrong.

## Valid-combination matrix

| Mode           | Actors xlsx | NLP  | Auto-actors | Result |
|----------------|-------------|------|-------------|--------|
| requirements   | set         | any  | off         | OK — secondary actors from xlsx (+NLP if on). |
| requirements   | any         | any  | on          | OK — auto-harvest pass feeds the requirements run; xlsx is used as seed. NLP strengthens the scan. |
| requirements   | unset       | on   | off         | OK — secondary actors from NLP only. Lower recall; acceptable. |
| requirements   | unset       | off  | off         | **Invalid** — only primary-column actors will be captured. Block. |
| actors         | any         | any  | n/a         | OK — primary-column + regex from seed (+NLP if on). Auto-actors / statement-set / dry-run don't apply. |

`auto-actors` in actors mode is meaningless (the run *is* an actor
scan). Statement-set and dry-run are likewise requirements-only.

## Widget-level rules

Centralise the enable/disable logic in a single `_update_option_state`
method and call it from `_on_mode_change`, the NLP toggle, the
auto-actors toggle, and the actors-path entry's `<FocusOut>` / trace
callback. Keep it idempotent so firing it more than once is harmless.

Add to `gui.py` under `ExtractorApp` (place near `_on_mode_change`):

```python
def _update_option_state(self) -> None:
    """Enable/disable mode-dependent controls.

    Called whenever mode, NLP, auto-actors, or the actors path changes.
    Single source of truth so no callback forgets a widget.
    """
    mode = self.mode.get()
    is_requirements = mode == "requirements"

    # Requirements-only options — off means both disabled AND visually
    # de-emphasised so the user doesn't wonder why clicking does nothing.
    req_only_state = "normal" if is_requirements else "disabled"
    for widget in (
        getattr(self, "auto_actors_cb", None),
        getattr(self, "dry_run_cb", None),
        getattr(self, "ss_checkbox", None),
    ):
        if widget is not None:
            widget.config(state=req_only_state)

    # Statement-set path row follows the checkbox *and* the mode.
    self._toggle_statement_set()

    # If we just left requirements mode, force the req-only booleans off
    # so a subsequent toggle back doesn't surprise the user.
    if not is_requirements:
        self.auto_actors.set(False)
        self.dry_run.set(False)
```

Wire the checkboxes to call it. Minimal diff against the current
`_build_options_section`:

```diff
-        ttk.Checkbutton(
-            frame,
-            text=(
-                "Dry run \u2014 parse & count but don't write any files "
-                "(requirements mode only)"
-            ),
-            variable=self.dry_run,
-        ).pack(anchor="w", padx=4, pady=2)
+        self.dry_run_cb = ttk.Checkbutton(
+            frame,
+            text=(
+                "Dry run \u2014 parse & count but don't write any files "
+                "(requirements mode only)"
+            ),
+            variable=self.dry_run,
+        )
+        self.dry_run_cb.pack(anchor="w", padx=4, pady=2)
         self.auto_actors_cb = ttk.Checkbutton(
             frame,
             text=(
                 "Auto-harvest actors first \u2014 scans the inputs once to "
                 "build an actor list, then uses it for the requirements pass "
                 "(overrides the Actors list above; requirements mode only)"
             ),
-            variable=self.auto_actors,
+            variable=self.auto_actors,
+            command=self._update_option_state,
         )
         self.auto_actors_cb.pack(anchor="w", padx=4, pady=2)
```

Then, at the bottom of `_on_mode_change`, delegate to the new helper:

```diff
     def _on_mode_change(self) -> None:
         ...
-        self._toggle_statement_set()
-        if hasattr(self, "ss_checkbox"):
-            self.ss_checkbox.config(
-                state="normal" if mode == "requirements" else "disabled"
-            )
+        self._update_option_state()
         # Swap default output name if the user hasn't picked a custom path.
         current = self.output_file.get().strip()
         ...
```

And trigger it once at the end of `_build_ui` so startup reflects the
loaded settings:

```diff
         self._build_run_section(frm, pad)
-        # Apply initial mode-dependent state (enables/disables ss section
-        # and adjusts output default for the current mode).
-        self._on_mode_change()
+        # Apply initial mode-dependent state (enables/disables ss section
+        # and adjusts output default for the current mode).  Also runs
+        # _update_option_state so the dry-run / auto-actors / ss widgets
+        # match the mode before the user touches anything.
+        self._on_mode_change()
```

(The existing call already lands us in the right place since
`_on_mode_change` now delegates.)

## Pre-run validation

`_run` currently only warns on empty inputs and empty output path. Add
an early secondary-actor-source check in requirements mode. Keep the
message specific about the remedy.

Patch `_run` (requirements branch, right after the `out_path` check):

```python
# --- Requirements-mode sanity: at least one secondary-actor source --- #
if self.mode.get() == "requirements":
    has_actors_file = bool(self.actors_file.get().strip())
    using_nlp = bool(self.use_nlp.get())
    using_auto = bool(self.auto_actors.get())
    if not (has_actors_file or using_nlp or using_auto):
        messagebox.showwarning(
            "No actor source selected",
            (
                "Requirements mode needs at least one way to find "
                "secondary actors, or it will only capture the "
                "first-column (primary) actor for each row. Pick one:\n\n"
                " \u2022 Point \"Actors list\" at a curated .xlsx "
                "(Save template\u2026 generates a starter).\n"
                " \u2022 Enable \"Use NLP to detect secondary actors\" "
                "(requires spaCy + English model).\n"
                " \u2022 Enable \"Auto-harvest actors first\" to let the "
                "tool build a list from the inputs before the run."
            ),
        )
        return
```

For actors mode, the current `_run_actors_scan` is fine — even a run
with no seed and no NLP produces a useful primary-column actor list,
which is the mode's entire purpose.

## Optional third layer — runtime log annotation

Both orchestrators already append an NLP-unavailable warning to
`stats.errors` when `use_nlp=True` but spaCy can't load. That message
lands in the log after the run finishes; surface it earlier by checking
`ActorResolver.has_nlp()` *before* the parse loop and echoing through
`log()`. That way a user who ticked "Use NLP" on a network without
spaCy sees the downgrade before the first file is parsed rather than
after all of them are done. One-line addition in
`extract_from_files` and `scan_actors_from_files` — worth doing but
strictly polish.

## Tests to pin

- `test_gui_state.py` or new `test_option_state.py`: construct a
  `GuiSettings` with mode=actors and confirm the helper zeroes the
  req-only booleans; inverse for mode=requirements.
- New `test_run_validation.py` (headless — stub `messagebox`): the
  requirements path with no actors + no NLP + no auto-actors returns
  early without starting a worker thread.

## Effort estimate

Widget-level changes: ~1 hour. Pre-run check + messagebox: 30 min.
Tests: 1 hour. All landable in a single PR.

## Open question for Eric

Hard-disable vs. warn: this plan hard-disables requirements-only
controls in actors mode and hard-blocks Run on the no-actor-source
case. The alternative is a yellow banner at the top of the form that
says "this run will only capture primary actors — proceed anyway?".
Hard-disable is safer for a team context where a silent no-op run
wastes review time; keep-and-warn preserves flexibility for debugging
odd documents where the primary column is the only thing worth
capturing. Default plan above is hard-disable; flip a flag on
`_update_option_state` if you want the warning flavour instead.
