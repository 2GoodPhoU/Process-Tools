"""Tests for the 0.6.1 compound-requirement pre-pass.

Two layers of coverage:

1. **Pure-helper tests** — exercise :mod:`requirements_extractor.compound`
   directly with hand-rolled ``_BlockInfo`` records.  No docx involved.
   Pins detection rules, marker-stripping, connector inference, and the
   ``where:`` exclusion.  Cheap and headless.

2. **End-to-end fixture tests** — parse each of the five compound
   fixtures under ``samples/procedures/compound/`` and assert the
   row-level extraction matches the documented expectation for that
   case.  Together with the pure-helper layer this gives ten+
   independent assertions over the patch surface.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.compound import (
    CompoundGroup,
    _BlockInfo,
    _detect_connector,
    _ends_with_definition_leadin,
    _strip_marker,
    _strip_trailing_connector,
    aggregate,
    detect_groups,
    has_list_marker_prefix,
)
from requirements_extractor.config import Config, build_config, resolve_config
from requirements_extractor.parser import parse_docx


# ---------------------------------------------------------------------------
# Layer 1: pure-helper tests.
# ---------------------------------------------------------------------------


class TestListMarkerPrefix(unittest.TestCase):

    def test_dash_bullet_dot_glyph(self) -> None:
        self.assertTrue(has_list_marker_prefix("- item"))
        self.assertTrue(has_list_marker_prefix("• item"))
        self.assertTrue(has_list_marker_prefix("* item"))

    def test_em_dash_and_en_dash(self) -> None:
        self.assertTrue(has_list_marker_prefix("— item"))
        self.assertTrue(has_list_marker_prefix("– item"))

    def test_numbered_and_lettered(self) -> None:
        self.assertTrue(has_list_marker_prefix("1. item"))
        self.assertTrue(has_list_marker_prefix("12) item"))
        self.assertTrue(has_list_marker_prefix("a. item"))
        self.assertTrue(has_list_marker_prefix("b) item"))

    def test_roman_numerals(self) -> None:
        self.assertTrue(has_list_marker_prefix("i. item"))
        self.assertTrue(has_list_marker_prefix("iv) item"))
        self.assertTrue(has_list_marker_prefix("IV. item"))

    def test_negatives(self) -> None:
        self.assertFalse(has_list_marker_prefix("not a list"))
        self.assertFalse(has_list_marker_prefix("non-blocking task"))
        self.assertFalse(has_list_marker_prefix(""))
        self.assertFalse(has_list_marker_prefix("-no space"))


class TestMarkerStripping(unittest.TestCase):

    def test_strip_dash(self) -> None:
        self.assertEqual(_strip_marker("- foo bar"), "foo bar")

    def test_strip_numbered(self) -> None:
        self.assertEqual(_strip_marker("1. foo bar"), "foo bar")
        self.assertEqual(_strip_marker("12) foo"), "foo")

    def test_strip_bullet_glyph(self) -> None:
        self.assertEqual(_strip_marker("• foo"), "foo")

    def test_no_marker_returns_input(self) -> None:
        self.assertEqual(_strip_marker("plain text"), "plain text")


class TestConnectorStripping(unittest.TestCase):

    def test_strips_trailing_and(self) -> None:
        self.assertEqual(_strip_trailing_connector("foo, and"), "foo")

    def test_strips_trailing_or(self) -> None:
        self.assertEqual(_strip_trailing_connector("foo, or"), "foo")

    def test_strips_trailing_unless(self) -> None:
        self.assertEqual(_strip_trailing_connector("foo unless"), "foo")

    def test_no_connector_unchanged(self) -> None:
        self.assertEqual(_strip_trailing_connector("foo bar"), "foo bar")


class TestConnectorInference(unittest.TestCase):

    def test_all_and_yields_and(self) -> None:
        items = ["A, and", "B, and", "C"]
        self.assertEqual(_detect_connector(items), "and")

    def test_any_or_yields_or(self) -> None:
        items = ["A, or", "B, or", "C"]
        self.assertEqual(_detect_connector(items), "or")

    def test_unless_outranks_others(self) -> None:
        items = ["A, unless", "B, and", "C"]
        self.assertEqual(_detect_connector(items), "unless")

    def test_no_connectors_defaults_to_and(self) -> None:
        # Last item often has no trailing connector; absence of any
        # signal is the common case and must default to ``and``.
        items = ["A", "B", "C"]
        self.assertEqual(_detect_connector(items), "and")


class TestDefinitionLeadin(unittest.TestCase):

    def test_ends_with_where(self) -> None:
        self.assertTrue(_ends_with_definition_leadin("Define T(x) where:"))
        self.assertTrue(_ends_with_definition_leadin("...the envelope where"))

    def test_other_leadins_not_definition(self) -> None:
        self.assertFalse(
            _ends_with_definition_leadin("Programs shall comply if they:")
        )

    def test_case_insensitive(self) -> None:
        self.assertTrue(_ends_with_definition_leadin("...WHERE:"))


class TestAggregation(unittest.TestCase):

    def test_and_clause_format(self) -> None:
        out = aggregate(
            "X shall do Y if they:",
            ["- A, and", "- B, and", "- C"],
            "and",
        )
        self.assertIn("(all of)", out)
        self.assertIn("(1) A", out)
        self.assertIn("(2) B", out)
        self.assertIn("(3) C", out)

    def test_or_clause_format(self) -> None:
        out = aggregate(
            "Notify if any of:",
            ["- A, or", "- B"],
            "or",
        )
        self.assertIn("(any of)", out)

    def test_unless_clause_format(self) -> None:
        out = aggregate(
            "Apply patch unless:",
            ["- A, unless", "- B"],
            "unless",
        )
        self.assertIn("(unless any of)", out)


class TestDetectGroups(unittest.TestCase):
    """Hand-rolled _BlockInfo lists exercise detect_groups directly."""

    def test_canonical_and_pattern(self) -> None:
        blocks = [
            _BlockInfo(text="X shall comply if they:", is_paragraph=True),
            _BlockInfo(text="A, and", is_paragraph=True, has_marker_prefix=False, is_bullet=True),
            _BlockInfo(text="B, and", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="C", is_paragraph=True, is_bullet=True),
        ]
        groups = detect_groups(blocks)
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g.lead_in_idx, 0)
        self.assertEqual(g.item_indices, [1, 2, 3])
        self.assertEqual(g.connector, "and")

    def test_where_leadin_blocks_aggregation(self) -> None:
        blocks = [
            _BlockInfo(text="X shall use T(x) where:", is_paragraph=True),
            _BlockInfo(text="T is a metric", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="x is a count", is_paragraph=True, is_bullet=True),
        ]
        self.assertEqual(detect_groups(blocks), [])

    def test_no_modal_blocks_aggregation(self) -> None:
        # Lead-in ends with `:` and has bullets — but no modal verb.
        blocks = [
            _BlockInfo(text="The following items are noted:", is_paragraph=True),
            _BlockInfo(text="A", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="B", is_paragraph=True, is_bullet=True),
        ]
        self.assertEqual(detect_groups(blocks), [])

    def test_no_items_blocks_aggregation(self) -> None:
        # Lead-in matches but no list items follow — should not aggregate.
        blocks = [
            _BlockInfo(text="X shall comply if:", is_paragraph=True),
            _BlockInfo(
                text="Some unrelated paragraph.", is_paragraph=True
            ),
        ]
        self.assertEqual(detect_groups(blocks), [])

    def test_two_back_to_back_groups(self) -> None:
        # Two compound patterns in a row both detected independently.
        blocks = [
            _BlockInfo(text="X shall A if:", is_paragraph=True),
            _BlockInfo(text="cond1", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="cond2", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="Y must B if any of:", is_paragraph=True),
            _BlockInfo(text="cond3, or", is_paragraph=True, is_bullet=True),
            _BlockInfo(text="cond4", is_paragraph=True, is_bullet=True),
        ]
        groups = detect_groups(blocks)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].connector, "and")
        self.assertEqual(groups[1].connector, "or")


# ---------------------------------------------------------------------------
# Layer 2: end-to-end fixture tests.
# ---------------------------------------------------------------------------


COMPOUND_DIR = Path(__file__).resolve().parent.parent / "samples" / "procedures" / "compound"


def _parse_fixture(name: str):
    """Parse a fixture .docx; returns the requirements list."""
    docx = COMPOUND_DIR / name
    cfg = resolve_config(docx_path=docx)
    resolver = ActorResolver()
    return parse_docx(docx, resolver_fn=resolver.resolve, config=cfg)


class TestFixtureAndList(unittest.TestCase):
    """fixture_1_and_list.docx — Eric's canonical example."""

    def test_emits_one_compound_row(self) -> None:
        reqs = _parse_fixture("fixture_1_and_list.docx")
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 1)

    def test_compound_text_lists_all_four_items(self) -> None:
        reqs = _parse_fixture("fixture_1_and_list.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        for label in ("(1)", "(2)", "(3)", "(4)"):
            self.assertIn(label, compound.text)
        self.assertIn("(all of)", compound.text)

    def test_compound_text_includes_eric_phrasing(self) -> None:
        reqs = _parse_fixture("fixture_1_and_list.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        self.assertIn("Domestic US-Based program", compound.text)
        self.assertIn("12 months", compound.text)

    def test_notes_mention_compound(self) -> None:
        reqs = _parse_fixture("fixture_1_and_list.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        self.assertIn("Compound requirement", compound.notes)
        self.assertIn("and-joined", compound.notes)


class TestFixtureOrList(unittest.TestCase):

    def test_emits_one_compound_row(self) -> None:
        reqs = _parse_fixture("fixture_2_or_list.docx")
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 1)

    def test_or_clause_used(self) -> None:
        reqs = _parse_fixture("fixture_2_or_list.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        self.assertIn("(any of)", compound.text)
        self.assertIn("or-joined", compound.notes)


class TestFixtureMixedMarkers(unittest.TestCase):

    def test_emits_one_compound_row(self) -> None:
        reqs = _parse_fixture("fixture_3_mixed_markers.docx")
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 1)

    def test_handtyped_dash_item_claimed(self) -> None:
        reqs = _parse_fixture("fixture_3_mixed_markers.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        # The hand-typed dash item is the 4th in the list and should
        # appear in the aggregated text without its leading dash.
        self.assertIn("record the takeoff weight", compound.text)


class TestFixtureWhereDefinitions(unittest.TestCase):
    """Negative case: definition blocks must NOT aggregate."""

    def test_no_compound_row_emitted(self) -> None:
        reqs = _parse_fixture("fixture_4_where_definitions.docx")
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 0)

    def test_leadin_still_captured_as_regular_requirement(self) -> None:
        # The lead-in has a modal ("shall") so the legacy walker should
        # still emit it even though compound detection skipped it.
        reqs = _parse_fixture("fixture_4_where_definitions.docx")
        leadin_rows = [r for r in reqs if "throughput envelope" in r.text]
        self.assertGreaterEqual(len(leadin_rows), 1)


class TestFixtureUnlessExclusion(unittest.TestCase):

    def test_emits_one_compound_row(self) -> None:
        reqs = _parse_fixture("fixture_5_unless_exclusion.docx")
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 1)

    def test_unless_clause_used(self) -> None:
        reqs = _parse_fixture("fixture_5_unless_exclusion.docx")
        compound = next(r for r in reqs if "(compound)" in r.block_ref)
        self.assertIn("(unless any of)", compound.text)
        self.assertIn("unless-joined", compound.notes)


# ---------------------------------------------------------------------------
# Layer 3: config flag wiring + defensive disable.
# ---------------------------------------------------------------------------


class TestConfigFlag(unittest.TestCase):

    def test_default_enabled(self) -> None:
        self.assertTrue(Config.defaults().compound.enabled)

    def test_flat_compound_disable(self) -> None:
        cfg = build_config({"compound": {"enabled": False}})
        self.assertFalse(cfg.compound.enabled)

    def test_extraction_namespace_disable(self) -> None:
        cfg = build_config({"extraction": {"compound": {"enabled": False}}})
        self.assertFalse(cfg.compound.enabled)

    def test_extraction_namespace_unknown_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_config({"extraction": {"unknown": {}}})

    def test_disabled_falls_back_to_legacy(self) -> None:
        """When disabled, the lead-in is fragmentary and the bullets
        with no modal produce zero rows — the 0.6.0 behaviour."""
        from requirements_extractor.config import build_config
        from requirements_extractor.actors import ActorResolver
        cfg = build_config({"compound": {"enabled": False}})
        resolver = ActorResolver()
        reqs = parse_docx(
            COMPOUND_DIR / "fixture_1_and_list.docx",
            resolver_fn=resolver.resolve,
            config=cfg,
        )
        compound_rows = [r for r in reqs if "(compound)" in r.block_ref]
        self.assertEqual(len(compound_rows), 0)


if __name__ == "__main__":
    unittest.main()
