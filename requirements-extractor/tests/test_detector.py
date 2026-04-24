"""Unit tests for requirements_extractor.detector.

These use the standard-library ``unittest`` module so they run without any
extra install.  Pytest (if installed) auto-discovers them too.

Run:  python -m unittest tests.test_detector
"""

from __future__ import annotations

import unittest

from requirements_extractor.config import KeywordsConfig
from requirements_extractor.detector import (
    HARD_KEYWORDS,
    SOFT_KEYWORDS,
    KeywordMatcher,
    classify,
    compute_confidence,
    split_sentences,
)


class TestClassifyDefaults(unittest.TestCase):
    """Exercise the module-level ``classify`` helper (built-in defaults)."""

    def test_hard_shall(self) -> None:
        req, kws, conf = classify("The system shall reboot in 5 seconds.")
        self.assertEqual(req, "Hard")
        self.assertIn("shall", kws)
        self.assertEqual(conf, "High")

    def test_hard_must(self) -> None:
        req, kws, _ = classify("Passwords must be hashed with bcrypt.")
        self.assertEqual(req, "Hard")
        self.assertIn("must", kws)

    def test_soft_should(self) -> None:
        req, kws, conf = classify("Users should log out when finished.")
        self.assertEqual(req, "Soft")
        self.assertIn("should", kws)
        self.assertEqual(conf, "Medium")

    def test_soft_may(self) -> None:
        req, kws, _ = classify("Operators may override a lockout during emergencies.")
        self.assertEqual(req, "Soft")
        self.assertIn("may", kws)

    def test_not_a_requirement(self) -> None:
        req, kws, conf = classify("This is a plain descriptive statement.")
        self.assertEqual(req, "")
        self.assertEqual(kws, [])
        self.assertEqual(conf, "")

    def test_hard_beats_soft(self) -> None:
        """Text with both hard and soft keywords should classify as Hard."""
        req, kws, _ = classify("The system shall reboot and may emit a warning.")
        self.assertEqual(req, "Hard")
        self.assertIn("shall", kws)

    def test_case_insensitive(self) -> None:
        req, _, _ = classify("The system SHALL reboot.")
        self.assertEqual(req, "Hard")

    def test_word_boundary(self) -> None:
        """Embedded substrings don't trigger — 'recanted' is not 'can'."""
        req, _, _ = classify("The witness recanted their statement.")
        self.assertEqual(req, "")

    def test_multi_word_phrase(self) -> None:
        """Multi-word hard keyword: 'is to'."""
        req, kws, _ = classify("The payload is to be delivered within 24 hours.")
        self.assertEqual(req, "Hard")
        self.assertIn("is to", kws)

    def test_multi_word_ought_to(self) -> None:
        """'ought to' (soft) should win over 'ought' (not in the list)."""
        req, kws, _ = classify("The team ought to review this before shipping.")
        self.assertEqual(req, "Soft")
        self.assertIn("ought to", kws)


class TestConfidence(unittest.TestCase):
    def test_short_sentence_is_low(self) -> None:
        req, _, conf = classify("Shall do.")
        self.assertEqual(req, "Hard")
        self.assertEqual(conf, "Low")

    def test_medium_sentence_is_high(self) -> None:
        text = "The system shall authenticate every user before granting access to resources."
        _, _, conf = classify(text)
        self.assertEqual(conf, "High")

    def test_long_sentence_drops_to_medium(self) -> None:
        # 70+ words
        text = "The system " + "shall " + ("foo " * 70) + "end."
        _, _, conf = classify(text)
        self.assertEqual(conf, "Medium")


