"""Regression test - 0.6.1 baseline must survive 0.6.2 in `single` mode.

The 0.6.2 patch adds multi-action-requirement detection + decomposition.
By design it is additive: with ``multi_action.mode == "single"`` the
extractor's row-level output is byte-identical to 0.6.1.

This test pins that contract for every fixture in
``samples/procedures/`` (top-level) AND
``samples/procedures/compound/`` (the 0.6.1 fixtures shipped in the
prior patch).  A failure here is the canary for ANY behavioural drift
in single-mode extraction.

Captured baseline:
    tests/baselines/procedures_baseline_0_6_1.json

Captured by ``capture_baseline.py`` BEFORE any 0.6.2 source-level
changes were made.  If a future patch intentionally changes baseline
output for one of these fixtures, the correct fix is to:

  * regenerate the baseline JSON with the new expected values, AND
  * document the change in PATCH-N.N.N-NOTES.md.

Why a separate file from ``test_regression_baseline.py`` (the 0.6.0
baseline test)?  The 0.6.0 baseline pins behaviour BEFORE compound
detection shipped; the 0.6.1 baseline pins behaviour AFTER compound
detection but BEFORE multi-action detection.  Both contracts matter:
the 0.6.0 file proves single-mode 0.6.2 still matches 0.6.0 for
non-compound fixtures; the 0.6.1 file proves single-mode 0.6.2 still
matches 0.6.1 INCLUDING compound aggregation.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.config import (
    build_config,
    load_config_raw,
    merge_raw,
)
from requirements_extractor.parser import parse_docx


HERE = Path(__file__).resolve().parent
BASELINE_PATH = HERE / "baselines" / "procedures_baseline_0_6_1.json"
SAMPLES_DIR = HERE.parent / "samples" / "procedures"
COMPOUND_DIR = SAMPLES_DIR / "compound"


def _row_to_dict(r) -> dict:
    """Reduce a Requirement to the fields baseline-ed in 0.6.1.

    Includes ``notes`` because the 0.6.1 patch's compound rows carry
    an annotation there - the regression contract is that single-mode
    0.6.2 reproduces those annotations verbatim, including casing,
    whitespace, and connector word.
    """
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
        "notes": r.notes,
    }


def _fixture_path(key: str) -> Path:
    """Translate a baseline key to a filesystem path.

    Keys are either bare filenames (``simple_two_actors.docx``) for
    top-level fixtures or ``compound/<filename>`` for the 0.6.1
    compound-fixture subset.
    """
    if key.startswith("compound/"):
        return COMPOUND_DIR / key.split("/", 1)[1]
    return SAMPLES_DIR / key


def _parse_single_mode(docx: Path):
    """Re-parse a fixture under ``multi_action.mode = single``.

    Layered the same way :func:`config.resolve_config` would for the
    real run: per-doc ``<stem>.reqx.yaml`` first (if present), then
    the single-mode override.  This mirrors how a user setting
    ``mode: single`` in their per-run config would interact with any
    per-doc tweaks.
    """
    base_raw: dict = {}
    per_doc = docx.parent / f"{docx.stem}.reqx.yaml"
    if per_doc.exists():
        base_raw = load_config_raw(per_doc)
    raw = merge_raw(base_raw, {"multi_action": {"mode": "single"}})
    cfg = build_config(raw, source="0.6.1-baseline-test")
    resolver = ActorResolver()
    return parse_docx(docx, resolver_fn=resolver.resolve, config=cfg)


class TestProceduresBaseline061(unittest.TestCase):
    """Every fixture must match 0.6.1 in single mode."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def test_baseline_covers_every_fixture(self) -> None:
        baseline_names = set(self.baseline["files"].keys())
        actual_names = {p.name for p in SAMPLES_DIR.glob("*.docx")}
        actual_names |= {f"compound/{p.name}" for p in COMPOUND_DIR.glob("*.docx")}
        self.assertEqual(baseline_names, actual_names)

    def test_row_counts_match(self) -> None:
        for name, expected in self.baseline["files"].items():
            with self.subTest(fixture=name):
                reqs = _parse_single_mode(_fixture_path(name))
                self.assertEqual(
                    len(reqs), expected["count"],
                    f"row count drift in {name}: "
                    f"got {len(reqs)}, baseline {expected['count']}",
                )

    def test_per_row_content_matches(self) -> None:
        for name, expected in self.baseline["files"].items():
            with self.subTest(fixture=name):
                reqs = _parse_single_mode(_fixture_path(name))
                self.assertEqual(
                    len(reqs), expected["count"],
                    f"row count drift in {name}",
                )
                for got, exp in zip(reqs, expected["rows"]):
                    got_dict = _row_to_dict(got)
                    self.assertEqual(
                        got_dict, exp,
                        f"{name} order={got.order}: row drifted from "
                        f"0.6.1 baseline",
                    )


if __name__ == "__main__":
    unittest.main()
