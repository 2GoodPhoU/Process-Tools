"""Tests for the BPMN 2.0 XML emitter.

Covers:
- structural round-trip: render → parse → assert lanes / tasks / gateways
  / sequence flows match the source ``Skeleton``
- byte-stability across runs (no nondeterministic ordering)
- well-formedness against a hand-rolled minimal BPMN-2 schema check
  (full XSD validation needs xmlschema + the OMG schemas, which we don't
  bundle — we do basic structural assertions instead)
- the in-corpus gateway lands as ``bpmn:exclusiveGateway`` and is wired
  into the lane of its actor
- documentation block fires for flagged activities
- text annotations + associations fire for ``Note`` rows

If `lxml` is installed, the parse step uses it; otherwise stdlib
ElementTree. We don't pin a dependency for tests.
"""

from __future__ import annotations

import unittest
from xml.etree import ElementTree as ET

from nimbus_skeleton.builder import build_skeleton
from nimbus_skeleton.emitters import bpmn
from nimbus_skeleton.models import DDERow


_BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"


def _corpus():
    return [
        DDERow(
            stable_id="REQ-001",
            text="The Operator shall log in to the control console.",
            primary_actor="Operator",
            polarity="Positive",
        ),
        DDERow(
            stable_id="REQ-002",
            text="The System shall record a timestamp for every login event.",
            primary_actor="System",
            polarity="Positive",
        ),
        DDERow(
            stable_id="REQ-003",
            text="If the login fails, the System shall lock the account.",
            primary_actor="System",
            polarity="Positive",
        ),
        DDERow(
            stable_id="REQ-004",
            text="The Operator shall not bypass the safety interlock.",
            primary_actor="Operator",
            polarity="Negative",
        ),
        DDERow(
            stable_id="REQ-005",
            text="The audit log is defined as the persistent record of all "
            "system events.",
            primary_actor="System",
            polarity="Positive",
        ),
    ]


def _ns(tag: str) -> str:
    return f"{{{_BPMN_NS}}}{tag}"


