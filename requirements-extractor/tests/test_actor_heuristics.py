"""Regression tests for rule-based actor-extraction heuristics.

Each test pins one heuristic to the example sentence it was tuned
against (see the inline ``# Example:`` comments in
``actor_heuristics.py``).  A test failure here means a rule-edit
caused a real regression on a case Eric has flagged as load-bearing
on his actual specs.

Tests are deliberately *paired*: positive (rule fires on the case it
claims to cover) + negative (rule does *not* fire on a near-miss
sentence that would be a false positive).  False positives are how
this module gets tuned out by users, so the negatives are the more
important half of the suite.
"""

from __future__ import annotations

import unittest

from requirements_extractor.actor_heuristics import (
    extract_actor_candidates,
    _h_by_agent,
    _h_send_to,
    _h_possessive,
    _h_compound_subject,
    _h_conditional_subject,
    _h_for_beneficiary,
    _h_implicit_passive,
    _h_hyphenated_role,
    _h_between,
    _h_appositive,
    _is_role_phrase,
    _clean,
)


class TestRoleShapeProbe(unittest.TestCase):
    def test_head_noun_triggers(self) -> None:
        self.assertTrue(_is_role_phrase("Auth Service"))
        self.assertTrue(_is_role_phrase("Notification Manager"))

    def test_role_suffix_triggers(self) -> None:
        self.assertTrue(_is_role_phrase("Reviewer"))
        self.assertTrue(_is_role_phrase("Auditor"))
        self.assertTrue(_is_role_phrase("Specialist"))

    def test_lowercase_fragment_does_not_trigger(self) -> None:
        self.assertFalse(_is_role_phrase("the value"))
        self.assertFalse(_is_role_phrase("login event"))

    def test_acronym_triggers(self) -> None:
        self.assertTrue(_is_role_phrase("API"))

    def test_stopword_drops(self) -> None:
        self.assertIsNone(_clean("If"))


class TestRule1ByAgent(unittest.TestCase):
    """Passive-voice 'by' agent."""

    def test_approved_by(self) -> None:
        # Example: "The report shall be approved by the Reviewer."
        out = _h_by_agent("The report shall be approved by the Reviewer.")
        self.assertIn("Reviewer", out)

    def test_recorded_by(self) -> None:
        # Example: "Logs are recorded by the Audit Service."
        out = _h_by_agent("Logs are recorded by the Audit Service.")
        self.assertIn("Audit Service", out)

    def test_not_by_lowercase(self) -> None:
        # "by the user" -- 'user' is in the role list, but not Title-cased
        # in this sentence, so won't be captured.
        out = _h_by_agent("The form shall be approved by the user.")
        self.assertEqual(out, [])


class TestRule2SendTo(unittest.TestCase):
    def test_forward_to(self) -> None:
        # Example: "The System shall forward the alert to the Notification Service."
        out = _h_send_to(
            "The System shall forward the alert to the Notification Service."
        )
        self.assertIn("Notification Service", out)

    def test_notify_actor(self) -> None:
        # Example: "The Operator shall notify the Supervisor."
        out = _h_send_to("The Operator shall notify the Supervisor.")
        self.assertIn("Supervisor", out)

    def test_no_recipient_role(self) -> None:
        # "send to the file" -- 'file' isn't role-shaped.
        out = _h_send_to("The System shall send the data to the file.")
        self.assertEqual(out, [])


class TestRule3Possessive(unittest.TestCase):
    def test_apostrophe_s(self) -> None:
        # Example: "The Operator's screen shall display the alert."
        out = _h_possessive("The Operator's screen shall display the alert.")
        self.assertIn("Operator", out)

    def test_curly_apostrophe(self) -> None:
        # Curly ’s should also fire.
        out = _h_possessive("The Operator’s screen shall display the alert.")
        self.assertIn("Operator", out)

    def test_multi_word(self) -> None:
        # Example: "The Auth Service's logger shall flush every minute."
        out = _h_possessive(
            "The Auth Service's logger shall flush every minute."
        )
        self.assertIn("Auth Service", out)


class TestRule4CompoundSubject(unittest.TestCase):
    def test_two_actors(self) -> None:
        # Example: "The Operator and the Supervisor shall co-sign the release."
        out = _h_compound_subject(
            "The Operator and the Supervisor shall co-sign the release."
        )
        self.assertIn("Operator", out)
        self.assertIn("Supervisor", out)

    def test_two_services(self) -> None:
        out = _h_compound_subject(
            "The Auth Service and the Audit Logger shall both record the event."
        )
        self.assertIn("Auth Service", out)
        self.assertIn("Audit Logger", out)

    def test_lowercase_subject_does_not_fire(self) -> None:
        # "the user and the operator" -- both lowercase head, not role-shaped.
        out = _h_compound_subject(
            "the user and the operator shall confirm."
        )
        # 'operator' lowercase isn't role-shaped per our rules.
        self.assertEqual(out, [])


class TestRule5ConditionalSubject(unittest.TestCase):
    def test_if_actor_verb(self) -> None:
        # Example: "If the Auditor approves the change, the System shall deploy."
        out = _h_conditional_subject(
            "If the Auditor approves the change, the System shall deploy."
        )
        self.assertIn("Auditor", out)

    def test_when_actor_verb(self) -> None:
        # Example: "When the Operator presses the kill switch, all motion stops."
        out = _h_conditional_subject(
            "When the Operator presses the kill switch, all motion stops."
        )
        self.assertIn("Operator", out)

    def test_no_named_actor(self) -> None:
        out = _h_conditional_subject(
            "If the value exceeds the threshold, the alarm shall trigger."
        )
        self.assertEqual(out, [])


