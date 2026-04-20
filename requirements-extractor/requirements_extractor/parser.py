"""Walk a .docx document in order and emit a structural event stream.

Document assumptions (matches the user's typical spec format):
  - A header region at the top (title, optional metadata paragraphs).
  - One or more large 2-column tables.  In each row, column 1 holds a
    section title / topic / actor, and column 2 holds mixed content:
    paragraphs, bullet lists, or nested tables.
  - Standard Word heading styles (Heading 1/2/3) may appear outside of
    tables to group content — these are captured as a "heading trail".

The parser emits an ordered list of events:
  - HeadingEvent          — a top-level heading paragraph
  - SectionRowEvent       — a 2-col table row whose column-1 text looks
                            like a numbered section header (e.g. "3.1 Auth")
  - RequirementEvent      — a single extracted requirement

Writers that only care about requirements (e.g. the Excel writer) can
filter the stream; writers that need structural context (e.g. the
statement-set CSV exporter) consume it whole.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Union

from docx import Document
from docx.document import Document as _Document
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from .detector import classify, split_sentences
from .models import (
    HeadingEvent,
    Requirement,
    RequirementEvent,
    SectionRowEvent,
)

Event = Union[HeadingEvent, SectionRowEvent, RequirementEvent]

# A section-style row's column-1 text starts with a numeric prefix
# ("3", "3.1", "3.1.2", "3.1)", etc.) followed by a space.  Everything
# else is treated as an actor/topic row.
_SECTION_RE = re.compile(r"^\s*\d+(?:\.\d+)*[\.\)]?\s+\S")


@dataclass
class _ParseContext:
    source_file: str
    heading_trail: List[str]
    table_index: int = 0
    order_counter: int = 0

    def next_order(self) -> int:
        self.order_counter += 1
        return self.order_counter

    def trail_str(self) -> str:
        return " > ".join(h for h in self.heading_trail if h)


# ---------------------------------------------------------------------------
# docx traversal helpers
# ---------------------------------------------------------------------------


def iter_block_items(parent) -> Iterator[object]:
    """Yield Paragraph and Table objects from a parent in document order.

    Works on the Document body and on table cells.
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        parent_elm = getattr(parent, "_element", None) or getattr(parent, "element", None)

    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _paragraph_text(p: Paragraph) -> str:
    return (p.text or "").strip()


def _heading_level(p: Paragraph) -> Optional[int]:
    style = p.style.name if p.style is not None else ""
    if style and style.lower().startswith("heading "):
        try:
            return int(style.split()[-1])
        except ValueError:
            return None
    return None


def _is_bullet(p: Paragraph) -> bool:
    """Best-effort bullet/numbering detection."""
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        return False
    numPr = pPr.find(qn("w:numPr"))
    if numPr is not None:
        return True
    style = (p.style.name if p.style is not None else "").lower()
    return "list" in style or "bullet" in style


def _cell_text(cell: _Cell) -> str:
    """Concatenate all paragraph text in a cell, collapsing whitespace."""
    return " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())


def _cell_paragraph_text(cell: _Cell) -> str:
    """Join non-heading paragraph text from a cell — used for section intros."""
    parts: List[str] = []
    for block in iter_block_items(cell):
        if isinstance(block, Paragraph):
            level = _heading_level(block)
            if level is not None:
                continue  # skip embedded sub-headings
            text = _paragraph_text(block)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _update_heading_trail(trail: List[str], level: int, text: str) -> None:
    """Keep the trail at most `level` deep, then append the new heading."""
    while len(trail) >= level:
        trail.pop()
    trail.append(text)


def _looks_like_section(topic: str) -> bool:
    return bool(_SECTION_RE.match(topic or ""))


# ---------------------------------------------------------------------------
# Content walking — column-2 cell traversal
# ---------------------------------------------------------------------------


