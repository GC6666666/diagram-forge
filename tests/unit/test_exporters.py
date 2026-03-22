"""Unit tests for exporters."""

import json


class TestExcalidrawExporter:
    """Tests for Excalidraw JSON exporter."""

    def test_export_elements(self):
        from diagram_forge.exporters.excalidraw import export_to_excalidraw

        data = {
            "elements": [
                {"id": "a", "type": "rectangle", "x": 100, "y": 50},
            ]
        }
        result = export_to_excalidraw(data)
        parsed = json.loads(result)

        assert parsed["type"] == "excalidraw"
        assert parsed["version"] == 2
        assert len(parsed["elements"]) == 1

    def test_export_raw_elements(self):
        from diagram_forge.exporters.excalidraw import export_to_excalidraw

        elements = [
            {"id": "a", "type": "rectangle", "x": 0, "y": 0},
            {"id": "b", "type": "arrow", "x": 50, "y": 25},
        ]
        result = export_to_excalidraw(elements)
        parsed = json.loads(result)
        assert len(parsed["elements"]) == 2


class TestDrawioExporter:
    """Tests for Draw.io XML exporter."""

    def test_export_rectangle(self):
        from diagram_forge.exporters.drawio import export_to_drawio

        data = {
            "elements": [
                {"id": "a", "type": "rectangle", "x": 100, "y": 50, "width": 120, "height": 60, "text": "Service"},
            ]
        }
        result = export_to_drawio(data)
        assert b"<mxfile>" in result
        assert b"rectangle" in result.lower()
        assert b"Service" in result

    def test_export_ellipse(self):
        from diagram_forge.exporters.drawio import export_to_drawio

        data = {
            "elements": [
                {"id": "a", "type": "ellipse", "x": 0, "y": 0, "width": 100, "height": 60, "text": "Actor"},
            ]
        }
        result = export_to_drawio(data)
        assert b"ellipse" in result

    def test_xml_declaration(self):
        from diagram_forge.exporters.drawio import export_to_drawio

        result = export_to_drawio({"elements": []})
        assert result.startswith(b'<?xml version="1.0"')


class TestSVGExporter:
    """Tests for SVG exporter."""

    def test_export_rectangle(self):
        from diagram_forge.exporters.svg import export_to_svg

        data = {
            "elements": [
                {"id": "a", "type": "rectangle", "x": 10, "y": 10, "width": 100, "height": 50},
            ]
        }
        result = export_to_svg(data)
        assert b"<svg" in result
        assert b"<rect" in result
        assert b'x="10"' in result

    def test_export_text(self):
        from diagram_forge.exporters.svg import export_to_svg

        data = {
            "elements": [
                {"id": "a", "type": "text", "x": 10, "y": 20, "text": "Hello World"},
            ]
        }
        result = export_to_svg(data)
        assert b"<text" in result
        assert b"Hello World" in result

    def test_svg_declaration(self):
        from diagram_forge.exporters.svg import export_to_svg

        result = export_to_svg({"elements": []})
        assert result.startswith(b'<?xml version="1.0"')
