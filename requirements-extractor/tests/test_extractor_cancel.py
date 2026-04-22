"""Tests for the ``cancel_check`` / ``file_progress`` hooks in extractor.

These validate the new plumbing that the GUI relies on: a multi-file
run must honour cancellation between files, and file_progress must be
invoked with monotonically increasing indices.

Run:  python -m unittest tests.test_extractor_cancel
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from requirements_extractor.extractor import (
    ExtractionCancelled,
    extract_from_files,
)


SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_spec.docx"


class TestFileProgress(unittest.TestCase):
    def test_called_once_per_input_with_monotonic_indices(self) -> None:
        calls: list[tuple[int, int, str]] = []

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            # Pass the same sample three times to get a 3-file run without
            # needing additional fixtures.  The extractor parses each entry
            # independently so this is a valid stress test.
            extract_from_files(
                input_paths=[SAMPLE, SAMPLE, SAMPLE],
                output_path=out,
                file_progress=lambda i, n, name: calls.append((i, n, name)),
            )

        self.assertEqual([c[0] for c in calls], [1, 2, 3])
        self.assertTrue(all(c[1] == 3 for c in calls))
        self.assertTrue(all(c[2].endswith("sample_spec.docx") for c in calls))


class TestCancelCheck(unittest.TestCase):
    def test_cancel_before_first_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            with self.assertRaises(ExtractionCancelled):
                extract_from_files(
                    input_paths=[SAMPLE],
                    output_path=out,
                    cancel_check=lambda: True,
                )
            # Output file must NOT exist — a cancelled run writes nothing.
            self.assertFalse(out.exists())

    def test_cancel_between_files_stops_further_processing(self) -> None:
        """A cancel_check that flips True after the first file should abort."""
        flipped = {"after": 0}

        def check() -> bool:
            flipped["after"] += 1
            # Return True on the second invocation so the first file
            # completes and the second one is refused.
            return flipped["after"] > 1

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            with self.assertRaises(ExtractionCancelled):
                extract_from_files(
                    input_paths=[SAMPLE, SAMPLE, SAMPLE],
                    output_path=out,
                    cancel_check=check,
                )
            # The cancel happened before any output was written.
            self.assertFalse(out.exists())

    def test_cancel_false_allows_full_run(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            result = extract_from_files(
                input_paths=[SAMPLE],
                output_path=out,
                cancel_check=lambda: False,
            )
            self.assertEqual(result.stats.files_processed, 1)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
