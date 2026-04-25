"""BPMN 2.0 XML emitter.

Output is a ``.bpmn`` (XML) file conforming to OMG's BPMN 2.0 interchange
specification (formal/2011-01-03). Importable into Camunda Modeler,
bpmn.io, Signavio, Bizagi, ARIS, and most tools that speak BPMN 2.0.

Why we have this on top of the existing Nimbus / XMI / Visio emitters:
TIBCO Nimbus's on-premise product retired Sept 1, 2025 — see
``research/2026-04-25-stack-alternatives-survey.md``. BPMN 2.0 is the
de-facto open process-modelling interchange and the migration path
recommended by that survey. Adding this emitter takes the in-memory
``Skeleton`` (already structured around primitives BPMN 2.0 covers
natively — actors as swimlanes, activities as tasks, gateways as
decisions, ordered sequence flows, free-text notes) and serialises it
without remodelling.

Model produced is a single ``bpmn:process`` containing:

- One ``bpmn:laneSet`` with one ``bpmn:lane`` per actor (the swimlanes)
- ``bpmn:task`` nodes for activities
- ``bpmn:exclusiveGateway`` for gateways (Skeleton stores a single
  condition per gateway — XOR is the closest 1:1)
- ``bpmn:textAnnotation`` + ``bpmn:association`` for declarative notes
- ``bpmn:startEvent`` and ``bpmn:endEvent`` bracketing the flow
- ``bpmn:sequenceFlow`` edges between nodes

Diagram-interchange (BPMNDI) graphical layout is intentionally NOT
emitted. Modern BPMN tools (Camunda Modeler, bpmn.io) auto-layout on
import, and shipping a hand-rolled DI section means picking pixel
coordinates that no tool would agree with anyway.

The XML is hand-built rather than via ``xml.etree.ElementTree`` to match
the XMI emitter's style and keep output byte-stable across runs (ET's
attribute ordering varies across Python minor versions).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape as xml_escape, quoteattr

from ..models import Activity, Gateway, Note, Skeleton


# OMG-published namespace URIs for BPMN 2.0.
_BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
_DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
_DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def render(skeleton: Skeleton, title: str = "Process Skeleton") -> str:
    """Return a BPMN 2.0 XML document as a string."""

    process_id = "Process_1"
    definitions_id = "Definitions_1"
    collab_id = "Collaboration_1"
    start_id = "StartEvent_1"
    end_id = "EndEvent_1"

    # Stable id → BPMN id map. BPMN ids must be xsd:ID-valid (NCName);
    # mirror the XMI emitter's id strategy. Prefix by kind so the id
    # makes sense in modeller UIs.
    bpmn_ids: Dict[str, str] = {}
    for activity in skeleton.activities:
        bpmn_ids[activity.stable_id] = "Task_" + _safe_id(activity.stable_id)
    for gateway in skeleton.gateways:
        bpmn_ids[gateway.stable_id] = "Gateway_" + _safe_id(gateway.stable_id)
    for note in skeleton.notes:
        bpmn_ids[note.stable_id] = "TextAnn_" + _safe_id(note.stable_id)

    # Compute lane → contained flowNodeRefs.
    actor_to_nodes: Dict[str, List[str]] = {actor: [] for actor in skeleton.actors}
    for activity in skeleton.activities:
        actor_to_nodes.setdefault(activity.actor, []).append(bpmn_ids[activity.stable_id])
    for gateway in skeleton.gateways:
        actor_to_nodes.setdefault(gateway.actor, []).append(bpmn_ids[gateway.stable_id])

    # Collect sequence-flow records first so each node can declare its
    # incoming/outgoing children — Camunda Modeler is strict about this.
    sequence_flows: List[tuple[str, str, str]] = []  # (flow_id, src_bpmn_id, tgt_bpmn_id)
    flow_counter = 0
    incoming_per_node: Dict[str, List[str]] = {}
    outgoing_per_node: Dict[str, List[str]] = {}

    def _add_flow(src_bid: str, tgt_bid: str) -> None:
        nonlocal flow_counter
        flow_counter += 1
        fid = f"SequenceFlow_{flow_counter}"
        sequence_flows.append((fid, src_bid, tgt_bid))
        outgoing_per_node.setdefault(src_bid, []).append(fid)
        incoming_per_node.setdefault(tgt_bid, []).append(fid)

    # Implicit start → first node.
    if skeleton.activities or skeleton.gateways:
        first_node_bid = (
            bpmn_ids[skeleton.activities[0].stable_id]
            if skeleton.activities
            else bpmn_ids[skeleton.gateways[0].stable_id]
        )
        _add_flow(start_id, first_node_bid)

    for src, tgt in skeleton.flows:
        if src not in bpmn_ids or tgt not in bpmn_ids:
            continue
        _add_flow(bpmn_ids[src], bpmn_ids[tgt])

    # Last-node → end. "Last node" mirrors the XMI emitter: any activity
    # with no outgoing flow in the skeleton.
    if skeleton.activities or skeleton.gateways:
        flow_sources = {src for src, _ in skeleton.flows}
        candidates = [
            bpmn_ids[a.stable_id]
            for a in skeleton.activities
            if a.stable_id not in flow_sources
        ]
        if not candidates and skeleton.activities:
            candidates = [bpmn_ids[skeleton.activities[-1].stable_id]]
        for cand in candidates:
            _add_flow(cand, end_id)

    parts: List[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<bpmn:definitions '
        f'xmlns:bpmn="{_BPMN_NS}" '
        f'xmlns:bpmndi="{_BPMNDI_NS}" '
        f'xmlns:dc="{_DC_NS}" '
        f'xmlns:di="{_DI_NS}" '
        f'xmlns:xsi="{_XSI_NS}" '
        f'id={quoteattr(definitions_id)} '
        f'targetNamespace="http://nimbus-skeleton/bpmn" '
        f'exporter="nimbus-skeleton" exporterVersion="1.0">'
    )

    # Collaboration with a single participant pointing at our process —
    # gives modellers a pool wrapper around the lanes by default.
    parts.append(
        f'  <bpmn:collaboration id={quoteattr(collab_id)}>'
    )
    parts.append(
        f'    <bpmn:participant id="Participant_1" '
        f'name={quoteattr(title)} processRef={quoteattr(process_id)}/>'
    )
    parts.append('  </bpmn:collaboration>')

    parts.append(
        f'  <bpmn:process id={quoteattr(process_id)} '
        f'name={quoteattr(title)} isExecutable="false">'
    )

    # Lane set — one lane per actor.
    if skeleton.actors:
        parts.append('    <bpmn:laneSet id="LaneSet_1">')
        for i, actor in enumerate(skeleton.actors, 1):
            lane_id = f"Lane_{i}_" + _safe_id(actor)
            parts.append(
                f'      <bpmn:lane id={quoteattr(lane_id)} '
                f'name={quoteattr(actor)}>'
            )
            for node_bid in actor_to_nodes.get(actor, []):
                parts.append(
                    f'        <bpmn:flowNodeRef>{xml_escape(node_bid)}</bpmn:flowNodeRef>'
                )
            parts.append('      </bpmn:lane>')
        parts.append('    </bpmn:laneSet>')

    # Start event.
    parts.append(f'    <bpmn:startEvent id={quoteattr(start_id)} name="start">')
    for fid in outgoing_per_node.get(start_id, []):
        parts.append(f'      <bpmn:outgoing>{xml_escape(fid)}</bpmn:outgoing>')
    parts.append('    </bpmn:startEvent>')

    # Tasks (activities).
    for activity in skeleton.activities:
        bid = bpmn_ids[activity.stable_id]
        parts.append(
            f'    <bpmn:task id={quoteattr(bid)} '
            f'name={quoteattr(activity.label)}>'
        )
        if activity.flagged:
            reason = activity.flag_reason or "review needed"
            parts.append(
                f'      <bpmn:documentation>'
                f'{xml_escape("REVIEW — " + reason)}'
                f'</bpmn:documentation>'
            )
        for fid in incoming_per_node.get(bid, []):
            parts.append(f'      <bpmn:incoming>{xml_escape(fid)}</bpmn:incoming>')
        for fid in outgoing_per_node.get(bid, []):
            parts.append(f'      <bpmn:outgoing>{xml_escape(fid)}</bpmn:outgoing>')
        parts.append('    </bpmn:task>')

    # Gateways. Skeleton's Gateway carries one condition string — closest
    # BPMN 2.0 1:1 is exclusive (XOR). Parallel/inclusive gateways would
    # need additional metadata the in-memory model doesn't carry today;
    # if/when Skeleton learns gateway-kind, expand this block.
    for gateway in skeleton.gateways:
        bid = bpmn_ids[gateway.stable_id]
        parts.append(
            f'    <bpmn:exclusiveGateway id={quoteattr(bid)} '
            f'name={quoteattr(gateway.condition)}>'
        )
        for fid in incoming_per_node.get(bid, []):
            parts.append(f'      <bpmn:incoming>{xml_escape(fid)}</bpmn:incoming>')
        for fid in outgoing_per_node.get(bid, []):
            parts.append(f'      <bpmn:outgoing>{xml_escape(fid)}</bpmn:outgoing>')
        parts.append('    </bpmn:exclusiveGateway>')

    # End event.
    parts.append(f'    <bpmn:endEvent id={quoteattr(end_id)} name="end">')
    for fid in incoming_per_node.get(end_id, []):
        parts.append(f'      <bpmn:incoming>{xml_escape(fid)}</bpmn:incoming>')
    parts.append('    </bpmn:endEvent>')

    # Sequence flows.
    for fid, src_bid, tgt_bid in sequence_flows:
        parts.append(
            f'    <bpmn:sequenceFlow id={quoteattr(fid)} '
            f'sourceRef={quoteattr(src_bid)} '
            f'targetRef={quoteattr(tgt_bid)}/>'
        )

    # Text annotations (notes) + associations to first activity if any.
    # Mirrors the XMI emitter's strategy: anchor every note to the first
    # activity in builder-emission order (or omit association if there
    # are no activities, in which case the note still appears in-canvas).
    first_activity_bid: str | None = (
        bpmn_ids[skeleton.activities[0].stable_id] if skeleton.activities else None
    )
    assoc_counter = 0
    for note in skeleton.notes:
        ann_id = bpmn_ids[note.stable_id]
        parts.append(
            f'    <bpmn:textAnnotation id={quoteattr(ann_id)}>'
        )
        parts.append(
            f'      <bpmn:text>{xml_escape(note.text)}</bpmn:text>'
        )
        parts.append('    </bpmn:textAnnotation>')
        if first_activity_bid is not None:
            assoc_counter += 1
            assoc_id = f"Association_{assoc_counter}"
            parts.append(
                f'    <bpmn:association id={quoteattr(assoc_id)} '
                f'sourceRef={quoteattr(first_activity_bid)} '
                f'targetRef={quoteattr(ann_id)}/>'
            )

    parts.append('  </bpmn:process>')
    parts.append('</bpmn:definitions>')
    parts.append("")
    return "\n".join(parts)


def write(skeleton: Skeleton, output_path, title: str = "Process Skeleton") -> None:
    Path(output_path).write_text(render(skeleton, title=title), encoding="utf-8")


def _safe_id(stable_id: str) -> str:
    """BPMN ids must be xsd:ID-valid (an NCName): start with a letter or
    underscore, then [A-Za-z0-9-_.] only. ``REQ-AB12`` is valid;
    ``actor name with spaces`` is not — replace bad chars with
    underscores. Empty input yields ``anon`` so we never emit an empty
    id (which would be a hard schema-validation failure)."""

    if not stable_id:
        return "anon"
    safe = []
    for ch in stable_id:
        if ch.isalnum() or ch in "-_.":
            safe.append(ch)
        else:
            safe.append("_")
    out = "".join(safe)
    if not (out[0].isalpha() or out[0] == "_"):
        out = "_" + out
    return out
