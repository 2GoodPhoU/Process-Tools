"""Regression test — 0.6.0 baseline must survive 0.6.1.

The 0.6.1 patch adds compound-requirement detection, an additive feature
that runs as a pre-pass over a parent block's children.  The contract
documented in PATCH-0.6.1-NOTES.md is:

    A document parsed by 0.6.1 that has no compound patterns must
    produce IDENTICAL output to 0.6.0.

This test pins that contract.  Before any source-level changes were
made, the existing fixture set under ``samples/procedures/*.docx``
was parsed and the resulting requirement list was serialised into
``tests/baselines/procedures_baseline_0_6_0.json`` (one row per
extracted requirement, capturing every column the writers emit).

This test:

  1. Re-parses the same fixtures with the current code.
  2. Asserts the per-fixture row counts match the baseline.
  3. Asserts every per-row scalar column matches verbatim.

A test failure here is the canary for ANY behavioural drift in the
shipping parser, not just the compound pre-pass.  If a future patch
intentionally changes baseline output for one of these fixtures, the
correct fix is to:

  * regenerate the baseline JSON with the new expected values, AND
  * document the change in PATCH-N.N.N-NOTES.md.

Compound-fixture coverage lives separately in ``test_compound.py`` —
those tests live under ``samples/procedures/compound/`` so the glob
here doesn't pick them up.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.config import resolve_config
from requirements_extractor.parser import parse_docx


HERE = Path(__file__).resolve().parent
BASELINE_PATH = HERE / "baselines" / "procedures_baseline_0_6_0.json"
SAMPLES_DIR = HERE.parent / "samples" / "procedures"


def _row_to_dict(r) -> dict:
    """Reduce a Requirement to the fields baseline-ed in 0.6.0."""
    return {
        "order": r.order,
        "source_file": r.source_file,
        "row_ref": r.row_ref,
        "block_ref": r.block_ref,
        "primary_actor": r.primary_actor,
        "secondary_actors": list(r.secondary_actors),
        "text": r.text,
        "req_type": r.req_type,
        "keywords": list(r.keywords),
        "confidence": r.confidence,
        "polarity": r.polarity,
        "stable_id": r.stable_id,
    }


class TestProceduresBaseline(unittest.TestCase):
    """Every fixture in samples/procedures/*.docx must match 0.6.0."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.resolver = ActorResolver()

    def _reparse(self, name: str):
        docx = SAMPLES_DIR / name
        cfg = resolve_config(docx_path=docx)
        return parse_docx(docx, resolver_fn=self.resolver.resolve, config=cfg)

    def test_baseline_covers_every_top_level_fixture(self) -> None:
        """Sanity: the baseline names every .docx under samples/procedures.

        If a new top-level fixture was added without rebuilding the
        baseline, this fails fast — the error is more useful than a
        per-fixture mismatch downstream.
        """
        baseline_names = set(self.baseline["files"].keys())
        actual_names = {p.name for p in SAMPLES_DIR.glob("*.docx")}
        self.assertEqual(baseline_names, actual_names)

    def test_row_counts_match(self) -> None:
        for name, expected in self.baseline["files"].items():
            with self.subTest(fixture=name):
                reqs = self._reparse(name)
                self.assertEqual(
                    len(reqs), expected["count"],
                    f"row count drift in {name}: "
                    f"got {len(reqs)}, baseline {expected['count']}",
                )

    def test_per_row_content_matches(self) -> None:
        for name, expected in self.baseline["files"].items():
            with self.subTest(fixture=name):
                reqs = self._reparse(name)
                self.assertEqual(
                    len(reqs), expected["count"],
                    f"row count drift in {name}",
                )
                for got, exp in zip(reqs, expected["rows"]):
                    got_dict = _row_to_dict(got)
                    self.assertEqual(
                        got_dict, exp,
                        f"{name} order={got.order}: row drifted from baseline",
                    )


if __name__ == "__main__":
    unittest.main()
