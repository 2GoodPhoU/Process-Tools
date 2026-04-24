"""Direct unit tests for the shared orchestration helpers.

The helpers in ``_orchestration`` already get integration coverage
through every test that exercises ``extract_from_files`` or
``scan_actors_from_files`` (some 200+ tests), but those go through a
lot of pipeline so a regression in one helper would surface as a
mysterious downstream failure.  These tests pin each helper's
contract directly:

* expected return value on the success path,
* error message recorded on stats.errors,
* exception narrowing matches the historical inline behaviour,
* mode-specific phrasing (the ``label`` kwarg, the
  ``unsupported_message`` kwarg) round-trips intact.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import List

from requirements_extractor._orchestration import (
    HasErrors,
    build_resolver,
    load_actors_or_warn,
    resolve_per_doc_config,
    validate_input_path,
    validate_run_config,
)
from requirements_extractor.actors import ActorEntry
from requirements_extractor.config import Config


class _Stats:
    """Minimal HasErrors-satisfying object — both ExtractionStats and
    ActorScanStats provide the ``errors`` list, but for unit tests we
    don't want to depend on either of those compound dataclasses."""

    def __init__(self) -> None:
        self.errors: List[str] = []


def _capturing_logger():
    log_lines: List[str] = []
    return log_lines, log_lines.append


# ---------------------------------------------------------------------------
# load_actors_or_warn
# ---------------------------------------------------------------------------


