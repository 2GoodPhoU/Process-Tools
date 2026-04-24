"""Tests for the ReqIF writer (REVIEW §3.10 extended).

Covers:

1. Basic XML shape — valid root, namespace, required sections
   (THE-HEADER, CORE-CONTENT, SPEC-OBJECTS, SPECIFICATIONS).
2. One SPEC-OBJECT per requirement, with every attribute value
   present and the stable_id as the IDENTIFIER.
3. Dialect differences: LONG-NAME, ReqIF.ForeignID, ReqIF.ChapterName,
   SPECIFICATION-TYPE.
4. Unknown-dialect rejection.

Uses ElementTree to parse what we produce so the XML is validated
structurally rather than string-matched.

Run:  python -m unittest tests.test_reqif_writer
"""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from requirements_extractor.models import Requirement, compute_stable_id
from requirements_extractor.reqif_writer import (
    REQIF_NAMESPACE,
    SUPPORTED_DIALECTS,
    write_requirements_reqif,
)


NS = {"r": REQIF_NAMESPACE}


def _make_req(
    text: str,
    *,
    source_file: str = "spec.docx",
    primary_actor: str = "User",
    heading_trail: str = "3. System Requirements",
    order: int = 1,
) -> Requirement:
    return Requirement(
        order=order,
        source_file=source_file,
        heading_trail=heading_trail,
        section_topic="",
        row_ref="Table 1, Row 1",
        block_ref="Paragraph 1",
        primary_actor=primary_actor,
        secondary_actors=[],
        text=text,
        req_type="Hard",
        keywords=["shall"],
        confidence="High",
        notes="",
        polarity="Positive",
        stable_id=compute_stable_id(source_file, primary_actor, text),
    )


