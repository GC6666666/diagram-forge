"""Pydantic schemas for API requests and responses."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class DiagramType(str, Enum):
    """Supported diagram types."""
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    FLOWCHART = "flowchart"


class OutputFormat(str, Enum):
    """Supported output formats."""
    EXCALIDRAW = "excalidraw"
    DRAWIO = "drawio"
    SVG = "svg"


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Requests ────────────────────────────────────────────────────────────────

class TextGenerateRequest(BaseModel):
    """Request body for text-to-diagram generation."""

    text: Annotated[str, Field(
        min_length=1,
        max_length=4000,
        description="Text description of the diagram to generate",
    )]
    diagram_type: DiagramType = Field(
        default=DiagramType.ARCHITECTURE,
        description="Type of diagram to generate",
    )

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("text cannot be empty or whitespace only")
        return stripped


# ─── Responses ──────────────────────────────────────────────────────────────

class GenerateResponse(BaseModel):
    """Response from a generation request."""

    job_id: str = Field(description="Unique job ID for tracking")
    status: JobStatus = Field(default=JobStatus.PENDING)
    message: str = Field(default="Job created successfully")
    poll_url: str = Field(description="URL to poll for job status")


class JobStatusResponse(BaseModel):
    """Response for job status queries."""

    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str | None = None
    diagram_type: DiagramType | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_url: str | None = Field(
        default=None,
        description="URL to download the completed diagram"
    )

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error details")
    request_id: str | None = Field(default=None, description="Request ID for support")
    retryable: bool = Field(default=False, description="Can this be retried?")
    retry_after_seconds: int | None = Field(
        default=None,
        description="Seconds to wait before retrying"
    )
