"""Tests for the 0.6.2 multi-action detection + decomposition.

Three layers of coverage:

1. **Pure-helper tests** - exercise
   :mod:`requirements_extractor.multi_action` directly with hand-rolled
   sentences.  No docx involved.  Pins detection rules, phrase
   splitting, shared-verb disambiguation, and the modal/connector
   gates.

2. **End-to-end fixture tests** - parse each of the five multi-action
   fixtures under ``samples/procedures/multi_action/`` in each of the
   three modes (single / flag / split) and assert the row-level
   extraction matches the documented expectation.

3. **Config wiring + defensive disable** - default mode, namespace
   resolution, mode validation, force_requirement gate.

Together this gives 30+ independent assertions over the 0.6.2 patch
surface.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from requirements_extractor.actors import ActorResolver
from requirements_extractor.config import (
    Config,
    MultiActionConfig,
    build_config,
    load_config_raw,
    merge_raw,
    resolve_config,
)
from requirements_extractor.multi_action import (
    MultiActionDetection,
    detect,
    render_flag_note,
    render_sub_requirement,
    _is_shared_verb,
    _phrase_head_verb,
    _regex_phrases,
)
from requirements_extractor.parser import parse_docx


# ---------------------------------------------------------------------------
# Layer 1: pure-helper tests.
# ---------------------------------------------------------------------------


class TestPhraseHeadVerb(unittest.TestCase):

    def test_recognises_action_verb(self) -> None:
        self.assertTrue(bool(_phrase_head_verb("create unit tests")))
        self.assertTrue(bool(_phrase_head_verb("implement CICD Pipelines")))
        self.assertTrue(bool(_phrase_head_verb("integrate quality systems")))

    def test_rejects_noun_with_tion_suffix(self) -> None:
        # "validation" is a derived noun, not a verb.
        self.assertEqual(_phrase_head_verb("validation"), "")

    def test_rejects_common_spec_nouns(self) -> None:
        # "policy" is in the explicit stoplist.
        self.assertEqual(_phrase_head_verb("policy B"), "")
        self.assertEqual(_phrase_head_verb("system status"), "")

    def test_rejects_function_words(self) -> None:
        self.assertEqual(_phrase_head_verb("with great care"), "")
        self.assertEqual(_phrase_head_verb("if needed"), "")

    def test_handles_leading_conjunction(self) -> None:
        # "and integrate ..." should still extract "integrate".
        self.assertTrue(bool(_phrase_head_verb("and integrate systems")))


class TestSharedVerbHeuristic(unittest.TestCase):

    def test_identical_heads_share(self) -> None:
        # "create" + "creates" both normalise to "creat".
        self.assertTrue(_is_shared_verb(["create A", "creates B"]))

    def test_different_heads_do_not_share(self) -> None:
        self.assertFalse(_is_shared_verb(["create A", "implement B"]))

    def test_empty_list_not_shared(self) -> None:
        self.assertFalse(_is_shared_verb([]))


class TestRegexPhrases(unittest.TestCase):

    def test_three_action_oxford(self) -> None:
        out = _regex_phrases(
            "create unit tests, implement CICD Pipelines, and integrate quality systems"
        )
        self.assertEqual(len(out), 3)
        self.assertIn("create", out[0])
        self.assertIn("implement", out[1])
        self.assertIn("integrate", out[2])

    def test_two_action_bare_or(self) -> None:
        out = _regex_phrases("log errors or alert operators")
        self.assertEqual(len(out), 2)

    def test_no_connector_returns_empty(self) -> None:
        self.assertEqual(_regex_phrases("complete the action"), [])

    def test_noun_list_not_split(self) -> None:
        # "policy A and policy B" - both halves head with a noun.
        self.assertEqual(_regex_phrases("comply with policy A and policy B"), [])


class TestDetect(unittest.TestCase):

    def test_eric_canonical_three_actions(self) -> None:
        d = detect(
            "Software engineers shall create unit tests, implement "
            "CICD Pipelines, and integrate software quality control "
            "systems."
        )
        self.assertTrue(d.is_multi_action)
        self.assertEqual(d.count, 3)
        self.assertEqual(d.modal.lower(), "shall")
        self.assertIn("Software engineers", d.actor_prefix)

    def test_two_action_or(self) -> None:
        d = detect("System shall log errors or alert operators.")
        self.assertTrue(d.is_multi_action)
        self.assertEqual(d.count, 2)

    def test_singular_with_continuation(self) -> None:
        # "with mean time" - second clause heads with "with" (function
        # word), so the regex fallback rejects.  Detection: not
        # multi-action.
        d = detect(
            "System shall be available 99.9% of the time, with mean "
            "time to recovery less than 1 hour."
        )
        self.assertFalse(d.is_multi_action)

    def test_two_modals_skipped(self) -> None:
        # Two ``shall`` tokens -> compound conditional, not
        # multi-action.  Detection: not multi-action.
        d = detect(
            "Engineers shall test the build, and Operators shall "
            "release it."
        )
        self.assertFalse(d.is_multi_action)

    def test_no_modal_skipped(self) -> None:
        d = detect("Engineers create unit tests and implement CICD.")
        self.assertFalse(d.is_multi_action)

    def test_min_actions_three_blocks_two_action(self) -> None:
        # min_actions=3 should reject a 2-action sentence.
        d = detect("System shall log errors or alert operators.", min_actions=3)
        self.assertFalse(d.is_multi_action)


class TestSubRequirementRendering(unittest.TestCase):

    def test_render_uses_actor_and_modal(self) -> None:
        d = MultiActionDetection(
            original_text="X",
            actions=["create unit tests"],
            modal="shall",
            actor_prefix="Software engineers ",
        )
        out = render_sub_requirement(d, "create unit tests")
        self.assertEqual(out, "Software engineers shall create unit tests.")

    def test_render_strips_leading_conjunction(self) -> None:
        d = MultiActionDetection(
            original_text="X", modal="shall", actor_prefix="Operator ",
        )
        out = render_sub_requirement(d, "and integrate systems")
        self.assertEqual(out, "Operator shall integrate systems.")

    def test_flag_note_mentions_count(self) -> None:
        d = MultiActionDetection(
            original_text="X",
            actions=["a", "b", "c"],
            modal="shall",
        )
        note = render_flag_note(d)
        self.assertIn("3 verb phrases", note)
        self.assertIn("consider splitting", note)


# ---------------------------------------------------------------------------
# Layer 2: end-to-end fixture tests.
# ---------------------------------------------------------------------------


MULTI_ACTION_DIR = (
    Path(__file__).resolve().parent.parent
    / "samples" / "procedures" / "multi_action"
)


def _parse_with_mode(name: str, mode: str):
    """Parse a fixture under a specific multi_action.mode override.

    Returns ONLY table rows (preamble paragraphs are filtered out so a
    fixture's introductory prose can include modals without polluting
    the row-count assertions).
    """
    docx = MULTI_ACTION_DIR / name
    base_raw = {}
    per_doc = MULTI_ACTION_DIR / f"{docx.stem}.reqx.yaml"
    if per_doc.exists():
        base_raw = load_config_raw(per_doc)
    raw = merge_raw(base_raw, {"multi_action": {"mode": mode}})
    cfg = build_config(raw, source=f"test:{mode}")
    resolver = ActorResolver()
    reqs = parse_docx(docx, resolver_fn=resolver.resolve, config=cfg)
    # Drop preamble rows so fixture intro prose doesn't affect counts.
    return [r for r in reqs if not r.row_ref.startswith("Preamble")]


class TestFixture1EricCanonical(unittest.TestCase):
    """Eric's canonical "create / implement / integrate" sentence."""

    def test_single_mode_emits_one_row(self) -> None:
        reqs = _parse_with_mode("fixture_1_eric_canonical.docx", "single")
        self.assertEqual(len(reqs), 1)
        self.assertIn("create unit tests", reqs[0].text)
        self.assertNotIn("Multi-action", reqs[0].notes)

    def test_flag_mode_emits_one_row_with_note(self) -> None:
        reqs = _parse_with_mode("fixture_1_eric_canonical.docx", "flag")
        self.assertEqual(len(reqs), 1)
        self.assertIn("Multi-action sentence: 3", reqs[0].notes)
        self.assertIn("consider splitting", reqs[0].notes)

    def test_split_mode_emits_parent_plus_three_subs(self) -> None:
        reqs = _parse_with_mode("fixture_1_eric_canonical.docx", "split")
        self.assertEqual(len(reqs), 4)
        parent = reqs[0]
        subs = reqs[1:]
        self.assertEqual(len(subs), 3)
        self.assertIn("Multi-action split", parent.notes)
        for i, sub in enumerate(subs, start=1):
            self.assertEqual(sub.parent_id, parent.stable_id)
            self.assertEqual(sub.stable_id, f"{parent.stable_id}.{i}")
            self.assertIn(f"sub {i}/3", sub.block_ref)

    def test_split_subs_carry_correct_text(self) -> None:
        reqs = _parse_with_mode("fixture_1_eric_canonical.docx", "split")
        subs = reqs[1:]
        sub_texts = " ".join(s.text for s in subs).lower()
        self.assertIn("create unit tests", sub_texts)
        self.assertIn("implement cicd pipelines", sub_texts)
        self.assertIn("integrate software quality control systems", sub_texts)


