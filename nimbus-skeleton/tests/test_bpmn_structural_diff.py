"""Tests for ``scripts/bpmn_structural_diff.py`` (QUEUE 2.1).

Five tests, one per DoD-required structural dimension:

1. identical files -> no deltas
2. missing + added element ids detected
3. lane-membership deltas detected
4. sequence-flow source/target deltas detected
5. flow-nodes-without-BPMNShape counts detected

Fixtures are minimal inline BPMN strings (just enough namespaces +
elements to exercise each dimension). Stdlib only — no lxml, no
network, air-gap-safe.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


# scripts/ is sibling to tests/ under nimbus-skeleton/; insert it on
# sys.path so we can import the helper as a module.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bpmn_structural_diff as bsd  # noqa: E402


# A minimal BPMN-2 document: collaboration, single lane, two tasks, two
# sequence flows, matching BPMNShapes for the tasks. Just enough to
# parse and exercise every dimension.
_BPMN_A = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  id="Defs_1" targetNamespace="urn:test">
  <bpmn:process id="Proc_1">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_A" name="A">
        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Task_2</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:task id="Task_1" name="t1"/>
    <bpmn:task id="Task_2" name="t2"/>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Task_1" targetRef="Task_2"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Diag_1">
    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Proc_1">
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1"/>
      <bpmndi:BPMNShape id="Task_2_di" bpmnElement="Task_2"/>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def _write(tmpdir, name, body):
    p = Path(tmpdir) / name
    p.write_text(body, encoding="utf-8")
    return str(p)


class BpmnStructuralDiffTests(unittest.TestCase):

    def test_identical_files_report_no_deltas(self):
        """Same file on both sides -> every dimension is empty + has_diff False."""
        with tempfile.TemporaryDirectory() as tmp:
            a = _write(tmp, "a.bpmn", _BPMN_A)
            b = _write(tmp, "b.bpmn", _BPMN_A)
            d = bsd.diff(a, b)
            self.assertEqual(d["missing_ids"], [])
            self.assertEqual(d["added_ids"], [])
            self.assertEqual(d["lane_deltas"], [])
            self.assertEqual(d["flow_ref_deltas"], [])
            self.assertEqual(d["flow_nodes_without_shape_a"], [])
            self.assertEqual(d["flow_nodes_without_shape_b"], [])
            self.assertFalse(bsd.has_diff(d))

    def test_missing_and_added_element_ids(self):
        """A has Task_2; B drops Task_2 and adds Task_3 in its place."""
        b_body = (
            _BPMN_A
            .replace(
                '<bpmn:flowNodeRef>Task_2</bpmn:flowNodeRef>',
                '<bpmn:flowNodeRef>Task_3</bpmn:flowNodeRef>',
            )
            .replace('<bpmn:task id="Task_2" name="t2"/>',
                     '<bpmn:task id="Task_3" name="t3"/>')
            .replace('targetRef="Task_2"', 'targetRef="Task_3"')
            .replace('id="Task_2_di" bpmnElement="Task_2"',
                     'id="Task_3_di" bpmnElement="Task_3"')
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = _write(tmp, "a.bpmn", _BPMN_A)
            b = _write(tmp, "b.bpmn", b_body)
            d = bsd.diff(a, b)
            self.assertIn("Task_2", d["missing_ids"])
            self.assertIn("Task_3", d["added_ids"])
            self.assertTrue(bsd.has_diff(d))

    def test_lane_membership_delta_detected(self):
        """A puts Task_2 in Lane_A; B moves it to Lane_B."""
        b_body = _BPMN_A.replace(
            '<bpmn:lane id="Lane_A" name="A">\n'
            '        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>\n'
            '        <bpmn:flowNodeRef>Task_2</bpmn:flowNodeRef>\n'
            '      </bpmn:lane>',
            '<bpmn:lane id="Lane_A" name="A">\n'
            '        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>\n'
            '      </bpmn:lane>\n'
            '      <bpmn:lane id="Lane_B" name="B">\n'
            '        <bpmn:flowNodeRef>Task_2</bpmn:flowNodeRef>\n'
            '      </bpmn:lane>',
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = _write(tmp, "a.bpmn", _BPMN_A)
            b = _write(tmp, "b.bpmn", b_body)
            d = bsd.diff(a, b)
            self.assertEqual(d["missing_ids"], [])
            self.assertIn("Lane_B", d["added_ids"])  # new lane id
            lane_keys = [tup[0] for tup in d["lane_deltas"]]
            self.assertIn("Task_2", lane_keys)
            for fn, la, lb in d["lane_deltas"]:
                if fn == "Task_2":
                    self.assertEqual(la, "Lane_A")
                    self.assertEqual(lb, "Lane_B")
            self.assertTrue(bsd.has_diff(d))

    def test_sequence_flow_ref_delta_detected(self):
        """A has Flow_1 Task_1->Task_2; B swaps target to Task_1 (self-loop)."""
        b_body = _BPMN_A.replace(
            'sourceRef="Task_1" targetRef="Task_2"',
            'sourceRef="Task_2" targetRef="Task_1"',
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = _write(tmp, "a.bpmn", _BPMN_A)
            b = _write(tmp, "b.bpmn", b_body)
            d = bsd.diff(a, b)
            self.assertEqual(d["missing_ids"], [])
            self.assertEqual(d["added_ids"], [])
            self.assertEqual(len(d["flow_ref_deltas"]), 1)
            fid, ra, rb = d["flow_ref_deltas"][0]
            self.assertEqual(fid, "Flow_1")
            self.assertEqual(ra, ("Task_1", "Task_2"))
            self.assertEqual(rb, ("Task_2", "Task_1"))
            self.assertTrue(bsd.has_diff(d))

    def test_flow_nodes_without_bpmnshape_counted(self):
        """B drops Task_2's BPMNShape -> Task_2 reported as shape-less in B only."""
        b_body = _BPMN_A.replace(
            '<bpmndi:BPMNShape id="Task_2_di" bpmnElement="Task_2"/>',
            "",
        )
        with tempfile.TemporaryDirectory() as tmp:
            a = _write(tmp, "a.bpmn", _BPMN_A)
            b = _write(tmp, "b.bpmn", b_body)
            d = bsd.diff(a, b)
            self.assertEqual(d["flow_nodes_without_shape_a"], [])
            self.assertEqual(d["flow_nodes_without_shape_b"], ["Task_2"])
            # B is also missing the Task_2_di id A had:
            self.assertIn("Task_2_di", d["missing_ids"])
            self.assertTrue(bsd.has_diff(d))


if __name__ == "__main__":
    unittest.main()