def _collect_from_cell(
    cell: _Cell,
    ctx: _ParseContext,
    *,
    row_ref: str,
    primary_actor: str,
    resolver_fn,
) -> Iterator[Requirement]:
    """Walk column-2 content and yield Requirement rows."""
    paragraph_idx = 0
    bullet_idx = 0
    nested_table_idx = 0

    for block in iter_block_items(cell):
        if isinstance(block, Paragraph):
            text = _paragraph_text(block)
            if not text:
                continue
            if _is_bullet(block):
                bullet_idx += 1
                block_ref = f"Bullet {bullet_idx}"
                yield from _emit(text, ctx, row_ref, block_ref, primary_actor, resolver_fn)
            else:
                paragraph_idx += 1
                block_ref = f"Paragraph {paragraph_idx}"
                for sent in split_sentences(text):
                    yield from _emit(sent, ctx, row_ref, block_ref, primary_actor, resolver_fn)
        elif isinstance(block, Table):
            nested_table_idx += 1
            for r_idx, nrow in enumerate(block.rows, start=1):
                for c_idx, ncell in enumerate(nrow.cells, start=1):
                    cell_text = _cell_text(ncell)
                    if not cell_text:
                        continue
                    block_ref = (
                        f"Nested Table {nested_table_idx} R{r_idx}C{c_idx}"
                    )
                    for sent in split_sentences(cell_text):
                        yield from _emit(
                            sent, ctx, row_ref, block_ref, primary_actor, resolver_fn
                        )


def _emit(
    text: str,
    ctx: _ParseContext,
    row_ref: str,
    block_ref: str,
    primary_actor: str,
    resolver_fn,
) -> Iterator[Requirement]:
    req_type, keywords, confidence = classify(text)
    if not req_type:
        return
    secondary = resolver_fn(text, primary_actor)
    notes = ""
    if req_type == "Soft":
        notes = "Soft language — verify with author whether this is a binding requirement."
    yield Requirement(
        order=ctx.next_order(),
        source_file=ctx.source_file,
        heading_trail=ctx.trail_str(),
        section_topic=primary_actor,
        row_ref=row_ref,
        block_ref=block_ref,
        primary_actor=primary_actor,
        secondary_actors=secondary,
        text=text,
        req_type=req_type,
        keywords=keywords,
        confidence=confidence,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse_docx_events(path: Path, resolver_fn) -> List[Event]:
    """Parse a .docx and return an ordered event stream.

    `resolver_fn(text, primary_actor) -> List[str]` is typically
    ActorResolver.resolve bound to an instance.
    """
    doc = Document(str(path))
    ctx = _ParseContext(source_file=path.name, heading_trail=[])
    events: List[Event] = []

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = _paragraph_text(block)
            if not text:
                continue
            level = _heading_level(block)
            if level is not None:
                _update_heading_trail(ctx.heading_trail, level, text)
                events.append(HeadingEvent(level=level, text=text))
                continue
            # Non-heading prose outside of tables is rarely a requirement in
            # this document style, but we still scan it so we don't miss
            # anything.  Primary actor is unknown here.
            for sent in split_sentences(text):
                for req in _emit(
                    sent, ctx,
                    row_ref="Preamble",
                    block_ref="Paragraph",
                    primary_actor="",
                    resolver_fn=resolver_fn,
                ):
                    events.append(RequirementEvent(requirement=req))
        elif isinstance(block, Table):
            ctx.table_index += 1
            is_two_col = len(block.columns) == 2
            for r_idx, row in enumerate(block.rows, start=1):
                cells = row.cells
                if is_two_col and len(cells) >= 2:
                    topic = _cell_text(cells[0])
                    row_ref = f"Table {ctx.table_index}, Row {r_idx}"

                    if _looks_like_section(topic):
                        # Section-style row: emit a structural event plus any
                        # requirements that happen to live inside it.
                        intro = _cell_paragraph_text(cells[1])
                        events.append(
                            SectionRowEvent(title=topic, intro=intro, row_ref=row_ref)
                        )
                        for req in _collect_from_cell(
                            cells[1],
                            ctx,
                            row_ref=row_ref,
                            primary_actor=topic,
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))
                    else:
                        # Actor/topic row.
                        for req in _collect_from_cell(
                            cells[1],
                            ctx,
                            row_ref=row_ref,
                            primary_actor=topic,
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))
                else:
                    # Non-2-col table: scan every cell, no primary actor.
                    for c_idx, cell in enumerate(cells, start=1):
                        row_ref = (
                            f"Table {ctx.table_index}, Row {r_idx}, Col {c_idx}"
                        )
                        for req in _collect_from_cell(
                            cell,
                            ctx,
                            row_ref=row_ref,
                            primary_actor="",
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))
    return events


def parse_docx(path: Path, resolver_fn) -> List[Requirement]:
    """Backward-compatible shim — returns only the requirement rows."""
    return [
        e.requirement
        for e in parse_docx_events(path, resolver_fn)
        if isinstance(e, RequirementEvent)
    ]
