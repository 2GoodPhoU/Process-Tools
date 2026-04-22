"""Tests for the subcommand-based CLI.

These tests focus on argparse wiring — we check that each subcommand
parses its expected flags correctly, that aliases work, that global
flags attach to the root parser, and that the shim in ``extract.py``
transparently prepends ``requirements`` to flag-style invocations.

Run:  python -m unittest tests.test_cli
"""

from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from requirements_extractor.cli import PROG_NAME, build_parser


ROOT = Path(__file__).resolve().parent.parent


def _load_extract_shim():
    """Load extract.py as a module so we can call its helpers directly."""
    spec = importlib.util.spec_from_file_location(
        "extract_shim", ROOT / "extract.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# build_parser — shape
# ---------------------------------------------------------------------------


class TestParserShape(unittest.TestCase):
    def test_prog_name_is_branded(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.prog, PROG_NAME)
        self.assertEqual(parser.prog, "document-data-extractor")

    def test_missing_subcommand_prints_help_and_exits_nonzero(self) -> None:
        from requirements_extractor.cli import main
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = main([])
        self.assertEqual(rc, 2)
        self.assertIn("MODE", buf.getvalue())

    def test_unknown_subcommand_errors(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["bogus", "spec.docx"])


# ---------------------------------------------------------------------------
# requirements subcommand
# ---------------------------------------------------------------------------


class TestRequirementsSubcommand(unittest.TestCase):
    def test_minimal(self) -> None:
        args = build_parser().parse_args(["requirements", "spec.docx"])
        self.assertEqual(args.mode, "requirements")
        self.assertEqual(args.inputs, [Path("spec.docx")])
        self.assertIsNone(args.output)
        self.assertIsNone(args.actors)
        self.assertFalse(args.nlp)
        self.assertIsNone(args.statement_set)
        # Defaults for the newer quality-of-life flags.
        self.assertFalse(args.dry_run)
        self.assertEqual(args.show_samples, 0)

    def test_alias_reqs(self) -> None:
        args = build_parser().parse_args(["reqs", "spec.docx"])
        self.assertEqual(args.mode, "reqs")

    def test_all_flags(self) -> None:
        args = build_parser().parse_args([
            "requirements",
            "folder/", "other.docx",
            "-o", "out.xlsx",
            "--actors", "actors.xlsx",
            "--nlp",
            "--statement-set", "ss.csv",
            "--dry-run",
            "--show-samples", "5",
        ])
        self.assertEqual(args.inputs, [Path("folder/"), Path("other.docx")])
        self.assertEqual(args.output, Path("out.xlsx"))
        self.assertEqual(args.actors, Path("actors.xlsx"))
        self.assertTrue(args.nlp)
        self.assertEqual(args.statement_set, Path("ss.csv"))
        self.assertTrue(args.dry_run)
        self.assertEqual(args.show_samples, 5)

    def test_requires_input(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["requirements"])


# ---------------------------------------------------------------------------
# actors subcommand
# ---------------------------------------------------------------------------


class TestActorsSubcommand(unittest.TestCase):
    def test_minimal(self) -> None:
        args = build_parser().parse_args(["actors", "spec.docx"])
        self.assertEqual(args.mode, "actors")
        self.assertEqual(args.inputs, [Path("spec.docx")])
        self.assertIsNone(args.output)
        self.assertIsNone(args.actors)
        self.assertFalse(args.nlp)
        # Actors mode does NOT expose --statement-set.
        self.assertFalse(hasattr(args, "statement_set"))

    def test_alias_scan(self) -> None:
        args = build_parser().parse_args(["scan", "folder/"])
        self.assertEqual(args.mode, "scan")

    def test_seed_and_nlp(self) -> None:
        args = build_parser().parse_args([
            "actors", "folder/",
            "--actors", "seed.xlsx",
            "--nlp",
            "-o", "out.xlsx",
        ])
        self.assertEqual(args.actors, Path("seed.xlsx"))
        self.assertTrue(args.nlp)
        self.assertEqual(args.output, Path("out.xlsx"))


# ---------------------------------------------------------------------------
# Global flags
# ---------------------------------------------------------------------------


class TestGlobalFlags(unittest.TestCase):
    def test_config_before_subcommand(self) -> None:
        args = build_parser().parse_args([
            "--config", "my.yaml",
            "requirements", "spec.docx",
        ])
        self.assertEqual(args.config, Path("my.yaml"))
        self.assertEqual(args.mode, "requirements")

    def test_quiet_and_no_summary(self) -> None:
        args = build_parser().parse_args([
            "-q", "--no-summary",
            "actors", "spec.docx",
        ])
        self.assertTrue(args.quiet)
        self.assertTrue(args.no_summary)

    def test_global_flags_after_subcommand_are_rejected(self) -> None:
        """argparse's normal behaviour: subparser doesn't know -q."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["requirements", "spec.docx", "-q"])


# ---------------------------------------------------------------------------
# End-to-end dispatch (via main)
# ---------------------------------------------------------------------------


class TestMainDispatch(unittest.TestCase):
    def test_requirements_end_to_end(self) -> None:
        import tempfile
        from requirements_extractor.cli import main
        sample = ROOT / "samples" / "sample_spec.docx"
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xlsx"
            rc = main([
                "--no-summary", "-q",
                "requirements", str(sample),
                "-o", str(out),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())

    def test_actors_end_to_end(self) -> None:
        import tempfile
        from requirements_extractor.cli import main
        sample = ROOT / "samples" / "sample_spec.docx"
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "actors.xlsx"
            rc = main([
                "--no-summary", "-q",
                "actors", str(sample),
                "-o", str(out),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())


# ---------------------------------------------------------------------------
# extract.py shim — backward-compat
# ---------------------------------------------------------------------------


class TestExtractShim(unittest.TestCase):
    def setUp(self) -> None:
        self.shim = _load_extract_shim()

    def test_flag_style_gets_requirements_prepended(self) -> None:
        out = self.shim._compat_argv(["spec.docx", "-o", "out.xlsx"])
        self.assertEqual(out, ["requirements", "spec.docx", "-o", "out.xlsx"])

    def test_subcommand_passthrough(self) -> None:
        out = self.shim._compat_argv(["requirements", "spec.docx"])
        self.assertEqual(out, ["requirements", "spec.docx"])

    def test_alias_passthrough(self) -> None:
        out = self.shim._compat_argv(["reqs", "spec.docx"])
        self.assertEqual(out, ["reqs", "spec.docx"])
        out2 = self.shim._compat_argv(["scan", "folder/"])
        self.assertEqual(out2, ["scan", "folder/"])

    def test_actors_subcommand_passthrough(self) -> None:
        out = self.shim._compat_argv(["actors", "spec.docx"])
        self.assertEqual(out, ["actors", "spec.docx"])

    def test_help_is_not_rewritten(self) -> None:
        self.assertEqual(self.shim._compat_argv(["--help"]), ["--help"])
        self.assertEqual(self.shim._compat_argv(["-h"]), ["-h"])

    def test_global_flags_survive_injection(self) -> None:
        out = self.shim._compat_argv(["--config", "my.yaml", "spec.docx"])
        self.assertEqual(
            out, ["--config", "my.yaml", "requirements", "spec.docx"],
        )

    def test_quiet_and_no_summary_survive_injection(self) -> None:
        out = self.shim._compat_argv(["-q", "--no-summary", "spec.docx"])
        self.assertEqual(
            out, ["-q", "--no-summary", "requirements", "spec.docx"],
        )

    def test_empty_argv_untouched(self) -> None:
        # Nothing to inject — let main() print help.
        self.assertEqual(self.shim._compat_argv([]), [])


if __name__ == "__main__":
    unittest.main()
