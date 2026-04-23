"""Generate synthetic procedure documents exercising actor-ID failure modes.

FIELD_NOTES §4. The real procedure documents the tool is run against
are controlled and can't be committed. These hand-authored synthetic
analogues reproduce the *structural* patterns that drive actor-ID
errors without containing any controlled content — industry-generic
shapes only.

Five documents, each targeting a specific failure mode:

  simple_two_actors.docx       — baseline: 2 named actors, clean prose.
                                 Pins the "it still works on easy mode"
                                 regression.
  ambiguous_roles.docx         — nested procedure where the same actor
                                 appears under several spellings
                                 ("Ops Engineer", "Operations Engineer",
                                 "the engineer") and multiple roles blur
                                 into one step.
  implicit_system_actor.docx   — every step attributed to "the system"
                                 or omitted entirely. Primary-column is
                                 empty or generic. Tests whether the
                                 resolver surfaces a reasonable actor
                                 when none is named.
  passive_voice.docx           — heavy passive-voice prose ("shall be
                                 performed by") that hides the agent
                                 inside a by-phrase. NLP should still
                                 catch most; regex/heuristic will miss.
  parallel_flows.docx          — multi-step parallel flows where two
                                 actors progress independently in
                                 interleaved steps. Tests row-ordering
                                 and actor continuity.

Run from the project root:
    python samples/procedures/generate.py

Output .docx files are written next to this script so the generator
and its artefacts live together — same pattern as samples/edge_cases/.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.table import _Cell


HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Small helpers — mirror samples/edge_cases/generate.py's conventions so
# anyone who's read one generator can read the other.
# ---------------------------------------------------------------------------


def _write_cell(cell: _Cell, *paragraphs) -> None:
    """Replace a cell's content with one or more paragraphs of plain text."""
    first = cell.paragraphs[0]
    first.text = ""
    if not paragraphs:
        return
    for i, text in enumerate(paragraphs):
        target = first if i == 0 else cell.add_paragraph()
        target.text = text


def _add_heading(doc: Document, text: str, level: int) -> None:
    doc.add_heading(text, level=level)


# ---------------------------------------------------------------------------
# Sample 1 — Simple two-actor procedure (baseline)
# ---------------------------------------------------------------------------


def build_simple_two_actors() -> None:
    """Two actors, clean prose, one requirement per row.

    The regression test: if this one stops working cleanly, something
    fundamental regressed. Expect 4 requirements (2 per actor), all
    Hard (shall / must).
    """
    doc = Document()
    doc.add_heading("Procedure \u2014 Daily System Check", level=0)
    doc.add_paragraph("Document ID: PROC-BASE-001")
    doc.add_paragraph(
        "Describes the shift-handover checks performed jointly by the "
        "Operator and the Supervisor."
    )

    _add_heading(doc, "1. Shift Start", level=1)
    t = doc.add_table(rows=4, cols=2)
    t.style = "Table Grid"

    _write_cell(t.rows[0].cells[0], "Operator")
    _write_cell(
        t.rows[0].cells[1],
        "The Operator shall log in to the control console and confirm "
        "the previous shift's handover notes.",
    )

    _write_cell(t.rows[1].cells[0], "Supervisor")
    _write_cell(
        t.rows[1].cells[1],
        "The Supervisor must review the overnight alarm log before "
        "releasing the Operator to normal duties.",
    )

    _write_cell(t.rows[2].cells[0], "Operator")
    _write_cell(
        t.rows[2].cells[1],
        "The Operator shall verify that all subsystem status indicators "
        "read nominal.",
    )

    _write_cell(t.rows[3].cells[0], "Supervisor")
    _write_cell(
        t.rows[3].cells[1],
        "The Supervisor must countersign the handover log once the "
        "checks are complete.",
    )

    doc.save(HERE / "simple_two_actors.docx")


# ---------------------------------------------------------------------------
# Sample 2 — Ambiguous actor spellings
# ---------------------------------------------------------------------------


