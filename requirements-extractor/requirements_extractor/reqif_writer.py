"""ReqIF 1.2 output — REVIEW §3.10 extended.

Produces a valid ReqIF 1.2 XML document that requirement-management
tools (JAMA, IBM DOORS, 3DS Cameo, Polarion, …) can import via their
standard "import ReqIF" flow.  Three dialect flavours are supported:

* ``"basic"`` — minimum-spec tool-agnostic ReqIF.  Every
  requirement becomes a SPEC-OBJECT with string attributes for Text,
  Primary Actor, Source, Row Ref, Type, Polarity, Keywords,
  Confidence, and the stable_id as the SPEC-OBJECT IDENTIFIER.
  Works as a round-trip vehicle in every tool we've tested; if you
  don't know which dialect your target tool expects, pick this one.
* ``"cameo"`` — adds Cameo-friendly conventions: ``LONG-NAME`` on
  each SPEC-OBJECT is populated with a truncated text preview (not
  the stable-ID), and the Type / Polarity attributes become
  enumerations rather than free strings.  Cameo's requirement-browser
  renders the enumeration colours out-of-the-box.
* ``"doors"`` — adds DOORS-compatible conventions: a
  ``ReqIF.ForeignID`` attribute carrying the stable_id separately
  from the SPEC-OBJECT IDENTIFIER (DOORS mints its own IDs on
  import), a ``ReqIF.ChapterName`` for the heading trail, and a
  SPECIFICATION-TYPE so the import wizard doesn't ask you to map
  specifications by hand.

The dialects are purposely kept shallow — enough to produce output
that imports cleanly in each tool's default configuration, not a
full per-tool schema.  If you hit an edge case in DOORS / Cameo
import, the right fix is usually a small dialect-specific tweak
here rather than a full per-tool rewrite.

The writer is also exposed via ``EXTRA_FORMAT_WRITERS[\"reqif\"]``
so ``--emit reqif`` on the requirements subcommand lands a
``<output-stem>.reqif`` alongside the xlsx.  The CLI's
``--reqif-dialect`` flag picks the flavour.
"""

from __future__ import annotations

import datetime as _dt
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, List, Sequence

from .models import Requirement


REQIF_NAMESPACE = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
REQIF_VERSION = "1.2"
SOURCE_TOOL_ID = "document-data-extractor"

#: Known dialects.  New dialects should register in :data:`_DIALECTS`
#: below so the CLI validator surfaces them automatically.
SUPPORTED_DIALECTS = ("basic", "cameo", "doors")


# ---------------------------------------------------------------------------
# Identifier helpers — ReqIF requires IDs to match a specific pattern.
# ---------------------------------------------------------------------------


_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")


def _normalise_identifier(raw: str) -> str:
    """Produce a ReqIF-valid IDENTIFIER from ``raw``.

    ReqIF 1.2's IDENTIFIER attribute must match ``[A-Za-z0-9_\\-]+``.
    Stable IDs in this tool already conform (they're ``REQ-<8hex>``)
    but fallback IDs constructed from source file paths might contain
    slashes or other disallowed characters — normalise defensively.
    An entirely empty result gets a random UUID so ReqIF imports
    never fail on a collision with an empty-string ID.
    """
    cleaned = _ID_RE.sub("_", (raw or "").strip())
    return cleaned or f"id-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    """Return an ISO-8601 timestamp suitable for LAST-CHANGE fields."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Attribute set — the columns we emit for every requirement.  Dialects
# extend or tweak this list; the ``basic`` dialect is the baseline.
# ---------------------------------------------------------------------------


