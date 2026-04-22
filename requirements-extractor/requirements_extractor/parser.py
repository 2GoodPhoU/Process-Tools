"""Walk a .docx document in order and emit a structural event stream.

Document assumptions (matches the user's typical spec format):
  - A header region at the top (title, optional metadata paragraphs).
  - One or more "requirements tables".  By default these are 2-column
    tables; both the column geometry and per-column meaning are
    user-configurable via ``Config.tables``.
  - In each requirements-table row, one column holds a section title /
    topic / actor and the other holds mixed content (paragraphs, bullet
    lists, or nested tables — to arbitrary depth).
  - Standard Word heading styles (Heading 1/2/3) may appear outside of
    tables to group content — these are captured as a "heading trail".

The parser emits an ordered list of events:
  - HeadingEvent          — a top-level heading paragraph
  - SectionRowEvent       — a row whose actor-column text looks like a
                            numbered section header (e.g. "3.1 Auth")
  - RequirementEvent      — a single extracted requirement

Writers that only care about requirements (e.g. the Excel writer) can
filter the stream; writers that need structural context (e.g. the
statement-set CSV exporter) consume it whole.

Recursion
---------
When ``Config.parser.recursive`` is True (the default) the content walker
descends into cells and nested tables of arbitrary depth.  Block-refs
become dotted paths like ``T1R3C2 > T1R2C1 > P1`` so traceability is
preserved even for deeply nested content.  With ``recursive: false`` the
walker matches the original one-level-of-nesting behaviour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Union

from docx import Document
from docx.document import Document as _Document
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from .config import Config
from .detector import KeywordMatcher, split_sentences
from .models import (
    HeadingEvent,
    Requirement,
    RequirementEvent,
    SectionRowEvent,
)

Event = Union[HeadingEvent, SectionRowEvent, RequirementEvent]


# ---------------------------------------------------------------------------
# Parse context — carried through the recursive walker.
# ---------------------------------------------------------------------------


@dataclass
class _ParseContext:
    source_file: str
    config: Config
    matcher: KeywordMatcher
    heading_trail: List[str] = field(default_factory=list)
    table_index: int = 0                    # counts top-level tables
    order_counter: int = 0
    # Latest section-style row title encountered; used to populate the
    # Requirement.section_topic column distinctly from primary_actor.
    current_section_title: str = ""

    def next_order(self) -> int:
        self.order_counter += 1
        return self.order_counter

    def trail_str(self) -> str:
        return " > ".join(h for h in self.heading_trail if h)


# ---------------------------------------------------------------------------
# docx traversal helpers — unchanged shape, tidied.
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


def _cell_text_all(cell: _Cell) -> str:
    """Concatenate visible text in a cell (including nested tables).

    Used when we need a summary string (e.g. the first-column topic).
    Whitespace is collapsed.
    """
    parts: List[str] = []

    def _walk(parent):
        for block in iter_block_items(parent):
            if isinstance(block, Paragraph):
                t = _paragraph_text(block)
                if t:
                    parts.append(t)
            elif isinstance(block, Table):
                for row in block.rows:
                    for subcell in row.cells:
                        _walk(subcell)

    _walk(cell)
    return " ".join(parts).strip()


def _cell_intro_text(cell: _Cell) -> str:
    """Non-heading paragraph text from a cell (used for section intros).

    Unlike ``_cell_text_all`` this does not descend into nested tables —
    section intros are expected to be plain prose.
    """
    parts: List[str] = []
    for block in iter_block_items(cell):
        if isinstance(block, Paragraph):
            level = _heading_level(block)
            if level is not None:
                continue
            text = _paragraph_text(block)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _update_heading_trail(trail: List[str], level: int, text: str) -> None:
    """Keep the trail at most ``level`` deep, then append the new heading."""
    while len(trail) >= level:
        trail.pop()
    trail.append(text)


# ---------------------------------------------------------------------------
# The recursive walker.
# ---------------------------------------------------------------------------


def _emit_candidate(
    text: str,
    ctx: _ParseContext,
    *,
    row_ref: str,
    block_ref: str,
    primary_actor: str,
) -> Optional[Requirement]:
    """Build a Requirement iff ``text`` passes detection + config filters.

    Returns None when the sentence should be dropped (not a requirement,
    filtered by ``content.skip_if_starts_with`` / ``skip_pattern``, or
    missing a required primary actor).
    """
    # Content-level filter: skip by prefix / pattern.
    if ctx.config.content.should_skip(text):
        return None

    req_type, keywords, confidence = ctx.matcher.classify(text)
    if not req_type:
        return None

    # Optional "must have an actor to count" filter.
    if ctx.config.content.require_primary_actor and not (primary_actor or "").strip():
        return None

    notes = ""
    if req_type == "Soft":
        notes = "Soft language — verify with author whether this is a binding requirement."

    polarity = "Negative" if ctx.matcher.is_negative(text) else "Positive"

    return Requirement(
        order=ctx.next_order(),
        source_file=ctx.source_file,
        heading_trail=ctx.trail_str(),
        section_topic=ctx.current_section_title,
        row_ref=row_ref,
        block_ref=block_ref,
        primary_actor=primary_actor,
        secondary_actors=[],            # filled in by the resolver below
        text=text,
        req_type=req_type,
        keywords=keywords,
        confidence=confidence,
        notes=notes,
        polarity=polarity,
    )


def _walk_content(
    parent,
    ctx: _ParseContext,
    *,
    row_ref: str,
    primary_actor: str,
    resolver_fn,
    ref_prefix: str = "",
    recursive: Optional[bool] = None,
) -> Iterator[Requirement]:
    """Walk the paragraph/table children of ``parent`` and yield Requirements.

    ``parent`` is typically the content-column cell from a requirements
    table, but this function also handles nested tables (recursively) and
    is reused for preamble prose.  ``ref_prefix`` is the dotted-path string
    we prepend to per-block refs so nested items stay traceable.
    """
    if recursive is None:
        recursive = ctx.config.parser.recursive

    paragraph_idx = 0
    bullet_idx = 0
    nested_table_idx = 0

    def _push_ref(tail: str) -> str:
        return f"{ref_prefix} > {tail}" if ref_prefix else tail

    for block in iter_block_items(parent):
        if isinstance(block, Paragraph):
            text = _paragraph_text(block)
            if not text:
                continue
            # Sub-headings inside a cell update the trail so nested content
            # inherits that context in its output.
            level = _heading_level(block)
            if level is not None:
                _update_heading_trail(ctx.heading_trail, level, text)
                continue
            if _is_bullet(block):
                bullet_idx += 1
                br = _push_ref(f"Bullet {bullet_idx}")
                req = _emit_candidate(
                    text, ctx,
                    row_ref=row_ref, block_ref=br, primary_actor=primary_actor,
                )
                if req is not None:
                    req.secondary_actors = resolver_fn(text, primary_actor)
                    yield req
            else:
                paragraph_idx += 1
                br = _push_ref(f"Paragraph {paragraph_idx}")
                for sent in split_sentences(text):
                    req = _emit_candidate(
                        sent, ctx,
                        row_ref=row_ref, block_ref=br, primary_actor=primary_actor,
                    )
                    if req is not None:
                        req.secondary_actors = resolver_fn(sent, primary_actor)
                        yield req
        elif isinstance(block, Table):
            nested_table_idx += 1
            table_tag = f"Nested Table {nested_table_idx}"
            if recursive:
                # True recursion: walk every nested cell with the same
                # walker.  Block ref becomes a dotted path so traceability
                # is preserved even at depth.
                for r_idx, nrow in enumerate(block.rows, start=1):
                    for c_idx, ncell in enumerate(nrow.cells, start=1):
                        nested_prefix = _push_ref(f"{table_tag} R{r_idx}C{c_idx}")
                        yield from _walk_content(
                            ncell, ctx,
                            row_ref=row_ref,
                            primary_actor=primary_actor,
                            resolver_fn=resolver_fn,
                            ref_prefix=nested_prefix,
                            recursive=True,
                        )
            else:
                # Legacy one-level behaviour: flatten each nested cell's
                # visible text and split into sentences — no further
                # descent.
                for r_idx, nrow in enumerate(block.rows, start=1):
                    for c_idx, ncell in enumerate(nrow.cells, start=1):
                        cell_text = _cell_text_all(ncell)
                        if not cell_text:
                            continue
                        br = _push_ref(f"{table_tag} R{r_idx}C{c_idx}")
                        for sent in split_sentences(cell_text):
                            req = _emit_candidate(
                                sent, ctx,
                                row_ref=row_ref, block_ref=br,
                                primary_actor=primary_actor,
                            )
                            if req is not None:
                                req.secondary_actors = resolver_fn(sent, primary_actor)
                                yield req


# ---------------------------------------------------------------------------
# Top-level entry points.
# ---------------------------------------------------------------------------


def parse_docx_events(
    path: Path,
    resolver_fn,
    *,
    config: Optional[Config] = None,
) -> List[Event]:
    """Parse a .docx and return an ordered event stream.

    ``resolver_fn(text, primary_actor) -> List[str]`` is typically
    ``ActorResolver.resolve`` bound to an instance.  ``config`` tweaks what
    counts as a requirements table, which sections to skip, which
    keywords to use, etc.  When omitted, built-in defaults apply.
    """
    cfg = config or Config.defaults()
    matcher = KeywordMatcher.from_config(cfg.keywords)

    path = Path(path)
    doc = Document(str(path))
    ctx = _ParseContext(
        source_file=path.name,
        config=cfg,
        matcher=matcher,
    )
    events: List[Event] = []
    section_re = cfg.tables.section_re()

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
            # Preamble / inter-table prose.  Scan for requirements but use an
            # empty primary actor — the content filter can drop everything
            # here if the user prefers strict mode.
            for sent in split_sentences(text):
                req = _emit_candidate(
                    sent, ctx,
                    row_ref="Preamble",
                    block_ref="Paragraph",
                    primary_actor="",
                )
                if req is not None:
                    req.secondary_actors = resolver_fn(sent, "")
                    events.append(RequirementEvent(requirement=req))
            continue

        if isinstance(block, Table):
            ctx.table_index += 1

            # User-driven whole-table skip.
            if ctx.table_index in cfg.skip_sections.table_indices:
                continue

            num_cols = len(block.columns)
            is_req_table = cfg.tables.is_requirement_table(num_cols)
            actor_idx = cfg.tables.actor_column - 1      # to 0-based
            content_idx = cfg.tables.content_column - 1

            for r_idx, row in enumerate(block.rows, start=1):
                cells = row.cells
                row_ref = f"Table {ctx.table_index}, Row {r_idx}"

                if is_req_table and len(cells) > max(actor_idx, content_idx):
                    topic = _cell_text_all(cells[actor_idx])
                    content_cell = cells[content_idx]

                    # Skip this row when it matches a user-configured title.
                    if cfg.skip_sections.matches_title(topic):
                        continue

                    if section_re.match(topic or ""):
                        # Section-style row: emit a structural event, set
                        # the current section title, then walk content for
                        # any requirements found directly inside it.
                        intro = _cell_intro_text(content_cell)
                        ctx.current_section_title = topic
                        events.append(
                            SectionRowEvent(
                                title=topic, intro=intro, row_ref=row_ref,
                            )
                        )
                        # Requirements inside a section-style row have no
                        # obvious primary actor — use "" so they can still
                        # be filtered out by require_primary_actor if the
                        # user wants strict output.
                        for req in _walk_content(
                            content_cell, ctx,
                            row_ref=row_ref,
                            primary_actor="",
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))
                    else:
                        # Actor/topic row.
                        for req in _walk_content(
                            content_cell, ctx,
                            row_ref=row_ref,
                            primary_actor=topic,
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))
                else:
                    # Not a requirements table (wrong column count or user
                    # asked us to treat this table as data-only).  Walk
                    # every cell anyway so nothing gets silently dropped,
                    # but with no primary actor.
                    for c_idx, cell in enumerate(cells, start=1):
                        for req in _walk_content(
                            cell, ctx,
                            row_ref=f"{row_ref}, Col {c_idx}",
                            primary_actor="",
                            resolver_fn=resolver_fn,
                        ):
                            events.append(RequirementEvent(requirement=req))

    return events


def parse_docx(
    path: Path,
    resolver_fn,
    *,
    config: Optional[Config] = None,
) -> List[Requirement]:
    """Backward-compatible shim — returns only the requirement rows."""
    return [
        e.requirement
        for e in parse_docx_events(path, resolver_fn, config=config)
        if isinstance(e, RequirementEvent)
    ]
