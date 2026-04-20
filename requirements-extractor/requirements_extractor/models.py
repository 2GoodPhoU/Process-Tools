"""Dataclasses used across the extractor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


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

    @property
    def source(self) -> str:
        """Human-readable source path for the Excel 'Source' column."""
        parts = [self.source_file]
        if self.heading_trail:
            parts.append(self.heading_trail)
        if self.section_topic:
            parts.append(self.section_topic)
        parts.append(self.row_ref)
        if self.block_ref:
            parts.append(self.block_ref)
        return " > ".join(p for p in parts if p)

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
# Document events — a lightweight ordered stream used by writers that need
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
