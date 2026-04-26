"""Tests for ``process_tools_common.cli_helpers``."""

from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stdout

from process_tools_common.cli_helpers import (
    QUIET_HELP,
    add_quiet_flag,
    make_logger,
)


class TestAddQuietFlag(unittest.TestCase):
    def test_short_form(self):
        parser = add_quiet_flag(argparse.ArgumentParser())
        args = parser.parse_args(["-q"])
        self.assertTrue(args.quiet)

    def test_long_form(self):
        parser = add_quiet_flag(argparse.ArgumentParser())
        args = parser.parse_args(["--quiet"])
        self.assertTrue(args.quiet)

    def test_default_is_false(self):
        parser = add_quiet_flag(argparse.ArgumentParser())
        args = parser.parse_args([])
        self.assertFalse(args.quiet)

    def test_returns_parser_for_chaining(self):
        parser = argparse.ArgumentParser()
        returned = add_quiet_flag(parser)
        self.assertIs(returned, parser)

    def test_help_text_is_consistent(self):
        """Both consumer tools should advertise the same help text."""
        parser = add_quiet_flag(argparse.ArgumentParser())
        # argparse stores it on the action; surface check:
        self.assertEqual(QUIET_HELP, "Suppress progress output (errors still print).")


class TestMakeLogger(unittest.TestCase):
    def test_quiet_returns_noop(self):
        log = make_logger(quiet=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            log("hello")
            log("world", "extra", sep=" | ")
        self.assertEqual(buf.getvalue(), "")

    def test_loud_forwards_to_print(self):
        log = make_logger(quiet=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            log("hello")
        self.assertEqual(buf.getvalue(), "hello\n")

    def test_loud_supports_print_kwargs(self):
        log = make_logger(quiet=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            log("a", "b", sep="-", end="!")
        self.assertEqual(buf.getvalue(), "a-b!")

    def test_noop_returns_none(self):
        log = make_logger(quiet=True)
        self.assertIsNone(log("anything"))


if __name__ == "__main__":
    unittest.main()