class TestFixture2TwoActionOr(unittest.TestCase):

    def test_single_mode(self) -> None:
        reqs = _parse_with_mode("fixture_2_two_action_or.docx", "single")
        self.assertEqual(len(reqs), 1)

    def test_flag_mode_marks_two_actions(self) -> None:
        reqs = _parse_with_mode("fixture_2_two_action_or.docx", "flag")
        self.assertEqual(len(reqs), 1)
        self.assertIn("2 verb phrases", reqs[0].notes)

    def test_split_mode_emits_parent_plus_two(self) -> None:
        reqs = _parse_with_mode("fixture_2_two_action_or.docx", "split")
        self.assertEqual(len(reqs), 3)
        self.assertEqual(reqs[1].parent_id, reqs[0].stable_id)
        self.assertEqual(reqs[2].parent_id, reqs[0].stable_id)


class TestFixture3SharedVerbCompound(unittest.TestCase):
    """Negative case: must NOT split."""

    def test_single_mode_one_row(self) -> None:
        reqs = _parse_with_mode("fixture_3_shared_verb_compound.docx", "single")
        self.assertEqual(len(reqs), 1)

    def test_flag_mode_one_row_no_multi_action_note(self) -> None:
        reqs = _parse_with_mode("fixture_3_shared_verb_compound.docx", "flag")
        self.assertEqual(len(reqs), 1)
        self.assertNotIn("Multi-action sentence", reqs[0].notes)

    def test_split_mode_does_not_split(self) -> None:
        reqs = _parse_with_mode("fixture_3_shared_verb_compound.docx", "split")
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].parent_id, "")


