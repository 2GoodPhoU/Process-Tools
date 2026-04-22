"""Export extracted content to a "statement set" CSV.

The format (matching the user-supplied example) is a pre-order-flattened
hierarchy.  Each row fills exactly one `(Level N, Description N)` pair
and leaves all other level/description columns blank:

    Level 1,Description 1,Level 2,Description 2,Level 3,Description 3,...

Mapping
-------

Heading and section-row events determine the "depth offset" that all
subsequent rows sit at:

  - Level 1  = the most recent document-level Heading 1 ("top heading").
  - Level 2  = the most recent Heading 2, if any, else the preamble
               bucket (see REVIEW §1.6) / a section-style row from the
               2-col table that sits directly under an H1.
  - Level 3  = the most recent Heading 3 (if H2 is also present), else a
               section-style 2-col-table row (if an H2 was seen), else
               the requirement itself.
  - Level 4+ = deeper-nested levels as the document structure demands.

Requirements always land at the deepest level below whatever structural
context precedes them:

  Level N title         = "<Primary Actor> <N>"   (N restarts per
                          (section_scope, actor) pair)
  Level N description   = "<Primary Actor>\\n\\n<Requirement text>"

Preamble requirements (``row_ref == 'Preamble'`` — emitted by the parser
for prose sitting outside the requirements table) are no longer dropped.
They land under a synthetic "(preamble)" Level-2 bucket so they stay
visible in the CSV without polluting the real structural hierarchy.
This fixes REVIEW §1.6.

Empty-hierarchy degenerate case: if an input document has no H1, no H2,
and no section-row table, requirements get routed under a single
"(preamble)" bucket so every extracted row still reaches the output.

The writer emits a fixed-width header (Level 1..Level 4 + a final
"Level #" placeholder) to match the user-supplied template regardless
of the actual depth reached by any given run.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .models import (
    HeadingEvent,
    RequirementEvent,
    SectionRowEvent,
)


# Header-only level pair count.  Controls how many (Level N, Description N)
# column pairs are emitted in the header row to match the template's width.
# A final "Level #, Description #" placeholder pair is always appended after.
# With H2/H3 plumbing enabled (REVIEW §3.9) requirements can now land as
# deep as Level 5, so we widen the header to match.
_HEADER_LEVEL_PAIRS = 5

# Synthetic "catch-all" bucket for requirements that lack any section /
# heading context (REVIEW §1.6).  Placed at Level 2 so it sits at the
# same depth as a real SectionRowEvent under an H1.
_PREAMBLE_L2_TITLE = "(preamble)"
_PREAMBLE_L2_DESC = (
    "Requirements extracted from prose outside the main requirements "
    "table hierarchy.  Review manually and promote into a real section "
    "as needed."
)


def _header_row() -> List[str]:
    cols: List[str] = []
    for i in range(1, _HEADER_LEVEL_PAIRS + 1):
        cols += [f"Level {i}", f"Description {i}"]
    cols += ["Level #", "Description #"]
    return cols


def _blank_row() -> List[str]:
    return [""] * ((_HEADER_LEVEL_PAIRS + 1) * 2)


def _place(row: List[str], level: int, title: str, description: str) -> None:
    """Write `title` and `description` into the row at the given level."""
    # Levels are 1-indexed; each level occupies two adjacent columns.
    # Column index for Level N title = (N-1) * 2, description = (N-1) * 2 + 1.
    idx = (level - 1) * 2
    row[idx] = title or ""
    row[idx + 1] = description or ""


def events_to_rows(events: Sequence[object]) -> List[List[str]]:
    """Turn an event stream into a list of CSV rows (no header).

    Honours doc Heading 2 / Heading 3 as structural levels (REVIEW §3.9)
    and emits preamble requirements under a synthetic "(preamble)" bucket
    rather than dropping them (REVIEW §1.6).
    """
    rows: List[List[str]] = []

    current_l1: str = ""                      # most recent Heading 1
    current_h2: str = ""                      # most recent Heading 2
    current_h3: str = ""                      # most recent Heading 3
    current_section_title: str = ""           # most recent SectionRowEvent title
    # Per (section_scope, actor) running counters.  section_scope is the
    # deepest structural anchor available for the requirement so that the
    # "<Actor> N" numbering is stable within its nearest section.
    counters: dict[Tuple[str, str], int] = {}
    # Track printed structural anchors keyed by the tuple of ancestors so a
    # given heading only emits its own row once per context.
    printed_anchors: set[Tuple[str, ...]] = set()

    def _emit_anchor(level: int, title: str, description: str, anchor_key: Tuple[str, ...]) -> None:
        if not title:
            return
        if anchor_key in printed_anchors:
            return
        row = _blank_row()
        _place(row, level, title, description)
        rows.append(row)
        printed_anchors.add(anchor_key)

    def _ensure_l1_emitted() -> None:
        if current_l1:
            _emit_anchor(1, current_l1, "", ("L1", current_l1))

    def _depth_below_headings() -> int:
        """Return the level at which a section row / preamble bucket sits,
        given the current H2/H3 context."""
        depth = 2  # always at least below L1
        if current_h2:
            depth += 1  # now at L3 (or preamble inside L2 when no H2 — handled separately)
        if current_h2 and current_h3:
            depth += 1
        return depth

    for ev in events:
        if isinstance(ev, HeadingEvent):
            if ev.level == 1:
                current_l1 = ev.text
                # A new H1 resets the whole subtree.
                current_h2 = ""
                current_h3 = ""
                current_section_title = ""
                _ensure_l1_emitted()
                continue
            if ev.level == 2:
                current_h2 = ev.text
                current_h3 = ""
                current_section_title = ""
                if current_h2:
                    _ensure_l1_emitted()
                    _emit_anchor(2, current_h2, "", ("L2", current_l1, current_h2))
                continue
            if ev.level == 3:
                current_h3 = ev.text
                current_section_title = ""
                if current_h3:
                    _ensure_l1_emitted()
                    # Don't synthesise an H2 if the source document skipped
                    # one — emit H3 at L3 directly so the nesting follows
                    # the document instead of inventing structure.
                    target_level = 3 if current_h2 else 2
                    _emit_anchor(
                        target_level, current_h3, "",
                        ("L" + str(target_level), current_l1, current_h2, current_h3),
                    )
                continue
            # Deeper headings (H4+) are still ignored — pushing them into
            # the pair table would blow past our 5-level template width.
            continue

        if isinstance(ev, SectionRowEvent):
            current_section_title = ev.title
            _ensure_l1_emitted()
            target_level = _depth_below_headings()
            _emit_anchor(
                target_level, ev.title, ev.intro,
                (
                    "SEC", current_l1, current_h2, current_h3, ev.title,
                ),
            )
            continue

        if isinstance(ev, RequirementEvent):
            req = ev.requirement

            # Preamble prose — emit under a synthetic "(preamble)" bucket
            # so it stays visible (REVIEW §1.6).
            if req.row_ref == "Preamble":
                _ensure_l1_emitted()
                _emit_anchor(
                    2, _PREAMBLE_L2_TITLE, _PREAMBLE_L2_DESC,
                    ("L2", current_l1, _PREAMBLE_L2_TITLE),
                )
                section_scope = _PREAMBLE_L2_TITLE
                req_level = 3
            else:
                _ensure_l1_emitted()
                section_scope = current_section_title or current_h3 or current_h2 or current_l1 or "(root)"
                # Requirements live one level deeper than the deepest
                # structural anchor we have.
                anchor_depth = _depth_below_headings()
                if current_section_title:
                    # Section row pinned us a level below H2/H3.
                    req_level = anchor_depth + 1
                else:
                    req_level = anchor_depth
                req_level = min(req_level, _HEADER_LEVEL_PAIRS)

            actor = req.primary_actor or "(no primary actor)"
            ctr_key = (section_scope, actor)
            counters[ctr_key] = counters.get(ctr_key, 0) + 1
            level_title = f"{actor} {counters[ctr_key]}"
            description = f"{actor}\n\n{req.text}"
            row = _blank_row()
            _place(row, req_level, level_title, description)
            rows.append(row)
            continue

    return rows


def write_statement_set(
    events_per_file: Iterable[Tuple[str, Sequence[object]]],
    output_path: Path,
) -> Path:
    """Write a statement-set CSV.

    `events_per_file` is an iterable of `(filename, events)` pairs.  When
    multiple input documents are processed we write their rows back-to-back,
    preserving per-document hierarchy.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(_header_row())
        for _filename, events in events_per_file:
            for row in events_to_rows(events):
                writer.writerow(row)

    return output_path