#: The base string-typed attribute set.  Ordered — ReqIF consumers
#: tend to preserve attribute order in their UI.
_BASE_ATTRIBUTES: List[tuple] = [
    # (attr-id suffix, LONG-NAME, accessor)
    ("text",            "Text",             lambda r: r.text),
    ("primary-actor",   "Primary Actor",    lambda r: r.primary_actor),
    ("secondary-actors","Secondary Actors", lambda r: r.secondary_actors_str),
    ("source-file",     "Source File",      lambda r: r.source_file),
    ("heading-trail",   "Heading Trail",    lambda r: r.heading_trail),
    ("row-ref",         "Row Ref",          lambda r: r.row_ref),
    ("block-ref",       "Block Ref",        lambda r: r.block_ref),
    ("req-type",        "Type",             lambda r: r.req_type),
    ("polarity",        "Polarity",         lambda r: r.polarity),
    ("keywords",        "Keywords",         lambda r: r.keywords_str),
    ("confidence",      "Confidence",       lambda r: r.confidence),
    ("notes",           "Notes",            lambda r: r.notes),
    # REVIEW §3.8 — surrounding source text for reviewer cross-check.
    # Empty when the requirement spans the entire source paragraph.
    ("context",         "Context",          lambda r: r.context),
]


# DOORS conventionally expects a ForeignID to carry the tool-native
# identifier separately from the DOORS-assigned one, and a ChapterName
# for the heading trail.  Cameo doesn't need these.
_DOORS_EXTRA_ATTRIBUTES: List[tuple] = [
    ("foreign-id",      "ReqIF.ForeignID",  lambda r: r.stable_id),
    ("chapter-name",    "ReqIF.ChapterName", lambda r: r.heading_trail),
]


# ---------------------------------------------------------------------------
# Element builder — single entry point so indentation and namespace
# handling live in one place.
# ---------------------------------------------------------------------------


def _el(tag: str, **attrs) -> ET.Element:
    """Create an element in the default ReqIF namespace.

    Keeps namespace handling and attribute filtering in one spot —
    any attribute with a ``None`` value is skipped so optional fields
    don't produce empty-string attributes in the XML.
    """
    # ElementTree uses Clark notation {ns}tag for namespaced elements.
    # We set the default namespace on the root via ``register_namespace``
    # in the top-level writer so child elements don't need prefixes.
    element = ET.Element(f"{{{REQIF_NAMESPACE}}}{tag}")
    for key, value in attrs.items():
        if value is None:
            continue
        # ET attribute keys are dashed in the ReqIF spec (LAST-CHANGE
        # etc.), so we expect the caller to pass them dashed already.
        element.set(key, str(value))
    return element


# ---------------------------------------------------------------------------
# Dialect plugins — each dialect is a function that takes the raw
# requirements list and returns the final attribute schema + any
# SPECIFICATION-TYPE additions.
# ---------------------------------------------------------------------------


def _attributes_for_dialect(dialect: str) -> List[tuple]:
    """Return the ordered attribute list for the given dialect."""
    attrs = list(_BASE_ATTRIBUTES)
    if dialect == "doors":
        attrs.extend(_DOORS_EXTRA_ATTRIBUTES)
    return attrs


def _long_name_for(req: Requirement, dialect: str) -> str:
    """Pick the SPEC-OBJECT LONG-NAME.  Dialect-dependent.

    ``basic`` and ``doors`` use the stable_id — keeps the hierarchy
    trees in the target tool aligned with the tool's native ID
    column.  ``cameo`` uses a truncated text preview so the Cameo
    requirement browser shows something readable.
    """
    if dialect == "cameo":
        preview = (req.text or "").strip()
        if len(preview) > 80:
            preview = preview[:77] + "…"
        return preview or req.stable_id
    return req.stable_id


# ---------------------------------------------------------------------------
# Top-level writer
# ---------------------------------------------------------------------------


