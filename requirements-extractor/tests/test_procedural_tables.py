"""Regression tests for the procedural "required-action" table pipeline.

Covers the four parser changes Eric's 2026-04-23 work-network pass
drove (FIELD_NOTES §4, plus the 3-col fixtures in
``samples/procedures/procedural_*.docx``):

    1a. Header-aware ``| (blank) | Step | Required Action |`` detection
        — every body row is a requirement regardless of modal keywords.
    1b. Blank-actor continuation — blank column-1 body cells inherit
        the actor from the nearest non-blank predecessor within the
        same table.
    1c. Multi-actor-cell resolution — column-1 cells that list several
        candidates ("Auth Service, Gateway, Logger") resolve per-row
        to whichever candidate the sentence subject names; sentences
        that don't name a candidate fall back to the joined cell text.
    1d. Bullet / numbered list per row — each list item emits as its
        own requirement (this one falls out of 1a naturally since
        bullets were already paragraph-split before, just gated behind
        the keyword detector).

Also pins that the procedural pipeline does NOT change behaviour for
the five existing 2-column procedural fixtures — the new rules are
gated behind the header signal.

Run:  python -m unittest tests.test_procedural_tables
"""

from __future__ import annotations

import unittest
from pathlib import Path

from requirements_extractor.config import resolve_config
from requirements_extractor.parser import (
    REQUIRED_ACTION_KEYWORD,
    _resolve_primary_from_candidates,
    _split_candidate_actors,
    is_required_action_header,
    parse_docx,
)


PROCEDURES = Path(__file__).resolve().parents[1] / "samples" / "procedures"


def _parse(fixture_name: str):
    """Parse a fixture and return the full Requirement list.

    Uses ``resolve_config`` with no run-config so the per-doc
    ``<stem>.reqx.yaml`` is picked up.  Resolver-fn is a no-op — these
    tests care about primary-actor / text / keyword shape, not
    secondary-actor resolution.
    """
    path = PROCEDURES / f"{fixture_name}.docx"
    cfg = resolve_config(docx_path=path)
    return parse_docx(path, resolver_fn=lambda t, a: [], config=cfg)


def _table_rows(reqs):
    """Filter a Requirement list down to in-table rows.

    The four procedural fixtures all have a short prose preamble that
    can spuriously match keywords like "must" / "required" / "may"
    because it *describes* the fixture's purpose.  The table-level
    assertions below should not depend on those preamble artefacts, so
    we filter to rows whose row_ref names a table.
    """
    return [r for r in reqs if r.row_ref.startswith("Table ")]


# ---------------------------------------------------------------------------
# Pure-helper unit tests
# ---------------------------------------------------------------------------


class TestIsRequiredActionHeader(unittest.TestCase):
    """Header-shape detector — must match exactly three cells with
    ``("", "step", "required action")`` after whitespace/case
    normalisation, and nothing else.
    """

    def test_exact_match(self) -> None:
        self.assertTrue(is_required_action_header(["", "Step", "Required Action"]))

    def test_case_insensitive(self) -> None:
        self.assertTrue(is_required_action_header(["", "STEP", "required action"]))
        self.assertTrue(is_required_action_header(["", "step", "Required ACTION"]))

    def test_whitespace_tolerant(self) -> None:
        self.assertTrue(is_required_action_header(["  ", " Step ", "Required  Action"]))
        self.assertTrue(is_required_action_header(["", "Step", "Required\nAction"]))

    def test_wrong_col1_rejected(self) -> None:
        # Actor|Step|Required Action is the *other* 3-col shape — keeps
        # the normal keyword-driven detection path.
        self.assertFalse(
            is_required_action_header(["Actor", "Step", "Required Action"])
        )

    def test_wrong_col2_rejected(self) -> None:
        self.assertFalse(
            is_required_action_header(["", "Number", "Required Action"])
        )

    def test_wrong_col3_rejected(self) -> None:
        self.assertFalse(is_required_action_header(["", "Step", "Action"]))
        self.assertFalse(is_required_action_header(["", "Step", "Description"]))

    def test_wrong_column_count_rejected(self) -> None:
        self.assertFalse(is_required_action_header(["", "Step"]))
        self.assertFalse(
            is_required_action_header(["", "Step", "Required Action", "Notes"])
        )


