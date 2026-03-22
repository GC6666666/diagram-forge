"""SVG exporter (rendered, not semantic)."""

import xml.etree.ElementTree as ET
from typing import Any


def export_to_svg(diagram_data: dict) -> bytes:
    """
    Export a diagram to SVG format (rendered, not fully editable).

    This is a simple renderer that converts Excalidraw-style elements
    to SVG shapes. For full semantic SVG, a more sophisticated exporter
    is needed (Phase 6+).

    Elements mapping:
    - rectangle → <rect>
    - ellipse → <ellipse>
    - diamond → <polygon> (diamond shape)
    - text → <text>
    - arrow → <line> or <path>
    """

    if "elements" in diagram_data:
        elements = diagram_data["elements"]
    else:
        elements = diagram_data

    # Calculate bounding box
    min_x = min((e.get("x", 0) for e in elements if "x" in e), default=0)
    min_y = min((e.get("y", 0) for e in elements if "y" in e), default=0)
    max_x = max((e.get("x", 0) + e.get("width", 100) for e in elements if "x" in e), default=800)
    max_y = max((e.get("y", 0) + e.get("height", 60) for e in elements if "y" in e), default=600)

    padding = 40
    width = max_x - min_x + padding * 2
    height = max_y - min_y + padding * 2

    svg = ET.Element("svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(width),
        height=str(height),
        viewBox=f"{min_x - padding} {min_y - padding} {width} {height}",
    )

    # Background
    bg = ET.SubElement(svg, "rect",
        x=str(min_x - padding),
        y=str(min_y - padding),
        width=str(width),
        height=str(height),
        fill="white",
    )

    # Defs for arrow markers
    defs = ET.SubElement(svg, "defs")
    marker = ET.SubElement(defs, "marker",
        id="arrowhead",
        markerWidth="10",
        markerHeight="7",
        refX="10",
        refY="3.5",
        orient="auto",
    )
    ET.SubElement(marker, "polygon",
        points="0 0, 10 3.5, 0 7",
        fill="#000000",
    )

    # Process elements
    shape_map = {}  # id → element for binding

    for elem in elements:
        elem_type = elem.get("type")
        elem_id = elem.get("id", "")
        x = elem.get("x", 0)
        y = elem.get("y", 0)
        w = elem.get("width", 100)
        h = elem.get("height", 50)
        stroke = elem.get("strokeColor", "#000000")
        bg_color = elem.get("backgroundColor", "#ffffff")
        text = elem.get("text", "")
        shape_map[elem_id] = elem

        if elem_type == "rectangle":
            rect = ET.SubElement(svg, "rect",
                x=str(x), y=str(y),
                width=str(w), height=str(h),
                fill=bg_color,
                stroke=stroke,
                stroke_width="2",
                rx="4",
            )

        elif elem_type == "ellipse":
            cx = x + w / 2
            cy = y + h / 2
            ell = ET.SubElement(svg, "ellipse",
                cx=str(cx), cy=str(cy),
                rx=str(w / 2), ry=str(h / 2),
                fill=bg_color,
                stroke=stroke,
                stroke_width="2",
            )

        elif elem_type == "diamond":
            # Diamond as polygon
            pts = f"{x + w/2},{y} {x + w},{y + h/2} {x + w/2},{y + h} {x},{y + h/2}"
            poly = ET.SubElement(svg, "polygon",
                points=pts,
                fill=bg_color,
                stroke=stroke,
                stroke_width="2",
            )

        elif elem_type == "text":
            t_elem = ET.SubElement(svg, "text",
                x=str(x), y=str(y + 16),
                font_size="14",
                font_family="Arial, sans-serif",
                fill=stroke,
            )
            t_elem.text = str(text)

    # Second pass for arrows (so they render on top)
    for elem in elements:
        if elem.get("type") != "arrow":
            continue

        # Get bound elements
        start_id = elem.get("startBinding", {}).get("elementId")
        end_id = elem.get("endBinding", {}).get("elementId")

        start_elem = shape_map.get(start_id, {}) if start_id else {}
        end_elem = shape_map.get(end_id, {}) if end_id else {}

        x1 = elem.get("x", start_elem.get("x", 0) + start_elem.get("width", 0))
        y1 = elem.get("y", start_elem.get("y", 0) + start_elem.get("height", 0) / 2)
        x2 = elem.get("lastCommittedPoint", {}).get("x", end_elem.get("x", x1 + 100))
        y2 = elem.get("lastCommittedPoint", {}).get("y", end_elem.get("y", y1))

        line = ET.SubElement(svg, "line",
            x1=str(x1), y1=str(y1),
            x2=str(x2), y2=str(y2),
            stroke=elem.get("strokeColor", "#000000"),
            stroke_width="2",
            marker_end="url(#arrowhead)",
        )

    xml_str = ET.tostring(svg, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}\n'.encode("utf-8")
