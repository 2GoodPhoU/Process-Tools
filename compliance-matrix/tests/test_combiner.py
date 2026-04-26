"""Tests for the combiner's weight-application logic.

Pinned in 2026-04-25 after a bug where ``fuzzy_id`` shipped without
an entry in ``DEFAULT_WEIGHTS`` and silently used the 0.5 fallback.
These tests assert every shipped matcher has an explicit weight and
that weights flow through to the combined score correctly.
"""

from __future__ import annotations

import unittest

from compliance_matrix.combiner import DEFAULT_WEIGHTS, combine
from compliance_matrix.models import Match


# Every matcher name that ships under compliance_matrix.matchers/. If a
# new matcher is added, add it here; the missing-weight assertion below
# will fail otherwise, surfacing the bug at test time rather than in
# production output.
SHIPPED_MATCHERS = {
    "explicit_id",
    "manual_mapping",
    "fuzzy_id",
    "similarity",
    "keyword_overlap",
}


class TestDefaultWeights(unittest.TestCase):
    def test_every_shipped_matcher_has_an_explicit_weight(self):
        """Every matcher under matchers/ must have a deliberate weight.

        Falling back to combiner's 0.5 default is a bug — it means the
        matcher contributes a score that wasn't picked deliberately.
        """
        missing = SHIPPED_MATCHERS - DEFAULT_WEIGHTS.keys()
        self.assertEqual(
            missing,
            set(),
            f"Matchers missing from DEFAULT_WEIGHTS: {sorted(missing)}",
        )

    def test_fuzzy_id_weight_is_at_least_0_9(self):
        """Fuzzy-id is a near-gold matcher (catches typo'd citations).

        Anything below 0.9 would imply we trust it less than similarity
        (0.85), which would defeat its purpose.
        """
        self.assertGreaterEqual(DEFAULT_WEIGHTS["fuzzy_id"], 0.9)

    def test_gold_matchers_at_full_weight(self):
        """Manual mappings and explicit IDs are gold standard."""
        self.assertEqual(DEFAULT_WEIGHTS["explicit_id"], 1.0)
        self.assertEqual(DEFAULT_WEIGHTS["manual_mapping"], 1.0)


class TestCombineWeightApplication(unittest.TestCase):
    def test_weight_multiplies_score(self):
        """combine() multiplies match score by the matcher's weight."""
        m = Match(
            contract_id="REQ-A1",
            procedure_id="PROC-1",
            matcher="similarity",
            score=0.5,
            evidence="cosine 0.5",
        )
        out = combine([m])
        # similarity weight is 0.85 → combined 0.5 * 0.85 = 0.425
        self.assertAlmostEqual(out[("REQ-A1", "PROC-1")].score, 0.425)

    def test_unknown_matcher_falls_back_to_0_5(self):
        """Unknown matcher names get the 0.5 fallback (safety net).

        This protects against the previous failure mode where a
        not-yet-registered matcher silently contributed at 0.5.
        Production matchers must NOT rely on this — see
        TestDefaultWeights.test_every_shipped_matcher_has_an_explicit_weight.
        """
        m = Match(
            contract_id="REQ-A1",
            procedure_id="PROC-1",
            matcher="experimental_matcher_not_yet_in_dict",
            score=1.0,
            evidence="hypothetical",
        )
        out = combine([m])
        self.assertAlmostEqual(out[("REQ-A1", "PROC-1")].score, 0.5)

    def test_max_wins_across_matchers(self):
        """When multiple matchers fire on the same pair, the max
        weighted score is recorded (not sum, not average)."""
        matches = [
            # similarity 0.6 * 0.85 = 0.51
            Match("REQ-A1", "PROC-1", "similarity", 0.6, "cosine"),
            # fuzzy_id 0.9 * 0.95 = 0.855  ← should win
            Match("REQ-A1", "PROC-1", "fuzzy_id", 0.9, "lev 0.9"),
            # keyword_overlap 0.5 * 0.65 = 0.325
            Match("REQ-A1", "PROC-1", "keyword_overlap", 0.5, "jaccard"),
        ]
        out = combine(matches)
        record = out[("REQ-A1", "PROC-1")]
        self.assertAlmostEqual(record.score, 0.855)
        # All three should appear in the matchers list and evidence
        self.assertEqual(set(record.matchers), {"similarity", "fuzzy_id", "keyword_overlap"})
        self.assertEqual(len(record.evidence), 3)

    def test_custom_weights_override_defaults(self):
        """Caller can supply their own weights dict."""
        m = Match("REQ-A1", "PROC-1", "similarity", 0.5, "cosine")
        out = combine([m], weights={"similarity": 0.5})
        self.assertAlmostEqual(out[("REQ-A1", "PROC-1")].score, 0.25)


if __name__ == "__main__":
    unittest.main()
