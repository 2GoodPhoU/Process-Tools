"""Tests for the REVIEW §1.6 + §3.2 + §3.9 + §3.13 + auto-actors batch.

Covers:

* ``config.load_keywords_raw`` — YAML "tweak" schema, YAML "replace"
  schema, text-format, error cases, and the reject-mix guard.
* ``detector._apply_add_remove`` — with the ``"*"`` wipe-baseline sentinel.
* ``statement_set.events_to_rows`` — preamble bucket (§1.6) and H2/H3
  routing (§3.9).
* ``cli.main`` — exit codes 0/1/2/130 (§3.13) and the ``--keywords`` +
  ``--auto-actors`` flags.
* ``gui_state.GuiSettings`` — the two new persisted fields round-trip
  (``last_keywords_path``, ``auto_actors``).

Run:  python -m unittest tests.test_batch_improvements
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from textwrap import dedent

from requirements_extractor.config import load_keywords_raw
from requirements_extractor.detector import (
    HARD_KEYWORDS,
    SOFT_KEYWORDS,
    KeywordMatcher,
    _apply_add_remove,
)
from requirements_extractor.gui_state import GuiSettings
from requirements_extractor.models import (
    HeadingEvent,
    Requirement,
    RequirementEvent,
    SectionRowEvent,
)
from requirements_extractor.statement_set import events_to_rows


ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# §3.2 — load_keywords_raw (YAML tweak schema)
# ---------------------------------------------------------------------------


class TestLoadKeywordsYamlTweak(unittest.TestCase):
    def _write(self, body: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "kw.yaml"
        p.write_text(dedent(body), encoding="utf-8")
        return p

    def test_tweak_schema_loads(self) -> None:
        p = self._write(
            """
            hard_add: [is to, are to]
            hard_remove: [will]
            soft_add: [anticipated]
            soft_remove: []
            """
        )
        raw = load_keywords_raw(p)
        self.assertEqual(set(raw["hard_add"]), {"is to", "are to"})
        self.assertEqual(raw["hard_remove"], ["will"])
        self.assertEqual(raw["soft_add"], ["anticipated"])
        self.assertEqual(raw["soft_remove"], [])

    def test_empty_file_gives_empty_lists(self) -> None:
        p = self._write("")
        raw = load_keywords_raw(p)
        self.assertEqual(raw["hard_add"], [])
        self.assertEqual(raw["hard_remove"], [])
        self.assertEqual(raw["soft_add"], [])
        self.assertEqual(raw["soft_remove"], [])

    def test_null_value_coerces_to_empty_list(self) -> None:
        p = self._write(
            """
            hard_add: null
            """
        )
        raw = load_keywords_raw(p)
        self.assertEqual(raw["hard_add"], [])


# ---------------------------------------------------------------------------
# §3.2 — load_keywords_raw (YAML replace schema + sentinel translation)
# ---------------------------------------------------------------------------


class TestLoadKeywordsYamlReplace(unittest.TestCase):
    def _write(self, body: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "kw.yaml"
        p.write_text(dedent(body), encoding="utf-8")
        return p

    def test_replace_hard_emits_wipe_sentinel(self) -> None:
        p = self._write(
            """
            hard: [shall, must]
            """
        )
        raw = load_keywords_raw(p)
        # "replace" shape translates to: wipe baseline, then add the new set.
        self.assertEqual(raw["hard_remove"], ["*"])
        self.assertEqual(set(raw["hard_add"]), {"shall", "must"})

    def test_replace_soft_emits_wipe_sentinel(self) -> None:
        p = self._write(
            """
            soft: [should, may]
            """
        )
        raw = load_keywords_raw(p)
        self.assertEqual(raw["soft_remove"], ["*"])
        self.assertEqual(set(raw["soft_add"]), {"should", "may"})

    def test_replace_and_tweak_across_buckets_allowed(self) -> None:
        # Replacing HARD but tweaking SOFT is fine — the contradiction rule
        # only fires within a single bucket.
        p = self._write(
            """
            hard: [shall]
            soft_add: [anticipated]
            """
        )
        raw = load_keywords_raw(p)
        self.assertEqual(raw["hard_remove"], ["*"])
        self.assertEqual(raw["hard_add"], ["shall"])
        self.assertEqual(raw["soft_add"], ["anticipated"])


# ---------------------------------------------------------------------------
# §3.2 — load_keywords_raw (error cases)
# ---------------------------------------------------------------------------


class TestLoadKeywordsErrors(unittest.TestCase):
    def _write(self, name: str, body: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / name
        p.write_text(dedent(body), encoding="utf-8")
        return p

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_keywords_raw(Path("/nonexistent/kw.yaml"))

    def test_unknown_extension_is_rejected(self) -> None:
        p = self._write("kw.json", "{}")
        with self.assertRaises(ValueError) as ctx:
            load_keywords_raw(p)
        self.assertIn("unsupported keywords file extension", str(ctx.exception))

    def test_mixing_replace_and_tweak_same_bucket_is_rejected(self) -> None:
        p = self._write(
            "kw.yaml",
            """
            hard: [shall]
            hard_add: [is to]
            """,
        )
        with self.assertRaises(ValueError) as ctx:
            load_keywords_raw(p)
        self.assertIn("hard", str(ctx.exception))

    def test_unknown_top_level_key_is_rejected(self) -> None:
        p = self._write(
            "kw.yaml",
            """
            hard_add: [shall]
            nonsense: [x]
            """,
        )
        with self.assertRaises(ValueError) as ctx:
            load_keywords_raw(p)
        self.assertIn("unknown keys", str(ctx.exception))

    def test_non_list_value_is_rejected(self) -> None:
        p = self._write(
            "kw.yaml",
            """
            hard_add: shall
            """,
        )
        with self.assertRaises(ValueError) as ctx:
            load_keywords_raw(p)
        self.assertIn("list", str(ctx.exception))

    def test_non_mapping_root_is_rejected(self) -> None:
        p = self._write("kw.yaml", "[1, 2, 3]\n")
        with self.assertRaises(ValueError):
            load_keywords_raw(p)


# ---------------------------------------------------------------------------
# §3.2 — load_keywords_raw (text format)
# ---------------------------------------------------------------------------


class TestLoadKeywordsTextFormat(unittest.TestCase):
    def _write(self, body: str, suffix: str = ".txt") -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / f"kw{suffix}"
        p.write_text(dedent(body), encoding="utf-8")
        return p

    def test_basic_sections(self) -> None:
        p = self._write(
            """
            # comment
            [hard_add]
            is to
            are to

            [hard_remove]
            will

            [soft_add]
            anticipated
            """
        )
        raw = load_keywords_raw(p)
        self.assertEqual(set(raw["hard_add"]), {"is to", "are to"})
        self.assertEqual(raw["hard_remove"], ["will"])
        self.assertEqual(raw["soft_add"], ["anticipated"])

    def test_kw_extension_accepted(self) -> None:
        p = self._write("shall\nmust\n", suffix=".kw")
        raw = load_keywords_raw(p)
        # Entries before any section marker default to hard_add.
        self.assertEqual(set(raw["hard_add"]), {"shall", "must"})

    def test_unknown_section_marker_rejected(self) -> None:
        p = self._write("[bogus]\nshall\n")
        with self.assertRaises(ValueError):
            load_keywords_raw(p)


# ---------------------------------------------------------------------------
# §3.2 — _apply_add_remove with the "*" sentinel + KeywordMatcher wiring
# ---------------------------------------------------------------------------


class TestApplyAddRemoveSentinel(unittest.TestCase):
    def test_wipe_sentinel_clears_baseline(self) -> None:
        result = _apply_add_remove(
            baseline={"shall", "must", "required"},
            add=["is to"],
            remove=["*"],
        )
        self.assertEqual(result, {"is to"})

    def test_wipe_sentinel_plus_other_removes_still_just_wipes(self) -> None:
        # Once we see "*", any explicit removes are moot — the bucket is
        # empty before the adds are merged in.
        result = _apply_add_remove(
            baseline={"shall", "must"},
            add=["x"],
            remove=["*", "shall"],
        )
        self.assertEqual(result, {"x"})

    def test_no_sentinel_is_normal_diff(self) -> None:
        result = _apply_add_remove(
            baseline={"shall", "must"},
            add=["is to"],
            remove=["must"],
        )
        self.assertEqual(result, {"shall", "is to"})

    def test_adds_dont_treat_sentinel_as_keyword(self) -> None:
        # A "*" accidentally left in the add list should NOT become a
        # keyword — it's strictly a remove-side sentinel.
        result = _apply_add_remove(
            baseline=set(),
            add=["*", "shall"],
            remove=[],
        )
        self.assertEqual(result, {"shall"})


class TestKeywordMatcherWithReplaceShape(unittest.TestCase):
    """End-to-end: load a keywords file, build a KeywordMatcher, classify."""

    def test_hard_replace_narrows_the_bucket(self) -> None:
        d = tempfile.mkdtemp()
        p = Path(d) / "kw.yaml"
        p.write_text("hard: [shall]\n", encoding="utf-8")
        raw = load_keywords_raw(p)

        # Build a KeywordsConfig-like object and feed it in.
        class KW:
            hard_add = raw["hard_add"]
            hard_remove = raw["hard_remove"]
            soft_add = raw["soft_add"]
            soft_remove = raw["soft_remove"]

        matcher = KeywordMatcher.from_config(KW)
        self.assertEqual(matcher.hard, {"shall"})  # baseline wiped, only 'shall' left
        # Built-in 'must' is gone — the replace schema dropped it.
        req_type, _kw, _conf = matcher.classify("The system must respond in 5s.")
        self.assertNotEqual(req_type, "Hard")
        req_type2, _kw2, _conf2 = matcher.classify("The system shall respond in 5s.")
        self.assertEqual(req_type2, "Hard")


# ---------------------------------------------------------------------------
# §1.6 + §3.9 — statement-set routing
# ---------------------------------------------------------------------------


def _make_req(primary: str, text: str, row_ref: str = "Table 1, Row 2") -> RequirementEvent:
    """Minimal RequirementEvent for statement-set tests."""
    req = Requirement(
        order=1,
        source_file="spec.docx",
        heading_trail="",
        section_topic=primary,
        row_ref=row_ref,
        block_ref="Paragraph 1",
        primary_actor=primary,
        secondary_actors=[],
        text=text,
        req_type="Hard",
        keywords=["shall"],
        confidence="High",
    )
    return RequirementEvent(requirement=req)


class TestStatementSetPreamble(unittest.TestCase):
    """§1.6 — requirements with row_ref='Preamble' land in a bucket."""

    def test_preamble_req_routed_under_preamble_bucket(self) -> None:
        events = [
            HeadingEvent(level=1, text="Chapter 1"),
            _make_req("", "This is preamble prose.", row_ref="Preamble"),
        ]
        rows = events_to_rows(events)
        # Expect: L1 anchor, "(preamble)" L2 bucket anchor, then the requirement at L3.
        all_text = "\n".join(" | ".join(r) for r in rows)
        self.assertIn("Chapter 1", all_text)
        self.assertIn("(preamble)", all_text)
        # The requirement row is last and carries the text.
        self.assertTrue(any("preamble prose" in cell for row in rows for cell in row))

    def test_preamble_bucket_appears_once_even_with_many_reqs(self) -> None:
        events = [
            HeadingEvent(level=1, text="Chapter 1"),
            _make_req("", "First preamble.", row_ref="Preamble"),
            _make_req("", "Second preamble.", row_ref="Preamble"),
        ]
        rows = events_to_rows(events)
        bucket_hits = sum(
            1 for r in rows
            if r[2] == "(preamble)"  # Level 2 title column
        )
        self.assertEqual(bucket_hits, 1)

    def test_empty_hierarchy_still_emits_requirements(self) -> None:
        """Degenerate case: no H1, no H2, no section row, no preamble marker
        either — requirements should still reach the output under the
        empty-hierarchy fallback."""
        events = [_make_req("Auth Service", "The Auth Service shall X.")]
        rows = events_to_rows(events)
        # Must emit at least one row with the requirement text.
        self.assertTrue(any("shall X" in cell for row in rows for cell in row))


class TestStatementSetHeadingPlumbing(unittest.TestCase):
    """§3.9 — H2 / H3 are respected as structural levels."""

    def test_h2_emits_at_level_2(self) -> None:
        events = [
            HeadingEvent(level=1, text="Top"),
            HeadingEvent(level=2, text="Sub"),
        ]
        rows = events_to_rows(events)
        # Look for a row where column index 2 (Level 2) == "Sub".
        l2_titles = [r[2] for r in rows if r[2]]
        self.assertIn("Sub", l2_titles)

    def test_h3_with_h2_emits_at_level_3(self) -> None:
        events = [
            HeadingEvent(level=1, text="Top"),
            HeadingEvent(level=2, text="Sub"),
            HeadingEvent(level=3, text="SubSub"),
        ]
        rows = events_to_rows(events)
        l3_titles = [r[4] for r in rows if r[4]]  # Level 3 title column
        self.assertIn("SubSub", l3_titles)

    def test_h3_without_h2_emits_at_level_2(self) -> None:
        """When a document skips H2 entirely, emit H3 at L2 — do NOT
        invent a missing L2."""
        events = [
            HeadingEvent(level=1, text="Top"),
            HeadingEvent(level=3, text="Deep"),
        ]
        rows = events_to_rows(events)
        l2_titles = [r[2] for r in rows if r[2]]
        self.assertIn("Deep", l2_titles)

    def test_new_h1_resets_subtree(self) -> None:
        """A new H1 wipes H2/H3 state so subsequent content doesn't
        think it's still under the old H2."""
        events = [
            HeadingEvent(level=1, text="Alpha"),
            HeadingEvent(level=2, text="A-Sub"),
            HeadingEvent(level=1, text="Beta"),
            _make_req("Auth Service", "Beta requirement."),
        ]
        rows = events_to_rows(events)
        # The requirement must land under Beta with no A-Sub context.
        # Find the requirement row by matching on text.
        req_row = next(r for r in rows if any("Beta requirement." in c for c in r))
        # A-Sub must not appear in the same row.
        self.assertNotIn("A-Sub", req_row)

    def test_requirement_level_is_clamped_to_header_width(self) -> None:
        """If nesting goes beyond the header width, requirement level
        clamps at _HEADER_LEVEL_PAIRS (5) instead of blowing past it."""
        from requirements_extractor.statement_set import _HEADER_LEVEL_PAIRS
        events = [
            HeadingEvent(level=1, text="L1"),
            HeadingEvent(level=2, text="L2"),
            HeadingEvent(level=3, text="L3"),
            SectionRowEvent(title="SecRow", intro="", row_ref="Table 1, Row 1"),
            _make_req("Actor", "Deep requirement."),
        ]
        rows = events_to_rows(events)
        req_row = next(r for r in rows if any("Deep requirement." in c for c in r))
        # Row must have at most (_HEADER_LEVEL_PAIRS + 1) * 2 columns.
        self.assertEqual(len(req_row), (_HEADER_LEVEL_PAIRS + 1) * 2)