def build_ambiguous_roles() -> None:
    """Same actor appears under several spellings; nested procedure.

    Exercises the resolver's normalisation + grouping rules. The
    aliasing is deliberately messy so the test can pin down which
    normalisations are working and which aren't.
    """
    doc = Document()
    doc.add_heading("Procedure \u2014 Incident Escalation", level=0)
    doc.add_paragraph("Document ID: PROC-AMBIG-002")
    doc.add_paragraph(
        "Escalation path for production incidents. The same roles are "
        "referenced under multiple spellings across the tables."
    )

    _add_heading(doc, "2. Triage", level=1)

    outer = doc.add_table(rows=2, cols=2)
    outer.style = "Table Grid"

    _write_cell(outer.rows[0].cells[0], "Ops Engineer")
    r0c1 = outer.rows[0].cells[1]
    _write_cell(
        r0c1,
        "The Ops Engineer shall open a triage channel within 5 minutes "
        "of page acknowledgement.",
    )
    nested = r0c1.add_table(rows=3, cols=2)
    nested.style = "Table Grid"

    _write_cell(nested.rows[0].cells[0], "Operations Engineer")
    _write_cell(
        nested.rows[0].cells[1],
        "The Operations Engineer must capture the initial alert payload "
        "and paste it into the channel.",
    )
    _write_cell(nested.rows[1].cells[0], "the engineer")
    _write_cell(
        nested.rows[1].cells[1],
        "The engineer shall page the on-call Platform Lead if the "
        "incident is not acknowledged within 10 minutes.",
    )
    _write_cell(nested.rows[2].cells[0], "Platform Lead")
    _write_cell(
        nested.rows[2].cells[1],
        "The Platform Lead must join the triage channel and assume "
        "incident command.",
    )

    _write_cell(outer.rows[1].cells[0], "Platform-Lead")
    _write_cell(
        outer.rows[1].cells[1],
        "The Platform-Lead shall designate a scribe and a communicator "
        "within the first 15 minutes of the incident.",
    )

    doc.save(HERE / "ambiguous_roles.docx")


# ---------------------------------------------------------------------------
# Sample 3 — Implicit / unnamed actor ("the system")
# ---------------------------------------------------------------------------


def build_implicit_system_actor() -> None:
    """Steps attributed to 'the system' or left unattributed.

    Primary-column cells are either generic ("System") or blank, which
    is the documentary reality for auto-generated or loosely-authored
    procedures. Tests whether the resolver returns anything sensible.
    """
    doc = Document()
    doc.add_heading("Procedure \u2014 Automated Backup Run", level=0)
    doc.add_paragraph("Document ID: PROC-IMPLICIT-003")
    doc.add_paragraph(
        "Describes the nightly backup sequence. Steps are largely "
        "automated; explicit actor naming is minimal."
    )

    _add_heading(doc, "3. Sequence", level=1)
    t = doc.add_table(rows=5, cols=2)
    t.style = "Table Grid"

    _write_cell(t.rows[0].cells[0], "System")
    _write_cell(
        t.rows[0].cells[1],
        "At 02:00 local, the system shall begin a full snapshot of the "
        "primary data volume.",
    )

    _write_cell(t.rows[1].cells[0], "System")
    _write_cell(
        t.rows[1].cells[1],
        "The system must verify snapshot integrity before promoting "
        "the image to the off-site store.",
    )

    # Unattributed row — first cell blank.
    _write_cell(t.rows[2].cells[0], "")
    _write_cell(
        t.rows[2].cells[1],
        "A summary report shall be emailed to the on-call distribution "
        "list once the run completes.",
    )

    _write_cell(t.rows[3].cells[0], "System")
    _write_cell(
        t.rows[3].cells[1],
        "If verification fails, the system must retain the primary "
        "volume in read-write mode and page the on-call engineer.",
    )

    # Another unattributed row, this time with generic content.
    _write_cell(t.rows[4].cells[0], "")
    _write_cell(
        t.rows[4].cells[1],
        "Retention policy shall prune snapshots older than 30 days.",
    )

    doc.save(HERE / "implicit_system_actor.docx")


# ---------------------------------------------------------------------------
# Sample 4 — Heavy passive voice
# ---------------------------------------------------------------------------