class TestLoadActorsOrWarn(unittest.TestCase):
    def test_none_path_returns_empty_no_warning(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        result = load_actors_or_warn(None, stats, log_fn)
        self.assertEqual(result, [])
        self.assertEqual(stats.errors, [])
        self.assertEqual(log, [])

    def test_missing_file_records_friendly_warning(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        result = load_actors_or_warn(
            Path("/nonexistent/actors.xlsx"), stats, log_fn,
        )
        self.assertEqual(result, [])
        self.assertEqual(len(stats.errors), 1)
        self.assertIn("Failed to load actors file", stats.errors[0])
        self.assertEqual(log, [f"WARNING: {stats.errors[0]}"])

    def test_seed_label_changes_error_phrasing(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        load_actors_or_warn(
            Path("/nonexistent/seed.xlsx"), stats, log_fn, label="seed actors",
        )
        self.assertEqual(len(stats.errors), 1)
        self.assertIn("Failed to load seed actors", stats.errors[0])

    def test_success_path_returns_loaded_entries(self):
        # Build a minimal valid actors.xlsx via the writer's template
        # helper so we don't have to hand-roll openpyxl here.
        from requirements_extractor.gui_state import write_actors_template
        with tempfile.TemporaryDirectory() as d:
            actors_path = Path(d) / "actors.xlsx"
            write_actors_template(actors_path)
            stats = _Stats()
            log, log_fn = _capturing_logger()
            entries = load_actors_or_warn(actors_path, stats, log_fn)
            self.assertGreater(len(entries), 0)
            self.assertEqual(stats.errors, [])
            self.assertEqual(len(log), 1)
            self.assertIn("Loaded", log[0])
            self.assertIn("actors", log[0])


# ---------------------------------------------------------------------------
# build_resolver
# ---------------------------------------------------------------------------


class TestBuildResolver(unittest.TestCase):
    def test_no_nlp_no_warning(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        resolver = build_resolver([], use_nlp=False, stats=stats, log=log_fn)
        self.assertIsNotNone(resolver)
        self.assertEqual(stats.errors, [])
        self.assertEqual(log, [])

    def test_nlp_requested_but_unavailable_warns(self):
        # Whether NLP is actually available depends on the test env.
        # Either way the run shouldn't crash; if it's available we get
        # no warning, if it's not we get exactly one.
        stats = _Stats()
        log, log_fn = _capturing_logger()
        resolver = build_resolver([], use_nlp=True, stats=stats, log=log_fn)
        self.assertIsNotNone(resolver)
        if not resolver.has_nlp():
            self.assertEqual(len(stats.errors), 1)
            self.assertIn("NLP requested but spaCy", stats.errors[0])
            self.assertIn("install with", stats.errors[0].lower())
            self.assertEqual(log, [f"WARNING: {stats.errors[0]}"])
        else:
            self.assertEqual(stats.errors, [])
            self.assertEqual(log, [])


# ---------------------------------------------------------------------------
# validate_run_config
# ---------------------------------------------------------------------------


class TestValidateRunConfig(unittest.TestCase):
    def test_both_none_returns_both_none_no_warning(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        cfg, kw = validate_run_config(None, None, stats, log_fn)
        self.assertIsNone(cfg)
        self.assertIsNone(kw)
        self.assertEqual(stats.errors, [])
        self.assertEqual(log, [])

    def test_missing_config_records_warning_and_clears_path(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        cfg, kw = validate_run_config(
            Path("/nonexistent/cfg.yaml"), None, stats, log_fn,
        )
        # Path is cleared so per-doc resolve_config doesn't keep retrying.
        self.assertIsNone(cfg)
        self.assertIsNone(kw)
        self.assertEqual(len(stats.errors), 1)
        self.assertIn("Failed to load config", stats.errors[0])

    def test_keywords_only_path_validated(self):
        # No --config but a --keywords path; broken path should warn
        # and get cleared the same way.
        stats = _Stats()
        log, log_fn = _capturing_logger()
        cfg, kw = validate_run_config(
            None, Path("/nonexistent/kw.yaml"), stats, log_fn,
        )
        self.assertIsNone(cfg)
        self.assertIsNone(kw)
        self.assertEqual(len(stats.errors), 1)
        self.assertIn("Failed to load keywords file", stats.errors[0])

    def test_valid_config_logs_loaded_message(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_path = Path(d) / "cfg.yaml"
            cfg_path.write_text("skip_sections:\n  titles: [Notes]\n")
            stats = _Stats()
            log, log_fn = _capturing_logger()
            cfg, kw = validate_run_config(cfg_path, None, stats, log_fn)
            self.assertEqual(cfg, cfg_path)
            self.assertIsNone(kw)
            self.assertEqual(stats.errors, [])
            self.assertEqual(len(log), 1)
            self.assertIn("Loaded run config", log[0])


# ---------------------------------------------------------------------------
# resolve_per_doc_config
# ---------------------------------------------------------------------------


class TestResolvePerDocConfig(unittest.TestCase):
    def test_success_returns_real_config(self):
        with tempfile.TemporaryDirectory() as d:
            doc_path = Path(d) / "spec.docx"
            doc_path.write_text("placeholder")
            stats = _Stats()
            log, log_fn = _capturing_logger()
            cfg = resolve_per_doc_config(doc_path, None, None, stats, log_fn)
            self.assertIsInstance(cfg, Config)
            self.assertEqual(stats.errors, [])

    def test_malformed_per_doc_falls_back_to_defaults(self):
        # A <stem>.reqx.yaml with a syntax error should record a warning
        # and the function returns Config.defaults() — the per-file loop
        # still continues.
        with tempfile.TemporaryDirectory() as d:
            doc_path = Path(d) / "spec.docx"
            doc_path.write_text("placeholder")
            (Path(d) / "spec.reqx.yaml").write_text(
                "skip_sections:\n  not_a_real_key: 1\n"
            )
            stats = _Stats()
            log, log_fn = _capturing_logger()
            cfg = resolve_per_doc_config(doc_path, None, None, stats, log_fn)
            self.assertIsInstance(cfg, Config)
            self.assertEqual(len(stats.errors), 1)
            self.assertIn(
                "Failed to load per-doc config for spec.docx", stats.errors[0]
            )


# ---------------------------------------------------------------------------
# validate_input_path
# ---------------------------------------------------------------------------


class TestValidateInputPath(unittest.TestCase):
    def test_existing_accepted_suffix_returns_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "spec.docx"
            p.write_text("x")
            stats = _Stats()
            log, log_fn = _capturing_logger()
            out = validate_input_path(p, {".docx", ".doc", ".pdf"}, stats, log_fn)
            self.assertEqual(out, p)
            self.assertEqual(stats.errors, [])

    def test_missing_file_records_warning(self):
        stats = _Stats()
        log, log_fn = _capturing_logger()
        out = validate_input_path(
            Path("/nope/spec.docx"), {".docx"}, stats, log_fn,
        )
        self.assertIsNone(out)
        self.assertEqual(len(stats.errors), 1)
        self.assertIn("File not found", stats.errors[0])

    def test_unsupported_suffix_uses_callable_when_provided(self):
        # The two existing callers each pass their own historical message
        # via the unsupported_message kwarg.  Verify the callable is
        # invoked and its return string is recorded verbatim.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "spec.txt"
            p.write_text("x")
            stats = _Stats()
            log, log_fn = _capturing_logger()
            out = validate_input_path(
                p, {".docx"}, stats, log_fn,
                unsupported_message=lambda x: f"Skipping non-.docx file: {x.name}",
            )
            self.assertIsNone(out)
            self.assertEqual(stats.errors, ["Skipping non-.docx file: spec.txt"])

    def test_unsupported_suffix_default_message_lists_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "spec.txt"
            p.write_text("x")
            stats = _Stats()
            log, log_fn = _capturing_logger()
            out = validate_input_path(p, {".docx", ".pdf"}, stats, log_fn)
            self.assertIsNone(out)
            self.assertEqual(len(stats.errors), 1)
            # Default message includes both allowed suffixes
            self.assertIn("Skipping unsupported file", stats.errors[0])
            self.assertIn(".docx", stats.errors[0])
            self.assertIn(".pdf", stats.errors[0])


if __name__ == "__main__":
    unittest.main()