class TestSplitCandidateActors(unittest.TestCase):
    """Candidate-cell parser.  Returns [] for single-actor cells so the
    caller can cleanly decide whether to take the multi-actor path.
    """

    def test_comma_separated(self) -> None:
        self.assertEqual(
            _split_candidate_actors("Auth Service, Gateway, Logger"),
            ["Auth Service", "Gateway", "Logger"],
        )

    def test_slash_separated(self) -> None:
        self.assertEqual(
            _split_candidate_actors("Auth Service / Gateway / Logger"),
            ["Auth Service", "Gateway", "Logger"],
        )

    def test_mixed_separators(self) -> None:
        self.assertEqual(
            _split_candidate_actors("Auth Service and Gateway & Logger"),
            ["Auth Service", "Gateway", "Logger"],
        )

    def test_single_actor_returns_empty(self) -> None:
        # The "multi-actor signal" is at least two parts — a single
        # name returns [] so the caller doesn't accidentally enter the
        # candidate-resolution path for a conventional single-actor
        # cell.
        self.assertEqual(_split_candidate_actors("Operator"), [])

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_split_candidate_actors(""), [])
        self.assertEqual(_split_candidate_actors("   "), [])

    def test_trailing_separator_still_single(self) -> None:
        # "A," is still one actor — don't invent a ghost second entry.
        self.assertEqual(_split_candidate_actors("Auth Service,"), [])


class TestResolvePrimaryFromCandidates(unittest.TestCase):
    """Per-sentence candidate picker.  Returns the earliest-appearing
    candidate (case-insensitive, word-bounded) or None when none match.
    """

    CANDS = ["Auth Service", "Gateway", "Logger"]

    def test_single_subject_match(self) -> None:
        self.assertEqual(
            _resolve_primary_from_candidates(
                "The Gateway shall forward the request.", self.CANDS
            ),
            "Gateway",
        )

    def test_multi_word_candidate(self) -> None:
        self.assertEqual(
            _resolve_primary_from_candidates(
                "The Auth Service must verify the token.", self.CANDS
            ),
            "Auth Service",
        )

    def test_earliest_candidate_wins(self) -> None:
        # Both Gateway (pos ~4) and Auth Service (later) appear.
        self.assertEqual(
            _resolve_primary_from_candidates(
                "The Gateway forwards the request to the Auth Service.",
                self.CANDS,
            ),
            "Gateway",
        )

    def test_none_matches_returns_none(self) -> None:
        self.assertIsNone(
            _resolve_primary_from_candidates(
                "If verification fails, an error shall be returned.",
                self.CANDS,
            )
        )

    def test_word_bounded(self) -> None:
        # "Authentication" must NOT match the candidate "Auth Service"
        # — word-boundary aware matching keeps us from false-positives
        # on substring-like names.
        self.assertIsNone(
            _resolve_primary_from_candidates(
                "Authentication succeeds only after token verification.",
                self.CANDS,
            )
        )


# ---------------------------------------------------------------------------
# End-to-end fixture tests — one per parser change
# ---------------------------------------------------------------------------