def build_passive_voice() -> None:
    """Passive-voice prose: 'shall be performed by X'.

    Primary-column is present but the semantic actor is buried in a
    trailing by-phrase. Regex / heuristic paths should miss the
    by-phrase agent; NLP (dependency parse / NER) should catch most.
    """
    doc = Document()
    doc.add_heading("Procedure \u2014 Change-Management Review", level=0)
    doc.add_paragraph("Document ID: PROC-PASSIVE-004")
    doc.add_paragraph(
        "Review steps for a production change request. Language is "
        "deliberately passive throughout."
    )

    _add_heading(doc, "4. Review Steps", level=1)
    t = doc.add_table(rows=4, cols=2)
    t.style = "Table Grid"

    _write_cell(t.rows[0].cells[0], "Change Board")
    _write_cell(
        t.rows[0].cells[1],
        "Each change request shall be reviewed by the Change Board "
        "before any production deployment.",
    )

    _write_cell(t.rows[1].cells[0], "Change Board")
    _write_cell(
        t.rows[1].cells[1],
        "Approval must be granted by the Security Officer when the "
        "change touches authentication flows.",
    )

    _write_cell(t.rows[2].cells[0], "Change Board")
    _write_cell(
        t.rows[2].cells[1],
        "A rollback plan shall be signed off by the Release Manager "
        "prior to the change window.",
    )

    _write_cell(t.rows[3].cells[0], "Change Board")
    _write_cell(
        t.rows[3].cells[1],
        "Post-change validation must be completed by the Duty "
        "Engineer within 30 minutes of deployment.",
    )

    doc.save(HERE / "passive_voice.docx")


# ---------------------------------------------------------------------------
# Sample 5 — Parallel / interleaved flows
# ---------------------------------------------------------------------------


def build_parallel_flows() -> None:
    """Two actors progress in parallel; their steps interleave.

    Tests row-ordering and actor continuity across a longer table.
    No nesting; the complexity is in the interleaving and the fact
    that each actor's narrative has to be reconstructed from non-
    contiguous rows.
    """
    doc = Document()
    doc.add_heading("Procedure \u2014 Dual-Approver Release", level=0)
    doc.add_paragraph("Document ID: PROC-PARALLEL-005")
    doc.add_paragraph(
        "Two approvers work in parallel during a release window. The "
        "QA Lead exercises the release candidate while the Release "
        "Manager coordinates the deployment pipeline."
    )

    _add_heading(doc, "5. Release Window", level=1)
    t = doc.add_table(rows=8, cols=2)
    t.style = "Table Grid"

    _write_cell(t.rows[0].cells[0], "QA Lead")
    _write_cell(
        t.rows[0].cells[1],
        "The QA Lead shall begin the smoke-test suite against the "
        "release candidate build.",
    )

    _write_cell(t.rows[1].cells[0], "Release Manager")
    _write_cell(
        t.rows[1].cells[1],
        "The Release Manager must stage the deployment package in the "
        "canary environment.",
    )

    _write_cell(t.rows[2].cells[0], "QA Lead")
    _write_cell(
        t.rows[2].cells[1],
        "The QA Lead shall record smoke-test results in the release "
        "tracker within 30 minutes.",
    )

    _write_cell(t.rows[3].cells[0], "Release Manager")
    _write_cell(
        t.rows[3].cells[1],
        "The Release Manager must confirm canary health telemetry for "
        "at least 10 minutes before promotion.",
    )

    _write_cell(t.rows[4].cells[0], "QA Lead")
    _write_cell(
        t.rows[4].cells[1],
        "The QA Lead shall sign off on the release once all smoke "
        "tests pass.",
    )

    _write_cell(t.rows[5].cells[0], "Release Manager")
    _write_cell(
        t.rows[5].cells[1],
        "The Release Manager must promote the canary to production "
        "only after QA sign-off.",
    )

    _write_cell(t.rows[6].cells[0], "QA Lead")
    _write_cell(
        t.rows[6].cells[1],
        "If any smoke test fails, the QA Lead shall halt the release "
        "and notify the Release Manager.",
    )

    _write_cell(t.rows[7].cells[0], "Release Manager")
    _write_cell(
        t.rows[7].cells[1],
        "On halt, the Release Manager must roll back the canary and "
        "capture diagnostic logs for the post-mortem.",
    )

    doc.save(HERE / "parallel_flows.docx")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> None:
    build_simple_two_actors()
    build_ambiguous_roles()
    build_implicit_system_actor()
    build_passive_voice()
    build_parallel_flows()
    print(f"Generated 5 procedure fixtures in {HERE}:")
    for p in sorted(HERE.glob("*.docx")):
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
