#!/usr/bin/env python3
"""BPMN 2.0 structural-diff helper for Camunda-resave round-trip checks.

Pure stdlib (``xml.etree.ElementTree``). Used to compare an emitter's
BPMN output against the same file after Camunda Modeler resave, to
catch silent structural changes the GUI may introduce on import +
save (renamed ids, moved flow nodes, lost shapes, etc.).

Usage:
    python bpmn_structural_diff.py FILE_A.bpmn FILE_B.bpmn

Prints a structural diff report and exits 0 if files are structurally
equivalent, 1 if any delta found, 2 on usage error.

Dimensions reported (per QUEUE 2.1 DoD):
  1. Missing element ids (in A, not B)
  2. Added element ids (in B, not A)
  3. Lane-membership deltas (flowNode moved between lanes)
  4. Sequence-flow source/target deltas (sourceRef or targetRef changed)
  5. Flow-nodes without BPMNShape in BPMNDiagram (per side)
"""
from __future__ import annotations

import sys
from xml.etree import ElementTree as ET

_BPMN = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
_BPMNDI = "{http://www.omg.org/spec/BPMN/20100524/DI}"

# Flow-node element tags expected to carry a BPMNShape in the diagram.
_FLOW_NODE_TAGS = frozenset({
    f"{_BPMN}task", f"{_BPMN}userTask", f"{_BPMN}serviceTask",
    f"{_BPMN}manualTask", f"{_BPMN}scriptTask", f"{_BPMN}businessRuleTask",
    f"{_BPMN}sendTask", f"{_BPMN}receiveTask", f"{_BPMN}callActivity",
    f"{_BPMN}subProcess",
    f"{_BPMN}startEvent", f"{_BPMN}endEvent",
    f"{_BPMN}intermediateThrowEvent", f"{_BPMN}intermediateCatchEvent",
    f"{_BPMN}boundaryEvent",
    f"{_BPMN}exclusiveGateway", f"{_BPMN}parallelGateway",
    f"{_BPMN}inclusiveGateway", f"{_BPMN}eventBasedGateway",
    f"{_BPMN}complexGateway",
    f"{_BPMN}textAnnotation",
})


def _index(path):
    """Parse one BPMN file and project the dimensions we care about."""
    root = ET.parse(path).getroot()
    element_ids = {e.get("id") for e in root.iter() if e.get("id")}

    lane_membership = {}
    for lane in root.iter(f"{_BPMN}lane"):
        lid = lane.get("id")
        for ref in lane.findall(f"{_BPMN}flowNodeRef"):
            if ref.text:
                lane_membership[ref.text.strip()] = lid

    flow_ref = {
        sf.get("id"): (sf.get("sourceRef"), sf.get("targetRef"))
        for sf in root.iter(f"{_BPMN}sequenceFlow")
    }

    shape_targets = {
        s.get("bpmnElement") for s in root.iter(f"{_BPMNDI}BPMNShape")
        if s.get("bpmnElement")
    }

    flow_nodes = set()
    for tag in _FLOW_NODE_TAGS:
        for fn in root.iter(tag):
            if fn.get("id"):
                flow_nodes.add(fn.get("id"))

    return {
        "element_ids": element_ids,
        "lane_membership": lane_membership,
        "flow_ref": flow_ref,
        "shape_targets": shape_targets,
        "flow_nodes": flow_nodes,
    }


def diff(file_a, file_b):
    """Compute the structural diff between two BPMN files.

    Returns a dict with sorted, deterministic lists for each dimension
    so callers can equality-compare without ordering surprises.
    """
    a = _index(file_a)
    b = _index(file_b)
    lane_keys = a["lane_membership"].keys() | b["lane_membership"].keys()
    flow_keys = a["flow_ref"].keys() | b["flow_ref"].keys()
    return {
        "missing_ids": sorted(a["element_ids"] - b["element_ids"]),
        "added_ids": sorted(b["element_ids"] - a["element_ids"]),
        "lane_deltas": sorted(
            (fn, a["lane_membership"].get(fn), b["lane_membership"].get(fn))
            for fn in lane_keys
            if a["lane_membership"].get(fn) != b["lane_membership"].get(fn)
        ),
        "flow_ref_deltas": sorted(
            (fid, a["flow_ref"].get(fid), b["flow_ref"].get(fid))
            for fid in flow_keys
            if a["flow_ref"].get(fid) != b["flow_ref"].get(fid)
        ),
        "flow_nodes_without_shape_a": sorted(a["flow_nodes"] - a["shape_targets"]),
        "flow_nodes_without_shape_b": sorted(b["flow_nodes"] - b["shape_targets"]),
    }


def has_diff(d):
    """True if any dimension reports a delta."""
    return any(d[k] for k in (
        "missing_ids", "added_ids", "lane_deltas", "flow_ref_deltas",
        "flow_nodes_without_shape_a", "flow_nodes_without_shape_b",
    ))


def format_report(d, file_a, file_b):
    """Render a deterministic, line-per-delta plaintext report."""
    out = [f"Structural diff: {file_a} vs {file_b}"]
    out.append(f"  Missing element ids (in A, not B): {len(d['missing_ids'])}")
    out.extend(f"    - {x}" for x in d["missing_ids"])
    out.append(f"  Added element ids (in B, not A): {len(d['added_ids'])}")
    out.extend(f"    - {x}" for x in d["added_ids"])
    out.append(f"  Lane-membership deltas: {len(d['lane_deltas'])}")
    out.extend(f"    - {fn}: A={la} B={lb}" for fn, la, lb in d["lane_deltas"])
    out.append(f"  Sequence-flow source/target deltas: {len(d['flow_ref_deltas'])}")
    out.extend(f"    - {fid}: A={ra} B={rb}" for fid, ra, rb in d["flow_ref_deltas"])
    out.append(f"  Flow-nodes without BPMNShape in A: {len(d['flow_nodes_without_shape_a'])}")
    out.extend(f"    - {x}" for x in d["flow_nodes_without_shape_a"])
    out.append(f"  Flow-nodes without BPMNShape in B: {len(d['flow_nodes_without_shape_b'])}")
    out.extend(f"    - {x}" for x in d["flow_nodes_without_shape_b"])
    return "\n".join(out)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: bpmn_structural_diff.py FILE_A.bpmn FILE_B.bpmn", file=sys.stderr)
        return 2
    d = diff(args[0], args[1])
    print(format_report(d, args[0], args[1]))
    return 1 if has_diff(d) else 0


if __name__ == "__main__":
    sys.exit(main())
