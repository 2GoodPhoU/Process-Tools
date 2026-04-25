"""Native Visio (.vsdx) emitter — Phase 2 deliverable.

A `.vsdx` is an Office Open XML (OOXML) package: a zip archive
containing several XML parts. Generating one from scratch is a fair
chunk of XML, but only one Visio page with a handful of shapes and
connectors is needed for a useful skeleton.

Layout strategy:

- Each actor becomes a column in the diagram (one column per
  swimlane). Activities and gateways within an actor stack vertically.
- Activities → Visio shape NameU=``"Process"`` (rectangle).
- Gateways  → Visio shape NameU=``"Decision"`` (diamond).
- Sequence-flow edges → Visio NameU=``"Dynamic connector"`` shapes
  with ``Connect`` glue tying them to the source / target shapes.

Why these specific NameU values? They match the default rules in
TIBCO Nimbus's Visio-import rules file (per the user-guide pages 311-
314): ``Process`` → Rectangle, ``Decision`` → Decision, ``Dynamic
connector`` → Straight/Dog-leg Line. So when Eric drops the .vsdx
into Nimbus via File → Import/Export → Import from Visio, the shapes
land on the canvas as the right Nimbus types without any rules-file
tweaking.

This emitter does NOT yet emit swimlane band shapes — that's a v2
addition. Activities are still grouped in actor columns visually, just
without the rectangular band overlay.

The XML is hand-built rather than via ``xml.etree.ElementTree`` so the
output stays byte-stable across runs (ET's attribute-ordering varies
across Python minor versions).
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
from xml.sax.saxutils import escape as xml_escape, quoteattr

from ..models import Activity, Gateway, Skeleton


# Geometry, in Visio inches (Visio's native unit).
_COL_WIDTH = 4.0          # horizontal distance between actor columns
_ROW_HEIGHT = 1.2         # vertical distance between consecutive nodes
_SHAPE_WIDTH = 2.5
_ACTIVITY_HEIGHT = 0.75
_GATEWAY_HEIGHT = 0.85
_PAGE_LEFT_MARGIN = 1.0
_PAGE_TOP = 11.0          # nodes hang below this, growing downward


# OOXML content-types and relationship URIs. These strings are exactly
# what Visio expects — don't reformat them.
_CT_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>
<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>
'''

_TOP_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>
'''

_DOCUMENT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>
</Relationships>
'''

_PAGES_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>
</Relationships>
'''

_DOCUMENT_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2012/main"
               xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<DocumentSettings TopPage="0" DefaultTextStyle="3" DefaultLineStyle="3" DefaultFillStyle="3" DefaultGuideStyle="4">
<GlyphSettingsEnabled>0</GlyphSettingsEnabled>
</DocumentSettings>
</VisioDocument>
'''

_PAGES_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<Page ID="0" NameU="Page-1" Name="Page-1" ViewScale="1" ViewCenterX="4.25" ViewCenterY="5.5">
<PageSheet>
<Cell N="PageWidth" V="11"/>
<Cell N="PageHeight" V="11"/>
<Cell N="ShdwOffsetX" V="0.125"/>
<Cell N="ShdwOffsetY" V="-0.125"/>
<Cell N="PageScale" V="1"/>
<Cell N="DrawingScale" V="1"/>
<Cell N="DrawingSizeType" V="0"/>
<Cell N="DrawingScaleType" V="0"/>
</PageSheet>
<Rel r:id="rId1"/>
</Page>
</Pages>
'''


def _app_xml(title: str) -> str:
    safe_title = xml_escape(title)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>nimbus-skeleton</Application>
<AppVersion>0.1.0</AppVersion>
<Template/>
<Manager/>
<Company/>
<HyperlinkBase/>
</Properties>
'''


def _core_xml(title: str) -> str:
    safe_title = xml_escape(title)
    # Use a fixed timestamp so two runs over the same input produce
    # byte-identical output (the manifest already has this property).
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>{safe_title}</dc:title>
<dc:creator>nimbus-skeleton</dc:creator>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-04-24T00:00:00Z</dcterms:created>
</cp:coreProperties>
'''


def _shape_xml(
    shape_id: int,
    name_u: str,
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    """A single Visio shape (Process / Decision / Terminator)."""

    safe_text = xml_escape(text)
    safe_name = quoteattr(name_u)
    return f'''<Shape ID="{shape_id}" NameU={safe_name} Name={safe_name} Type="Shape" LineStyle="3" FillStyle="3" TextStyle="3">
<Cell N="PinX" V="{x:.4f}"/>
<Cell N="PinY" V="{y:.4f}"/>
<Cell N="Width" V="{width:.4f}"/>
<Cell N="Height" V="{height:.4f}"/>
<Cell N="LocPinX" F="Width*0.5"/>
<Cell N="LocPinY" F="Height*0.5"/>
<Text>{safe_text}</Text>
</Shape>'''


def _connector_xml(
    shape_id: int,
    src_id: int,
    tgt_id: int,
) -> str:
    """A Dynamic connector shape with two glue Connects to its endpoints."""

    return f'''<Shape ID="{shape_id}" NameU="Dynamic connector" Name="Dynamic connector" Type="Shape" LineStyle="3" FillStyle="3" TextStyle="3">
<Cell N="BeginX" V="0"/>
<Cell N="BeginY" V="0"/>
<Cell N="EndX" V="0"/>
<Cell N="EndY" V="0"/>
</Shape>'''


def _connect_xml(
    connector_id: int,
    src_id: int,
    tgt_id: int,
) -> str:
    """A pair of Connect elements gluing the connector's BeginX/EndX cells
    to the source / target shapes' PinX cells."""

    return f'''<Connect FromSheet="{connector_id}" FromCell="BeginX" FromPart="9" ToSheet="{src_id}" ToCell="PinX" ToPart="3"/>
<Connect FromSheet="{connector_id}" FromCell="EndX" FromPart="12" ToSheet="{tgt_id}" ToCell="PinX" ToPart="3"/>'''