class TestRule6ForBeneficiary(unittest.TestCase):
    def test_for_role(self) -> None:
        # Example: "The System shall generate a report for the Compliance Officer."
        out = _h_for_beneficiary(
            "The System shall generate a report for the Compliance Officer."
        )
        self.assertIn("Compliance Officer", out)

    def test_for_lowercase_user_drops(self) -> None:
        out = _h_for_beneficiary(
            "The System shall generate a report for the user to review."
        )
        self.assertEqual(out, [])


class TestRule7ImplicitPassive(unittest.TestCase):
    def test_shall_be_logged(self) -> None:
        out = _h_implicit_passive("Every login attempt shall be logged.")
        self.assertEqual(out, ["(implicit System)"])

    def test_with_explicit_agent_no_fire(self) -> None:
        # If there's a "by ACTOR" the passive isn't *implicit* -- skip.
        out = _h_implicit_passive(
            "Every login attempt shall be logged by the Audit Service."
        )
        self.assertEqual(out, [])


class TestRule8HyphenatedRole(unittest.TestCase):
    def test_actor_initiated(self) -> None:
        # Example: "An Operator-initiated abort shall halt the run."
        out = _h_hyphenated_role(
            "An Operator-initiated abort shall halt the run."
        )
        self.assertIn("Operator", out)

    def test_reviewer_driven(self) -> None:
        out = _h_hyphenated_role(
            "Reviewer-driven approvals are queued for batch processing."
        )
        self.assertIn("Reviewer", out)


class TestRule9Between(unittest.TestCase):
    def test_between_two_actors(self) -> None:
        # Example: "Communication between the Operator and the Auth Service
        #           shall be encrypted."
        out = _h_between(
            "Communication between the Operator and the Auth Service "
            "shall be encrypted."
        )
        self.assertIn("Operator", out)
        self.assertIn("Auth Service", out)


class TestRule10Appositive(unittest.TestCase):
    def test_role_appositive(self) -> None:
        # Example: "The QA Lead, the Reviewer, shall countersign the report."
        out = _h_appositive(
            "The QA Lead, the Reviewer, shall countersign the report."
        )
        # The Reviewer must come through (it's the role-marker that
        # validates the appositive).
        self.assertIn("Reviewer", out)


class TestExtractActorCandidatesIntegration(unittest.TestCase):
    """End-to-end: every heuristic plumbed through ``extract_actor_candidates``."""

    def test_dedupe_across_heuristics(self) -> None:
        # "by the Reviewer" + "the Reviewer's signature" -- two rules
        # both fire on Reviewer; the result should contain it once.
        out = extract_actor_candidates(
            "The report shall be approved by the Reviewer; "
            "the Reviewer's signature shall be retained."
        )
        self.assertEqual(out.count("Reviewer"), 1)

    def test_primary_excluded(self) -> None:
        # Operator is the primary; we shouldn't echo it back as a
        # secondary even when the rule would've matched it.
        out = extract_actor_candidates(
            "The Operator and the Supervisor shall co-sign the release.",
            primary="Operator",
        )
        self.assertNotIn("Operator", out)
        self.assertIn("Supervisor", out)

    def test_empty_sentence(self) -> None:
        self.assertEqual(extract_actor_candidates(""), [])

    def test_no_actor_sentence(self) -> None:
        # Pure data-statement -- should produce an empty (or near-empty)
        # list; we tolerate the implicit-passive rule firing here.
        out = extract_actor_candidates("The voltage shall be 5 volts.")
        # No real actor was named -- only acceptable hit is the
        # implicit-passive synthetic, but this sentence isn't even a
        # logging passive.
        for cand in out:
            self.assertTrue(cand.startswith("("))  # synthetic only

    def test_cleanup_strips_determiners(self) -> None:
        # If a rule captured "the Reviewer" verbatim, the cleanup pass
        # has already stripped "the ".
        out = extract_actor_candidates(
            "The report shall be approved by the Reviewer."
        )
        self.assertIn("Reviewer", out)
        self.assertNotIn("the Reviewer", out)


if __name__ == "__main__":
    unittest.main()


class TestActorResolverHeuristicsIntegration(unittest.TestCase):
    """Confirm ActorResolver.use_heuristics wires through correctly."""

    def test_off_by_default(self) -> None:
        from requirements_extractor.actors import ActorResolver
        r = ActorResolver()  # use_heuristics defaults False
        out = r.resolve(
            "The report shall be approved by the Reviewer.", primary="Operator"
        )
        # Without seed list and without heuristics, nothing.
        self.assertEqual(out, [])

    def test_opt_in_finds_role(self) -> None:
        from requirements_extractor.actors import ActorResolver
        r = ActorResolver(use_heuristics=True)
        matches = list(r.iter_matches(
            "The report shall be approved by the Reviewer.",
            primary="Operator",
        ))
        # Source must be 'rule' since no seed list / NLP.
        sources = {src for _, src in matches}
        names = [name for name, _ in matches]
        self.assertIn("Reviewer", names)
        self.assertEqual(sources, {"rule"})

    def test_seed_list_takes_priority_over_rule(self) -> None:
        from requirements_extractor.actors import ActorEntry, ActorResolver
        r = ActorResolver(
            actors=[ActorEntry(name="Reviewer", aliases=["the reviewer"])],
            use_heuristics=True,
        )
        matches = list(r.iter_matches(
            "The report shall be approved by the Reviewer.",
            primary="Operator",
        ))
        # Reviewer should appear once, attributed to the regex pass
        # (higher-confidence than the rule pass).
        names = [name for name, _ in matches]
        self.assertEqual(names.count("Reviewer"), 1)
        self.assertEqual(matches[0], ("Reviewer", "regex"))