# ---------------------------------------------------------------------------
# §3.13 — CLI exit codes + --auto-actors + --keywords flag parsing
# ---------------------------------------------------------------------------


class TestCliExitCodes(unittest.TestCase):
    def test_exit_ok_is_zero(self) -> None:
        from requirements_extractor.cli import EXIT_OK
        self.assertEqual(EXIT_OK, 0)

    def test_exit_usage_is_two(self) -> None:
        from requirements_extractor.cli import EXIT_USAGE
        self.assertEqual(EXIT_USAGE, 2)

    def test_exit_runtime_is_one(self) -> None:
        from requirements_extractor.cli import EXIT_RUNTIME
        self.assertEqual(EXIT_RUNTIME, 1)

    def test_missing_subcommand_returns_usage(self) -> None:
        from requirements_extractor.cli import main, EXIT_USAGE
        with redirect_stderr(io.StringIO()):
            rc = main([])
        self.assertEqual(rc, EXIT_USAGE)

    def test_no_docx_found_returns_usage(self) -> None:
        """Pointing the CLI at a folder with no .docx children should
        return the usage exit code, not runtime."""
        from requirements_extractor.cli import main, EXIT_USAGE
        with tempfile.TemporaryDirectory() as d:
            empty = Path(d)
            with redirect_stderr(io.StringIO()):
                rc = main(["requirements", str(empty)])
            self.assertEqual(rc, EXIT_USAGE)

    def test_bad_keywords_file_soft_warns_and_completes(self) -> None:
        """A keywords file that doesn't exist is captured as a WARNING
        in stats.errors and the run still completes — the CLI reports a
        non-fatal warning rather than failing the whole batch.  This
        matches --config's behaviour so both flags are consistent."""
        from requirements_extractor.cli import main, EXIT_OK
        sample = ROOT / "samples" / "sample_spec.docx"
        if not sample.exists():
            self.skipTest("sample_spec.docx not available")
        out_buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            with redirect_stderr(io.StringIO()), redirect_stdout(out_buf):
                rc = main([
                    "--keywords", str(Path(d) / "nope.yaml"),
                    "requirements", str(sample),
                    "-o", str(out),
                ])
        self.assertEqual(rc, EXIT_OK)
        # The warning message should surface in progress/summary output.
        self.assertIn("keywords", out_buf.getvalue().lower())

    def test_help_exits_zero_via_systemexit(self) -> None:
        """argparse raises SystemExit(0) for --help.  We exercise that
        path to guard the RawDescriptionHelpFormatter / epilog wiring
        doesn't crash at format time."""
        from requirements_extractor.cli import build_parser
        parser = build_parser()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                parser.parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)


