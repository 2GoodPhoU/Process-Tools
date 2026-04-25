"""UML 2.5 XMI emitter.

Output is an `.xmi` file conforming to OMG's UML 2.5 / XMI 2.5.1
interchange specification. Importable into Cameo Systems Modeler,
Enterprise Architect, MagicDraw, Papyrus, and most other UML tools that
speak XMI.

The model produced is a single ``uml:Activity`` containing:

- One ``uml:ActivityPartition`` per actor (the swimlanes)
- ``uml:OpaqueAction`` nodes for activities
- ``uml:DecisionNode`` for gateways
- ``uml:Comment`` for declarative notes
- ``uml:InitialNode`` and ``uml:ActivityFinalNode`` bracketing the flow
- ``uml:ControlFlow`` edges between nodes

This is the "standard UML" deliverable. Nimbus does NOT directly import
XMI (Nimbus's diagram-import paths are Visio .vsd, ARIS XML, and
.cpk packages — see TIB_nimbus_10.6.1_User_Guide.pdf §"Importing"); the
XMI's value is for archival, audit, and downstream UML tooling. The
README documents the practical Nimbus pathway separately.

The XML is hand-built rather than via ``xml.etree.ElementTree`` so the
output stays byte-stable across runs (ET's attribute ordering varies
across Python minor versions).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape as xml_escape, quoteattr

from ..models import Activity, Gateway, Note, Skeleton


# OMG-published namespace URIs for UML 2.5 / XMI 2.5.1.
_XMI_NS = "http://www.omg.org/spec/XMI/20131001"
_UML_NS = "http://www.omg.org/spec/UML/20131001"


def render(skeleton: Skeleton, title: str = "Process Skeleton") -> str:
    """Return a UML 2.5 XMI document as a string."""

    activity_id = "act_1"
    initial_id = "node_initial"
    final_id = "node_final"

    # Stable id → XMI id map. XMI ids must be NCName-valid; we prefix
    # the original DDE stable_id with a kind-tag and replace any chars
    # outside [A-Za-z0-9_-] with underscores so e.g. "REQ-AB12-gw"
    # becomes a valid id "node_REQ-AB12-gw".
    xmi_ids: Dict[str, str] = {}
    for activity in skeleton.activities:
        xmi_ids[activity.stable_id] = "node_" + _safe_id(activity.stable_id)
    for gateway in skeleton.gateways:
        xmi_ids[gateway.stable_id] = "node_" + _safe_id(gateway.stable_id)
    for note in skeleton.notes:
        xmi_ids[note.stable_id] = "comment_" + _safe_id(note.stable_id)

    # Compute swimlane → list of contained node-xmi-ids.
    actor_to_nodes: Dict[str, List[str]] = {actor: [] for actor in skeleton.actors}
    for activity in skeleton.activities:
        actor_to_nodes.setdefault(activity.actor, []).append(xmi_ids[activity.stable_id])
    for gateway in skeleton.gateways:
        actor_to_nodes.setdefault(gateway.actor, []).append(xmi_ids[gateway.stable_id])

    parts: List[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<xmi:XMI xmi:version="2.5" '
        f'xmlns:xmi="{_XMI_NS}" '
        f'xmlns:uml="{_UML_NS}">'
    )
    parts.append(f'  <uml:Model xmi:id="model_1" name={quoteattr(title)}>')
    parts.append(
        f'    <packagedElement xmi:type="uml:Activity" '
        f'xmi:id={quoteattr(activity_id)} name={quoteattr(title)}>'
    )

    # Initial / final nodes.
    parts.append(
        f'      <node xmi:type="uml:InitialNode" xmi:id={quoteattr(initial_id)} '
        f'name="start"/>'
    )
    parts.append(
        f'      <node xmi:type="uml:ActivityFinalNode" xmi:id={quoteattr(final_id)} '
        f'name="end"/>'
    )

    # Action nodes.
    for activity in skeleton.activities:
        attrs = (
            f'xmi:type="uml:OpaqueAction" '
            f'xmi:id={quoteattr(xmi_ids[activity.stable_id])} '
            f'name={quoteattr(activity.label)}'
        )
        if activity.flagged:
            reason = activity.flag_reason or "review needed"
            parts.append(f'      <node {attrs}>')
            parts.append(
                f'        <ownedComment xmi:type="uml:Comment" '
                f'xmi:id={quoteattr(xmi_ids[activity.stable_id] + "_c")}>'
            )
            parts.append(
                f'          <body>{xml_escape("REVIEW — " + reason)}</body>'
            )
            parts.append(f'        </ownedComment>')
            parts.append(f'      </node>')
        else:
            parts.append(f'      <node {attrs}/>')

    # Decision nodes (gateways).
    for gateway in skeleton.gateways:
        parts.append(
            f'      <node xmi:type="uml:DecisionNode" '
            f'xmi:id={quoteattr(xmi_ids[gateway.stable_id])} '
            f'name={quoteattr(gateway.condition)}/>'
        )

    # Control flow edges.
    edge_counter = 0
    # Implicit start → first node, last node → final.
    if skeleton.activities or skeleton.gateways:
        first_node_id = (
            xmi_ids[skeleton.activities[0].stable_id]
            if skeleton.activities
            else xmi_ids[skeleton.gateways[0].stable_id]
        )
        edge_counter += 1
        parts.append(
            f'      <edge xmi:type="uml:ControlFlow" '
            f'xmi:id={quoteattr(f"flow_{edge_counter}")} '
            f'source={quoteattr(initial_id)} '
            f'target={quoteattr(first_node_id)}/>'
        )

    for src, tgt in skeleton.flows:
        if src not in xmi_ids or tgt not in xmi_ids:
            continue
        edge_counter += 1
        parts.append(
            f'      <edge xmi:type="uml:ControlFlow" '
            f'xmi:id={quoteattr(f"flow_{edge_counter}")} '
            f'source={quoteattr(xmi_ids[src])} '
            f'target={quoteattr(xmi_ids[tgt])}/>'
        )

    # Last-node → final edge. "Last node" is the activity with no outgoing
    # flow in the skeleton; falling back to the last in declaration order.
    if skeleton.activities or skeleton.gateways:
        flow_sources = {src for src, _ in skeleton.flows}
        candidates = [
            xmi_ids[a.stable_id]
            for a in skeleton.activities
            if a.stable_id not in flow_sources
        ]
        if not candidates:
            candidates = [xmi_ids[skeleton.activities[-1].stable_id]] if skeleton.activities else []
        for cand in candidates:
            edge_counter += 1
            parts.append(
                f'      <edge xmi:type="uml:ControlFlow" '
                f'xmi:id={quoteattr(f"flow_{edge_counter}")} '
                f'source={quoteattr(cand)} '
                f'target={quoteattr(final_id)}/>'
            )

    # Activity partitions (swimlanes).
    for actor in skeleton.actors:
        node_ids = actor_to_nodes.get(actor, [])
        partition_id = "part_" + _safe_id(actor)
        parts.append(
            f'      <group xmi:type="uml:ActivityPartition" '
            f'xmi:id={quoteattr(partition_id)} name={quoteattr(actor)}>'
        )
        for node_xmi_id in node_ids:
            parts.append(f'        <node xmi:idref={quoteattr(node_xmi_id)}/>')
        parts.append(f'      </group>')

    # Free-floating notes → uml:Comment owned by the activity.
    for note in skeleton.notes:
        comment_id = xmi_ids[note.stable_id]
        body = xml_escape(note.text)
        parts.append(
            f'      <ownedComment xmi:type="uml:Comment" '
            f'xmi:id={quoteattr(comment_id)}>'
        )
        parts.append(f'        <body>{body}</body>')
        parts.append(f'      </ownedComment>')

    parts.append("    </packagedElement>")
    parts.append("  </uml:Model>")
    parts.append("</xmi:XMI>")
    parts.append("")
    return "\n".join(parts)


def write(skeleton: Skeleton, output_path, title: str = "Process Skeleton") -> None:
    Path(output_path).write_text(render(skeleton, title=title), encoding="utf-8")


def _safe_id(stable_id: str) -> str:
    """XMI ids must be NCName-valid: start with a letter or underscore,
    then [A-Za-z0-9-_.] only. ``REQ-AB12`` is valid; ``actor name with
    spaces`` is not — replace bad chars with underscores."""

    if not stable_id:
        return "anon"
    safe = []
    for i, ch in enumerate(stable_id):
        if ch.isalnum() or ch in "-_.":
            safe.append(ch)
        else:
            safe.append("_")
    out = "".join(safe)
    if not (out[0].isalpha() or out[0] == "_"):
        out = "_" + out
    return out
