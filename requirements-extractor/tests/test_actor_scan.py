"""Tests for the actor-only extraction module.

These are all headless: the grouping and normalisation tests are pure
Python, and the end-to-end tests run against the bundled sample .docx.

Run:  python -m unittest tests.test_actor_scan
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from requirements_extractor.actor_scan import (
    ActorObservation,
    ActorScanCancelled,
    group_observations,
    normalise_actor_text,
    scan_actors_from_files,
)
from requirements_extractor.actors import ActorEntry, load_actors_from_xlsx


SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_spec.docx"


# ---------------------------------------------------------------------------
# normalise_actor_text
# ---------------------------------------------------------------------------


class TestNormaliseActorText(unittest.TestCase):
    def test_empty_returns_empty(self) -> None:
        self.assertEqual(normalise_actor_text(""), "")
        self.assertEqual(normalise_actor_text("   "), "")

    def test_basic_lowercasing(self) -> None:
        self.assertEqual(normalise_actor_text("Auth Service"), "auth service")

    def test_strips_leading_determiners(self) -> None:
        self.assertEqual(normalise_actor_text("The Auth Service"), "auth service")
        self.assertEqual(normalise_actor_text("the auth service"), "auth service")
        self.assertEqual(normalise_actor_text("A User"), "user")
        self.assertEqual(normalise_actor_text("an operator"), "operator")

    def test_strips_trailing_possessive(self) -> None:
        self.assertEqual(normalise_actor_text("Auth Service's"), "auth service")
        self.assertEqual(normalise_actor_text("Auth Service\u2019s"), "auth service")
        self.assertEqual(normalise_actor_text("Ops\u2019"), "ops")
        self.assertEqual(normalise_actor_text("Ops'"), "ops")

    def test_collapses_whitespace(self) -> None:
        self.assertEqual(
            normalise_actor_text("  Auth    Service  "), "auth service"
        )

    def test_combined_transforms(self) -> None:
        self.assertEqual(
            normalise_actor_text("  The  Auth Service\u2019s "), "auth service"
        )


# ---------------------------------------------------------------------------
# group_observations — unseeded
# ---------------------------------------------------------------------------


def _obs(raw: str, file: str = "a.docx", source: str = "primary", row: str = "Row 1") -> ActorObservation:
    return ActorObservation(
        raw=raw,
        normalised=normalise_actor_text(raw),
        source=source,
        file=file,
        row_ref=row,
        heading_trail="",
    )


class TestGroupObservationsUnseeded(unittest.TestCase):
    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(group_observations([]), [])

    def test_identical_raw_forms_merge(self) -> None:
        groups = group_observations([_obs("Auth Service"), _obs("Auth Service")])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].canonical, "Auth Service")
        self.assertEqual(groups[0].count, 2)
        self.assertEqual(groups[0].aliases, [])

    def test_case_and_determiner_variants_merge(self) -> None:
        groups = group_observations([
            _obs("Auth Service"),
            _obs("auth service"),
            _obs("The Auth Service"),
        ])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].canonical, "Auth Service")  # has upper → wins
        self.assertIn("auth service", [a.lower() for a in groups[0].aliases])
        self.assertEqual(groups[0].count, 3)

    def test_canonical_picks_most_frequent(self) -> None:
        groups = group_observations([
            _obs("Auth Service"),
            _obs("auth service"),
            _obs("auth service"),
            _obs("auth service"),
        ])
        # "auth service" (3) beats "Auth Service" (1) on frequency despite
        # the has-upper tiebreak.
        self.assertEqual(groups[0].canonical, "auth service")

    def test_sorted_by_count_desc(self) -> None:
        groups = group_observations([
            _obs("Rare Actor"),
            _obs("Common Actor"),
            _obs("Common Actor"),
            _obs("Common Actor"),
        ])
        self.assertEqual([g.canonical for g in groups], ["Common Actor", "Rare Actor"])

    def test_files_and_first_seen_captured(self) -> None:
        groups = group_observations([
            _obs("Auth", file="spec1.docx", row="Table 1, Row 2"),
            _obs("Auth", file="spec2.docx", row="Table 1, Row 4"),
        ])
        self.assertEqual(groups[0].files, ["spec1.docx", "spec2.docx"])
        self.assertEqual(groups[0].first_seen, "spec1.docx \u2014 Table 1, Row 2")

    def test_empty_normalised_observation_is_skipped(self) -> None:
        groups = group_observations([_obs(""), _obs("   ")])
        self.assertEqual(groups, [])


# ---------------------------------------------------------------------------
# group_observations — seeded
# ---------------------------------------------------------------------------


class TestGroupObservationsSeeded(unittest.TestCase):
    def test_seed_canonical_wins_over_observation_spellings(self) -> None:
        seeds = [ActorEntry(name="Auth Service", aliases=["Authenticator"])]
        groups = group_observations(
            [_obs("auth service"), _obs("Authenticator")],
            seed_entries=seeds,
        )
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g.canonical, "Auth Service")
        # The seed's curated alias is preserved; observed variants beyond
        # the canonical are added.
        self.assertIn("Authenticator", g.aliases)
        self.assertTrue(g.seeded)
        self.assertEqual(g.count, 2)

    def test_seed_without_observations_still_appears(self) -> None:
        seeds = [ActorEntry(name="Ghost Actor", aliases=[])]
        groups = group_observations([], seed_entries=seeds)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].canonical, "Ghost Actor")
        self.assertEqual(groups[0].count, 0)
        self.assertTrue(groups[0].seeded)

    def test_unseeded_observations_still_group_independently(self) -> None:
        seeds = [ActorEntry(name="Seeded One", aliases=[])]
        groups = group_observations(
            [_obs("Seeded One"), _obs("Brand New Actor")],
            seed_entries=seeds,
        )
        names = {g.canonical for g in groups}
        self.assertIn("Seeded One", names)
        self.assertIn("Brand New Actor", names)
        # The seeded group is flagged; the new one is not.
        for g in groups:
            if g.canonical == "Seeded One":
                self.assertTrue(g.seeded)
            else:
                self.assertFalse(g.seeded)

    def test_new_variant_becomes_alias_on_seeded_group(self) -> None:
        """A variant whose normalised form matches a seed alias (but not the
        canonical) should be recorded as an alias on the seeded group."""
        seeds = [ActorEntry(name="Auth Service", aliases=["Authentication Service"])]
        groups = group_observations(
            [_obs("authentication service")],  # matches the seed alias normalisation
            seed_entries=seeds,
        )
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g.canonical, "Auth Service")
        # The seed's curated alias survives, and the new lowercased spelling
        # is recorded too so the user can see how the doc actually writes it.
        self.assertIn("Authentication Service", g.aliases)
        self.assertIn("authentication service", g.aliases)

    def test_pure_case_variants_of_canonical_do_not_pollute_aliases(self) -> None:
        """Variants whose normalised form == normalise(canonical) are
        silently collapsed — they don't clutter the Actors sheet.  The raw
        sightings are still available on the Observations sheet."""
        seeds = [ActorEntry(name="Auth Service", aliases=[])]
        groups = group_observations(
            [_obs("auth service"), _obs("AUTH SERVICE")],
            seed_entries=seeds,
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].aliases, [])


# ---------------------------------------------------------------------------
# End-to-end — scan a real sample and re-parse the output.
# ---------------------------------------------------------------------------


class TestScanEndToEnd(unittest.TestCase):
    def test_scan_writes_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "actors.xlsx"
            result = scan_actors_from_files(
                input_paths=[SAMPLE],
                output_path=out,
            )
            self.assertTrue(out.exists())
            self.assertEqual(result.stats.files_processed, 1)
            self.assertGreater(result.stats.groups, 0)
            self.assertEqual(result.output_path, out)

    def test_output_is_readable_by_actor_loader(self) -> None:
        """The scan output must round-trip through load_actors_from_xlsx."""
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "actors.xlsx"
            scan_actors_from_files(input_paths=[SAMPLE], output_path=out)
            entries = load_actors_from_xlsx(out)
            self.assertGreater(len(entries), 0)
            # Every canonical should have a non-empty name.
            for e in entries:
                self.assertTrue(e.name)

    def test_seeded_scan_preserves_canonical(self) -> None:
        """If we seed a known canonical, the scan should preserve it verbatim."""
        with tempfile.TemporaryDirectory() as d:
            # Write a minimal seed file with a canonical whose alias matches
            # a real actor in the sample doc.
            from openpyxl import Workbook
            seed_path = Path(d) / "seed.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.append(["Actor", "Aliases"])
            ws.append(["Authentication Service", "Auth Service"])
            wb.save(str(seed_path))

            out = Path(d) / "actors.xlsx"
            result = scan_actors_from_files(
                input_paths=[SAMPLE],
                output_path=out,
                seed_actors_xlsx=seed_path,
            )
            canonicals = {g.canonical for g in result.groups}
            # The seed's canonical must win over the raw spelling in the doc.
            self.assertIn("Authentication Service", canonicals)
            self.assertNotIn("Auth Service", canonicals)


class TestScanCancellation(unittest.TestCase):
    def test_cancel_before_first_file_raises_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "actors.xlsx"
            with self.assertRaises(ActorScanCancelled):
                scan_actors_from_files(
                    input_paths=[SAMPLE],
                    output_path=out,
                    cancel_check=lambda: True,
                )
            self.assertFalse(out.exists())

    def test_file_progress_called_monotonically(self) -> None:
        calls: list[tuple[int, int, str]] = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "actors.xlsx"
            scan_actors_from_files(
                input_paths=[SAMPLE, SAMPLE, SAMPLE],
                output_path=out,
                file_progress=lambda i, n, name: calls.append((i, n, name)),
            )
        self.assertEqual([c[0] for c in calls], [1, 2, 3])
        self.assertTrue(all(c[1] == 3 for c in calls))


if __name__ == "__main__":
    unittest.main()
