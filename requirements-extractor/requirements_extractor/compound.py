"""Compound-requirement detection — aggregate a modal+colon lead-in
with the bulleted/dashed/numbered/lettered list that follows.

Trigger pattern (from the 2026-04-27 field gap)::

    "Programs shall comply with this document if they:
        - Domestic US-Based program, and
        - exceed 12 months in duration, and
        - Pre-preliminary design review <MRL 5 overall maturity, and
        - design and/produce hardware content"

The 0.6.0 detector treats line 1 as fragmentary (ends with ``:``, no
sentence terminator) and ignores lines 2–5 (no modal verbs).  The
intended output is ONE compound requirement that captures the lead-in
plus all conditions joined by their inferred connector (and / or /
unless).

Design notes
------------

* **Additive only.**  Detection runs as a *pre-pass* over the children
  of a content cell (or other parent block).  It claims a contiguous
  range of paragraph indices — the lead-in plus its list items — and
  the legacy walker is told to skip those when emitting per-paragraph
  requirements.  Anything the pre-pass doesn't claim falls through
  unchanged, so a document with no compound patterns produces output
  byte-identical to 0.6.0.

* **Pure helper.**  The detector operates on a small ``_BlockInfo``
  record (text, is_bullet, has_marker_prefix) rather than docx
  ``Paragraph`` wrappers, so it can be unit-tested headlessly without
  spinning up a python-docx Document.  The walker translates docx
  blocks into ``_BlockInfo`` records once per parent.

* **`where:` exclusion.**  A lead-in whose last word before the colon
  is "where" introduces a glossary / definition list, NOT a set of
  conditions.  Those are deliberately *not* aggregated; the legacy
  per-paragraph walker continues to handle them so the resulting rows
  still flow into actor extraction normally.

* **`unless:` handling.**  Items ending with "unless" are aggregated
  but the synthetic compound text is rendered with an "(unless any of)"
  clause so the polarity is unambiguous.  Reviewers see at a glance
  that the bullets are exclusion conditions.

Out of scope for 0.6.1 (deferred to follow-up patches)
------------------------------------------------------

* Nested lists (sub-bullets within a bullet item).
* List items that carry their own modal verbs — those are arguably
  sub-requirements within a compound and need a design call before
  implementation.
* Tables of conditions — different pipeline; separate patch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Plain-text list-marker detection.
#
# Word's ``numPr`` element is the authoritative bullet/numbered signal
# (handled via :func:`parser._is_bullet`), but real-world specs often
# format lists with hand-typed dashes or asterisks instead of using a
# proper list style.  This regex catches those so the compound detector
# doesn't miss a list just because the author didn't apply Word styling.
#
# Character classes:
#   * Bullet glyphs:   • ▪ ◦ ‣  + ASCII *
#   * Dashes:          —  –  -
#   * Numeric prefix:  1.  1)  42.   (1–3 digits, period or close-paren)
#   * Alphabetic:      a.  b)        (single ASCII letter, period or
#                                    close-paren)
#   * Roman numerals:  i.  iv)       (1–4 i/v/x letters, lower or upper)
#
# The trailing ``\s+\S`` enforces "marker is followed by whitespace and
# at least one non-whitespace character" — empty bullets ("- ") and
# stray hyphenated words at the start of a line ("non-blocking ...")
# don't match.
# ---------------------------------------------------------------------------


_LIST_MARKER_RE = re.compile(
    r"^("
    r"[•▪◦‣*]"          # bullet glyphs / ASCII *
    r"|[—–\-]"                    # em dash / en dash / hyphen
    r"|\d{1,3}[.)]"                         # 1.  1)  42.
    r"|[a-zA-Z][.)]"                        # a.  b)
    r"|[ivxIVX]{1,4}[.)]"                   # i.  iv)  IV.
    r")\s+\S",
    flags=re.UNICODE,
)


# ---------------------------------------------------------------------------
# Modal trigger.
#
# Mirrors detector.HARD_KEYWORDS + SOFT_KEYWORDS.  Re-implemented here as
# a small regex rather than reusing ``KeywordMatcher`` because:
#   (a) we don't want to require a full ``Config`` to run the detector
#       (keeps unit-testing cheap);
#   (b) the per-call cost of compiling KeywordMatcher's full regex
#       caches is overkill when all we need is "does this paragraph
#       look like an obligation".
#
# A regression test in ``tests/test_compound.py`` pins the trigger
# alignment with detector.HARD_KEYWORDS | SOFT_KEYWORDS so a future
# vocabulary change in detector.py surfaces as a test failure rather
# than silent drift.
# ---------------------------------------------------------------------------


_MODAL_RE = re.compile(
    r"\b(?:shall|must|required|mandatory|is\s+to|are\s+to"
    r"|should|may|might|can|could|will|recommended|preferred"
    r"|ought\s+to)\b",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Trailing-connector detector.
#
# A list item's trailing ``and`` / ``or`` / ``unless`` (with optional
# punctuation) is the connector signal.  We tolerate trailing comma,
# semicolon, or period because authors are inconsistent.  The
# connector is also stripped before the item is folded into the
# compound text so the rendered output reads cleanly.
# ---------------------------------------------------------------------------


_CONNECTOR_RE = re.compile(
    r"[,;\.]?\s*\b(and|or|unless)[,;\.]?\s*$",
    flags=re.IGNORECASE,
)


# Words that — when a colon-terminated lead-in ends in them — flag the
# block as a definition list rather than a conditions list.  Today that
# is just ``where``; the tuple shape leaves room for future additions
# (e.g. ``defined as``) without re-shaping the call site.
_DEFINITION_LEADINS: tuple = ("where",)


# ---------------------------------------------------------------------------
# Public dataclasses.
# ---------------------------------------------------------------------------


@dataclass
class CompoundGroup:
    """One compound requirement spanning a lead-in + N list items.

    Stores indices into the original block sequence so the walker can
    skip past the claimed rows when emitting legacy per-paragraph
    requirements.  ``aggregated_text`` is the synthetic compound
    sentence the new pass emits.
    """

    lead_in_idx: int
    item_indices: List[int] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    lead_in_text: str = ""
    connector: str = "and"             # "and" | "or" | "unless"
    aggregated_text: str = ""

    @property
    def claimed_indices(self) -> List[int]:
        return [self.lead_in_idx] + list(self.item_indices)


@dataclass
class _BlockInfo:
    """Lightweight wrapper used by :func:`detect_groups`.

    Decoupled from python-docx so the detector stays unit-testable
    without spinning up a Document.  ``is_paragraph`` is False for
    table blocks (or any non-paragraph child); they break a list run
    naturally because they can't be list items.
    """

    text: str = ""
    is_paragraph: bool = True
    is_bullet: bool = False             # Word's numPr / list-style signal
    has_marker_prefix: bool = False     # plain-text marker fallback

    @property
    def is_list_item(self) -> bool:
        return self.is_paragraph and (self.is_bullet or self.has_marker_prefix)


# ---------------------------------------------------------------------------
# Public helpers.
# ---------------------------------------------------------------------------


def has_list_marker_prefix(text: str) -> bool:
    """Return True iff ``text`` starts with a recognised list marker.

    Used by the parser as a fallback for paragraphs that don't carry
    Word's ``numPr`` element but that the author hand-formatted with a
    dash, asterisk, etc.  See :data:`_LIST_MARKER_RE` for the exact
    accepted glyphs.
    """
    if not text:
        return False
    return _LIST_MARKER_RE.match(text.lstrip()) is not None


def _strip_marker(item_text: str) -> str:
    """Remove a leading bullet/dash/numbered marker from an item, if any."""
    s = (item_text or "").lstrip()
    m = _LIST_MARKER_RE.match(s)
    if not m:
        return item_text
    # The match consumes "marker + whitespace + first body char" — back
    # off one position so the body char survives.
    body_start = m.end() - 1
    return s[body_start:].lstrip()


def _strip_trailing_connector(item_text: str) -> str:
    """Strip a trailing ``and`` / ``or`` / ``unless`` (with optional punctuation)."""
    s = _CONNECTOR_RE.sub("", item_text or "").rstrip()
    # Belt-and-braces: also drop a now-orphaned trailing comma/semicolon.
    return s.rstrip(",;").rstrip()


def _ends_with_definition_leadin(text: str) -> bool:
    """Lead-in whose last alpha word is in :data:`_DEFINITION_LEADINS`."""
    s = (text or "").rstrip()
    if s.endswith(":"):
        s = s[:-1].rstrip()
    if not s:
        return False
    m = re.search(r"([A-Za-z]+)$", s)
    if not m:
        return False
    return m.group(1).lower() in _DEFINITION_LEADINS


def _detect_connector(items: List[str]) -> str:
    """Infer the compound's connector from items' trailing tokens.

    Priority is ``unless`` > ``or`` > ``and``.  The reasoning:

    * ``unless`` is a strong polarity-flipping signal — even one
      ``unless`` in a list of conditions makes the whole compound an
      exclusion list, so it wins outright.
    * ``or`` outranks ``and`` when at least one item carries an explicit
      ``or``: in real specs, authors usually mark "any-of" lists more
      carefully than "all-of" lists, so the presence of even one ``or``
      tilts the compound toward a disjunction.
    * Otherwise default to ``and`` (the most common case).

    The last item often has no trailing connector — it's the terminal
    item — so absence of any signal across the whole list is normal and
    correctly maps to the ``and`` default.
    """
    counts = {"and": 0, "or": 0, "unless": 0}
    for it in items:
        m = _CONNECTOR_RE.search(it or "")
        if m:
            counts[m.group(1).lower()] += 1
    if counts["unless"] > 0:
        return "unless"
    if counts["or"] > 0:
        return "or"
    return "and"


def aggregate(lead_in: str, items: List[str], connector: str) -> str:
    """Build the synthetic compound-requirement sentence.

    Format::

        "<lead-in stripped of trailing colon> <clause>: (1) item; (2) item; ..."

    where ``<clause>`` is one of:

      * ``(all of)``     for an ``and`` compound
      * ``(any of)``     for an ``or`` compound
      * ``(unless any of)`` for an ``unless`` compound

    The numeric ``(N)`` prefix on each item preserves item ordering in
    the rendered text — useful for reviewers who want to cross-reference
    a specific condition without scanning back to the source document.
    """
    lead = (lead_in or "").rstrip()
    if lead.endswith(":"):
        lead = lead[:-1].rstrip()
    if connector == "unless":
        clause = "(unless any of)"
    elif connector == "or":
        clause = "(any of)"
    else:
        clause = "(all of)"
    body_parts: List[str] = []
    for i, raw in enumerate(items, start=1):
        cleaned = _strip_marker((raw or "").strip()).strip()
        cleaned = _strip_trailing_connector(cleaned)
        if not cleaned:
            continue
        body_parts.append(f"({i}) {cleaned}")
    body = "; ".join(body_parts)
    if not body:
        # Defensive: if every item stripped down to "", fall back to the
        # raw lead-in.  Should be impossible in practice — _detect_groups
        # only fires when at least one list item is present and non-empty
        # — but the guard keeps a malformed input from emitting a row
        # whose text is just "lead-in (all of):".
        return lead
    return f"{lead} {clause}: {body}".strip()


def detect_groups(blocks: List[_BlockInfo]) -> List[CompoundGroup]:
    """Scan a sequence of block infos and return any compound groups.

    Pure function over :class:`_BlockInfo` records.  Walks left-to-right;
    when a paragraph ends with ``:``, contains a modal verb, and is
    NOT a definition lead-in, looks ahead for a contiguous run of list
    items and (if at least one is present) emits a :class:`CompoundGroup`
    spanning the lead-in plus its run.  The walker continues from the
    block immediately AFTER the run, so two back-to-back compound
    groups in the same parent are detected independently.
    """
    groups: List[CompoundGroup] = []
    n = len(blocks)
    i = 0
    while i < n:
        b = blocks[i]
        if (
            b.is_paragraph
            and not b.is_list_item
            and b.text.rstrip().endswith(":")
            and _MODAL_RE.search(b.text)
            and not _ends_with_definition_leadin(b.text)
        ):
            items: List[str] = []
            indices: List[int] = []
            j = i + 1
            while j < n and blocks[j].is_list_item:
                items.append(blocks[j].text)
                indices.append(j)
                j += 1
            if items:
                connector = _detect_connector(items)
                aggregated = aggregate(b.text, items, connector)
                groups.append(
                    CompoundGroup(
                        lead_in_idx=i,
                        item_indices=indices,
                        items=items,
                        lead_in_text=b.text,
                        connector=connector,
                        aggregated_text=aggregated,
                    )
                )
                i = j
                continue
        i += 1
    return groups
