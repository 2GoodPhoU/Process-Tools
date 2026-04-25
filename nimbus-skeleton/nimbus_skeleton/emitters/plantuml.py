"""PlantUML activity-diagram emitter.

Output is a ``.puml`` text file using PlantUML's modern activity-diagram
syntax (``|swimlane|`` notation, ``:label;`` for actions, ``if/endif``
for gateways, ``note right`` for annotations).

PlantUML can be rendered server-side via plantuml.com, locally via the
``plantuml`` CLI, or inline in many editors. The output is deliberately
simple — no styling, no colours — so reviewers can paste it into any
PlantUML environment.
"""

from __future__ import annotations

from typing import List

from ..models import Activity, Gateway, Note, Skeleton


def render(skeleton: Skeleton, title: str = "Process Skeleton") -> str:
    """Return a PlantUML activity-diagram source string."""

    lines: List[str] = []
    lines.append("@startuml")
    lines.append(f"title {title}")
    lines.append("start")

    # Walk the activities in order, switching swimlanes as needed and
    # inserting gateway / note blocks where appropriate.
    current_actor: str | None = None
    notes_per_node: dict[str, list[str]] = _index_notes_by_following_node(skeleton)
    gateway_for_activity = {
        flow_target: skeleton.gateways[i]
        for i, gw in enumerate(skeleton.gateways)
        for src, flow_target in skeleton.flows
        if src == gw.stable_id and skeleton.node_kind.get(flow_target) == "activity"
    }
    # The above mapping is only used to know "this activity is preceded
    # by this gateway" so we render the gateway *before* the activity.

    for activity in skeleton.activities:
        if activity.actor != current_actor:
            lines.append(f"|{_escape(activity.actor)}|")
            current_actor = activity.actor

        gw = gateway_for_activity.get(activity.stable_id)
        if gw is not None:
            lines.append(f"if ({_escape(gw.condition)}) then (yes)")
            lines.append(f"  :{_escape(activity.label)};")
            if activity.flagged:
                lines.append(
                    f"  note right: REVIEW — {_escape(activity.flag_reason or '')}"
                )
            lines.append("else (no)")
            lines.append("  :(branch — define manually);")
            lines.append("endif")
        else:
            lines.append(f":{_escape(activity.label)};")
            if activity.flagged:
                lines.append(
                    f"note right: REVIEW — {_escape(activity.flag_reason or '')}"
                )

        # Attached notes (declarative requirements that landed near this
        # activity in document order).
        for note_text in notes_per_node.get(activity.stable_id, []):
            lines.append(f"note right: {_escape(note_text)}")

    lines.append("stop")

    # Trailing notes that didn't anchor to a specific activity (because
    # there were no activities after them).
    if skeleton.notes and not skeleton.activities:
        for note in skeleton.notes:
            lines.append(f"note right: {_escape(note.text)}")

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def write(skeleton: Skeleton, output_path, title: str = "Process Skeleton") -> None:
    from pathlib import Path

    Path(output_path).write_text(render(skeleton, title=title), encoding="utf-8")


def _escape(text: str) -> str:
    """Make a label safe for PlantUML — no unescaped pipes or semicolons."""

    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace(";", ",")
        .replace("\n", " ")
    )


def _index_notes_by_following_node(skeleton: Skeleton) -> dict[str, list[str]]:
    """Notes attach to whichever activity comes after them in the
    builder's emission order. This is approximate — a 'real' tool would
    let the reviewer reposition them — but it surfaces declarative
    requirements next to the action they explain, which is usually
    where the reader expects them."""

    out: dict[str, list[str]] = {}
    if not skeleton.notes or not skeleton.activities:
        return out
    # Map note → first activity whose stable_id appears later in the
    # builder's input order. Because we don't carry document order
    # through, fall back to attaching all notes to the first activity.
    first_activity_id = skeleton.activities[0].stable_id
    out.setdefault(first_activity_id, []).extend(n.text for n in skeleton.notes)
    return out
