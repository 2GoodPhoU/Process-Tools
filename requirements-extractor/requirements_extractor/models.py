"""Dataclasses used across the extractor."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Stable-ID helpers.
#
# The goal: a short, human-quotable identifier that stays the same across
# runs *as long as the underlying requirement hasn't meaningfully changed*.
# Meaningful change is defined narrowly as: the source filename, the
# primary actor, or the requirement sentence itself.
#
# Deliberately NOT in the hash: table/row/block refs, heading trail,
# appearance order.  If we included those, inserting an unrelated
# paragraph upstream would renumber everything — defeating the point.
#
# Format is ``REQ-<8 hex chars>``.  At ~10k requirements across a corpus
# the birthday-collision probability is ≈0.001%, low enough to be a
# non-issue; a true collision is disambiguated with a numeric suffix
# (see ``Requirement.ensure_unique_stable_ids``).
# ---------------------------------------------------------------------------


_WHITESPACE_RUN = re.compile(r"\s+")
_STABLE_ID_PREFIX = "REQ-"
_STABLE_ID_HEX_LEN = 8


def _normalise_for_hash(value: str) -> str:
    """Collapse whitespace and casefold — so cosmetic reformatting
    (double spaces → single, capitalisation of an actor name) doesn't
    churn the ID."""
    return _WHITESPACE_RUN.sub(" ", value.strip()).casefold()


def compute_stable_id(source_file: str, primary_actor: str, text: str) -> str:
    """Return a stable ``REQ-<8hex>`` identifier for a requirement.

    Pure function — takes the three identity-defining inputs and returns
    a deterministic ID.  Callers that need collision handling should use
    :func:`ensure_unique_stable_ids` on the full list.
    """
    blob = "\x1f".join(
        _normalise_for_hash(part) for part in (source_file, primary_actor, text)
    )
    digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()
    return f"{_STABLE_ID_PREFIX}{digest[:_STABLE_ID_HEX_LEN]}"


def ensure_unique_stable_ids(requirements: List["Requirement"]) -> None:
    """In-place disambiguation of colliding stable IDs.

    SHA1 collisions on three-field inputs are astronomically unlikely,
    but *duplicate rows* (two requirements with identical file, actor,
    and text) do happen in real corpora — the same boilerplate shared
    across sections, copy-paste mistakes, etc.  For those, we append
    ``-1``, ``-2``, … to the later occurrences in first-seen order so
    each row still has a unique handle while the shared prefix stays
    greppable.
    """
    seen: dict[str, int] = {}
    for req in requirements:
        base = req.stable_id
        if not base:
            continue
        count = seen.get(base, 0)
        if count > 0:
            req.stable_id = f"{base}-{count}"
        seen[base] = count + 1


def annotate_cross_source_duplicates(requirements: List["Requirement"]) -> int:
    """Flag requirements that share ``(primary_actor, text)`` with an
    earlier-appearing row in the corpus.

    REVIEW §1.10: the same boilerplate often shows up in multiple spec
    files — a company-standard paragraph copied across documents, a
    shared compliance clause, etc.  Today those come through the
    extractor as N independent rows and a reviewer has to notice the
    duplication manually.  This pass appends a ``Duplicate of <stable_id>
    (<source_file>, <row_ref>)`` line to the ``notes`` column of every
    duplicate except the first, so triage is mechanical.

    Matching is cross-source on purpose: two rows with the same actor
    and text but from different files are the interesting case.  Within
    a single source file we already have :func:`ensure_unique_stable_ids`
    which suffixes the duplicates.  The dedup key is whitespace-
    collapsed and case-folded (via :func:`_normalise_for_hash`) so
    cosmetic differences don't cause a boilerplate pair to look unique.

    Returns the number of rows that were newly flagged.  Pure function
    over the input list — the caller decides when in the pipeline to
    run it (for the Excel pipeline that's right after stable-ID
    assignment; see :func:`extractor.extract_from_files`).
    """
    seen: dict[tuple, "Requirement"] = {}
    flagged = 0
    for req in requirements:
        actor_norm = _normalise_for_hash(req.primary_actor or "")
        text_norm = _normalise_for_hash(req.text or "")
        if not text_norm:
            # Empty-text rows shouldn't happen but guard anyway — we
            # don't want a single "" row to poison the map for every
            # subsequent empty-text row.
            continue
        key = (actor_norm, text_norm)
        original = seen.get(key)
        if original is None:
            seen[key] = req
            continue
        # Duplicate of an earlier row.  Point to the first-seen row's
        # stable_id and source so reviewers can hop there directly.
        note = (
            f"Duplicate of {original.stable_id} "
            f"({original.source_file}, {original.row_ref})."
        )
        req.notes = f"{req.notes}\n{note}".strip() if req.notes else note
        flagged += 1
    return flagged


@dataclass
class Requirement:
    """One extracted requirement row."""

    order: int                          # global appearance order (1-based)
    source_file: str                    # just the filename, not full path
    heading_trail: str                  # e.g. "3. System Requirements > 3.2 Auth"
    section_topic: str                  # column-1 topic for the row
    row_ref: str                        # e.g. "Table 2, Row 4"
    block_ref: str                      # e.g. "Paragraph 1" or "Bullet 2" or "Nested Table R2C1"
    primary_actor: str                  # main responsible role/entity
    secondary_actors: List[str]         # other actors referenced
    text: str                           # the requirement sentence/item
    req_type: str                       # "Hard" | "Soft"
    keywords: List[str]                 # keywords that matched
    confidence: str                     # "High" | "Medium" | "Low"
    notes: str = ""                     # free-text flags for reviewers
    polarity: str = "Positive"          # "Positive" | "Negative" (shall-not etc.)
    stable_id: str = ""                 # "REQ-<8hex>" - survives upstream content churn
    context: str = ""                   # surrounding source text for reviewer context (REVIEW §3.8); empty when redundant with `text`

    @property
    def secondary_actors_str(self) -> str:
        return ", ".join(self.secondary_actors)

    @property
    def keywords_str(self) -> str:
        return ", ".join(self.keywords)


@dataclass
class ExtractionStats:
    files_processed: int = 0
    requirements_found: int = 0
    hard_count: int = 0
    soft_count: int = 0
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Document events - a lightweight ordered stream used by writers that need
# structural context (e.g. the statement-set CSV exporter).  The Excel writer
# only needs RequirementEvent values, so it can filter the stream.
# ---------------------------------------------------------------------------


@dataclass
class HeadingEvent:
    """A Word heading paragraph at the document (top) level."""

    level: int                  # 1 for Heading 1, 2 for Heading 2, etc.
    text: str


@dataclass
class SectionRowEvent:
    """A 2-col table row whose column-1 text looks like a section header.

    The column-2 content (paragraph text) becomes `intro`.  This event is
    emitted before any requirements found inside that same row.
    """

    title: str                  # e.g. "3.1 Authentication"
    intro: str                  # joined paragraph text from column 2
    row_ref: str                # e.g. "Table 1, Row 3"


@dataclass
class RequirementEvent:
    """Wraps a single Requirement so it can live alongside structural events."""

    requirement: "Requirement"


# A DocumentEvents is simply an ordered list of the above.  We don't use a
# separate type alias to keep the imports simple for callers.
