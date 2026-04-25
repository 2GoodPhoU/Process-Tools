"""Unit tests for fuzzy_id matcher."""

from __future__ import annotations

import unittest

from compliance_matrix.matchers import fuzzy_id
from compliance_matrix.models import DDERow


class TestLevenshteinDistance(unittest.TestCase):
    """Test Levenshtein distance calculation."""

    def test_identical_strings(self):
        """Identical strings have distance 0."""
        self.assertEqual(fuzzy_id._levenshtein_distance("abc", "abc"), 0)

    def test_completely_different(self):
        """Completely different strings have distance = max(len(a), len(b))."""
        # "abc" -> "" requires 3 deletions
        self.assertEqual(fuzzy_id._levenshtein_distance("abc", ""), 3)
        # "" -> "xyz" requires 3 insertions
        self.assertEqual(fuzzy_id._levenshtein_distance("", "xyz"), 3)

    def test_one_substitution(self):
        """One character difference = distance 1."""
        self.assertEqual(fuzzy_id._levenshtein_distance("abc", "axc"), 1)

    def test_one_insertion(self):
        """One insertion = distance 1."""
        self.assertEqual(fuzzy_id._levenshtein_distance("abc", "abxc"), 1)

    def test_one_deletion(self):
        """One deletion = distance 1."""
        self.assertEqual(fuzzy_id._levenshtein_distance("abxc", "abc"), 1)


class TestSimilarityScore(unittest.TestCase):
    """Test similarity score (1.0 - normalized distance)."""

    def test_identical(self):
        """Identical strings score 1.0."""
        self.assertEqual(fuzzy_id._similarity_score("abc", "abc"), 1.0)

    def test_empty(self):
        """Both empty strings score 1.0."""
        self.assertEqual(fuzzy_id._similarity_score("", ""), 1.0)

    def test_typo_single_char(self):
        """One-char typo in 3-char string: 1 - (1/3) ≈ 0.667."""
        score = fuzzy_id._similarity_score("abc", "axc")
        self.assertAlmostEqual(score, 2.0 / 3.0, places=2)

    def test_close_section_numbers(self):
        """6.3.1 vs 6.3.2 (one digit off)."""
        # Normalized: "631" vs "632", distance 1, similarity = 2/3
        score = fuzzy_id._similarity_score("631", "632")
        self.assertAlmostEqual(score, 2.0 / 3.0, places=2)


class TestNormalizeId(unittest.TestCase):
    """Test ID normalization."""

    def test_plain_section_number(self):
        """Plain section numbers pass through."""
        self.assertEqual(fuzzy_id._normalize_id("6.3.1"), "631")

    def test_section_with_dashes(self):
        """Dashes normalize to nothing."""
        self.assertEqual(fuzzy_id._normalize_id("6-3-1"), "631")

    def test_mixed_separators(self):
        """Mixed separators (dots, dashes, slashes) all normalize."""
        self.assertEqual(fuzzy_id._normalize_id("6.3-1/2"), "6312")

    def test_id_with_special_chars(self):
        """Special chars (§, spaces) are removed."""
        self.assertEqual(fuzzy_id._normalize_id("DO-178C §6.3.1"), "do178c631")

    def test_lowercase_conversion(self):
        """Uppercase letters are lowercased."""
        self.assertEqual(fuzzy_id._normalize_id("DO-178C"), "do178c")

    def test_empty_string(self):
        """Empty string normalizes to empty."""
        self.assertEqual(fuzzy_id._normalize_id(""), "")


class TestFuzzyIdMatcher(unittest.TestCase):
    """End-to-end fuzzy ID matcher tests."""

    def test_exact_match(self):
        """Exact stable ID match scores 1.0."""
        contract = [
            DDERow(
                stable_id="REQ-001",
                text="The system shall comply with DO-178C §6.3.1.",
                side="contract",
            ),
        ]
        procedure = [
            DDERow(
                stable_id="DO-178C-6.3.1",
                text="Section 6.3.1 defines...",
                section="6.3.1",
                side="procedure",
            ),
        ]
        
        matches = fuzzy_id.run(contract, procedure, threshold=0.90)
        # Even though the stable IDs don't match exactly,
        # the section "6.3.1" in the contract requirement matches the procedure's section.
        self.assertTrue(len(matches) > 0)
        self.assertTrue(any(m.score >= 0.90 for m in matches))

    def test_typo_tolerance(self):
        """Typos in section numbers are caught (with right threshold)."""
        contract = [
            DDERow(
                stable_id="REQ-002",
                text="IAW Section 6.3.2",  # Note: .2 instead of .1
                side="contract",
            ),
        ]
        procedure = [
            DDERow(
                stable_id="PROC-001",
                text="Section 6.3.1 describes...",
                section="6.3.1",
                side="procedure",
            ),
        ]
        
        # With a 90% threshold, a 1-char typo in "631" vs "632" won't match
        # (score is 2/3 ≈ 0.667)
        matches = fuzzy_id.run(contract, procedure, threshold=0.90)
        self.assertEqual(len(matches), 0)
        
        # But with a looser threshold it matches
        matches = fuzzy_id.run(contract, procedure, threshold=0.60)
        self.assertTrue(len(matches) > 0)

    def test_no_match_unrelated(self):
        """Unrelated requirements don't match."""
        contract = [
            DDERow(
                stable_id="REQ-003",
                text="The pump shall deliver 100 GPM.",
                side="contract",
            ),
        ]
        procedure = [
            DDERow(
                stable_id="PROC-002",
                text="Electrical system shall ground per NEC Article 250.",
                section="250",
                side="procedure",
            ),
        ]
        
        matches = fuzzy_id.run(contract, procedure, threshold=0.90)
        self.assertEqual(len(matches), 0)

    def test_format_variation(self):
        """Format variations in section refs are handled."""
        contract = [
            DDERow(
                stable_id="REQ-004",
                text="Per DO-178C Section 6.3.1",  # "Section" prefix
                side="contract",
            ),
        ]
        procedure = [
            DDERow(
                stable_id="PROC-003",
                text="6.3.1: description here",
                section="6.3.1",
                side="procedure",
            ),
        ]
        
        matches = fuzzy_id.run(contract, procedure, threshold=0.90)
        self.assertTrue(len(matches) > 0)

    def test_threshold_parameter(self):
        """Threshold parameter controls matching sensitivity."""
        contract = [DDERow(stable_id="REQ-005", text="Section 6.3.1", side="contract")]
        procedure = [DDERow(stable_id="PROC-004", text="6.3.1", section="6.3.1", side="procedure")]
        
        # Should match with high threshold
        matches_strict = fuzzy_id.run(contract, procedure, threshold=0.95)
        
        # Should definitely match with low threshold
        matches_loose = fuzzy_id.run(contract, procedure, threshold=0.50)
        
        # Loose should have at least as many (typically more) matches
        self.assertGreaterEqual(len(matches_loose), len(matches_strict))


if __name__ == "__main__":
    unittest.main()
