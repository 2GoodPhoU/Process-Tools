# Field notes — work-network testing

Tested 2026-04-23: ~50% success rate. Five observations logged.

First real pass on a work-network machine (the environment the tool is actually meant for). Roughly half of runs produced usable output; the other half failed or degraded in ways worth tracking. Observations grouped by category, with the NLP/actor-ID issue flagged as the priority blocker because it's the one preventing real-world use rather than first-run friction.

Matches the voice of `REVIEW.md` — no implementation here, just what was seen and where to dig next.

---

## 1. Actor-identification inaccuracies tied to NLP availability

**Category:** Environmental constraint + accuracy issue
**Severity:** Blocker (highest priority — blocks real-world use on the target network)
**Status (2026-04-24):** Path (a) selected — PyInstaller bundle with spaCy + `en_core_web_sm` 3.7.1 pre-baked. All build scaffolding landed: NLP pins active in `packaging/build-requirements.txt`, pinned model-wheel URL in the build recipe, step-by-step smoke-test runbook at `docs/NLP_BUNDLE_SMOKE_TEST.md`. Final validation is the manual build + work-network smoke test (Eric to run).

Actor-ID depends heavily on NLP being present. The work network where the tool is actually used does not have NLP available (model/dependency not installable through the network's package path). Without NLP, actor extraction accuracy drops to the point where output is not trustworthy. Rule-based / regex fallback alone isn't carrying the load on real documents.

**Suggested fix direction**

- (a) Ship the NLP model/dependency *inside* the tool's install bundle so it works fully offline on the work network. This is the cleanest outcome if the model size / licensing cooperates.
- (b) Strengthen a non-NLP fallback — rule-based actor extraction tuned against the documents we actually run on — so the tool degrades gracefully when NLP is absent.
- (c) Split the workflow: pre-process on a connected machine where NLP is available, then import the resulting actors xlsx (`--actors`) on the restricted network. Already supported mechanically; the question is whether the operational flow is acceptable.

**Open questions**

- What's the size and license of the spaCy model (or whichever NLP dependency) if we bundle it? Is bundling actually allowed under the network's software-approval policy?
- Is option (c) — pre-process elsewhere, import actors — acceptable to Eric as a workaround, or does the tool need to stand alone on the restricted network?

---

## 2. GUI window opens half-visible

**Category:** UX bug
**Severity:** Minor (first-run friction, not a blocker)
**Status (2026-04-24):** ✅ Tier-1 fix shipped. `ExtractorApp._fit_window_to_content()` runs after `_build_ui()`, measures the layout's requested size, and grows the saved geometry to fit (never shrinks). `GuiSettings.window_geometry` default bumped from `760x560` to `900x760`. `minsize` pinned from the packed layout so the handle can't clip it. Regression tests in `tests/test_gui_state.py::TestWindowGeometryBump`. Tier-2 (scrollable canvas) deferred until field data says it's needed.

On launch, only roughly half of the GUI is visible. The rest of the controls are hidden below / beside the visible area until the user manually resizes the window. There's no visible indication that the window is resizable or that there's more content hidden — a new user could easily assume what they see is the whole tool.

**Suggested fix direction**

- Size the window to show the full GUI by default (measure content, set initial geometry accordingly).
- Add a scrollbar / scroll wheel support for the content area so content that exceeds the window is reachable without manual resize.
- Add a visual affordance — edge indicator, chevron, or similar — that hints at hidden content if we keep the current default size.

**Open questions**

- Is this specific to Windows on the work laptop, or does it reproduce on macOS / a clean Windows install? (Possible HiDPI / display-scaling interaction.)
- Preferred fix: resize-to-fit by default, or scrollable container?

**Root cause**

`ExtractorApp.__init__` calls `root.geometry(self.settings.window_geometry)` *before* the widgets are packed, and the default geometry in `GuiSettings` (`gui_state.py`) is `"760x560"`. On first launch — or any machine where the saved geometry is smaller than what the widgets need at the current DPI — Tk honours the too-small geometry and the lower half of the form is clipped. There is no `minsize()` call, so even manual resize is a guessing game.

**Tier 1 — trivial fix (apply directly).** Measure requested size after `_build_ui()`, grow the window to fit, and pin `minsize` so it can never shrink below the layout minimum. Also bump the default in `GuiSettings` so a deleted/absent `settings.json` still lands in a reasonable place on a fresh machine.

Patch against `requirements_extractor/gui.py` (`ExtractorApp.__init__`):

```diff
         self._build_ui()
+        self._fit_window_to_content()
         root.protocol("WM_DELETE_WINDOW", self._on_close)
```

Add this method to `ExtractorApp` (near `_build_ui`):

```python
def _fit_window_to_content(self) -> None:
    """Ensure the initial window is at least as big as the packed layout.

    Tk only computes widget requested sizes after an idle pass, so the
    ``root.geometry(...)`` call in ``__init__`` can't know how tall the
    form actually wants to be.  Running ``update_idletasks()`` forces
    geometry to settle, then we grow (never shrink) the saved size to
    cover the layout and pin ``minsize`` so the user can't accidentally
    clip the form by dragging the handle.
    """
    self.root.update_idletasks()
    req_w = self.root.winfo_reqwidth()
    req_h = self.root.winfo_reqheight()
    # Parse "WxH+X+Y" or "WxH"; fall back silently if the string is odd.
    saved_w, saved_h = req_w, req_h
    try:
        size_part = self.settings.window_geometry.split("+", 1)[0]
        sw, sh = size_part.split("x", 1)
        saved_w, saved_h = int(sw), int(sh)
    except (ValueError, AttributeError):
        pass
    final_w = max(saved_w, req_w)
    final_h = max(saved_h, req_h)
    self.root.geometry(f"{final_w}x{final_h}")
    self.root.minsize(req_w, req_h)
```

Patch against `requirements_extractor/gui_state.py` (`GuiSettings.window_geometry` default):

```diff
-    window_geometry: str = "760x560"
+    # Grew from 760x560 after field testing — the old default clipped the
+    # bottom half of the form on Windows HiDPI laptops.  Actual minsize
+    # is still pinned at runtime from the packed layout's reqheight.
+    window_geometry: str = "900x760"
```

This is a one-method addition plus two one-line edits; `minsize` alone would solve the acute symptom, but bumping the default avoids depending on `_fit_window_to_content` racing with the first `update_idletasks` on slow machines.

**Tier 2 — polish (follow-on, plan only).** If the layout keeps growing past what fits on small displays:
- Wrap the main `frm` in a `ttk.Frame` + `Canvas` + vertical `Scrollbar`, re-parent each section into the inner frame. `ScrolledText` already handles scroll for the log area; the surrounding form doesn't.
- Add a subtle chevron / "More below" label in the status row when `winfo_height() < reqheight` as a visual hint.
- Capture a Windows + macOS screenshot on a HiDPI display into the eventual `fixtures/` or `docs/` to pin the regression.

Tier 2 touches layout in ~10 places and is worth deferring until Tier 1 lands and we have a datapoint on whether it's still needed.

---

## 3. Missing option-exclusion logic

**Category:** Feature gap / UX correctness
**Severity:** Major (produces silently-useless runs)
**Status (2026-04-24):** ✅ Shipped (hard-disable variant). Centralised `_update_option_state()` in `gui.py` greys out req-only options in actors mode and force-resets their booleans so flipping modes is never a surprise. Pre-run validation messagebox in `_run` hard-blocks a requirements run with no secondary-actor source, listing the three ways to fix it. Guard is a pure function (`gui_state.has_secondary_actor_source`) covered by `tests/test_gui_state.py::TestHasSecondaryActorSource`.

The UI lets users run the tool in configurations that cannot produce useful output. Two specific cases observed:

- Running with neither NLP nor Actors enabled produces no useful output. At least one of the two should be required.
- Auto-actor-extraction doesn't work without NLP enabled — the option is selectable but silently non-functional.

The UI should enforce a minimal valid option set: disable / gray out dependent options when their prerequisites aren't met, and prevent Run when no viable combination is selected (with a clear message explaining why).

**Suggested fix direction**

- Dependency graph between options, enforced at the widget level (enable/disable) rather than only at run-time.
- Pre-run validation step that surfaces "this combination won't produce output because X" before the extraction starts.

**Open questions**

- Full matrix of valid option combinations — needs to be written down. Candidate for a section in `README.md` once finalized.
- Should invalid combinations be hard-disabled, or allowed with a warning banner? (Hard-disable is safer; warning is more flexible.)

---

## 4. Test-data constraint

**Category:** Test blocker / test-infrastructure gap
**Severity:** Major (supporting workstream — unblocks reliable testing of everything above)
**Status (2026-04-24):** ✅ Shipped — four new `procedural_*.docx` fixtures in `samples/procedures/` (plus paired `.reqx.yaml` configs) reproduce the failure modes observed on the work network: header-signal requirements without keywords, blank-actor continuation, multi-actor-cell resolution, bulleted/numbered list rows. Four parser changes (1a/1b/1c/1d) landed to handle them, with 36 regression tests in `tests/test_procedural_tables.py` pinning each case. Mixed-language and very-long stress fixtures still on the backlog.

The real documents Eric runs the tool on are controlled and can't be shared or committed. This means none of them can be used to seed automated tests or fixtures, and the current `samples/` and `test_data/` content only covers a narrow slice of what shows up in practice.

Need a set of hand-authored synthetic documents that:

- Exercise the failure modes observed in the field (items 1–3 above) without containing any controlled content.
- Cover the edge cases that drove the ~50% failure rate — document structure variations, actor-naming patterns, section layouts that the parser is currently getting wrong.
- Live somewhere obvious (`tests/fixtures/` or extending `samples/edge_cases/`) so future sessions can reproduce specific failures.

**Suggested fix direction**

- Stand up a `fixtures/` (or extend `samples/edge_cases/`) directory of synthetic `.docx` inputs, each one designed to reproduce a specific observed failure.
- As each fixture is added, write a test that asserts the expected output — pins the behavior so regressions show up.

**Open questions**

- Which specific structural patterns from the real documents are driving failures? (Needs Eric to characterize them at a shape-only level — e.g. "nested 2-column tables with merged cells in column 1" — without sharing the content itself.)
- Where should fixtures live — new `tests/fixtures/` or under existing `samples/edge_cases/`?

---

## 5. No onboarding / help

**Category:** UX gap
**Severity:** Minor (polish, comes after the blockers above)
**Status (2026-04-24):** ✅ All three surfaces shipped. Help menu (Getting started… / Open README / About), first-run modal in `gui_help.GettingStartedDialog` (dismissible-forever via `GuiSettings.onboarding_seen`), and hover-tooltips on the four non-obvious checkboxes (NLP, dry-run, auto-actors, statement-set). Persistence tested in `tests/test_gui_state.py::TestOnboardingSeen`.

The tool has no startup guide, tooltip, or in-app help. First-time users — and returning users coming back after time away — have to infer what each option does from context and the README. That's fine for the author; it's friction for anyone else on the team, and for Eric himself on re-entry.

**Suggested fix direction**

- First-run "getting started" modal that explains the two modes (requirements / actors), the NLP dependency, and the minimal valid option set (see item 3).
- Persistent **Help** menu with a brief walkthrough and links to README sections.
- Tooltip-on-hover for each option, describing what it does and any prerequisites.

**Open questions**

- Scope: full walkthrough, or just tooltips + a short Help panel? Tooltips alone are a much smaller lift.
- Should the first-run modal be dismissible-forever, or re-appear until a real run succeeds?

---

## Next steps — priority order

1. **Observation 3 (NLP / actor-ID on the work network)** — the only blocker. Decide between bundling the NLP model, strengthening the non-NLP fallback, or formalizing the pre-process-elsewhere workflow. Nothing else on this list matters if the tool can't produce trustworthy output in its target environment.
2. **Observation 1 (GUI half-visible on open)** — first-run friction; cheap to fix once the approach is chosen.
3. **Observation 2 (option-exclusion logic)** — closely related to #1 in spirit (first-run UX correctness) but more work. Also depends on writing down the valid-combination matrix.
4. **Observation 4 (test-data / fixtures)** — supporting workstream. Start this in parallel with #3 because fixtures for invalid-combination behavior and for NLP-absent behavior are needed to validate the fixes above.
5. **Observation 5 (onboarding / help)** — polish. Address once #1–#3 are stable, so the help content reflects the final behavior rather than being rewritten after each fix.
