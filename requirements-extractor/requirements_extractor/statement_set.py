"""Export extracted content to a "statement set" CSV.

The format (matching the user-supplied example) is a pre-order-flattened
hierarchy.  Each row fills exactly one `(Level N, Description N)` pair
and leaves all other level/description columns blank:

    Level 1,Description 1,Level 2,Description 2,Level 3,Description 3,...

Mapping used here:
  - Level 1  = the most recent document-level Heading 1 (the "top heading")
  - Level 2  = a section-style row from the 2-col table
               (title in Level 2, intro paragraph in Description 2)
  - Level 3  = an individual requirement, with
                 Level 3       = "<Primary Actor> <N>"  (N restarts per
                                 section/actor pair)
                 Description 3 = "<Primary Actor>\\n\\n<Requirement text>"

Only headings, section rows, and requirements produce output rows.

The writer emits a fixed-width header that matches the provided example
(Level 1..Level 4 + a final "Level #" placeholder), so the exported CSV
drops into the same template.  If you ever see requirements nested more
than three levels deep, bump `_MAX_LEVEL` below.
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


# Pair count for concrete levels (L1..L4).  A final "Level #, Description #"
# pair is always appended to match the provided example header exactly.
_MAX_LEVEL = 4


def _header_row() -> List[str]:
    cols: List[str] = []
    for i in range(1, _MAX_LEVEL + 1):
        cols += [f"Level {i}", f"Description {i}"]
    cols += ["Level #", "Description #"]
    return cols


def _blank_row() -> List[str]:
    return [""] * ((_MAX_LEVEL + 1) * 2)


def _place(row: List[str], level: int, title: str, description: str) -> None:
    """Write `title` and `description` into the row at the given level."""
    # Levels are 1-indexed; each level occupies two adjacent columns.
    # Column index for Level N title = (N-1) * 2, description = (N-1) * 2 + 1.
    idx = (level - 1) * 2
    row[idx] = title or ""
    row[idx + 1] = description or ""


def events_to_rows(events: Sequence[object]) -> List[List[str]]:
    """Turn an event stream into a list of CSV rows (no header)."""
    rows: List[List[str]] = []

    current_l1: str = ""                    # most recent Heading 1
    current_section_title: str = ""         # most recent SectionRowEvent title
    # Per (section_title, actor) running counters.
    counters: dict[Tuple[str, str], int] = {}
    # Track which L1/L2 titles we've already printed so we don't repeat them
    # when multiple things live under the same parent.
    printed_l1: set[str] = set()
    printed_l2_keys: set[Tuple[str, str]] = set()

    for ev in events:
        if isinstance(ev, HeadingEvent):
            if ev.level == 1:
                current_l1 = ev.text
                # Reset L2 context — a new H1 starts a new subtree.
                current_section_title = ""
                if current_l1 and current_l1 not in printed_l1:
                    row = _blank_row()
                    _place(row, 1, current_l1, "")
                    rows.append(row)
                    printed_l1.add(current_l1)
            # Lower-level doc headings are currently ignored for statement-set
            # output — our hierarchy uses section-style 2-col-table rows for
            # Level 2 instead.
            continue

        if isinstance(ev, SectionRowEvent):
            current_section_title = ev.title
            key = (current_l1, ev.title)
            if key not in printed_l2_keys:
                row = _blank_row()
                _place(row, 2, ev.title, ev.intro)
                rows.append(row)
                printed_l2_keys.add(key)
            continue

        if isinstance(ev, RequirementEvent):
            req = ev.requirement
            # Skip anything found in the document preamble — boilerplate prose
            # ahead of the main hierarchy doesn't belong in a statement set.
            # (It's still captured in the Excel workbook for review.)
            if req.row_ref == "Preamble":
                continue
            actor = req.primary_actor or "(no primary actor)"
            # Running counter is scoped to (section, actor).  If there's no
            # current section, the actor's own name is used as the scope so
            # counters still behave sensibly.
            section_scope = current_section_title or req.heading_trail or ""
            ctr_key = (section_scope, actor)
            counters[ctr_key] = counters.get(ctr_key, 0) + 1
            level_title = f"{actor} {counters[ctr_key]}"
            description = f"{actor}\n\n{req.text}"
            row = _blank_row()
            _place(row, 3, level_title, description)
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