class TestKeywordMatcherConfig(unittest.TestCase):
    """Config-driven add/remove tuning."""

    def test_will_is_soft_by_default(self) -> None:
        """Under current defaults 'will' is SOFT (future-tense prose).

        Kept as a regression guard: if someone moves ``will`` back into
        HARD, all the drift-flagging goes away and this test fails loudly.
        """
        m = KeywordMatcher.default()
        req, kws, _ = m.classify("Sessions will expire after 30 minutes.")
        self.assertEqual(req, "Soft")
        self.assertIn("will", kws)

    def test_soft_remove_will(self) -> None:
        """Dropping 'will' entirely (soft_remove) makes the sentence vanish."""
        cfg = KeywordsConfig(soft_remove=["will"])
        m = KeywordMatcher.from_config(cfg)
        req, _, _ = m.classify("Sessions will expire after 30 minutes.")
        self.assertEqual(req, "")

    def test_hard_add_custom_phrase(self) -> None:
        cfg = KeywordsConfig(hard_add=["is responsible for"])
        m = KeywordMatcher.from_config(cfg)
        req, kws, _ = m.classify("The operator is responsible for the lockout.")
        self.assertEqual(req, "Hard")
        self.assertIn("is responsible for", kws)

    def test_soft_remove(self) -> None:
        cfg = KeywordsConfig(soft_remove=["can"])
        m = KeywordMatcher.from_config(cfg)
        req, _, _ = m.classify("Users can upload images.")
        self.assertEqual(req, "")

    def test_remove_is_case_insensitive(self) -> None:
        cfg = KeywordsConfig(soft_remove=["WILL"])
        m = KeywordMatcher.from_config(cfg)
        req, _, _ = m.classify("Sessions will expire.")
        self.assertEqual(req, "")

    def test_hard_wins_when_same_word_in_both_lists(self) -> None:
        # Should-never-happen, but belts-and-braces.
        cfg = KeywordsConfig(hard_add=["should"])
        m = KeywordMatcher.from_config(cfg)
        req, _, _ = m.classify("Users should log out.")
        self.assertEqual(req, "Hard")

    def test_none_config_is_defaults(self) -> None:
        m = KeywordMatcher.from_config(None)
        req, _, _ = m.classify("The system shall reboot.")
        self.assertEqual(req, "Hard")


class TestSplitSentences(unittest.TestCase):
    def test_simple_split(self) -> None:
        out = split_sentences("First sentence. Second sentence.")
        self.assertEqual(out, ["First sentence.", "Second sentence."])

    def test_short_bullet_fragment_kept_whole(self) -> None:
        """A short bullet without terminal punctuation stays as one item."""
        out = split_sentences("Ground Control overrides a lockout")
        self.assertEqual(out, ["Ground Control overrides a lockout"])

    def test_blank_returns_empty(self) -> None:
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])

    def test_whitespace_normalisation(self) -> None:
        out = split_sentences("A.  \n  B.")
        self.assertEqual(out, ["A.", "B."])

    # --- Abbreviation handling (§1.3) ---------------------------------- #

    def test_title_abbreviation_not_split(self) -> None:
        out = split_sentences("Dr. Smith shall approve the design.")
        self.assertEqual(out, ["Dr. Smith shall approve the design."])

    def test_multiple_title_abbreviations_not_split(self) -> None:
        out = split_sentences(
            "See Dr. Jones, Mr. Brown, and Ms. Lee. They reviewed it."
        )
        self.assertEqual(out, [
            "See Dr. Jones, Mr. Brown, and Ms. Lee.",
            "They reviewed it.",
        ])

    def test_latin_abbreviation_not_split(self) -> None:
        # "i.e." followed by a lowercase letter never split in the first
        # place (the lookahead requires capital/digit).  The harder case
        # is "e.g." followed by a capital — check both forms.
        out = split_sentences(
            "The system shall provide i.e. authentication, authorization."
        )
        self.assertEqual(
            out,
            ["The system shall provide i.e. authentication, authorization."],
        )
        out2 = split_sentences("See e.g. Alpha. It matters.")
        self.assertEqual(out2, ["See e.g. Alpha.", "It matters."])

    def test_reference_abbreviation_not_split(self) -> None:
        out = split_sentences("See Fig. 3 for details. The operator may retry.")
        self.assertEqual(out, [
            "See Fig. 3 for details.",
            "The operator may retry.",
        ])

    def test_enumeration_step_not_split(self) -> None:
        out = split_sentences("Step 1. The user shall log in.")
        self.assertEqual(out, ["Step 1. The user shall log in."])

    def test_enumeration_item_not_split(self) -> None:
        out = split_sentences("Item 42. The system shall respond.")
        self.assertEqual(out, ["Item 42. The system shall respond."])

    def test_parenthetical_abbreviation_not_split(self) -> None:
        # "(e.g." has leading punctuation on the token — still recognised.
        out = split_sentences(
            "The design (e.g. Fig. 3) shows foo. The operator may retry."
        )
        self.assertEqual(out, [
            "The design (e.g. Fig. 3) shows foo.",
            "The operator may retry.",
        ])

    def test_real_sentence_still_splits_after_abbreviation(self) -> None:
        """After merging Dr. with the following fragment, the NEXT real
        sentence boundary must still be respected."""
        out = split_sentences(
            "Dr. Smith shall approve the design. Operators must comply."
        )
        self.assertEqual(out, [
            "Dr. Smith shall approve the design.",
            "Operators must comply.",
        ])

    def test_case_insensitive_abbreviation(self) -> None:
        # Mixed casing of the abbreviation token.
        out = split_sentences("See FIG. 5. The diagram is canonical.")
        self.assertEqual(out, [
            "See FIG. 5.",
            "The diagram is canonical.",
        ])


