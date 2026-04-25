"""Dataclasses shared across loader, matchers, combiner, and writer.

Both sides of the matrix (contract requirements and procedure clauses) come
from the same DDE xlsx shape, so they share a single ``DDERow`` data carrier
with a ``side`` discriminator. Keeping a single shape — rather than two
near-identical dataclasses — means matchers can stay symmetric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DDERow:
    """One row out of a DDE xlsx workbook.

    Field names mirror the DDE writer's column headers (lowercased,
    underscored). All fields except ``stable_id`` and ``text`` are optional
    because hand-edited xlsx may have gaps; matchers must tolerate ``None``.
    """

    stable_id: str
    text: str
    source_file: Optional[str] = None
    heading_trail: Optional[str] = None
    section: Optional[str] = None
    row_ref: Optional[str] = None
    block_ref: Optional[str] = None
    primary_actor: Optional[str] = None
    secondary_actors: Optional[str] = None
    req_type: Optional[str] = None
    polarity: Optional[str] = None
    keywords: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    context: Optional[str] = None
    # Discriminator: "contract" or "procedure". Set by the loader.
    side: str = "contract"


@dataclass
class Match:
    """One matcher's vote that a contract requirement maps to a procedure clause.

    ``score`` is matcher-defined but normalised to [0.0, 1.0] so the combiner
    can blend results across matchers. ``evidence`` is a short human-readable
    string explaining *why* the match fired (e.g. the regex hit, the
    overlapping tokens, the line in the manual mapping file). The combiner
    concatenates evidence strings so a reviewer sees every signal that voted
    for the link.
    """

    contract_id: str
    procedure_id: str
    matcher: str
    score: float
    evidence: str = ""


@dataclass
class CombinedMatch:
    """Per-pair aggregate. One row per (contract_id, procedure_id) where at
    least one matcher fired."""

    contract_id: str
    procedure_id: str
    score: float
    matchers: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)


@dataclass
class MatrixData:
    """The complete dataset assembled before writing the output xlsx."""

    contract_rows: List[DDERow]
    procedure_rows: List[DDERow]
    combined: Dict[Tuple[str, str], CombinedMatch] = field(default_factory=dict)

    def get(self, contract_id: str, procedure_id: str) -> Optional[CombinedMatch]:
        return self.combined.get((contract_id, procedure_id))