class TestFixture4AfterCompoundAggregation(unittest.TestCase):
    """0.6.1 aggregation runs first; 0.6.2 must not crash on result."""

    def test_single_mode_emits_compound_only(self) -> None:
        reqs = _parse_with_mode(
            "fixture_4_after_compound_aggregation.docx", "single"
        )
        # One compound row plus possibly one passing-through bullet row;
        # exact count is determined by 0.6.1 aggregation - we only
        # require that single mode does NOT produce sub-requirements.
        self.assertGreaterEqual(len(reqs), 1)
        for r in reqs:
            self.assertEqual(r.parent_id, "")

    def test_flag_or_split_modes_do_not_crash(self) -> None:
        # Pipeline ordering: 0.6.1 aggregation produces a row; 0.6.2
        # detection runs on it.  Whether the aggregated text is
        # detected as multi-action depends on the synthetic compound
        # rendering; this test just pins that NEITHER mode crashes.
        for mode in ("flag", "split"):
            reqs = _parse_with_mode(
                "fixture_4_after_compound_aggregation.docx", mode
            )
            self.assertGreaterEqual(len(reqs), 1)

    def test_split_mode_does_not_redecompose_compound_rows(self) -> None:
        # 0.6.2 guard: when 0.6.1 has already aggregated a modal lead-in
        # plus a bulleted list into one compound row, split mode must
        # NOT re-decompose that synthetic text into sub-requirements.
        # Pin: total row count under split == single, and no compound
        # row spawns a child (parent_id stays empty).
        single_reqs = _parse_with_mode(
            "fixture_4_after_compound_aggregation.docx", "single"
        )
        split_reqs = _parse_with_mode(
            "fixture_4_after_compound_aggregation.docx", "split"
        )
        self.assertEqual(len(split_reqs), len(single_reqs))
        compound_parents = {
            r.stable_id for r in split_reqs if "(compound)" in r.block_ref
        }
        # At least one compound row should exist in the fixture; if the
        # fixture changes, this guard is the canary.
        self.assertGreaterEqual(len(compound_parents), 1)
        for r in split_reqs:
            self.assertNotIn(
                r.parent_id,
                compound_parents,
                msg=(
                    "compound row %s was re-decomposed by split mode "
                    "(child stable_id=%s)" % (r.parent_id, r.stable_id)
                ),
            )


