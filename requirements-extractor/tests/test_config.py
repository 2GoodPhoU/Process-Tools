"""Unit tests for requirements_extractor.config.

Run:  python -m unittest tests.test_config
"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from requirements_extractor.config import (
    Config,
    autodiscover_config,
    build_config,
    load_config_raw,
    merge_raw,
    resolve_config,
)


def _write(tmp: Path, name: str, body: str) -> Path:
    p = tmp / name
    p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return p


class TestDefaults(unittest.TestCase):
    def test_defaults_match_expectations(self) -> None:
        cfg = Config.defaults()
        self.assertEqual(cfg.version, 1)
        self.assertEqual(cfg.source, "default")
        self.assertEqual(cfg.tables.actor_column, 1)
        self.assertEqual(cfg.tables.content_column, 2)
        self.assertEqual(cfg.tables.min_columns, 2)
        self.assertEqual(cfg.tables.max_columns, 2)
        self.assertTrue(cfg.parser.recursive)
        self.assertEqual(cfg.skip_sections.titles, [])
        self.assertEqual(cfg.skip_sections.table_indices, [])


class TestLoadRaw(unittest.TestCase):
    def test_load_valid(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = _write(Path(d), "c.yaml", """
                version: 1
                skip_sections:
                  titles: [Revision History]
                tables:
                  actor_column: 1
                  content_column: 2
            """)
            raw = load_config_raw(p)
            self.assertEqual(raw["version"], 1)
            self.assertEqual(raw["skip_sections"]["titles"], ["Revision History"])
            self.assertEqual(raw["tables"]["content_column"], 2)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_config_raw(Path("/tmp/definitely-does-not-exist.yaml"))

    def test_unknown_top_level_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = _write(Path(d), "c.yaml", """
                version: 1
                frobnicator:
                  foo: bar
            """)
            with self.assertRaises(ValueError) as ctx:
                load_config_raw(p)
            self.assertIn("unknown top-level keys", str(ctx.exception))
            self.assertIn("frobnicator", str(ctx.exception))

    def test_unknown_sub_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = _write(Path(d), "c.yaml", """
                tables:
                  actor_column: 1
                  mystery_key: true
            """)
            with self.assertRaises(ValueError) as ctx:
                load_config_raw(p)
            self.assertIn("mystery_key", str(ctx.exception))

    def test_non_mapping_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = _write(Path(d), "c.yaml", """
                - this
                - is
                - a list
            """)
            with self.assertRaises(ValueError):
                load_config_raw(p)


class TestBuildConfig(unittest.TestCase):
    def test_empty_raw_is_defaults(self) -> None:
        cfg = build_config({}, source="default")
        self.assertEqual(cfg.source, "default")
        self.assertEqual(cfg.tables.actor_column, 1)

    def test_partial_overrides_only_touched_fields(self) -> None:
        raw = {
            "tables": {"actor_column": 2},
            "keywords": {"hard_remove": ["will"]},
        }
        cfg = build_config(raw, source="x.yaml")
        self.assertEqual(cfg.tables.actor_column, 2)
        # Untouched fields remain at default.
        self.assertEqual(cfg.tables.content_column, 2)
        self.assertEqual(cfg.tables.min_columns, 2)
        self.assertEqual(cfg.keywords.hard_remove, ["will"])
        self.assertEqual(cfg.keywords.hard_add, [])
        self.assertEqual(cfg.source, "x.yaml")


class TestMergeRaw(unittest.TestCase):
    def test_scalar_replaces(self) -> None:
        out = merge_raw({"tables": {"actor_column": 1}}, {"tables": {"actor_column": 3}})
        self.assertEqual(out["tables"]["actor_column"], 3)

    def test_list_replaces_wholesale(self) -> None:
        """Lists do NOT append — this is documented behaviour."""
        base = {"skip_sections": {"titles": ["A", "B"]}}
        over = {"skip_sections": {"titles": ["C"]}}
        out = merge_raw(base, over)
        self.assertEqual(out["skip_sections"]["titles"], ["C"])

    def test_nested_dicts_merge_key_by_key(self) -> None:
        base = {"tables": {"actor_column": 1, "content_column": 2}}
        over = {"tables": {"content_column": 3}}
        out = merge_raw(base, over)
        self.assertEqual(out["tables"], {"actor_column": 1, "content_column": 3})

    def test_override_adds_new_sections(self) -> None:
        base = {"tables": {"actor_column": 1}}
        over = {"keywords": {"hard_add": ["foo"]}}
        out = merge_raw(base, over)
        self.assertEqual(out["tables"]["actor_column"], 1)
        self.assertEqual(out["keywords"]["hard_add"], ["foo"])


class TestAutodiscover(unittest.TestCase):
    def test_finds_reqx_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")  # placeholder
            yml = _write(Path(d), "spec.reqx.yaml", "version: 1\n")
            self.assertEqual(autodiscover_config(docx), yml)

    def test_finds_reqx_yml(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")
            yml = _write(Path(d), "spec.reqx.yml", "version: 1\n")
            self.assertEqual(autodiscover_config(docx), yml)

    def test_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")
            self.assertIsNone(autodiscover_config(docx))


class TestResolveConfig(unittest.TestCase):
    def test_defaults_when_nothing_passed(self) -> None:
        cfg = resolve_config(run_config_path=None, docx_path=None)
        self.assertEqual(cfg.source, "default")
        self.assertEqual(cfg.tables.actor_column, 1)

    def test_per_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            run = _write(Path(d), "run.yaml", """
                tables:
                  actor_column: 3
            """)
            cfg = resolve_config(run_config_path=run, docx_path=None)
            self.assertEqual(cfg.tables.actor_column, 3)
            self.assertIn("run.yaml", cfg.source)

    def test_per_doc_overrides_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            run = _write(Path(d), "run.yaml", """
                tables:
                  actor_column: 3
                  content_column: 4
                keywords:
                  hard_remove: [will]
            """)
            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")
            _write(Path(d), "spec.reqx.yaml", """
                tables:
                  actor_column: 5
            """)
            cfg = resolve_config(run_config_path=run, docx_path=docx)
            # Per-doc override applied
            self.assertEqual(cfg.tables.actor_column, 5)
            # Per-run values preserved where per-doc didn't specify
            self.assertEqual(cfg.tables.content_column, 4)
            self.assertEqual(cfg.keywords.hard_remove, ["will"])
            # Both files should be in the source
            self.assertIn("run.yaml", cfg.source)
            self.assertIn("spec.reqx.yaml", cfg.source)

    def test_per_doc_list_replaces_not_appends(self) -> None:
        """Critical invariant: per-doc titles: [X] replaces per-run titles wholesale."""
        with tempfile.TemporaryDirectory() as d:
            run = _write(Path(d), "run.yaml", """
                skip_sections:
                  titles: [References, Glossary]
            """)
            docx = Path(d) / "spec.docx"
            docx.write_bytes(b"")
            _write(Path(d), "spec.reqx.yaml", """
                skip_sections:
                  titles: [Appendix]
            """)
            cfg = resolve_config(run_config_path=run, docx_path=docx)
            self.assertEqual(cfg.skip_sections.titles, ["Appendix"])


class TestSkipSectionsHelper(unittest.TestCase):
    def test_matches_equal(self) -> None:
        from requirements_extractor.config import SkipSections
        s = SkipSections(titles=["Glossary"])
        self.assertTrue(s.matches_title("Glossary"))
        self.assertTrue(s.matches_title("  glossary  "))

    def test_matches_contained(self) -> None:
        from requirements_extractor.config import SkipSections
        s = SkipSections(titles=["Revision History"])
        self.assertTrue(s.matches_title("3. Revision History"))
        self.assertTrue(s.matches_title("Section 3: Revision History"))

    def test_no_match(self) -> None:
        from requirements_extractor.config import SkipSections
        s = SkipSections(titles=["Glossary"])
        self.assertFalse(s.matches_title("System Requirements"))
        self.assertFalse(s.matches_title(""))


class TestContentShouldSkip(unittest.TestCase):
    def test_prefix(self) -> None:
        from requirements_extractor.config import ContentConfig
        c = ContentConfig(skip_if_starts_with=["Note:", "Example:"])
        self.assertTrue(c.should_skip("Note: this is informational."))
        self.assertTrue(c.should_skip("note: case insensitive"))
        self.assertFalse(c.should_skip("The system shall reboot."))

    def test_pattern(self) -> None:
        from requirements_extractor.config import ContentConfig
        c = ContentConfig(skip_pattern=r"\bTBD\b")
        self.assertTrue(c.should_skip("The spec says TBD here."))
        self.assertFalse(c.should_skip("The spec is complete."))

    def test_blank_is_skipped(self) -> None:
        from requirements_extractor.config import ContentConfig
        c = ContentConfig()
        self.assertTrue(c.should_skip(""))


class TestTablesConfig(unittest.TestCase):
    def test_is_requirement_table(self) -> None:
        from requirements_extractor.config import TablesConfig
        t = TablesConfig(min_columns=2, max_columns=2)
        self.assertFalse(t.is_requirement_table(1))
        self.assertTrue(t.is_requirement_table(2))
        self.assertFalse(t.is_requirement_table(3))

    def test_no_upper_cap(self) -> None:
        from requirements_extractor.config import TablesConfig
        t = TablesConfig(min_columns=2, max_columns=-1)
        self.assertTrue(t.is_requirement_table(2))
        self.assertTrue(t.is_requirement_table(50))

    def test_section_re_matches_alphanumeric(self) -> None:
        from requirements_extractor.config import TablesConfig
        r = TablesConfig().section_re()
        self.assertTrue(r.match("3.1 Authentication"))
        self.assertTrue(r.match("SR-1.2 Something"))
        self.assertTrue(r.match("A.1 Annex Item"))
        self.assertTrue(r.match("REQ-042 Requirement"))
        self.assertFalse(r.match("Introduction"))


if __name__ == "__main__":
    unittest.main()
