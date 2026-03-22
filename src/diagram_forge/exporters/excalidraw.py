"""Excalidraw JSON exporter."""

import json
from typing import Any


def export_to_excalidraw(diagram_data: dict, pretty: bool = True) -> bytes:
    """
    Export a diagram to Excalidraw JSON format.

    Args:
        diagram_data: Dict with 'elements' key or raw elements list
        pretty: Whether to pretty-print the JSON

    Returns:
        UTF-8 encoded Excalidraw JSON bytes
    """
    # Normalize input
    if "elements" in diagram_data:
        elements = diagram_data["elements"]
    else:
        elements = diagram_data

    excalidraw_doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "diagram-forge",
        "elements": elements,
    }

    indent = 2 if pretty else None
    return json.dumps(excalidraw_doc, indent=indent, ensure_ascii=False).encode("utf-8")


def validate_excalidraw_elements(elements: list[dict]) -> list[str]:
    """
    Validate Excalidraw elements for export compatibility.

    Returns list of warnings (not errors) — we try to fix issues.
    """
    warnings = []
    valid_types = {"rectangle", "ellipse", "diamond", "text", "arrow", "line", "freedraw"}

    for i, elem in enumerate(elements):
        if not isinstance(elem, dict):
            warnings.append(f"Element {i}: not a dict, skipping")
            continue

        elem_type = elem.get("type")
        if elem_type not in valid_types:
            warnings.append(f"Element {i}: unknown type '{elem_type}'")

        # Ensure required fields exist
        if "id" not in elem:
            elem["id"] = f"elem-{i}"

        if "x" not in elem:
            warnings.append(f"Element {i}: missing 'x' coordinate")

        if "y" not in elem:
            warnings.append(f"Element {i}: missing 'y' coordinate")

    return warnings
