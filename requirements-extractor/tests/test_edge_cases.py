"""Integration tests for the edge-case sample suite in ``samples/edge_cases``.

Each sample targets a specific parser/config feature:

  nested_tables.docx        — recursive walker, dotted block refs.
  alphanumeric_sections.docx — broadened section_prefix regex.
  boilerplate_heavy.docx    — skip_sections.titles end-to-end.
  wide_table.docx           — tables.actor_column / content_column / min/max.
  noise_prose.docx          — content filters + keyword tuning + empties.

All samples are regenerated deterministically by
``samples/edge_cases/generate.py``.  If you ever need to refresh them,
run that script; these tests will re-validate the results.

Run: ``python -m unittest tests.test_edge_cases``
"""

from __future__ import annotations

import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.config import resolve_config
from requirements_extractor.models import RequirementEvent, SectionRowEvent
from requirements_extractor.parser import parse_docx_events


SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "edge_cases"


def _parse(docx: Path):
    """Parse with auto-discovered per-doc config, return (reqs, section_titles)."""
    cfg = resolve_config(run_config_path=None, docx_path=docx)
    events = parse_docx_events(docx, ActorResolver([]).resolve, config=cfg)
    reqs = [e.requirement for e in events if isinstance(e, RequirementEvent)]
    section_titles = [e.title for e in events if isinstance(e, SectionRowEvent)]
    return reqs, section_titles, cfg


class TestNestedTables(unittest.TestCase):
    """Arbitrary-depth nested tables with traceable block refs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reqs, cls.sections, cls.cfg = _parse(SAMPLES / "nested_tables.docx")

    def test_section_row_captured(self) -> None:
        self.assertIn("4.1 Interfaces", self.sections)

    def test_three_deep_block_ref_is_dotted(self) -> None:
        """The deepest-nested requirement should carry a dotted path."""
        deep = next(
            r for r in self.reqs
            if "malformed packets" in r.text
        )
        self.assertIn(" > ", deep.block_ref)
        # Expect something like 'Nested Table 1 R1C2 > Nested Table 1 R1C2 > Paragraph 1'
        self.assertIn("Nested Table", deep.block_ref)
        # section_topic propagates all the way down.
        self.assertEqual(deep.section_topic, "4.1 Interfaces")

    def test_all_sibling_paragraphs_in_nested_cell_captured(self) -> None:
        """Two paragraphs in the same nested cell → two separate rows."""
        texts = {r.text for r in self.reqs}
        self.assertIn(
            "The Ingress Gateway shall drop malformed packets within 10 ms.",
            texts,
        )
        self.assertIn(
            "The Ingress Gateway must reject traffic from unknown sources.",
            texts,
        )

    def test_bullets_are_separate_requirements(self) -> None:
        """Bullets inside a cell become one requirement each, not a blob."""
        bullet_reqs = [r for r in self.reqs if r.block_ref.startswith("Bullet")]
        self.assertEqual(len(bullet_reqs), 2)
        bullet_texts = sorted(r.text for r in bullet_reqs)
        self.assertEqual(
            bullet_texts,
            [
                "Telemetry may be suspended during reboot.",
                "Watchdog timeouts must trigger a soft reboot.",
            ],
        )

    def test_actor_row_flight_computer(self) -> None:
        fc_reqs = [r for r in self.reqs if r.primary_actor == "Flight Computer"]
        self.assertEqual(len(fc_reqs), 3)  # 1 paragraph + 2 bullets


class TestAlphanumericSections(unittest.TestCase):
    """Non-numeric section prefixes (SR-1.2, REQ-042, A.1) — no config needed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reqs, cls.sections, cls.cfg = _parse(
            SAMPLES / "alphanumeric_sections.docx"
        )

    def test_three_sections_detected(self) -> None:
        self.assertEqual(
            self.sections,
            ["SR-1.1 Access Control", "REQ-042 Key Rotation", "A.1 Annex — Audit"],
        )

    def test_each_req_has_its_section_topic(self) -> None:
        by_actor = {r.primary_actor: r for r in self.reqs}
        self.assertEqual(
            by_actor["Auth Service"].section_topic, "SR-1.1 Access Control",
        )
        self.assertEqual(
            by_actor["Key Manager"].section_topic, "REQ-042 Key Rotation",
        )
        self.assertEqual(
            by_actor["Audit Collector"].section_topic, "A.1 Annex — Audit",
        )

    def test_no_section_row_leaked_as_requirement(self) -> None:
        """A row that matches section_prefix must not also appear as a req."""
        section_texts = set(self.sections)
        for r in self.reqs:
            self.assertNotIn(r.primary_actor, section_texts)


