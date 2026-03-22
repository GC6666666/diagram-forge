"""Unit tests for API schemas."""

import pytest
from pydantic import ValidationError


class TestTextGenerateRequest:
    """Tests for TextGenerateRequest schema."""

    def test_valid_request(self):
        from diagram_forge.api.schemas import TextGenerateRequest

        req = TextGenerateRequest(text="User logs in", diagram_type="architecture")
        assert req.text == "User logs in"
        assert req.diagram_type.value == "architecture"

    def test_default_diagram_type(self):
        from diagram_forge.api.schemas import TextGenerateRequest

        req = TextGenerateRequest(text="test")
        assert req.diagram_type.value == "architecture"

    def test_empty_text_rejected(self):
        from diagram_forge.api.schemas import TextGenerateRequest

        with pytest.raises(ValidationError):
            TextGenerateRequest(text="")

    def test_whitespace_only_rejected(self):
        from diagram_forge.api.schemas import TextGenerateRequest

        with pytest.raises(ValidationError):
            TextGenerateRequest(text="   ")

    def test_max_length(self):
        from diagram_forge.api.schemas import TextGenerateRequest

        long_text = "a" * 4001
        with pytest.raises(ValidationError):
            TextGenerateRequest(text=long_text)


class TestDiagramType:
    """Tests for DiagramType enum."""

    def test_all_types(self):
        from diagram_forge.api.schemas import DiagramType

        assert DiagramType.ARCHITECTURE.value == "architecture"
        assert DiagramType.SEQUENCE.value == "sequence"
        assert DiagramType.FLOWCHART.value == "flowchart"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses(self):
        from diagram_forge.models.job import JobStatus

        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
