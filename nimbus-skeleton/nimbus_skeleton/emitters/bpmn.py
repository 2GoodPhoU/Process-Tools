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

Diagram-interchange (BPMNDI) graphical layout IS emitted — every shape
gets a ``bpmndi:BPMNShape`` with ``dc:Bounds`` and every flow gets a
``bpmndi:BPMNEdge`` with ``di:waypoint`` entries. The reference renderer
bpmn.io refuses to display a BPMN file that lacks a ``BPMNDiagram``
("no diagram to display"); recent Camunda Modeler versions behave the
same way. The earlier assumption that modern tools auto-layout DI-less
BPMN was disproven during S3 modeler validation on 2026-04-26 — see
``DECISIONS.md`` "BPMN DI generation" entry.

Layout is a deterministic horizontal-swimlane grid: pool wraps lanes
top-to-bottom in actor-insertion order, nodes within a lane spread
left-to-right by longest-path rank from the start event. Coordinates
are pixel integers so the output is byte-identical across runs (a
property the byte-stability test pins). The numbers won't match any
modeler's preferred layout — every modeler users open it in will
re-tidy on first save — but the diagram renders cleanly out of the box
and conveys the right shape on first import.

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


# Layout constants — pixels, integers (so the rendered XML is byte-stable
# and not vulnerable to floating-point format differences across Python
# versions). Numbers chosen for legible default rendering in bpmn.io and
# Camunda Modeler; nothing magic about them.
_POOL_X = 100               # pool top-left
_POOL_Y = 50
_PARTICIPANT_LABEL_W = 30   # left strip inside the pool reserved for the rotated participant name
_LANE_LABEL_W = 30          # left strip inside each lane reserved for the rotated lane name
_LANE_HEIGHT = 200
_LEFT_GUTTER = 40           # space inside the lane area before the first node column
_RIGHT_GUTTER = 60          # space after the last node column before the pool right edge
_COLUMN_WIDTH = 140         # per-rank horizontal slot (TASK_WIDTH 100 + gap 40)
_TASK_WIDTH = 100
_TASK_HEIGHT = 80
_EVENT_SIZE = 36            # start / end events are squares (rendered as circles)
_GATEWAY_SIZE = 50          # gateways are squares (rendered as diamonds)
_NOTE_WIDTH = 200
_NOTE_HEIGHT = 60
_NOTE_GAP_BELOW_POOL = 50
_NOTE_GAP_X = 40


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
    first_activity_bid = (
        bpmn_ids[skeleton.activities[0].stable_id] if skeleton.activities else None
    )
    assoc_counter = 0
    associations = []  # (assoc_id, src_bid, tgt_bid) — re-used for DI
    for note in skeleton.notes:
        ann_id = bpmn_ids[note.stable_id]
        parts.append(f'    <bpmn:textAnnotation id={quoteattr(ann_id)}>')
        parts.append(f'      <bpmn:text>{xml_escape(note.text)}</bpmn:text>')
        parts.append('    </bpmn:textAnnotation>')
        if first_activity_bid is not None:
            assoc_counter += 1
            assoc_id = f"Association_{assoc_counter}"
            associations.append((assoc_id, first_activity_bid, ann_id))
            parts.append(
                f'    <bpmn:association id={quoteattr(assoc_id)} '
                f'sourceRef={quoteattr(first_activity_bid)} '
                f'targetRef={quoteattr(ann_id)}/>'
            )

    parts.append('  </bpmn:process>')

    # BPMN Diagram Interchange (DI) — every shape gets a BPMNShape with
    # dc:Bounds and every flow gets a BPMNEdge with di:waypoints. Without
    # this section bpmn.io and recent Camunda Modeler refuse to render.
    shapes, edges, pool, lanes_di = _compute_layout(
        skeleton=skeleton,
        bpmn_ids=bpmn_ids,
        sequence_flows=sequence_flows,
        associations=associations,
        start_id=start_id,
        end_id=end_id,
    )
    parts.append('  <bpmndi:BPMNDiagram id="BPMNDiagram_1">')
    parts.append(
        f'    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement={quoteattr(collab_id)}>'
    )
    px, py, pw, ph = pool
    parts.append(
        f'      <bpmndi:BPMNShape id="Participant_1_di" '
        f'bpmnElement="Participant_1" isHorizontal="true">'
    )
    parts.append(
        f'        <dc:Bounds x="{px}" y="{py}" width="{pw}" height="{ph}"/>'
    )
    parts.append('      </bpmndi:BPMNShape>')
    for lane_bid, (lx, ly, lw, lh) in lanes_di.items():
        parts.append(
            f'      <bpmndi:BPMNShape id={quoteattr(lane_bid + "_di")} '
            f'bpmnElement={quoteattr(lane_bid)} isHorizontal="true">'
        )
        parts.append(
            f'        <dc:Bounds x="{lx}" y="{ly}" width="{lw}" height="{lh}"/>'
        )
        parts.append('      </bpmndi:BPMNShape>')
    di_shape_order = [start_id]
    for activity in skeleton.activities:
        di_shape_order.append(bpmn_ids[activity.stable_id])
    for gateway in skeleton.gateways:
        di_shape_order.append(bpmn_ids[gateway.stable_id])
    di_shape_order.append(end_id)
    for note in skeleton.notes:
        di_shape_order.append(bpmn_ids[note.stable_id])
    for bid in di_shape_order:
        if bid not in shapes:
            continue
        x, y, w, h = shapes[bid]
        parts.append(
            f'      <bpmndi:BPMNShape id={quoteattr(bid + "_di")} '
            f'bpmnElement={quoteattr(bid)}>'
        )
        parts.append(
            f'        <dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}"/>'
        )
        parts.append('      </bpmndi:BPMNShape>')
    for flow_id, _src, _tgt in sequence_flows:
        wp = edges.get(flow_id, [])
        if not wp:
            continue
        parts.append(
            f'      <bpmndi:BPMNEdge id={quoteattr(flow_id + "_di")} '
            f'bpmnElement={quoteattr(flow_id)}>'
        )
        for x, y in wp:
            parts.append(f'        <di:waypoint x="{x}" y="{y}"/>')
        parts.append('      </bpmndi:BPMNEdge>')
    for assoc_id, _src, _tgt in associations:
        wp = edges.get(assoc_id, [])
        if not wp:
            continue
        parts.append(
            f'      <bpmndi:BPMNEdge id={quoteattr(assoc_id + "_di")} '
            f'bpmnElement={quoteattr(assoc_id)}>'
        )
        for x, y in wp:
            parts.append(f'        <di:waypoint x="{x}" y="{y}"/>')
        parts.append('      </bpmndi:BPMNEdge>')
    parts.append('    </bpmndi:BPMNPlane>')
    parts.append('  </bpmndi:BPMNDiagram>')

    parts.append('</bpmn:definitions>')
    parts.append("")
    return "\n".join(parts)