class TestBoilerplateHeavy(unittest.TestCase):
    """Per-doc config suppresses Revision History / Glossary / TOC / References."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reqs, _, cls.cfg = _parse(SAMPLES / "boilerplate_heavy.docx")

    def test_per_doc_config_was_loaded(self) -> None:
        self.assertIn("boilerplate_heavy.reqx.yaml", self.cfg.source)

    def test_only_real_requirements_survive(self) -> None:
        texts = {r.text for r in self.reqs}
        self.assertEqual(len(self.reqs), 2)
        self.assertIn(
            "The Auth Service shall log every failed login attempt.", texts,
        )
        self.assertIn(
            "The Admin Console must support MFA for all administrative users.",
            texts,
        )

    def test_no_boilerplate_leaked(self) -> None:
        """None of the known boilerplate sentences should be present."""
        joined = " || ".join(r.text for r in self.reqs)
        for banned in (
            "publish updates quarterly",
            "Authors must proofread drafts",
            "grouped by role",
            "consult the standard",
        ):
            self.assertNotIn(banned, joined)


class TestWideTable(unittest.TestCase):
    """4-column table with actor/content remapped via config."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reqs, _, cls.cfg = _parse(SAMPLES / "wide_table.docx")

    def test_config_remapped_columns(self) -> None:
        self.assertEqual(self.cfg.tables.actor_column, 2)
        self.assertEqual(self.cfg.tables.content_column, 3)
        self.assertEqual(self.cfg.tables.min_columns, 4)
        self.assertEqual(self.cfg.tables.max_columns, 4)

    def test_three_real_requirements(self) -> None:
        self.assertEqual(len(self.reqs), 3)
        actors = sorted(r.primary_actor for r in self.reqs)
        self.assertEqual(
            actors, ["Actuator", "Controller", "Operator Console"],
        )

    def test_header_row_noun_keyword_suppressed(self) -> None:
        """'Requirement' (header text) was a known §1.2 false positive;
        the per-doc hard_remove drops it."""
        for r in self.reqs:
            self.assertNotEqual(r.text.strip().lower(), "requirement")

    def test_hard_soft_split(self) -> None:
        types = sorted(r.req_type for r in self.reqs)
        self.assertEqual(types, ["Hard", "Hard", "Soft"])


class TestNoiseProse(unittest.TestCase):
    """Content filters + keyword tuning + blank cells."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reqs, _, cls.cfg = _parse(SAMPLES / "noise_prose.docx")

    def test_per_doc_config_loaded(self) -> None:
        self.assertIn("noise_prose.reqx.yaml", self.cfg.source)

    def test_will_only_sentence_dropped(self) -> None:
        for r in self.reqs:
            self.assertNotIn("will attempt to flush", r.text)

    def test_note_example_caution_dropped(self) -> None:
        for r in self.reqs:
            low = r.text.strip().lower()
            self.assertFalse(low.startswith("note:"))
            self.assertFalse(low.startswith("example:"))
            self.assertFalse(low.startswith("caution:"))

    def test_tbd_pattern_dropped(self) -> None:
        for r in self.reqs:
            self.assertNotIn("TBD", r.text)

    def test_negation_retained(self) -> None:
        texts = " || ".join(r.text for r in self.reqs)
        self.assertIn("must not preempt", texts)

    def test_short_sentence_is_low_confidence(self) -> None:
        beacon = next(r for r in self.reqs if r.primary_actor == "Beacon")
        self.assertEqual(beacon.confidence, "Low")

    def test_blank_cells_produce_no_requirements(self) -> None:
        """Monitor and Reporter rows have empty/whitespace content cells."""
        actors = {r.primary_actor for r in self.reqs}
        self.assertNotIn("Monitor", actors)
        self.assertNotIn("Reporter", actors)

    def test_exactly_four_requirements(self) -> None:
        self.assertEqual(len(self.reqs), 4)


class TestAllSamplesSmoke(unittest.TestCase):
    """Defensive guard: every sample must at least parse without raising."""

    def test_every_sample_parses(self) -> None:
        docs = sorted(SAMPLES.glob("*.docx"))
        self.assertGreaterEqual(len(docs), 5, "edge_cases samples missing?")
        for d in docs:
            with self.subTest(doc=d.name):
                reqs, _sections, _cfg = _parse(d)
                # Every req must have the core fields populated.
                for r in reqs:
                    self.assertTrue(r.source_file)
                    self.assertTrue(r.block_ref)
                    self.assertIn(r.req_type, ("Hard", "Soft"))
                    self.assertGreaterEqual(r.order, 1)


if __name__ == "__main__":
    unittest.main()