def _write_and_parse(reqs, dialect="basic"):
    """Helper: write a ReqIF file and return the parsed ElementTree root."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.reqif"
        write_requirements_reqif(reqs, out, dialect=dialect)
        tree = ET.parse(str(out))
        return tree.getroot()


# ---------------------------------------------------------------------------
# Structure — every dialect must produce these anchors
# ---------------------------------------------------------------------------


class TestReqifStructure(unittest.TestCase):
    def test_root_element_is_namespaced_reqif(self) -> None:
        root = _write_and_parse([_make_req("The User shall log in.")])
        # Clark notation check — root tag is {namespace}REQ-IF.
        self.assertEqual(root.tag, f"{{{REQIF_NAMESPACE}}}REQ-IF")

    def test_has_required_top_level_sections(self) -> None:
        root = _write_and_parse([_make_req("X shall Y.")])
        self.assertIsNotNone(root.find("r:THE-HEADER", NS))
        core = root.find("r:CORE-CONTENT", NS)
        self.assertIsNotNone(core)
        content = core.find("r:REQ-IF-CONTENT", NS)
        self.assertIsNotNone(content)
        for section in ("DATATYPES", "SPEC-TYPES", "SPEC-OBJECTS",
                        "SPECIFICATIONS"):
            self.assertIsNotNone(
                content.find(f"r:{section}", NS),
                msg=f"missing section {section}",
            )

    def test_one_spec_object_per_requirement(self) -> None:
        reqs = [
            _make_req("Alpha.", order=1),
            _make_req("Beta.", order=2),
            _make_req("Gamma.", order=3),
        ]
        # Make stable_ids distinct — compute_stable_id hashes on the
        # (file, actor, text) triple, so three distinct texts give
        # three distinct IDs.  No post-hoc rewrite needed.
        root = _write_and_parse(reqs)
        spec_objects = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT",
            NS,
        )
        self.assertEqual(len(spec_objects), 3)

    def test_spec_object_identifier_is_stable_id(self) -> None:
        req = _make_req("The user shall authenticate.")
        root = _write_and_parse([req])
        spec_object = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT",
            NS,
        )
        self.assertEqual(spec_object.get("IDENTIFIER"), req.stable_id)

    def test_attribute_values_populated(self) -> None:
        req = _make_req("The system shall validate the token.")
        root = _write_and_parse([req])
        values = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT"
            "/r:VALUES/r:ATTRIBUTE-VALUE-STRING",
            NS,
        )
        # One value per base attribute (12 base + 0 dialect extras for basic).
        self.assertGreaterEqual(len(values), 10)
        the_values = [v.get("THE-VALUE") for v in values]
        # Requirement text must round-trip into one of the values.
        self.assertIn("The system shall validate the token.", the_values)
        self.assertIn("User", the_values)

    def test_specification_lists_every_spec_object(self) -> None:
        reqs = [
            _make_req("Alpha requirement."),
            _make_req("Beta requirement."),
        ]
        root = _write_and_parse(reqs)
        children = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPECIFICATIONS"
            "/r:SPECIFICATION/r:CHILDREN/r:SPEC-HIERARCHY",
            NS,
        )
        self.assertEqual(len(children), 2)


# ---------------------------------------------------------------------------
# Dialect-specific tweaks
# ---------------------------------------------------------------------------


class TestDialectDifferences(unittest.TestCase):
    def test_basic_long_name_is_stable_id(self) -> None:
        req = _make_req("The user shall log in via SSO when configured.")
        root = _write_and_parse([req], dialect="basic")
        obj = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT",
            NS,
        )
        self.assertEqual(obj.get("LONG-NAME"), req.stable_id)

    def test_cameo_long_name_is_text_preview(self) -> None:
        req = _make_req("The user shall log in via SSO when configured.")
        root = _write_and_parse([req], dialect="cameo")
        obj = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT",
            NS,
        )
        # Cameo dialect uses a text preview rather than the stable_id.
        long_name = obj.get("LONG-NAME") or ""
        self.assertIn("user", long_name.lower())
        self.assertNotEqual(long_name, req.stable_id)

    def test_doors_has_foreign_id_and_chapter_name_attributes(self) -> None:
        """DOORS dialect adds ReqIF.ForeignID and ReqIF.ChapterName
        attributes on SPEC-OBJECT-TYPE, and populates them per
        requirement."""
        req = _make_req("The system shall log.")
        root = _write_and_parse([req], dialect="doors")
        # Attribute definitions appear on the SPEC-OBJECT-TYPE.
        defs = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-TYPES/r:SPEC-OBJECT-TYPE"
            "/r:SPEC-ATTRIBUTES/r:ATTRIBUTE-DEFINITION-STRING",
            NS,
        )
        long_names = [d.get("LONG-NAME") for d in defs]
        self.assertIn("ReqIF.ForeignID", long_names)
        self.assertIn("ReqIF.ChapterName", long_names)
        # And the corresponding values on the SPEC-OBJECT.
        values = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT"
            "/r:VALUES/r:ATTRIBUTE-VALUE-STRING",
            NS,
        )
        the_values = [v.get("THE-VALUE") for v in values]
        self.assertIn(req.stable_id, the_values)        # ForeignID
        self.assertIn("3. System Requirements", the_values)  # ChapterName

    def test_doors_declares_specification_type(self) -> None:
        """DOORS import wizard is happier when a SPECIFICATION-TYPE
        is declared up-front rather than inferred."""
        req = _make_req("Something shall happen.")
        root = _write_and_parse([req], dialect="doors")
        spec_type = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-TYPES/"
            "r:SPECIFICATION-TYPE",
            NS,
        )
        self.assertIsNotNone(spec_type)
        # And the SPECIFICATION references it via TYPE / SPECIFICATION-TYPE-REF.
        type_ref = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPECIFICATIONS/r:SPECIFICATION"
            "/r:TYPE/r:SPECIFICATION-TYPE-REF",
            NS,
        )
        self.assertIsNotNone(type_ref)

    def test_basic_does_not_declare_specification_type(self) -> None:
        req = _make_req("Something shall happen.")
        root = _write_and_parse([req], dialect="basic")
        spec_type = root.find(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-TYPES/"
            "r:SPECIFICATION-TYPE",
            NS,
        )
        self.assertIsNone(spec_type)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestDialectValidation(unittest.TestCase):
    def test_unknown_dialect_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            with tempfile.TemporaryDirectory() as d:
                write_requirements_reqif(
                    [_make_req("X.")],
                    Path(d) / "out.reqif",
                    dialect="polarion",
                )
        self.assertIn("polarion", str(ctx.exception))
        self.assertIn("basic", str(ctx.exception))

    def test_supported_dialects_set(self) -> None:
        self.assertIn("basic", SUPPORTED_DIALECTS)
        self.assertIn("cameo", SUPPORTED_DIALECTS)
        self.assertIn("doors", SUPPORTED_DIALECTS)


# ---------------------------------------------------------------------------
# Empty-input safety
# ---------------------------------------------------------------------------


class TestEmptyInput(unittest.TestCase):
    def test_empty_requirements_produces_valid_file(self) -> None:
        """A zero-requirements extraction should still produce a valid
        ReqIF document (empty SPEC-OBJECTS / SPECIFICATION children)."""
        root = _write_and_parse([])
        spec_objects = root.findall(
            "r:CORE-CONTENT/r:REQ-IF-CONTENT/r:SPEC-OBJECTS/r:SPEC-OBJECT",
            NS,
        )
        self.assertEqual(len(spec_objects), 0)


if __name__ == "__main__":
    unittest.main()