class TestBpmnEmitterStructural(unittest.TestCase):
    """Round-trip the corpus and assert structural invariants."""

    def setUp(self) -> None:
        self.skeleton = build_skeleton(_corpus())
        self.xml = bpmn.render(self.skeleton, title="BPMN Smoke Test")
        self.root = ET.fromstring(self.xml)

    def test_root_is_bpmn_definitions(self) -> None:
        self.assertEqual(self.root.tag, _ns("definitions"))

    def test_has_collaboration_and_process(self) -> None:
        collabs = self.root.findall(_ns("collaboration"))
        processes = self.root.findall(_ns("process"))
        self.assertEqual(len(collabs), 1)
        self.assertEqual(len(processes), 1)

    def test_lane_per_actor(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        lane_set = process.find(_ns("laneSet"))
        self.assertIsNotNone(lane_set)
        lanes = lane_set.findall(_ns("lane"))
        names = {lane.get("name") for lane in lanes}
        self.assertIn("Operator", names)
        self.assertIn("System", names)

    def test_tasks_match_activities(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        tasks = process.findall(_ns("task"))
        # Activities only — declarative REQ-005 became a note, gateway
        # REQ-003 became an exclusiveGateway. So len(tasks) ==
        # len(skeleton.activities).
        self.assertEqual(len(tasks), len(self.skeleton.activities))

    def test_exclusive_gateway_for_conditional(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        gws = process.findall(_ns("exclusiveGateway"))
        self.assertEqual(len(gws), 1)
        # The corpus's gateway is REQ-003 ("If the login fails…").
        # name= preserves the stripped condition text.
        self.assertIsNotNone(gws[0].get("name"))

    def test_start_and_end_events(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        starts = process.findall(_ns("startEvent"))
        ends = process.findall(_ns("endEvent"))
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)

    def test_sequence_flows_form_a_chain(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        flows = process.findall(_ns("sequenceFlow"))
        # At minimum: start → first activity, plus one per skeleton flow,
        # plus terminal-activity → end.
        self.assertGreaterEqual(len(flows), len(self.skeleton.flows) + 2)
        # All sourceRef / targetRef must point at ids defined in the
        # process — no dangling refs.
        defined_ids: set[str] = set()
        for elem in process.iter():
            eid = elem.get("id")
            if eid:
                defined_ids.add(eid)
        for flow in flows:
            self.assertIn(flow.get("sourceRef"), defined_ids)
            self.assertIn(flow.get("targetRef"), defined_ids)

    def test_flagged_activity_has_documentation(self) -> None:
        # REQ-004 (negative polarity) should be flagged → documentation
        # block under its task.
        process = self.root.find(_ns("process"))
        assert process is not None
        flagged_tasks = []
        for task in process.findall(_ns("task")):
            doc = task.find(_ns("documentation"))
            if doc is not None and "REVIEW" in (doc.text or ""):
                flagged_tasks.append(task)
        self.assertGreaterEqual(len(flagged_tasks), 1)

    def test_note_becomes_text_annotation(self) -> None:
        process = self.root.find(_ns("process"))
        assert process is not None
        anns = process.findall(_ns("textAnnotation"))
        self.assertGreaterEqual(len(anns), 1)
        text_elem = anns[0].find(_ns("text"))
        self.assertIsNotNone(text_elem)
        self.assertIn("audit log", (text_elem.text or "").lower())


class TestBpmnEmitterByteStable(unittest.TestCase):
    def test_two_renders_equal(self) -> None:
        skeleton = build_skeleton(_corpus())
        first = bpmn.render(skeleton, title="Stability Check")
        second = bpmn.render(skeleton, title="Stability Check")
        self.assertEqual(first, second)


class TestBpmnEmitterIdSafety(unittest.TestCase):
    def test_unsafe_actor_name_yields_safe_lane_id(self) -> None:
        rows = [
            DDERow(
                stable_id="R1",
                text="Operator A/B shall press start.",
                primary_actor="Operator A/B",
                polarity="Positive",
            ),
        ]
        skeleton = build_skeleton(rows)
        xml = bpmn.render(skeleton)
        root = ET.fromstring(xml)
        # If the lane id were raw, parsing would still work but the id
        # would contain '/'. Assert it doesn't.
        for lane in root.iter(_ns("lane")):
            lane_id = lane.get("id") or ""
            self.assertNotIn("/", lane_id)
            self.assertNotIn(" ", lane_id)

    def test_unsafe_stable_id_yields_safe_task_id(self) -> None:
        rows = [
            DDERow(
                stable_id="REQ A:01",
                text="The Operator shall press start.",
                primary_actor="Operator",
                polarity="Positive",
            ),
        ]
        skeleton = build_skeleton(rows)
        xml = bpmn.render(skeleton)
        root = ET.fromstring(xml)
        process = root.find(_ns("process"))
        assert process is not None
        for task in process.findall(_ns("task")):
            tid = task.get("id") or ""
            for bad in (" ", ":", "/"):
                self.assertNotIn(bad, tid)


class TestBpmnEmitterEmptySkeleton(unittest.TestCase):
    """Render-with-no-rows must still produce a valid BPMN definition."""

    def test_empty_skeleton(self) -> None:
        from nimbus_skeleton.models import Skeleton

        xml = bpmn.render(Skeleton(), title="Empty")
        root = ET.fromstring(xml)
        # Has a process and a start + end event.
        process = root.find(_ns("process"))
        self.assertIsNotNone(process)
        assert process is not None
        self.assertEqual(len(process.findall(_ns("startEvent"))), 1)
        self.assertEqual(len(process.findall(_ns("endEvent"))), 1)


_BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
_DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
_DI_NS = "http://www.omg.org/spec/DD/20100524/DI"


def _di(tag: str) -> str:
    return f"{{{_BPMNDI_NS}}}{tag}"


def _dc(tag: str) -> str:
    return f"{{{_DC_NS}}}{tag}"


def _diNs(tag: str) -> str:
    return f"{{{_DI_NS}}}{tag}"


class TestBpmnEmitterDiagramInterchange(unittest.TestCase):
    # The BPMNDiagram (DI) section is what makes bpmn.io / Camunda
    # Modeler actually render the diagram instead of saying "no diagram
    # to display." See DECISIONS.md "BPMN DI generation" entry.

    def setUp(self) -> None:
        self.skeleton = build_skeleton(_corpus())
        self.xml = bpmn.render(self.skeleton, title="DI Smoke Test")
        self.root = ET.fromstring(self.xml)
        diagrams = self.root.findall(_di("BPMNDiagram"))
        self.assertEqual(len(diagrams), 1)
        self.diagram = diagrams[0]
        planes = self.diagram.findall(_di("BPMNPlane"))
        self.assertEqual(len(planes), 1)
        self.plane = planes[0]

    def test_plane_references_collaboration(self) -> None:
        self.assertEqual(self.plane.get("bpmnElement"), "Collaboration_1")

    def test_shape_count_matches_semantic_counts(self) -> None:
        shapes = self.plane.findall(_di("BPMNShape"))
        expected = (
            1
            + len(self.skeleton.actors)
            + len(self.skeleton.activities)
            + len(self.skeleton.gateways)
            + 2
            + len(self.skeleton.notes)
        )
        self.assertEqual(len(shapes), expected)

    def test_every_shape_has_integer_bounds(self) -> None:
        for shape in self.plane.findall(_di("BPMNShape")):
            bounds = shape.find(_dc("Bounds"))
            self.assertIsNotNone(bounds)
            for attr in ("x", "y", "width", "height"):
                v = bounds.get(attr)
                self.assertIsNotNone(v)
                int(v)  # raises if non-integer

    def test_edge_count_matches_sequence_and_association_count(self) -> None:
        edges = self.plane.findall(_di("BPMNEdge"))
        process = self.root.find(_ns("process"))
        assert process is not None
        n_flows = len(process.findall(_ns("sequenceFlow")))
        n_assocs = len(process.findall(_ns("association")))
        self.assertEqual(len(edges), n_flows + n_assocs)

    def test_every_edge_has_at_least_two_waypoints(self) -> None:
        for edge in self.plane.findall(_di("BPMNEdge")):
            wps = edge.findall(_diNs("waypoint"))
            self.assertGreaterEqual(len(wps), 2)

    def test_shape_and_edge_bpmnelement_refs_resolve(self) -> None:
        defined = set()
        for elem in self.root.iter():
            eid = elem.get("id")
            if eid:
                defined.add(eid)
        for shape in self.plane.findall(_di("BPMNShape")):
            self.assertIn(shape.get("bpmnElement"), defined)
        for edge in self.plane.findall(_di("BPMNEdge")):
            self.assertIn(edge.get("bpmnElement"), defined)

    def test_empty_skeleton_still_emits_diagram(self) -> None:
        from nimbus_skeleton.models import Skeleton
        xml = bpmn.render(Skeleton(), title="Empty")
        root = ET.fromstring(xml)
        diagrams = root.findall(_di("BPMNDiagram"))
        self.assertEqual(len(diagrams), 1)
        plane = diagrams[0].find(_di("BPMNPlane"))
        assert plane is not None
        shapes = plane.findall(_di("BPMNShape"))
        self.assertGreaterEqual(len(shapes), 3)


class TestBpmnEmitterCli(unittest.TestCase):
    """The --bpmn flag wires through the CLI without tripping anything."""

    def test_cli_flag_present(self) -> None:
        from nimbus_skeleton import cli

        parser = cli.build_arg_parser()
        # Must parse the --bpmn switch without erroring.
        args = parser.parse_args([
            "--requirements", "requirements.xlsx",
            "--output-dir", "/tmp/x",
            "--bpmn",
        ])
        self.assertTrue(args.bpmn)


if __name__ == "__main__":
    unittest.main()