class TestCliKeywordsAndAutoActorsFlags(unittest.TestCase):
    def test_keywords_flag_parses(self) -> None:
        from requirements_extractor.cli import build_parser
        args = build_parser().parse_args([
            "--keywords", "kw.yaml",
            "requirements", "spec.docx",
        ])
        self.assertEqual(args.keywords, Path("kw.yaml"))

    def test_auto_actors_flag_parses(self) -> None:
        from requirements_extractor.cli import build_parser
        args = build_parser().parse_args([
            "requirements", "spec.docx", "--auto-actors",
        ])
        self.assertTrue(args.auto_actors)

    def test_auto_actors_default_is_false(self) -> None:
        from requirements_extractor.cli import build_parser
        args = build_parser().parse_args(["requirements", "spec.docx"])
        self.assertFalse(args.auto_actors)

    def test_keywords_default_is_none(self) -> None:
        from requirements_extractor.cli import build_parser
        args = build_parser().parse_args(["requirements", "spec.docx"])
        self.assertIsNone(args.keywords)


# ---------------------------------------------------------------------------
# Auto-actors end-to-end (produces the sidecar file)
# ---------------------------------------------------------------------------


class TestAutoActorsEndToEnd(unittest.TestCase):
    def test_auto_actors_writes_sidecar(self) -> None:
        from requirements_extractor.cli import main
        sample = ROOT / "samples" / "sample_spec.docx"
        if not sample.exists():
            self.skipTest("sample_spec.docx not available")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            with redirect_stdout(io.StringIO()):
                rc = main([
                    "--no-summary", "-q",
                    "requirements", str(sample),
                    "--auto-actors",
                    "-o", str(out),
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists(), "requirements output missing")
            sidecar = out.with_name(f"{out.stem}_auto_actors.xlsx")
            self.assertTrue(sidecar.exists(), f"sidecar actors file missing: {sidecar}")


# ---------------------------------------------------------------------------
# GuiSettings — new persisted fields
# ---------------------------------------------------------------------------


class TestGuiSettingsBatchFields(unittest.TestCase):
    def test_new_fields_default_sanely(self) -> None:
        s = GuiSettings()
        self.assertEqual(s.last_keywords_path, "")
        self.assertFalse(s.auto_actors)

    def test_round_trip_preserves_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            before = GuiSettings(
                last_keywords_path="/tmp/kw.yaml",
                auto_actors=True,
            )
            before.save(p)
            after = GuiSettings.load(p)
            self.assertEqual(after.last_keywords_path, "/tmp/kw.yaml")
            self.assertTrue(after.auto_actors)

    def test_load_tolerates_missing_new_fields(self) -> None:
        """Older settings files (pre-batch) don't have the new keys —
        loading them must still succeed and fall back to defaults."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text(
                json.dumps({
                    "schema_version": 1,
                    "window_geometry": "800x600",
                    "use_nlp": True,
                }),
                encoding="utf-8",
            )
            after = GuiSettings.load(p)
            self.assertEqual(after.window_geometry, "800x600")
            self.assertTrue(after.use_nlp)
            # New fields → defaults, not errors.
            self.assertEqual(after.last_keywords_path, "")
            self.assertFalse(after.auto_actors)

    def test_wrong_type_new_field_falls_back_to_default(self) -> None:
        """A user who hand-edited the JSON and put a string where a bool
        is expected shouldn't crash the GUI."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text(
                json.dumps({"auto_actors": "yes please"}),
                encoding="utf-8",
            )
            after = GuiSettings.load(p)
            self.assertFalse(after.auto_actors)


# ---------------------------------------------------------------------------
# Sanity: the baseline lists still hold what we depend on elsewhere
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
