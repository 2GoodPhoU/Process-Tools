"""Procedural-table detection — header signal + multi-actor cell parsing.

A common shape in defense / aerospace specs is a 3-column procedural
table whose header is::

    | (blank) | Step | Required Action |

Every body row of such a table is a binding requirement by virtue of
the header — even when the action sentence has no shall/must/required
keyword.  Detecting the table type forces the parser into a
procedural mode that:

* skips the header row,
* maps the columns differently from a generic 2-col requirements table
  (actor=col 1, content=col 3),
* emits every captured sentence as Hard with a synthetic
  ``(Required Action)`` keyword marker so reviewers can see which
  detection path fired,
* allows blank column-1 cells to inherit the actor from the nearest
  non-blank predecessor row (procedural specs often only spell out
  the actor on the first row of a multi-step block),
* parses multi-actor column-1 cells (``Auth Service, Gateway, Logger``)
  as a *set* of candidates, then picks the candidate that appears
  earliest in each step's sentence text.

This module collects the pure helpers that implement those signals.
The walker proper (in :mod:`parser`) calls into them via the
``force_requirement`` and ``candidate_actors`` kwargs on the
``_walk_content`` / ``_emit_candidate`` chain.

Extracted from ``parser.py`` in a refactor — that module had grown
to ~870 lines because procedural-table detection was layered on top
of the original 2-col walker.  Lifting these helpers into their own
module makes the procedural feature audit-able as a unit (every
relevant function lives here, plus the 36 regression tests in
``test_procedural_tables.py``).  The walker is unchanged in shape;
it now just imports the procedural helpers instead of defining them
inline.

The helper names retain their underscore-prefixed form
(:func:`_split_candidate_actors`, :func:`_pick_primary`,
:func:`_resolve_primary_from_candidates`) and are re-exported via
:mod:`parser` so existing test imports
(``from requirements_extractor.parser import _split_candidate_actors``)
continue to resolve.  New code should prefer the direct import from
this module.
"""

from __future__ import annotations

import re
from typing import List, Optional


# ---------------------------------------------------------------------------
# Header signal — "(blank) | Step | Required Action"
# ---------------------------------------------------------------------------


#: Expected header cells (lower-cased, whitespace-collapsed) for a
#: required-action table.  The column-1 header is an empty string —
#: that's part of the type signal.
_REQUIRED_ACTION_HEADER = ("", "step", "required action")


#: Synthetic keyword label for rows captured by the header signal
#: rather than by a modal-keyword match.  Visible to reviewers in the
#: output's Keywords column so they can tell which detection path
#: fired.  Public — :func:`parser._emit_candidate` reads it.
REQUIRED_ACTION_KEYWORD = "(Required Action)"


def _normalise_header_cell(text: str) -> str:
    """Return ``text`` lower-cased with internal whitespace collapsed.

    Header comparisons are forgiving about casing and stray whitespace
    so a fixture authored with ``Required Action`` and a document
    authored with ``REQUIRED  ACTION`` or ``required\\naction`` both
    match.
    """
    return " ".join((text or "").split()).lower()


def is_required_action_header(row_cells_text: List[str]) -> bool:
    """Return True iff ``row_cells_text`` matches the procedural header.

    Takes a list of strings (the already-extracted text of each cell
    in a candidate header row) rather than python-docx objects so it
    can be unit-tested headlessly.  Matches exactly three cells with
    normalised contents ``("", "step", "required action")``.

    Case-insensitive and whitespace-tolerant: ``"Required  Action"``
    / ``"REQUIRED ACTION"`` / ``"  Required\\nAction  "`` all match
    the column-3 slot.
    """
    if len(row_cells_text) != 3:
        return False
    return tuple(_normalise_header_cell(c) for c in row_cells_text) == _REQUIRED_ACTION_HEADER


# ---------------------------------------------------------------------------
# Multi-actor-cell resolution (FIELD_NOTES §4 case 3 / Eric 2026-04-23)
#
# In procedural required-action tables, column 1 may list several
# eligible actors for a single step: "Auth Service, Gateway, Logger"
# or "Auth Service / Gateway / Logger".  The requirement text itself
# then picks which of the candidates actually performs the step
# ("The Gateway shall forward...").  We parse the cell as a *set* of
# candidates and, for each sentence, prefer the candidate whose name
# appears earliest in the sentence.  Sentences that don't name any
# candidate fall back to the joined cell text — preserving the
# caller's view that all candidates may be involved.
# ---------------------------------------------------------------------------


# Separators recognised when splitting a candidate-cell: comma,
# semicolon, " / " (with spaces), " and " (word-bounded), " & " (with
# spaces).  Matches authors' common conventions; intentionally does
# NOT split on plain " " since most single-actor names have internal
# spaces ("Auth Service").
_CANDIDATE_SPLIT_RE = re.compile(
    r"\s*[,;]\s*|\s+/\s+|\s+&\s+|\s+and\s+",
    flags=re.IGNORECASE,
)


def _split_candidate_actors(cell_text: str) -> List[str]:
    """Parse a candidate-cell into a list of actor names.

    Returns ``[]`` when the cell only names one actor (no separators)
    — the caller should then treat the cell as a conventional
    single-actor primary.  Trims each candidate and drops empty
    fragments so trailing separators (``"A, B,"``) don't produce
    ghost entries.
    """
    s = (cell_text or "").strip()
    if not s:
        return []
    parts = [p.strip() for p in _CANDIDATE_SPLIT_RE.split(s)]
    parts = [p for p in parts if p]
    # A single-actor cell (no separators) still returns [s] from the
    # split; the "multi-actor" signal is having at least two parts.
    if len(parts) < 2:
        return []
    return parts


def _pick_primary(
    sentence: str,
    default_primary: str,
    candidates: Optional[List[str]],
) -> str:
    """Choose the effective primary actor for ``sentence``.

    When ``candidates`` is falsy, just returns ``default_primary``
    unchanged — callers who don't care about multi-actor resolution
    get the existing behaviour.  When candidates are present, tries
    to resolve from the sentence subject; falls back to
    ``default_primary`` if no candidate appears in the sentence.
    This keeps rows whose text doesn't name a specific candidate
    attributed to the full candidate list (the joined cell text)
    rather than silently dropping them to an empty actor.
    """
    if not candidates:
        return default_primary
    picked = _resolve_primary_from_candidates(sentence, candidates)
    return picked if picked is not None else default_primary


def _resolve_primary_from_candidates(
    sentence: str, candidates: List[str]
) -> Optional[str]:
    """Pick the candidate whose name appears earliest in ``sentence``.

    Returns ``None`` when no candidate name is found, so the caller
    can decide what fallback to use (typically: the joined cell text).
    Case- and word-boundary aware — ``"Authentication Service"`` will
    not match a candidate named ``"Auth Service"``.
    """
    if not sentence or not candidates:
        return None
    lower_sent = sentence.lower()
    best: Optional[tuple] = None  # (position, candidate)
    for cand in candidates:
        if not cand:
            continue
        pattern = r"\b" + re.escape(cand.lower()) + r"\b"
        m = re.search(pattern, lower_sent)
        if m is None:
            continue
        pos = m.start()
        if best is None or pos < best[0]:
            best = (pos, cand)
    return best[1] if best else None
