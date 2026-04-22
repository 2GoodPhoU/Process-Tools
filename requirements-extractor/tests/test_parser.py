"""Integration tests for the parser using samples/sample_spec.docx.

These are integration-flavoured but kept light: they assert on expected
counts and a few specific rows rather than on every detail so they don't
become brittle.

Run:  python -m unittest tests.test_parser
"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.config import Config, resolve_config
from requirements_extractor.models import RequirementEvent, SectionRowEvent
from requirements_extractor.parser import parse_docx, parse_docx_events


SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_spec.docx"


def _reqs(events):
    return [e.requirement for e in events if isinstance(e, RequirementEvent)]


class TestParserDefaults(unittest.TestCase):
    """Parser behaviour against the sample spec with built-in defaults."""

    def setUp(self) -> None:
        self.resolver = ActorResolver([])
        self.events = parse_docx_events(SAMPLE, self.resolver.resolve)
        self.reqs = _reqs(self.events)

    def test_finds_expected_count(self) -> None:
        # 15 against the committed sample (stable baseline).
        self.assertEqual(len(self.reqs), 15)

    def test_hard_soft_split(self) -> None:
        hard = [r for r in self.reqs if r.req_type == "Hard"]
        soft = [r for r in self.reqs if r.req_type == "Soft"]
        # 'will' is SOFT by default, so "Sessions will expire" lands in soft.
        # 7 hard / 8 soft (the extra soft is the Note paragraph that
        # matches on "should").
        self.assertEqual(len(hard), 7)
        self.assertEqual(len(soft), 8)

    def test_polarity_field_populated(self) -> None:
        """Every extracted requirement carries a polarity."""
        for r in self.reqs:
            self.assertIn(r.polarity, ("Positive", "Negative"))

    def test_default_polarity_is_positive(self) -> None:
        """The sample spec has no negated modals, so all rows are Positive.

        The Note row DOES contain "should not" and is our single Negative
        fixture; everything else is Positive.
        """
        negatives = [r for r in self.reqs if r.polarity == "Negative"]
        self.assertEqual(len(negatives), 1)
        self.assertIn("should not appear", negatives[0].text)

    def test_section_row_events_emitted(self) -> None:
        """Section rows like '3.1 Authentication' become SectionRowEvents."""
        titles = [
            e.title for e in self.events if isinstance(e, SectionRowEvent)
        ]
        self.assertIn("3.1 Authentication", titles)
        self.assertIn("3.2 Telemetry", titles)
        self.assertIn("3.3 Payload Operations", titles)

    def test_section_topic_is_distinct_from_actor(self) -> None:
        """Regression guard: the §2.1 fix must stay fixed.

        Previously ``section_topic`` duplicated ``primary_actor``; the fix
        was to carry the last SectionRowEvent title instead.
        """
        for r in self.reqs:
            if r.primary_actor and r.section_topic:
                self.assertNotEqual(
                    r.primary_actor, r.section_topic,
                    f"section_topic should not equal primary_actor: {r!r}",
                )

    def test_primary_actor_populated_for_actor_rows(self) -> None:
        actors = {r.primary_actor for r in self.reqs if r.primary_actor}
        self.assertIn("Auth Service", actors)
        self.assertIn("Flight Software", actors)
        self.assertIn("Payload Operator", actors)
        self.assertIn("Ground Control", actors)

    def test_all_rows_have_block_refs(self) -> None:
        for r in self.reqs:
            self.assertTrue(r.block_ref, f"missing block_ref on {r!r}")

    def test_order_is_monotonically_increasing(self) -> None:
        orders = [r.order for r in self.reqs]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(orders[0], 1)


class TestParserShims(unittest.TestCase):
    """Backward-compat shims — don't break existing callers."""

    def test_parse_docx_accepts_string_path(self) -> None:
        resolver = ActorResolver([])
        reqs = parse_docx(str(SAMPLE), resolver.resolve)
        self.assertEqual(len(reqs), 15)

    def test_parse_docx_accepts_pathlib(self) -> None:
        resolver = ActorResolver([])
        reqs = parse_docx(SAMPLE, resolver.resolve)
        self.assertEqual(len(reqs), 15)


class TestConfigDrivenFilters(unittest.TestCase):
    """End-to-end verification that config actually changes parser output."""

    def setUp(self) -> None:
        self.resolver = ActorResolver([])

    def test_keywords_soft_remove(self) -> None:
        """Dropping 'will' via soft_remove removes the one 'will'-only row."""
        cfg = Config.defaults()
        # 'will' lives in SOFT under the curated defaults, so dropping it
        # requires soft_remove, not hard_remove.
        cfg.keywords.soft_remove = ["will"]
        # Rebuild via the matcher path (the parser builds its matcher from
        # cfg.keywords, so we need to exercise the real path).
        events = parse_docx_events(SAMPLE, self.resolver.resolve, config=cfg)
        reqs = _reqs(events)
        joined = " || ".join(r.text for r in reqs)
        self.assertNotIn("Sessions will expire", joined)
        # Only one sentence was 'will'-only, so count drops by exactly 1.
        self.assertEqual(len(reqs), 14)

    def test_content_skip_note_prefix(self) -> None:
        cfg = Config.defaults()
        cfg.content.skip_if_starts_with = ["Note:"]
        events = parse_docx_events(SAMPLE, self.resolver.resolve, config=cfg)
        reqs = _reqs(events)
        for r in reqs:
            self.assertFalse(
                r.text.lower().startswith("note:"),
                f"Note-prefixed row leaked through: {r.text!r}",
            )

    def test_skip_section_title(self) -> None:
        """A skip_sections.titles entry suppresses the whole row."""
        cfg = Config.defaults()
        # Suppress every actor row by skipping the topic text — a blunt but
        # deterministic way to test the hook end-to-end.
        cfg.skip_sections.titles = ["Auth Service"]
        events = parse_docx_events(SAMPLE, self.resolver.resolve, config=cfg)
        reqs = _reqs(events)
        actors = {r.primary_actor for r in reqs}
        self.assertNotIn("Auth Service", actors)
        # Other actors still come through.
        self.assertIn("Flight Software", actors)

    def test_require_primary_actor_drops_preamble_and_section_rows(self) -> None:
        cfg = Config.defaults()
        cfg.content.require_primary_actor = True
        events = parse_docx_events(SAMPLE, self.resolver.resolve, config=cfg)
        reqs = _reqs(events)
        for r in reqs:
            self.assertTrue(r.primary_actor, f"should have dropped: {r!r}")


class TestPerDocConfigResolution(unittest.TestCase):
    """Simulate per-doc discovery on a small synthetic file tree."""

    def test_resolve_layers(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "run.yaml"
            run.write_text(textwrap.dedent("""
                tables:
                  actor_column: 1
                  content_column: 2
                keywords:
                  soft_remove: [will]
            """).lstrip(), encoding="utf-8")

            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")

            per_doc = Path(d) / "spec.reqx.yaml"
            per_doc.write_text(textwrap.dedent("""
                content:
                  require_primary_actor: true
            """).lstrip(), encoding="utf-8")

            cfg = resolve_config(run_config_path=run, docx_path=docx)
            self.assertTrue(cfg.content.require_primary_actor)
            self.assertEqual(cfg.keywords.soft_remove, ["will"])
            self.assertIn("run.yaml", cfg.source)
            self.assertIn("spec.reqx.yaml", cfg.source)


if __name__ == "__main__":
    unittest.main()
