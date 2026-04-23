"""Tests for REVIEW §2.8 (heading-trail padding) + §2.13 (logging).

§2.8 — When a document skips heading levels (H1 → H3), the internal
heading trail list should be padded with empty strings so the index of
each heading still reflects its depth.  The presentation string
(``trail_str``) should still skip empty slots.

§2.13 — The progress callback passed to ``extract_from_files`` /
``scan_actors_in_files`` should mirror every message to the
``requirements_extractor`` logger, with level routed by prefix
(``ERROR:`` → ERROR, ``WARNING:`` → WARNING, anything else → INFO).
"""

from __future__ import annotations

import logging
import unittest

from requirements_extractor._logging import make_progress_logger
from requirements_extractor.parser import _ParseContext, _update_heading_trail
from requirements_extractor.config import build_config
from requirements_extractor.detector import HARD_KEYWORDS, SOFT_KEYWORDS, KeywordMatcher


class HeadingTrailPaddingTests(unittest.TestCase):
    def test_sequential_levels_no_padding(self):
        trail: list[str] = []
        _update_heading_trail(trail, 1, "Intro")
        _update_heading_trail(trail, 2, "Scope")
        _update_heading_trail(trail, 3, "In scope")
        self.assertEqual(trail, ["Intro", "Scope", "In scope"])

    def test_h1_to_h3_pads_missing_h2(self):
        trail: list[str] = []
        _update_heading_trail(trail, 1, "Chapter")
        _update_heading_trail(trail, 3, "Detail")
        # Depth preserved: Chapter is at level 1 (index 0),
        # the missing H2 is "", Detail is at level 3 (index 2).
        self.assertEqual(trail, ["Chapter", "", "Detail"])

    def test_trail_str_skips_padding(self):
        # _ParseContext.trail_str() is what surfaces in the output column;
        # empty strings should not produce stray " > " separators.
        cfg = build_config()
        ctx = _ParseContext(
            source_file="spec.docx",
            config=cfg,
            matcher=KeywordMatcher(HARD_KEYWORDS, SOFT_KEYWORDS),
        )
        _update_heading_trail(ctx.heading_trail, 1, "Chapter")
        _update_heading_trail(ctx.heading_trail, 3, "Detail")
        self.assertEqual(ctx.trail_str(), "Chapter > Detail")

    def test_new_h1_clears_subtree(self):
        trail: list[str] = ["Chapter 1", "", "Detail"]
        _update_heading_trail(trail, 1, "Chapter 2")
        self.assertEqual(trail, ["Chapter 2"])

    def test_new_h2_replaces_earlier_h2_and_clears_below(self):
        trail: list[str] = ["Chapter", "Scope A", "Detail"]
        _update_heading_trail(trail, 2, "Scope B")
        self.assertEqual(trail, ["Chapter", "Scope B"])

    def test_starting_at_h2_pads_from_zero(self):
        trail: list[str] = []
        _update_heading_trail(trail, 2, "Orphan H2")
        self.assertEqual(trail, ["", "Orphan H2"])


class ProgressLoggerTests(unittest.TestCase):
    def setUp(self):
        # Capture records emitted to the package logger.
        self.logger = logging.getLogger("requirements_extractor")
        self.records: list[logging.LogRecord] = []

        class _Sink(logging.Handler):
            def __init__(self, sink):
                super().__init__()
                self.sink = sink

            def emit(self, record):  # noqa: D401 — logging protocol
                self.sink.append(record)

        self.handler = _Sink(self.records)
        self.handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_info_messages_route_to_info_level(self):
        log = make_progress_logger(None)
        log("Parsing spec.docx ...")
        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0].levelno, logging.INFO)
        self.assertIn("Parsing spec.docx", self.records[0].getMessage())

    def test_warning_prefix_routes_to_warning(self):
        log = make_progress_logger(None)
        log("WARNING: keywords file not found")
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_error_prefix_routes_to_error(self):
        log = make_progress_logger(None)
        log("ERROR: failed to parse spec")
        self.assertEqual(self.records[0].levelno, logging.ERROR)

    def test_callback_still_invoked(self):
        captured: list[str] = []
        log = make_progress_logger(captured.append)
        log("Loaded 3 actors.")
        # Callback got the message verbatim and logger got it too.
        self.assertEqual(captured, ["Loaded 3 actors."])
        self.assertEqual(len(self.records), 1)

    def test_null_handler_attached_by_default(self):
        # Importing _logging must not remove/replace any handler a host
        # app attached — we only add a NullHandler.
        from requirements_extractor import _logging as log_mod

        self.assertTrue(
            any(isinstance(h, logging.NullHandler) for h in log_mod.logger.handlers),
            "requirements_extractor logger should have a NullHandler attached",
        )


if __name__ == "__main__":
    unittest.main()
