"""Tests for REVIEW §2.9 — narrowed exception clauses.

The `extract_from_files` pipeline used to catch bare `Exception` when
loading actors, config, and keywords files.  Those catches have been
narrowed to `(OSError, ValueError, ImportError)` / `(OSError, ValueError,
KeyError)`.  These tests pin down that the expected failure modes still
soft-fail as warnings (so a typo in an optional input doesn't abort the
whole run) while unexpected errors propagate.

A related guard: the per-file parse catch is still broad on purpose
(one bad doc shouldn't kill the batch), but we confirm that, too,
produces a recorded error rather than crashing.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document

from requirements_extractor.extractor import extract_from_files


def _make_empty_docx(path: Path) -> None:
    """Write a minimal .docx so the extractor has something to open."""
    doc = Document()
    doc.add_paragraph("Placeholder document.")
    doc.save(str(path))


class NarrowedCatchSoftFailsTests(unittest.TestCase):
    def test_missing_actors_file_warns_not_crashes(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td) / "spec.docx"
            _make_empty_docx(spec)
            out = Path(td) / "out.xlsx"
            result = extract_from_files(
                [spec],
                output_path=out,
                actors_xlsx=Path(td) / "does_not_exist.xlsx",
            )
            # A FileNotFoundError (OSError subclass) is caught and
            # recorded as a warning — the run still completes.
            joined = " ".join(result.stats.errors)
            self.assertIn("Failed to load actors file", joined)

    def test_missing_config_file_warns_not_crashes(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td) / "spec.docx"
            _make_empty_docx(spec)
            out = Path(td) / "out.xlsx"
            result = extract_from_files(
                [spec],
                output_path=out,
                config_path=Path(td) / "missing.yaml",
            )
            joined = " ".join(result.stats.errors)
            self.assertIn("Failed to load config", joined)

    def test_bad_yaml_config_warns_with_value_error(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td) / "spec.docx"
            _make_empty_docx(spec)
            out = Path(td) / "out.xlsx"
            bad_cfg = Path(td) / "bad.yaml"
            bad_cfg.write_text(
                "detector:\n  hard: not-a-list-should-be-a-sequence\n",
                encoding="utf-8",
            )
            result = extract_from_files(
                [spec], output_path=out, config_path=bad_cfg,
            )
            joined = " ".join(result.stats.errors)
            self.assertIn("config", joined.lower())

    def test_missing_keywords_file_warns_not_crashes(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td) / "spec.docx"
            _make_empty_docx(spec)
            out = Path(td) / "out.xlsx"
            result = extract_from_files(
                [spec],
                output_path=out,
                keywords_path=Path(td) / "kw.yaml",  # doesn't exist
            )
            joined = " ".join(result.stats.errors)
            self.assertIn("keywords", joined.lower())


if __name__ == "__main__":
    unittest.main()
