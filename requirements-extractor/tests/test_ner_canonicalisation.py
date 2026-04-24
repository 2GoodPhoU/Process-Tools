"""Unit tests for the NER canonicalisation helper (REVIEW §1.7).

Covers the pure ``canonicalise_ner_name`` function directly — the
full ``ActorResolver.iter_nlp_hits`` path requires spaCy + an English
model, so it's exercised by the NLP smoke-test procedure
(``docs/NLP_BUNDLE_SMOKE_TEST.md``) rather than here.

Run:  python -m unittest tests.test_ner_canonicalisation
"""

from __future__ import annotations

import unittest

from requirements_extractor.actors import canonicalise_ner_name


class TestLeadingDeterminers(unittest.TestCase):
    """Strip 'the' / 'a' / 'an' from the start of the entity text."""

    def test_the_stripped(self) -> None:
        self.assertEqual(
            canonicalise_ner_name("the Auth Service"),
            "Auth Service",
        )

    def test_the_case_insensitive(self) -> None:
        self.assertEqual(canonicalise_ner_name("The Gateway"), "Gateway")
        self.assertEqual(canonicalise_ner_name("THE LOGGER"), "LOGGER")

    def test_a_and_an_stripped(self) -> None:
        self.assertEqual(canonicalise_ner_name("a User"), "User")
        self.assertEqual(canonicalise_ner_name("an Operator"), "Operator")

    def test_no_determiner_untouched(self) -> None:
        self.assertEqual(canonicalise_ner_name("Gateway"), "Gateway")

    def test_internal_the_not_touched(self) -> None:
        # "The" inside the name (not at start) must survive so we don't
        # butcher names like "Bank of the West".
        self.assertEqual(
            canonicalise_ner_name("Bank of the West"),
            "Bank of the West",
        )


class TestTrailingPossessives(unittest.TestCase):
    """Strip ``'s`` / curly-apostrophe ``\u2019s`` from the end."""

    def test_ascii_apostrophe(self) -> None:
        self.assertEqual(
            canonicalise_ner_name("Gateway's"),
            "Gateway",
        )

    def test_curly_apostrophe(self) -> None:
        self.assertEqual(
            canonicalise_ner_name("Auth Service\u2019s"),
            "Auth Service",
        )

    def test_no_possessive_untouched(self) -> None:
        self.assertEqual(
            canonicalise_ner_name("Gateway"),
            "Gateway",
        )

    def test_combined_with_determiner(self) -> None:
        # "the Gateway's" → strip both in one pass.
        self.assertEqual(
            canonicalise_ner_name("the Gateway's"),
            "Gateway",
        )


class TestEmptyAndPunctuation(unittest.TestCase):
    """Drop entities that are empty or lack any letters/digits."""

    def test_empty_string_dropped(self) -> None:
        self.assertIsNone(canonicalise_ner_name(""))

    def test_whitespace_only_dropped(self) -> None:
        self.assertIsNone(canonicalise_ner_name("   "))

    def test_punctuation_only_dropped(self) -> None:
        # After stripping "the ", nothing alphanumeric remains.
        self.assertIsNone(canonicalise_ner_name(",,,"))

    def test_none_stripping_leaves_nothing_dropped(self) -> None:
        # "the" alone, then the determiner strip yields ""; drop.
        self.assertIsNone(canonicalise_ner_name("the"))


class TestCanonicalOverlapFilter(unittest.TestCase):
    """When a canonical list is provided, keep only entities that
    share at least one word-bounded token with any canonical name."""

    CANONICAL = ["Auth Service", "Gateway", "Logger"]

    def test_matching_canonical_passes(self) -> None:
        self.assertEqual(
            canonicalise_ner_name(
                "the Gateway", canonical_names=self.CANONICAL,
            ),
            "Gateway",
        )

    def test_partial_token_match_passes(self) -> None:
        # "Auth" overlaps the canonical "Auth Service".
        self.assertEqual(
            canonicalise_ner_name(
                "Auth", canonical_names=self.CANONICAL,
            ),
            "Auth",
        )

    def test_non_overlapping_dropped(self) -> None:
        # "ISO" shares no token with any canonical name — dropped.
        self.assertIsNone(
            canonicalise_ner_name(
                "ISO", canonical_names=self.CANONICAL,
            )
        )

    def test_substring_without_word_boundary_not_a_match(self) -> None:
        # "AuthoringSystem" has NO whole-word token overlap with the
        # canonicals — must not falsely match on the "Auth" prefix.
        self.assertIsNone(
            canonicalise_ner_name(
                "AuthoringSystem", canonical_names=self.CANONICAL,
            )
        )

    def test_empty_canonical_list_passes_everything(self) -> None:
        # Empty list is truthy-falsy (len 0) — treated the same as
        # None: no filter applied.
        self.assertEqual(
            canonicalise_ner_name("ISO", canonical_names=[]),
            "ISO",
        )

    def test_none_canonical_list_passes_everything(self) -> None:
        self.assertEqual(
            canonicalise_ner_name("ISO", canonical_names=None),
            "ISO",
        )

    def test_canonical_multiword_overlap(self) -> None:
        # "Auth Service Team" shares "Auth" and "Service" with
        # canonical "Auth Service" — pass, cleaned.
        self.assertEqual(
            canonicalise_ner_name(
                "the Auth Service Team", canonical_names=self.CANONICAL,
            ),
            "Auth Service Team",
        )


if __name__ == "__main__":
    unittest.main()