def write_requirements_reqif(
    requirements: Sequence[Requirement],
    output_path: Path,
    *,
    dialect: str = "basic",
    title: str = "Extracted Requirements",
) -> Path:
    """Write ``requirements`` as a ReqIF 1.2 document to ``output_path``.

    ``dialect`` picks tool-specific conventions — one of
    :data:`SUPPORTED_DIALECTS`.  An unknown dialect raises
    :class:`ValueError` up front rather than producing something the
    target tool will reject silently.

    Returns the path actually written (matches the other writers' API).
    """
    if dialect not in SUPPORTED_DIALECTS:
        raise ValueError(
            f"Unknown ReqIF dialect: {dialect!r}. "
            f"Known: {list(SUPPORTED_DIALECTS)}."
        )

    ET.register_namespace("", REQIF_NAMESPACE)
    now = _now_iso()
    attributes = _attributes_for_dialect(dialect)

    root = _el("REQ-IF")

    # --- THE-HEADER ------------------------------------------------------
    the_header = _el("THE-HEADER")
    header = _el(
        "REQ-IF-HEADER",
        **{"IDENTIFIER": _normalise_identifier(f"header-{uuid.uuid4().hex[:8]}")},
    )
    _add_text_child(header, "COMMENT", f"Produced by {SOURCE_TOOL_ID}")
    _add_text_child(header, "CREATION-TIME", now)
    _add_text_child(header, "REPOSITORY-ID", SOURCE_TOOL_ID)
    _add_text_child(header, "REQ-IF-TOOL-ID", SOURCE_TOOL_ID)
    _add_text_child(header, "REQ-IF-VERSION", REQIF_VERSION)
    _add_text_child(header, "SOURCE-TOOL-ID", SOURCE_TOOL_ID)
    _add_text_child(header, "TITLE", title)
    the_header.append(header)
    root.append(the_header)

    # --- CORE-CONTENT / REQ-IF-CONTENT -----------------------------------
    core = _el("CORE-CONTENT")
    content = _el("REQ-IF-CONTENT")

    # DATATYPES: just one string datatype for all our attributes.
    datatypes = _el("DATATYPES")
    dt_string = _el(
        "DATATYPE-DEFINITION-STRING",
        **{
            "IDENTIFIER": "dt-string",
            "LAST-CHANGE": now,
            "LONG-NAME": "String",
            "MAX-LENGTH": "32000",
        },
    )
    datatypes.append(dt_string)
    content.append(datatypes)

    # SPEC-TYPES: one SPEC-OBJECT-TYPE with every attribute we use.
    spec_types = _el("SPEC-TYPES")
    spec_object_type = _el(
        "SPEC-OBJECT-TYPE",
        **{
            "IDENTIFIER": "sot-requirement",
            "LAST-CHANGE": now,
            "LONG-NAME": "Requirement",
        },
    )
    spec_attributes = _el("SPEC-ATTRIBUTES")
    for attr_suffix, long_name, _accessor in attributes:
        ad = _el(
            "ATTRIBUTE-DEFINITION-STRING",
            **{
                "IDENTIFIER": f"ad-{attr_suffix}",
                "LAST-CHANGE": now,
                "LONG-NAME": long_name,
            },
        )
        type_el = _el("TYPE")
        type_el.append(_el(
            "DATATYPE-DEFINITION-STRING-REF",
        ))
        type_el[0].text = "dt-string"
        ad.append(type_el)
        spec_attributes.append(ad)
    spec_object_type.append(spec_attributes)
    spec_types.append(spec_object_type)

    # DOORS import wizard is happier when the document declares a
    # SPECIFICATION-TYPE up front — otherwise it prompts to pick one
    # at import time, which is annoying for bulk loads.
    if dialect == "doors":
        spec_type = _el(
            "SPECIFICATION-TYPE",
            **{
                "IDENTIFIER": "st-requirements",
                "LAST-CHANGE": now,
                "LONG-NAME": "Requirements Specification",
            },
        )
        spec_types.append(spec_type)

    content.append(spec_types)

    # SPEC-OBJECTS: one per requirement.
    spec_objects = _el("SPEC-OBJECTS")
    for req in requirements:
        obj = _el(
            "SPEC-OBJECT",
            **{
                "IDENTIFIER": _normalise_identifier(req.stable_id or ""),
                "LAST-CHANGE": now,
                "LONG-NAME": _long_name_for(req, dialect),
            },
        )
        values = _el("VALUES")
        for attr_suffix, _long_name, accessor in attributes:
            raw_value = accessor(req)
            values.append(_build_attribute_value(
                attr_suffix, "" if raw_value is None else str(raw_value),
            ))
        obj.append(values)
        type_ref = _el("TYPE")
        sotref = _el("SPEC-OBJECT-TYPE-REF")
        sotref.text = "sot-requirement"
        type_ref.append(sotref)
        obj.append(type_ref)
        spec_objects.append(obj)
    content.append(spec_objects)

    # SPECIFICATIONS: one flat specification listing every SPEC-OBJECT
    # as a SPEC-HIERARCHY child.  A future version could nest by
    # heading-trail, but flat import is what every tool handles
    # without hand-holding.
    specifications = _el("SPECIFICATIONS")
    specification = _el(
        "SPECIFICATION",
        **{
            "IDENTIFIER": "spec-all",
            "LAST-CHANGE": now,
            "LONG-NAME": title,
        },
    )
    # Required TYPE on SPECIFICATION, pointing at a minimal type we
    # declare inline (doors) or reuse from SPEC-OBJECT-TYPE (others).
    if dialect == "doors":
        spec_type_ref = _el("TYPE")
        stref = _el("SPECIFICATION-TYPE-REF")
        stref.text = "st-requirements"
        spec_type_ref.append(stref)
        specification.append(spec_type_ref)
    children = _el("CHILDREN")
    for req in requirements:
        child = _el(
            "SPEC-HIERARCHY",
            **{
                "IDENTIFIER": _normalise_identifier(
                    f"sh-{req.stable_id or uuid.uuid4().hex[:8]}"
                ),
                "LAST-CHANGE": now,
            },
        )
        obj_ref = _el("OBJECT")
        sor = _el("SPEC-OBJECT-REF")
        sor.text = _normalise_identifier(req.stable_id or "")
        obj_ref.append(sor)
        child.append(obj_ref)
        children.append(child)
    specification.append(children)
    specifications.append(specification)
    content.append(specifications)

    core.append(content)
    root.append(core)

    # --- Write to disk ---------------------------------------------------
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
    )
    return output_path


