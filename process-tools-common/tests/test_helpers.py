"""Tests for ``load_into`` and ``find_sidecar`` (added 2026-04-25)."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from process_tools_common.dde_xlsx import find_sidecar, load_into


def _make_dde_xlsx(path: Path) -> None:
    """Tiny helper: build a 2-row DDE-shaped workbook for tests."""
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Requirement", "Primary Actor", "Polarity"])
    ws.append(["REQ-aaaa1111", "The system shall log in.", "User", "Positive"])
    ws.append(["REQ-bbbb2222", "The system shall log out.", "User", "Positive"])
    wb.save(path)


@dataclass
class _Row:
    stable_id: str
    text: str
    primary_actor: str = ""


@dataclass
class _NarrowRow:
    stable_id: str
    text: str


class TestLoadInto(unittest.TestCase):
    def test_no_filter_passes_all_known_fields(self):
        with tempfile.TemporaryDirectory() as d:
            xlsx = Path(d) / "x.xlsx"
            _make_dde_xlsx(xlsx)
            # _Row accepts polarity? No — it doesn't. So no-filter would fail.
            # Test the case where the row dataclass DOES accept all known fields.

            @dataclass
            class _AllFieldsRow:
                stable_id: str
                text: str
                primary_actor: str = ""
                polarity: str = ""

            rows = load_into(xlsx, _AllFieldsRow)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].stable_id, "REQ-aaaa1111")
            self.assertEqual(rows[0].polarity, "Positive")

    def test_field_whitelist_filters_extras(self):
        with tempfile.TemporaryDirectory() as d:
            xlsx = Path(d) / "x.xlsx"
            _make_dde_xlsx(xlsx)
            rows = load_into(
                xlsx,
                _NarrowRow,
                fields={"stable_id", "text"},
            )
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].stable_id, "REQ-aaaa1111")
            self.assertEqual(rows[1].text, "The system shall log out.")

    def test_factory_can_be_a_dict(self):
        """row_factory doesn't have to be a dataclass."""
        with tempfile.TemporaryDirectory() as d:
            xlsx = Path(d) / "x.xlsx"
            _make_dde_xlsx(xlsx)

            def to_dict(**kw):
                return kw

            rows = load_into(xlsx, to_dict, fields={"stable_id", "text"})
            self.assertEqual(rows[0]["stable_id"], "REQ-aaaa1111")

    def test_empty_workbook_yields_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            xlsx = Path(d) / "empty.xlsx"
            wb = Workbook()
            wb.active.append(["ID", "Requirement"])  # header only, no data
            wb.save(xlsx)

            rows = load_into(xlsx, _NarrowRow, fields={"stable_id", "text"})
            self.assertEqual(rows, [])


class TestFindSidecar(unittest.TestCase):
    def test_returns_path_when_sidecar_exists(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            input_xlsx = d / "contract.xlsx"
            sidecar = d / "contract_actors.xlsx"
            input_xlsx.write_text("")
            sidecar.write_text("")

            found = find_sidecar(input_xlsx, suffix="_actors")
            self.assertEqual(found, sidecar)

    def test_returns_none_when_sidecar_missing(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            input_xlsx = d / "contract.xlsx"
            input_xlsx.write_text("")

            found = find_sidecar(input_xlsx, suffix="_actors")
            self.assertIsNone(found)

    def test_custom_extension(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            input_yaml = d / "spec.yaml"
            sidecar = d / "spec_meta.json"
            input_yaml.write_text("")
            sidecar.write_text("{}")

            found = find_sidecar(
                input_yaml, suffix="_meta", extension=".json"
            )
            self.assertEqual(found, sidecar)

    def test_directory_with_matching_name_returns_none(self):
        """A directory at the candidate path should not be treated as a sidecar."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            input_xlsx = d / "contract.xlsx"
            input_xlsx.write_text("")
            (d / "contract_actors.xlsx").mkdir()  # directory, not file

            found = find_sidecar(input_xlsx, suffix="_actors")
            self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