class TestProceduralNoKeywords(unittest.TestCase):
    """1a — header signal captures every body row even without modal
    keywords.  Fixture has zero shall/must/should/may in body text.
    """

    def test_five_body_rows_captured(self) -> None:
        reqs = _table_rows(_parse("procedural_no_keywords"))
        self.assertEqual(len(reqs), 5)

    def test_header_row_not_emitted(self) -> None:
        reqs = _table_rows(_parse("procedural_no_keywords"))
        # Row 1 is the header row and must be skipped — first in-table
        # requirement should come from Row 2.
        self.assertTrue(reqs[0].row_ref.endswith("Row 2"))

    def test_all_keyword_markers_are_synthetic(self) -> None:
        reqs = _table_rows(_parse("procedural_no_keywords"))
        for r in reqs:
            self.assertEqual(r.keywords, [REQUIRED_ACTION_KEYWORD])

    def test_actors_are_as_authored(self) -> None:
        reqs = _table_rows(_parse("procedural_no_keywords"))
        expected = ["Operator", "Operator", "Supervisor", "Supervisor", "Operator"]
        self.assertEqual([r.primary_actor for r in reqs], expected)

    def test_all_rows_are_hard_positive(self) -> None:
        # Procedural rows are binding (by virtue of the header), never
        # Soft.  Polarity defaults to Positive since we didn't run the
        # negation detector on them.
        reqs = _table_rows(_parse("procedural_no_keywords"))
        for r in reqs:
            self.assertEqual(r.req_type, "Hard")
            self.assertEqual(r.polarity, "Positive")


class TestProceduralActorContinuation(unittest.TestCase):
    """1b — blank column-1 body cells inherit the actor from the
    nearest non-blank predecessor within the same table.
    """

    def test_five_body_rows_captured(self) -> None:
        reqs = _table_rows(_parse("procedural_actor_continuation"))
        self.assertEqual(len(reqs), 5)

    def test_blank_actor_inherits_previous(self) -> None:
        reqs = _table_rows(_parse("procedural_actor_continuation"))
        # Body: R2=Operator, R3=blank(→Operator), R4=Supervisor,
        #       R5=blank(→Supervisor), R6=Operator
        expected = ["Operator", "Operator", "Supervisor", "Supervisor", "Operator"]
        self.assertEqual([r.primary_actor for r in reqs], expected)

    def test_no_empty_primary_actor_after_continuation(self) -> None:
        reqs = _table_rows(_parse("procedural_actor_continuation"))
        # After continuation every body row must have a non-empty
        # actor — if this ever fails, the fallback path regressed.
        for r in reqs:
            self.assertTrue(
                r.primary_actor.strip(),
                msg=f"row {r.row_ref} has empty primary_actor",
            )


class TestProceduralMultiActorCell(unittest.TestCase):
    """1c — column-1 cells that list several candidates resolve to the
    candidate whose name appears in the sentence subject; sentences
    that don't name any candidate fall back to the joined cell text.
    """

    def test_four_body_rows_captured(self) -> None:
        reqs = _table_rows(_parse("procedural_multi_actor_cell"))
        self.assertEqual(len(reqs), 4)

    def test_subject_picked_per_sentence(self) -> None:
        reqs = _table_rows(_parse("procedural_multi_actor_cell"))
        # Order: Gateway, Auth Service, Logger, then fallback on
        # the sentence that doesn't name a candidate.
        expected = [
            "Gateway",
            "Auth Service",
            "Logger",
            "Auth Service, Gateway, Logger",
        ]
        self.assertEqual([r.primary_actor for r in reqs], expected)

    def test_slash_separated_cell_also_resolves(self) -> None:
        reqs = _table_rows(_parse("procedural_multi_actor_cell"))
        # Row 4 uses slash-separation in col 1 — must still resolve.
        # That row is the Logger row (index 2 in the fixture's order).
        logger_row = reqs[2]
        self.assertEqual(logger_row.primary_actor, "Logger")
        self.assertIn("Logger shall emit", logger_row.text)