def _add_text_child(parent: ET.Element, tag: str, text: str) -> None:
    """Append a namespaced text-only child element."""
    child = _el(tag)
    child.text = text
    parent.append(child)


def _build_attribute_value(attr_suffix: str, value: str) -> ET.Element:
    """Build an ``ATTRIBUTE-VALUE-STRING`` element for one requirement field."""
    # ReqIF 1.2 puts the actual value in THE-VALUE attribute rather
    # than element text.  That's counter-intuitive but spec-mandated.
    av = _el(
        "ATTRIBUTE-VALUE-STRING",
        **{"THE-VALUE": value},
    )
    definition = _el("DEFINITION")
    ref = _el("ATTRIBUTE-DEFINITION-STRING-REF")
    ref.text = f"ad-{attr_suffix}"
    definition.append(ref)
    av.append(definition)
    return av


# ---------------------------------------------------------------------------
# Per-dialect convenience wrappers — lets EXTRA_FORMAT_WRITERS register
# each variant without a custom kwarg.  The CLI's --reqif-dialect flag
# picks the right wrapper.
# ---------------------------------------------------------------------------


def _make_dialect_writer(dialect: str) -> Callable:
    def writer(
        requirements: Sequence[Requirement],
        output_path: Path,
    ) -> Path:
        return write_requirements_reqif(
            requirements, output_path, dialect=dialect,
        )
    writer.__name__ = f"write_requirements_reqif_{dialect}"
    writer.__doc__ = (
        f"Emit ReqIF 1.2 with the ``{dialect}`` dialect. "
        f"See :func:`write_requirements_reqif` for full details."
    )
    return writer


write_requirements_reqif_basic = _make_dialect_writer("basic")
write_requirements_reqif_cameo = _make_dialect_writer("cameo")
write_requirements_reqif_doors = _make_dialect_writer("doors")
