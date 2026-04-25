"""Explicit-ID matcher.

Detects clause references inside requirement text — phrases like
``IAW [DO-178C §6.3.1]``, ``per Section 4.2.2``, ``in accordance with
clause 7.4``. These are the highest-signal links because the spec author
*explicitly* wrote them; the trade-off is recall — only catches what's
been written down.

Approach:
1. For each procedure clause, derive a small set of "id-like" tokens that
   could plausibly appear inside a contract requirement (the stable ID,
   the section number, the heading trail's leaf number).
2. Build a single combined regex per token-set.
3. Scan every contract requirement's text and context for hits.

The score is 1.0 for any explicit hit — there's no gradient. False
positives are possible (the same section number in two different
standards) and the evidence string carries the raw match so a reviewer
can spot them.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Set

from ..models import DDERow, Match


# Patterns for extracting "section-number-like" tokens from a clause's
# row_ref / heading_trail / section field. Examples we want to capture:
#   "Table 3, Row 2"      → "3.2" or "3-2"
#   "1. Shift Start"      → "1"
#   "§6.3.1 General"      → "6.3.1"
_SECTION_NUM = re.compile(r"\b\d+(?:[.\-]\d+){0,4}\b")


def _candidate_tokens(clause: DDERow) -> Set[str]:
    """Tokens that, if present in a contract requirement's text, suggest a
    link to ``clause``. Always includes the stable ID; conditionally
    includes section / heading numbers when present."""

    tokens: Set[str] = {clause.stable_id}
    for field in (clause.row_ref, clause.heading_trail, clause.section):
        if not field:
            continue
        for hit in _SECTION_NUM.findall(field):
            # Skip purely single-digit hits unless they're the only thing
            # we have — single digits ("1", "2") match too liberally.
            if len(hit) >= 2 or "." in hit or "-" in hit:
                tokens.add(hit)
    return tokens


def _build_pattern(tokens: Iterable[str]) -> re.Pattern[str]:
    """A regex that matches any of the given tokens as a whole-word."""

    escaped = sorted({re.escape(t) for t in tokens if t}, key=len, reverse=True)
    if not escaped:
        # Pattern that never matches — keeps callers simple.
        return re.compile(r"$.^")
    return re.compile(r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w)")


def run(
    contract_rows: List[DDERow],
    procedure_rows: List[DDERow],
) -> List[Match]:
    matches: List[Match] = []
    for clause in procedure_rows:
        tokens = _candidate_tokens(clause)
        pat = _build_pattern(tokens)

        for req in contract_rows:
            haystack = " ".join(filter(None, (req.text, req.context or "")))
            if not haystack:
                continue
            hit = pat.search(haystack)
            if hit is None:
                continue
            evidence = f"explicit ref '{hit.group(0)}' in requirement text"
            matches.append(
                Match(
                    contract_id=req.stable_id,
                    procedure_id=clause.stable_id,
                    matcher="explicit_id",
                    score=1.0,
                    evidence=evidence,
                )
            )
    return matches