class TestProceduralBulletRows(unittest.TestCase):
    """1d — each bullet / numbered list item emits as its own
    requirement with a distinct block_ref.  Stacks cleanly with 1a
    (force-requirement) and 1b (actor continuation).
    """

    def test_ten_body_requirements_captured(self) -> None:
        # R2=1 lead-in, R3=1 lead-in + 3 bullets, R4=1 sentence,
        # R5=1 lead-in + 3 numbered items = 10.
        reqs = _table_rows(_parse("procedural_bullet_rows"))
        self.assertEqual(len(reqs), 10)

    def test_bullets_have_distinct_block_refs(self) -> None:
        reqs = _table_rows(_parse("procedural_bullet_rows"))
        # Row 3: lead-in Paragraph + Bullet 1/2/3
        row3 = [r for r in reqs if r.row_ref.endswith("Row 3")]
        self.assertEqual(len(row3), 4)
        refs = [r.block_ref for r in row3]
        self.assertIn("Paragraph 1", refs)
        self.assertIn("Bullet 1", refs)
        self.assertIn("Bullet 2", refs)
        self.assertIn("Bullet 3", refs)

    def test_bullets_inherit_actor_from_row(self) -> None:
        reqs = _table_rows(_parse("procedural_bullet_rows"))
        row3 = [r for r in reqs if r.row_ref.endswith("Row 3")]
        for r in row3:
            self.assertEqual(r.primary_actor, "QA Lead")

    def test_blank_actor_row_inherits_then_bullets_continue(self) -> None:
        reqs = _table_rows(_parse("procedural_bullet_rows"))
        # Row 4 has a blank Actor cell — should inherit "QA Lead"
        # from the Row 3 group above.
        row4 = [r for r in reqs if r.row_ref.endswith("Row 4")]
        self.assertEqual(len(row4), 1)
        self.assertEqual(row4[0].primary_actor, "QA Lead")

    def test_numbered_list_also_emits_per_item(self) -> None:
        reqs = _table_rows(_parse("procedural_bullet_rows"))
        row5 = [r for r in reqs if r.row_ref.endswith("Row 5")]
        # Lead-in (has "must") + 3 numbered items
        self.assertEqual(len(row5), 4)
        for r in row5:
            self.assertEqual(r.primary_actor, "Change Board")


# ---------------------------------------------------------------------------
# Gating: the new rules must NOT leak into 2-col tables
# ---------------------------------------------------------------------------


class TestExistingFixturesUnchanged(unittest.TestCase):
    """The four new parser changes are all gated behind the
    required-action header signal.  A plain 2-col fixture must produce
    the same requirement count it always did — if any of 1a/1b/1c/1d
    starts leaking into the default path, one of these assertions will
    fire.
    """

    #: Baseline row counts for the conventional 2-col procedure
    #: fixtures.  If the parser output for one of these changes, that's
    #: either an intended improvement (update the number) or a
    #: regression of the gating (investigate first).
    EXPECTED_COUNTS = {
        "simple_two_actors": 4,
        "passive_voice": 4,
        "parallel_flows": 8,
    }

    def test_two_col_fixture_counts(self) -> None:
        for name, expected in self.EXPECTED_COUNTS.items():
            with self.subTest(fixture=name):
                reqs = _table_rows(_parse(name))
                self.assertEqual(
                    len(reqs), expected,
                    msg=(
                        f"{name}: expected {expected} table rows, got "
                        f"{len(reqs)}.  Either the parser output drifted "
                        f"(regression) or the expected count needs a bump."
                    ),
                )

    def test_two_col_no_synthetic_required_action_keyword(self) -> None:
        """The synthetic ``(Required Action)`` keyword must only ever
        appear on procedural-table rows — a 2-col fixture emitting it
        would mean the header gate broke."""
        for name in self.EXPECTED_COUNTS:
            with self.subTest(fixture=name):
                reqs = _parse(name)
                for r in reqs:
                    self.assertNotIn(
                        REQUIRED_ACTION_KEYWORD, r.keywords,
                        msg=f"{name} row {r.row_ref} spuriously got the "
                            f"required-action marker",
                    )


if __name__ == "__main__":
    unittest.main()
