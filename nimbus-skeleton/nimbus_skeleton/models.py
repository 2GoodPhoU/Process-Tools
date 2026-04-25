"""Skeleton-domain dataclasses.

The full pipeline is::

    DDE xlsx  ─►  loader  ─►  list[DDERow]  ─►  builder  ─►  Skeleton
                                                              │
                                                              ├─►  PlantUML emitter
                                                              ├─►  XMI emitter
                                                              └─►  review-side-car xlsx

``Skeleton`` is the pivot type — both emitters consume it and don't talk
to DDE rows directly. Keeping the pivot small means a third emitter
(BPMN, Mermaid, native Nimbus format if/when we get one) is a one-file
addition rather than a refactor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class DDERow:
    """One row out of a DDE xlsx workbook (subset of fields the skeleton
    builder cares about)."""

    stable_id: str
    text: str
    source_file: Optional[str] = None
    heading_trail: Optional[str] = None
    section: Optional[str] = None
    row_ref: Optional[str] = None
    primary_actor: Optional[str] = None
    secondary_actors: Optional[str] = None
    polarity: Optional[str] = None
    req_type: Optional[str] = None


@dataclass
class Activity:
    """One action node in an actor's swimlane.

    ``stable_id`` ties the activity back to its source DDE row so
    reviewers can audit *why* a node was generated. ``flagged`` is True
    when the classifier wasn't confident about turning the requirement
    into an activity — the review-side-car xlsx surfaces every flagged
    activity for human judgment."""

    stable_id: str
    label: str
    actor: str
    flagged: bool = False
    flag_reason: Optional[str] = None


@dataclass
class Gateway:
    """Decision node, emitted when a requirement contains conditional
    language. The condition is preserved as the gateway's label; the
    builder doesn't try to be clever about branch targets — that's
    explicitly what humans review afterward."""

    stable_id: str
    condition: str
    actor: str


@dataclass
class Note:
    """Free-text annotation for declarative / non-actionable
    requirements. Notes attach to no swimlane — they're a margin
    annotation in PlantUML and a Comment element in XMI."""

    stable_id: str
    text: str
    actor: Optional[str] = None


@dataclass
class Skeleton:
    """The entire model — actors, ordered nodes per actor, and a flat
    sequence-flow list."""

    actors: List[str] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    gateways: List[Gateway] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    # Flow edges: (source_stable_id, target_stable_id). Source order
    # follows DDE xlsx row order; the builder doesn't try to detect
    # back-edges or loops.
    flows: List[tuple[str, str]] = field(default_factory=list)
    # Stable id → "activity" / "gateway" / "note" lookup, used by
    # emitters to resolve flow endpoints to node types.
    node_kind: dict[str, str] = field(default_factory=dict)

    def add_activity(self, activity: Activity) -> None:
        if activity.actor not in self.actors:
            self.actors.append(activity.actor)
        self.activities.append(activity)
        self.node_kind[activity.stable_id] = "activity"

    def add_gateway(self, gateway: Gateway) -> None:
        if gateway.actor not in self.actors:
            self.actors.append(gateway.actor)
        self.gateways.append(gateway)
        self.node_kind[gateway.stable_id] = "gateway"

    def add_note(self, note: Note) -> None:
        if note.actor and note.actor not in self.actors:
            self.actors.append(note.actor)
        self.notes.append(note)
        self.node_kind[note.stable_id] = "note"

    def review_records(self) -> List[Activity]:
        """All activities with ``flagged=True``, sorted for the side-car."""

        return [a for a in self.activities if a.flagged]