class TestBuiltInKeywordSets(unittest.TestCase):
    """Guardrails on the curated keyword lists — catches accidental drift."""

    def test_disjoint(self) -> None:
        self.assertFalse(HARD_KEYWORDS & SOFT_KEYWORDS)

    def test_contains_canonical(self) -> None:
        for w in ("shall", "must", "required"):
            self.assertIn(w, HARD_KEYWORDS)
        for w in ("should", "may"):
            self.assertIn(w, SOFT_KEYWORDS)

    def test_nouns_not_in_hard(self) -> None:
        """Bare nouns 'requirement'/'requirements' must NOT classify."""
        self.assertNotIn("requirement", HARD_KEYWORDS)
        self.assertNotIn("requirements", HARD_KEYWORDS)
        self.assertNotIn("requirement", SOFT_KEYWORDS)
        self.assertNotIn("requirements", SOFT_KEYWORDS)

    def test_will_is_soft_not_hard(self) -> None:
        """'will' is SOFT so future-tense prose gets yellow-flagged for review."""
        self.assertIn("will", SOFT_KEYWORDS)
        self.assertNotIn("will", HARD_KEYWORDS)


class TestNegationDetection(unittest.TestCase):
    """Polarity: KeywordMatcher.is_negative() flags modal+negation pairs."""

    def setUp(self) -> None:
        self.m = KeywordMatcher.default()

    def test_shall_not(self) -> None:
        self.assertTrue(self.m.is_negative("The system shall not reboot."))

    def test_must_not(self) -> None:
        self.assertTrue(self.m.is_negative("Users must not log in without MFA."))

    def test_may_not(self) -> None:
        self.assertTrue(
            self.m.is_negative("Operators may not override a lockout.")
        )

    def test_should_never(self) -> None:
        self.assertTrue(
            self.m.is_negative("Passwords should never be logged.")
        )

    def test_cannot_contraction(self) -> None:
        """'can't' (ASCII apostrophe) should be detected."""
        self.assertTrue(self.m.is_negative("The service can't accept blanks."))

    def test_will_not_also_flags(self) -> None:
        """Even SOFT modals get polarity tracking."""
        self.assertTrue(self.m.is_negative("The system will not retry."))

    def test_short_intervening_word_ok(self) -> None:
        """At most one filler word between modal and negation."""
        self.assertTrue(
            self.m.is_negative("Operators may sometimes never bypass the check.")
        )

    def test_too_far_apart_does_not_match(self) -> None:
        """Negation several words after the modal is not a contraction pair."""
        self.assertFalse(
            self.m.is_negative(
                "The system shall reboot but the log must persist and never be cleared."
            )
        )

    def test_positive_modal_not_negated(self) -> None:
        self.assertFalse(self.m.is_negative("The system shall reboot in 5 seconds."))

    def test_bare_not_without_modal(self) -> None:
        """'not' alone — with no modal nearby — is not a requirement negation."""
        self.assertFalse(self.m.is_negative("This is not tracked in JIRA."))



# ---------------------------------------------------------------------------
# compute_confidence (REVIEW §1.9) — length baseline with
# vague-qualifier and measurable-clause adjustments.
# ---------------------------------------------------------------------------


class TestComputeConfidenceBaseline(unittest.TestCase):
    """Length-only baseline: 5-60 words High, <5 Low, >60 Medium."""

    def test_medium_length_is_high(self) -> None:
        # 10 words, no vague qualifiers, no measurable clause.
        text = "The system shall validate the token before granting any access."
        self.assertEqual(compute_confidence(text), "High")

    def test_very_short_is_low(self) -> None:
        # <5 words — too short to be useful on its own.
        self.assertEqual(compute_confidence("Shall run."), "Low")

    def test_very_long_is_medium(self) -> None:
        # >60 words — usually over-specified, downgrade to Medium.
        text = " ".join(["word"] * 80)
        self.assertEqual(compute_confidence(text), "Medium")


