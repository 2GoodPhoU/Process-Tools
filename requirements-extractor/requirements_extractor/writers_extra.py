"""Additional output writers: JSON and Markdown.

REVIEW §3.10 — the Excel workbook is the primary deliverable, but
scripted consumers (CI checks, downstream tooling) benefit from a JSON
feed, and lightweight code-review PRs benefit from a compact Markdown
table.  ReqIF is explicitly out of scope here — it's a domain-specific
schema that warrants its own writer module.

Both writers accept the same ``Sequence[Requirement]`` that
:func:`requirements_extractor.writer.write_requirements` takes, produce
deterministic byte-for-byte output given the same input (for diffable
CI artefacts), and do not depend on openpyxl.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .models import Requirement


# ---------------------------------------------------------------------------
# JSON writer
# ---------------------------------------------------------------------------


def requirement_to_dict(req: Requirement) -> dict:
    """Return a JSON-serialisable dict for one requirement.

    Uses :func:`dataclasses.asdict` so any fields added to
    :class:`Requirement` later show up automatically — this matters for
    the stable_id, polarity, and confidence fields that were added over
    time.  The two string-joined conveniences (``secondary_actors_str``
    and ``keywords_str``) are NOT included — JSON consumers can rebuild
    them from the structured lists if they want.
    """
    return asdict(req)


def write_requirements_json(
    requirements: Sequence[Requirement],
    output_path: Path,
    *,
    indent: int = 2,
) -> Path:
    """Write a flat JSON array of requirement objects to ``output_path``.

    Top-level is a list — one element per requirement — so the file
    streams cleanly and every downstream consumer agrees on the shape.
    ``indent`` defaults to 2 so the file is human-readable; pass
    ``indent=None`` for a compact one-line form used by some CI tools.

    Deterministic: the same requirements list produces byte-identical
    output across runs.  That property is what makes this writer useful
    for CI diff checks.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [requirement_to_dict(r) for r in requirements]
    # ``sort_keys=False`` preserves the dataclass field order, which
    # mirrors the order in ``Requirement``'s declaration and keeps the
    # file readable for humans.
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )
    return output_path


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------


#: Columns included in the Markdown table, keyed by header text →
#: extractor-attribute name.  A subset of the xlsx columns — the ones
#: most useful in a pull-request review.  Full fidelity is via the
#: JSON or Excel outputs; Markdown is for legibility.
_MD_COLUMNS = (
    ("#", "order"),
    ("ID", "stable_id"),
    ("Source", "source_file"),
    ("Actor", "primary_actor"),
    ("Requirement", "text"),
    ("Type", "req_type"),
    ("Polarity", "polarity"),
    ("Confidence", "confidence"),
    ("Notes", "notes"),
)


def _escape_md_cell(value: object) -> str:
    """Make a value safe inside a Markdown table cell.

    Pipes and newlines would otherwise break the table; we replace each
    newline with ``<br>`` (rendered by most Markdown dialects) and
    escape pipes with a backslash.  Everything else passes through.
    """
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\\", "\\\\")
    s = s.replace("|", "\\|")
    s = s.replace("\r\n", "\n").replace("\n", "<br>")
    return s


def write_requirements_md(
    requirements: Sequence[Requirement],
    output_path: Path,
    *,
    title: str = "Extracted requirements",
) -> Path:
    """Write a compact Markdown table of requirements to ``output_path``.

    Leads with a single H1 title, a one-line summary of counts, and a
    pipe-delimited table.  Header columns match the :data:`_MD_COLUMNS`
    selection.  Empty requirements lists produce a valid file with a
    "No requirements captured." note — the writer never emits a naked
    header with no body rows (which renders oddly in most viewers).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    if not requirements:
        lines.append("_No requirements captured._")
        lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    hard = sum(1 for r in requirements if r.req_type == "Hard")
    soft = sum(1 for r in requirements if r.req_type == "Soft")
    neg = sum(1 for r in requirements if r.polarity == "Negative")
    lines.append(
        f"**{len(requirements)}** requirements — {hard} Hard, "
        f"{soft} Soft, {neg} Negative."
    )
    lines.append("")

    # Header + separator.
    headers = [h for h, _ in _MD_COLUMNS]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for req in requirements:
        row = []
        for _, attr in _MD_COLUMNS:
            row.append(_escape_md_cell(getattr(req, attr, "")))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
