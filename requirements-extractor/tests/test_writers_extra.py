"""Unit tests for the JSON and Markdown writers (REVIEW §3.10).

Pure-function tests over ``write_requirements_json`` and
``write_requirements_md`` — no Excel dependency, no integration with
the extractor pipeline.  Integration via the ``--emit`` CLI flag is
exercised by ``test_writers_extra_cli`` at the bottom.

Run:  python -m unittest tests.test_writers_extra
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from requirements_extractor.models import Requirement, compute_stable_id
from requirements_extractor.writers_extra import (
    requirement_to_dict,
    write_requirements_json,
    write_requirements_md,
)


def _make_req(
    text: str,
    *,
    order: int = 1,
    source_file: str = "spec.docx",
    primary_actor: str = "User",
    req_type: str = "Hard",
    keywords=None,
    confidence: str = "High",
    notes: str = "",
    polarity: str = "Positive",
) -> Requirement:
    return Requirement(
        order=order,
        source_file=source_file,
        heading_trail="3. System",
        section_topic="Auth",
        row_ref="Table 1, Row 3",
        block_ref="Paragraph 1",
        primary_actor=primary_actor,
        secondary_actors=[],
        text=text,
        req_type=req_type,
        keywords=list(keywords or ["shall"]),
        confidence=confidence,
        notes=notes,
        polarity=polarity,
        stable_id=compute_stable_id(source_file, primary_actor, text),
    )


# ---------------------------------------------------------------------------
# JSON writer
# ---------------------------------------------------------------------------


class TestRequirementToDict(unittest.TestCase):
    def test_all_public_fields_present(self) -> None:
        r = _make_req("The User shall log in.")
        d = requirement_to_dict(r)
        # Every dataclass field should be in the dict.  Spot-check the
        # load-bearing ones.
        for key in (
            "order", "source_file", "heading_trail", "section_topic",
            "row_ref", "block_ref", "primary_actor", "secondary_actors",
            "text", "req_type", "keywords", "confidence", "notes",
            "polarity", "stable_id",
        ):
            self.assertIn(key, d, f"field '{key}' missing from dict")

    def test_keywords_is_list_not_joined_string(self) -> None:
        r = _make_req("x", keywords=["shall", "required"])
        d = requirement_to_dict(r)
        self.assertEqual(d["keywords"], ["shall", "required"])


class TestJsonWriter(unittest.TestCase):
    def test_writes_flat_array(self) -> None:
        reqs = [
            _make_req("The User shall log in."),
            _make_req("The Admin must revoke access.", order=2,
                      primary_actor="Admin"),
        ]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.json"
            write_requirements_json(reqs, out)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)
            self.assertEqual(len(payload), 2)
            self.assertEqual(payload[0]["primary_actor"], "User")
            self.assertEqual(payload[1]["primary_actor"], "Admin")

    def test_deterministic_across_runs(self) -> None:
        reqs = [_make_req("Same input."), _make_req("Same input.", order=2)]
        with tempfile.TemporaryDirectory() as d:
            out_a = Path(d) / "a.json"
            out_b = Path(d) / "b.json"
            write_requirements_json(reqs, out_a)
            write_requirements_json(reqs, out_b)
            self.assertEqual(
                out_a.read_bytes(), out_b.read_bytes(),
                msg="JSON output must be byte-deterministic for CI diffs",
            )

    def test_empty_list_produces_empty_array(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.json"
            write_requirements_json([], out)
            self.assertEqual(json.loads(out.read_text()), [])

    def test_unicode_survives_round_trip(self) -> None:
        r = _make_req("The User shall validate \u2013 handshake complete.")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.json"
            write_requirements_json([r], out)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("\u2013", loaded[0]["text"])

    def test_parents_auto_created(self) -> None:
        # Parent directory doesn't exist yet — writer should create it.
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "nested" / "deep" / "out.json"
            write_requirements_json([_make_req("x")], out)
            self.assertTrue(out.exists())


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------


class TestMarkdownWriter(unittest.TestCase):
    def test_writes_title_and_summary_and_table(self) -> None:
        reqs = [
            _make_req("The User shall log in."),
            _make_req("The User may retry on failure.", req_type="Soft",
                      keywords=["may"], order=2),
        ]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.md"
            write_requirements_md(reqs, out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("# Extracted requirements", content)
            # Summary line.
            self.assertIn("**2**", content)
            self.assertIn("1 Hard", content)
            self.assertIn("1 Soft", content)
            # Table header row.
            self.assertIn("| # | ID | Source | Actor", content)

    def test_empty_list_produces_friendly_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.md"
            write_requirements_md([], out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("No requirements captured", content)
            # No naked table header when body is empty.
            self.assertNotIn("| # | ID |", content)

    def test_pipe_in_text_is_escaped(self) -> None:
        r = _make_req("The User shall parse a | b | c correctly.")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.md"
            write_requirements_md([r], out)
            content = out.read_text(encoding="utf-8")
            # Escaped pipes keep the table from breaking.
            self.assertIn("a \\| b \\| c", content)

    def test_newlines_in_text_become_br(self) -> None:
        r = _make_req("Line one.\nLine two.")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.md"
            write_requirements_md([r], out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("Line one.<br>Line two.", content)

    def test_negative_count_in_summary(self) -> None:
        r = _make_req("The system shall not crash.", polarity="Negative")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.md"
            write_requirements_md([r], out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("1 Negative", content)


class TestRemovedShimsRaise(unittest.TestCase):
    """Pin the ``json_writer`` / ``md_writer`` removal — importing
    either module must raise ``ImportError`` (the placeholder modules
    raise on load to prevent silent fallback to stale behaviour).

    Removed 2026-04-25 per REFACTOR.md item T1. Eric confirmed no
    external scripts use these names.
    """

    def test_json_writer_raises_on_import(self) -> None:
        # Force fresh import so a previously-cached module doesn't mask the raise.
        import importlib
        with self.assertRaises(ImportError) as ctx:
            importlib.import_module("requirements_extractor.json_writer")
        self.assertIn("removed 2026-04-25", str(ctx.exception))

    def test_md_writer_raises_on_import(self) -> None:
        import importlib
        with self.assertRaises(ImportError) as ctx:
            importlib.import_module("requirements_extractor.md_writer")
        self.assertIn("removed 2026-04-25", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