class TestConfidenceVagueDowngrade(unittest.TestCase):
    """Vague qualifiers shift confidence one step down from the
    length-based baseline."""

    def test_reasonable_downgrades(self) -> None:
        text = "The system shall respond in a reasonable amount of time to queries."
        # Baseline would be High; vague 'reasonable' drops to Medium.
        self.assertEqual(compute_confidence(text), "Medium")

    def test_appropriate_downgrades(self) -> None:
        text = "The system shall produce an appropriate response to all inputs."
        self.assertEqual(compute_confidence(text), "Medium")

    def test_where_practical_downgrades(self) -> None:
        text = "The system shall log every request where practical to do so."
        self.assertEqual(compute_confidence(text), "Medium")

    def test_short_vague_goes_to_low(self) -> None:
        # Baseline Low + downgrade = still Low (clamped).
        self.assertEqual(compute_confidence("Shall be appropriate."), "Low")


class TestConfidenceMeasurableUpgrade(unittest.TestCase):
    """A measurable clause shifts confidence one step up."""

    def test_short_measurable_goes_to_medium(self) -> None:
        # Baseline Low (<5 words); measurable clause lifts to Medium.
        text = "Response below 200 ms."
        self.assertEqual(compute_confidence(text), "Medium")

    def test_time_unit_upgrade_from_medium_baseline(self) -> None:
        # 70-word sentence (Medium baseline) with a time threshold →
        # measurable clause shifts to High.
        long_pad = " ".join(["word"] * 65)
        text = f"The system shall respond within 250 ms. {long_pad}"
        # Baseline Medium (length > 60) + measurable = High.
        self.assertEqual(compute_confidence(text), "High")

    def test_tolerance_counts_as_measurable(self) -> None:
        text = "Temperature shall stay within ± 5 C of nominal."
        # Baseline Low (6 words roughly), + measurable → Medium.
        self.assertEqual(compute_confidence(text), "High")

    def test_at_most_counts(self) -> None:
        text = "The system shall reboot at most 3 times per day on any node."
        # Baseline High (13 words); +measurable stays High (clamped).
        self.assertEqual(compute_confidence(text), "High")


class TestConfidenceSignalsCancel(unittest.TestCase):
    """A sentence with both vague and measurable signals lands back at
    the length-based baseline (the two offsets cancel)."""

    def test_both_signals_cancel(self) -> None:
        # Baseline High + -1 (vague) + 1 (measurable) = baseline.
        text = "Response within 500 ms where practical on the target network."
        self.assertEqual(compute_confidence(text), "High")


class TestClassifyRoutesThroughNewConfidence(unittest.TestCase):
    """The existing Hard / Soft classification paths should now use
    the upgraded confidence helper without changing their classification."""

    def test_hard_with_measurable_is_high(self) -> None:
        m = KeywordMatcher.default()
        req_type, _, conf = m.classify(
            "The system shall respond within 200 ms to every valid request."
        )
        self.assertEqual(req_type, "Hard")
        self.assertEqual(conf, "High")

    def test_hard_with_vague_drops(self) -> None:
        m = KeywordMatcher.default()
        req_type, _, conf = m.classify(
            "The system shall produce appropriate output under normal conditions."
        )
        self.assertEqual(req_type, "Hard")
        # Baseline High → -1 → Medium.
        self.assertEqual(conf, "Medium")

    def test_soft_baseline_still_medium(self) -> None:
        m = KeywordMatcher.default()
        req_type, _, conf = m.classify(
            "The system should attempt to keep connections alive."
        )
        self.assertEqual(req_type, "Soft")
        self.assertEqual(conf, "Medium")

    def test_soft_with_measurable_goes_high(self) -> None:
        m = KeywordMatcher.default()
        req_type, _, conf = m.classify(
            "The system should respond within 100 ms to pings."
        )
        self.assertEqual(req_type, "Soft")
        self.assertEqual(conf, "High")


if __name__ == "__main__":
    unittest.main()