def _layout(skeleton: Skeleton) -> Tuple[
    Dict[str, Tuple[float, float]],
    Dict[str, str],
]:
    """Compute (x, y) Pin positions for every node and a name_u
    classification ('Process' / 'Decision'). Returns (positions,
    name_u_map) keyed by stable_id."""

    positions: Dict[str, Tuple[float, float]] = {}
    name_u: Dict[str, str] = {}

    actor_to_col = {actor: i for i, actor in enumerate(skeleton.actors)}

    # Track per-actor row counter so successive nodes within one
    # swimlane stack vertically.
    actor_row: Dict[str, int] = {actor: 0 for actor in skeleton.actors}

    # Walk activities and gateways in declaration order; that's also
    # source-document order.
    for activity in skeleton.activities:
        col = actor_to_col.get(activity.actor, 0)
        row = actor_row.get(activity.actor, 0)
        x = _PAGE_LEFT_MARGIN + col * _COL_WIDTH + _SHAPE_WIDTH / 2
        y = _PAGE_TOP - row * _ROW_HEIGHT - _ACTIVITY_HEIGHT / 2
        positions[activity.stable_id] = (x, y)
        name_u[activity.stable_id] = "Process"
        actor_row[activity.actor] = row + 1

    for gateway in skeleton.gateways:
        col = actor_to_col.get(gateway.actor, 0)
        row = actor_row.get(gateway.actor, 0)
        x = _PAGE_LEFT_MARGIN + col * _COL_WIDTH + _SHAPE_WIDTH / 2
        y = _PAGE_TOP - row * _ROW_HEIGHT - _GATEWAY_HEIGHT / 2
        positions[gateway.stable_id] = (x, y)
        name_u[gateway.stable_id] = "Decision"
        actor_row[gateway.actor] = row + 1

    return positions, name_u


def render_page1(skeleton: Skeleton, title: str = "Process Skeleton") -> str:
    """Build the page1.xml content for the skeleton."""

    positions, name_u_map = _layout(skeleton)

    # Stable id → numeric Visio shape id. Visio ids are 1-based ints.
    next_id = 1
    visio_ids: Dict[str, int] = {}

    shapes_xml: List[str] = []
    connects_xml: List[str] = []

    for activity in skeleton.activities:
        x, y = positions[activity.stable_id]
        height = _ACTIVITY_HEIGHT
        visio_ids[activity.stable_id] = next_id
        shapes_xml.append(
            _shape_xml(
                shape_id=next_id,
                name_u=name_u_map[activity.stable_id],
                text=activity.label,
                x=x,
                y=y,
                width=_SHAPE_WIDTH,
                height=height,
            )
        )
        next_id += 1

    for gateway in skeleton.gateways:
        x, y = positions[gateway.stable_id]
        visio_ids[gateway.stable_id] = next_id
        shapes_xml.append(
            _shape_xml(
                shape_id=next_id,
                name_u=name_u_map[gateway.stable_id],
                text=gateway.condition,
                x=x,
                y=y,
                width=_SHAPE_WIDTH,
                height=_GATEWAY_HEIGHT,
            )
        )
        next_id += 1

    # Connectors between flow source / target.
    for src, tgt in skeleton.flows:
        if src not in visio_ids or tgt not in visio_ids:
            continue
        connector_id = next_id
        shapes_xml.append(
            _connector_xml(connector_id, visio_ids[src], visio_ids[tgt])
        )
        connects_xml.append(
            _connect_xml(connector_id, visio_ids[src], visio_ids[tgt])
        )
        next_id += 1

    safe_title = xml_escape(title)
    parts: List[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    parts.append(
        '<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    )
    parts.append("<Shapes>")
    parts.extend(shapes_xml)
    parts.append("</Shapes>")
    if connects_xml:
        parts.append("<Connects>")
        parts.extend(connects_xml)
        parts.append("</Connects>")
    parts.append("</PageContents>")
    return "\n".join(parts) + "\n"


def write(skeleton: Skeleton, output_path, title: str = "Process Skeleton") -> None:
    """Write a complete .vsdx package containing the skeleton."""

    output_path = Path(output_path)
    page1_xml = render_page1(skeleton, title=title)

    # ZIP_DEFLATED keeps the file small; ZIP_STORED would also be valid.
    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        zf.writestr("[Content_Types].xml", _CT_XML)
        zf.writestr("_rels/.rels", _TOP_RELS)
        zf.writestr("docProps/app.xml", _app_xml(title))
        zf.writestr("docProps/core.xml", _core_xml(title))
        zf.writestr("visio/document.xml", _DOCUMENT_XML)
        zf.writestr("visio/_rels/document.xml.rels", _DOCUMENT_RELS)
        zf.writestr("visio/pages/pages.xml", _PAGES_XML)
        zf.writestr("visio/pages/_rels/pages.xml.rels", _PAGES_RELS)
        zf.writestr("visio/pages/page1.xml", page1_xml)
