"""Draw.io XML exporter."""

import xml.etree.ElementTree as ET
from typing import Any


def export_to_drawio(diagram_data: dict) -> bytes:
    """
    Export a diagram to Draw.io XML format.

    Draw.io uses mxGraphModel XML:
    <mxfile>
      <diagram>
        <mxGraphModel>
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            ... elements ...
          </root>
        </mxGraphModel>
      </diagram>
    </mxfile>

    Elements mapping:
    - rectangle → mxCell with style="rounded=1;whiteSpace=wrap"
    - ellipse → mxCell with style="ellipse;whiteSpace=wrap"
    - diamond → mxCell with style="rhombus;whiteSpace=wrap"
    - text → mxCell with style="text;html=1"
    - arrow → mxCell with style="edgeStyle=orthogonalEdgeStyle;rounded=0"
    """

    # Normalize input
    if "elements" in diagram_data:
        elements = diagram_data["elements"]
    else:
        elements = diagram_data

    # Build XML
    root = ET.Element("mxfile")
    diagram = ET.SubElement(root, "diagram", name="Diagram Forge Export")
    model = ET.SubElement(diagram, "mxGraphModel", dx="1000", dy="800", grid="1", guides="1")
    root_elem = ET.SubElement(model, "root")

    # Root cell
    ET.SubElement(root_elem, "mxCell", id="0")

    # Parent cell
    ET.SubElement(root_elem, "mxCell", id="1", parent="0")

    cell_id = 2
    vertex_id = 2

    style_map = {
        "rectangle": "rounded=1;whiteSpace=wrap;html=1;shape=rectangle",
        "ellipse": "ellipse;whiteSpace=wrap;html=1;shape=ellipse",
        "diamond": "rhombus;whiteSpace=wrap;html=1;shape=rhombus",
        "text": "text;html=1;align=center;verticalAlign=middle",
    }

    for elem in elements:
        elem_type = elem.get("type")
        if elem_type not in {"rectangle", "ellipse", "diamond", "text"}:
            continue

        x = elem.get("x", 0)
        y = elem.get("y", 0)
        w = elem.get("width", 120)
        h = elem.get("height", 50)
        text = elem.get("text", "")
        stroke = elem.get("strokeColor", "#000000")
        bg = elem.get("backgroundColor", "#ffffff")

        style = style_map.get(elem_type, "")
        if bg and bg != "#ffffff":
            style += f";fillColor={bg}"
        if stroke:
            style += f";strokeColor={stroke}"

        cell = ET.SubElement(root_elem, "mxCell",
            id=str(cell_id),
            value=str(text),
            style=style,
            vertex="1",
            parent="1"
        )

        # Geometry
        geo = ET.SubElement(cell, "mxGeometry",
            x=str(x),
            y=str(y),
            width=str(w),
            height=str(h),
            as_="geometry"
        )

        cell_id += 1
        vertex_id = cell_id

    # Handle arrows
    for elem in elements:
        if elem.get("type") != "arrow":
            continue

        x = elem.get("x", 0)
        y = elem.get("y", 0)

        cell = ET.SubElement(root_elem, "mxCell",
            id=str(cell_id),
            style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1",
            edge="1",
            parent="1",
            source=elem.get("startBinding", {}).get("elementId", "1"),
            target=elem.get("endBinding", {}).get("elementId", "1"),
            as_="geometry"
        )

        # Simple point-based geometry
        ET.SubElement(cell, "mxPoint", x=str(x + 50), y=str(y), as_="sourcePoint")
        ET.SubElement(cell, "mxPoint", x=str(x + 150), y=str(y + 50), as_="targetPoint")

        cell_id += 1

    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}\n'.encode("utf-8")