def write(skeleton, output_path, title="Process Skeleton"):
    Path(output_path).write_text(render(skeleton, title=title), encoding="utf-8")


def _compute_ranks(node_ids, flows, start_id):
    """Longest-path rank from start_id to each node — X-axis column index."""
    rank = {nid: 0 for nid in node_ids}
    rank[start_id] = 0
    for _ in range(len(node_ids) + 1):
        changed = False
        for _flow_id, src, tgt in flows:
            new_rank = rank.get(src, 0) + 1
            if new_rank > rank.get(tgt, 0):
                rank[tgt] = new_rank
                changed = True
        if not changed:
            break
    return rank


def _compute_layout(skeleton, bpmn_ids, sequence_flows, associations, start_id, end_id):
    """Compute pixel-integer positions for every shape and waypoint.

    Returns (shapes, edges, pool, lanes). Layout is a horizontal-swimlane
    grid: lanes top-to-bottom in actor order; nodes within a lane spread
    left-to-right by longest-path rank from start; events at vertical
    centre of pool; notes in a strip below the pool; cross-lane edges as
    4-waypoint elbows; same-lane edges as 2-waypoint straight lines.
    """
    lane_ids = {}
    for i, actor in enumerate(skeleton.actors, 1):
        lane_ids[actor] = f"Lane_{i}_" + _safe_id(actor)

    node_to_actor = {}
    for activity in skeleton.activities:
        node_to_actor[bpmn_ids[activity.stable_id]] = activity.actor
    for gateway in skeleton.gateways:
        node_to_actor[bpmn_ids[gateway.stable_id]] = gateway.actor

    flow_node_ids = [start_id, end_id, *node_to_actor.keys()]
    rank = _compute_ranks(flow_node_ids, sequence_flows, start_id)
    max_rank = max([rank.get(nid, 0) for nid in flow_node_ids] + [0])
    rank[end_id] = max(max_rank, rank.get(end_id, 0))
    max_rank = rank[end_id]

    num_lanes = max(len(skeleton.actors), 1)
    pool_x = _POOL_X
    pool_y = _POOL_Y
    pool_inner_x_start = pool_x + _PARTICIPANT_LABEL_W + _LANE_LABEL_W + _LEFT_GUTTER
    pool_width = (
        _PARTICIPANT_LABEL_W + _LANE_LABEL_W + _LEFT_GUTTER
        + (max_rank + 1) * _COLUMN_WIDTH
        + _RIGHT_GUTTER
    )
    pool_height = num_lanes * _LANE_HEIGHT

    lanes = {}
    for i, actor in enumerate(skeleton.actors):
        lane_x = pool_x + _PARTICIPANT_LABEL_W
        lane_y = pool_y + i * _LANE_HEIGHT
        lane_w = pool_width - _PARTICIPANT_LABEL_W
        lane_h = _LANE_HEIGHT
        lanes[lane_ids[actor]] = (lane_x, lane_y, lane_w, lane_h)

    shapes = {}

    def x_for_rank(r):
        return pool_inner_x_start + r * _COLUMN_WIDTH

    def y_in_lane(actor, node_height):
        if actor not in lane_ids:
            return pool_y + (pool_height - node_height) // 2
        _lx, ly, _lw, lh = lanes[lane_ids[actor]]
        return ly + (lh - node_height) // 2

    shapes[start_id] = (
        x_for_rank(rank[start_id]),
        pool_y + (pool_height - _EVENT_SIZE) // 2,
        _EVENT_SIZE, _EVENT_SIZE,
    )
    shapes[end_id] = (
        x_for_rank(rank[end_id]),
        pool_y + (pool_height - _EVENT_SIZE) // 2,
        _EVENT_SIZE, _EVENT_SIZE,
    )
    for activity in skeleton.activities:
        bid = bpmn_ids[activity.stable_id]
        shapes[bid] = (
            x_for_rank(rank[bid]),
            y_in_lane(activity.actor, _TASK_HEIGHT),
            _TASK_WIDTH, _TASK_HEIGHT,
        )
    for gateway in skeleton.gateways:
        bid = bpmn_ids[gateway.stable_id]
        shapes[bid] = (
            x_for_rank(rank[bid]) + (_TASK_WIDTH - _GATEWAY_SIZE) // 2,
            y_in_lane(gateway.actor, _GATEWAY_SIZE),
            _GATEWAY_SIZE, _GATEWAY_SIZE,
        )
    note_y = pool_y + pool_height + _NOTE_GAP_BELOW_POOL
    for i, note in enumerate(skeleton.notes):
        bid = bpmn_ids[note.stable_id]
        shapes[bid] = (
            pool_x + i * (_NOTE_WIDTH + _NOTE_GAP_X),
            note_y,
            _NOTE_WIDTH, _NOTE_HEIGHT,
        )

    edges = {}

    def _waypoints(src_bid, tgt_bid):
        if src_bid not in shapes or tgt_bid not in shapes:
            return []
        sx0, sy0, sw, sh = shapes[src_bid]
        tx0, ty0, tw, th = shapes[tgt_bid]
        sx, sy = sx0 + sw, sy0 + sh // 2
        tx, ty = tx0, ty0 + th // 2
        if sy == ty:
            return [(sx, sy), (tx, ty)]
        mid_x = (sx + tx) // 2
        return [(sx, sy), (mid_x, sy), (mid_x, ty), (tx, ty)]

    for flow_id, src_bid, tgt_bid in sequence_flows:
        edges[flow_id] = _waypoints(src_bid, tgt_bid)
    for assoc_id, src_bid, tgt_bid in associations:
        edges[assoc_id] = _waypoints(src_bid, tgt_bid)

    return shapes, edges, (pool_x, pool_y, pool_width, pool_height), lanes


def _safe_id(stable_id):
    """BPMN ids must be xsd:ID-valid (NCName). Replace bad chars with _."""
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