class TestFixture5InsideProceduralTable(unittest.TestCase):
    """Procedural required-action gate: split must be DISABLED."""

    def test_split_mode_does_not_fragment_table_rows(self) -> None:
        reqs = _parse_with_mode(
            "fixture_5_inside_procedural_table.docx", "split"
        )
        # Two body rows in the procedural table, both atomic.
        # Multi-action splitting must NOT add sub-rows even though the
        # second row's text contains 3 verb phrases.
        self.assertEqual(len(reqs), 2)
        for r in reqs:
            self.assertEqual(r.parent_id, "")
            self.assertNotIn("sub ", r.block_ref)

    def test_flag_mode_does_not_annotate_table_rows(self) -> None:
        reqs = _parse_with_mode(
            "fixture_5_inside_procedural_table.docx", "flag"
        )
        self.assertEqual(len(reqs), 2)
        for r in reqs:
            self.assertNotIn("Multi-action sentence", r.notes)


# ---------------------------------------------------------------------------
# Layer 3: config wiring + defensive.
# ---------------------------------------------------------------------------


class TestConfigWiring(unittest.TestCase):

    def test_default_mode_is_flag(self) -> None:
        self.assertEqual(Config.defaults().multi_action.mode, "flag")

    def test_default_enabled(self) -> None:
        self.assertTrue(Config.defaults().multi_action.enabled)

    def test_default_min_actions_two(self) -> None:
        self.assertEqual(Config.defaults().multi_action.min_actions, 2)

    def test_flat_form_accepted(self) -> None:
        cfg = build_config({"multi_action": {"mode": "split"}})
        self.assertEqual(cfg.multi_action.mode, "split")

    def test_extraction_namespace_form_accepted(self) -> None:
        cfg = build_config({"extraction": {"multi_action": {"mode": "split"}}})
        self.assertEqual(cfg.multi_action.mode, "split")

    def test_extraction_compound_and_multi_action_coexist(self) -> None:
        cfg = build_config({
            "extraction": {
                "compound": {"enabled": False},
                "multi_action": {"mode": "split"},
            }
        })
        self.assertFalse(cfg.compound.enabled)
        self.assertEqual(cfg.multi_action.mode, "split")

    def test_invalid_mode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_config({"multi_action": {"mode": "bogus"}})

    def test_invalid_min_actions_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_config({"multi_action": {"min_actions": 1}})

    def test_disabled_short_circuits(self) -> None:
        # When enabled=False, mode is ignored - even split mode emits
        # a single row.
        cfg = build_config({"multi_action": {"mode": "split", "enabled": False}})
        from requirements_extractor.parser import parse_docx
        resolver = ActorResolver()
        reqs = parse_docx(
            MULTI_ACTION_DIR / "fixture_1_eric_canonical.docx",
            resolver_fn=resolver.resolve,
            config=cfg,
        )
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].parent_id, "")


if __name__ == "__main__":
    unittest.main()
