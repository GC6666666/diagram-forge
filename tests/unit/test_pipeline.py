"""Unit tests for text pipeline."""

import pytest


class TestExtractJSON:
    """Tests for JSON extraction from Claude responses."""

    def test_extract_from_code_block(self):
        from diagram_forge.pipeline.text import extract_json

        text = '''
        Here's the diagram:

        ```json
        {
          "elements": [
            {"id": "box1", "type": "rectangle", "x": 100, "y": 100}
          ]
        }
        ```
        '''
        result = extract_json(text)
        assert result is not None
        assert "elements" in result
        assert len(result["elements"]) == 1

    def test_extract_raw_json(self):
        from diagram_forge.pipeline.text import extract_json

        text = '{"elements": [{"id": "a", "type": "rectangle"}]}'
        result = extract_json(text)
        assert result is not None
        assert len(result["elements"]) == 1

    def test_extract_with_preceding_text(self):
        from diagram_forge.pipeline.text import extract_json

        text = 'Here is the diagram you requested:\n{"elements": []}\nLet me know if you need changes.'
        result = extract_json(text)
        assert result is not None

    def test_invalid_json_returns_none(self):
        from diagram_forge.pipeline.text import extract_json

        assert extract_json("not json at all") is None
        assert extract_json("") is None


class TestValidateExcalidraw:
    """Tests for Excalidraw JSON validation."""

    def test_valid_minimal(self):
        from diagram_forge.pipeline.text import validate_excalidraw

        data = {
            "elements": [
                {"id": "a", "type": "rectangle", "x": 0, "y": 0},
            ]
        }
        errors = validate_excalidraw(data)
        assert len(errors) == 0

    def test_missing_elements(self):
        from diagram_forge.pipeline.text import validate_excalidraw

        errors = validate_excalidraw({})
        assert "Missing 'elements'" in errors[0]

    def test_empty_elements(self):
        from diagram_forge.pipeline.text import validate_excalidraw

        errors = validate_excalidraw({"elements": []})
        assert "empty" in errors[0].lower()

    def test_unknown_type(self):
        from diagram_forge.pipeline.text import validate_excalidraw

        data = {
            "elements": [
                {"id": "a", "type": "unicorn", "x": 0, "y": 0},
            ]
        }
        errors = validate_excalidraw(data)
        assert any("unknown" in e.lower() for e in errors)

    def test_valid_multiple_shapes(self):
        from diagram_forge.pipeline.text import validate_excalidraw

        data = {
            "elements": [
                {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 100, "height": 50},
                {"id": "b", "type": "ellipse", "x": 200, "y": 0},
                {"id": "c", "type": "text", "x": 50, "y": 150, "text": "Hello"},
                {"id": "d", "type": "arrow", "x": 50, "y": 60},
            ]
        }
        errors = validate_excalidraw(data)
        assert len(errors) == 0
