"""API routes — all /v1/ endpoints."""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

import structlog

from diagram_forge.api import schemas
from diagram_forge.api.auth import APIKeyMiddleware
from diagram_forge.api.errors import error_response, ERR_CIRCUIT_OPEN, ERR_UPSTREAM_ERROR
from diagram_forge.models.job import JobStatus, job_store
from diagram_forge.pipeline.text import run_job
from diagram_forge.services.storage import StorageService
from diagram_forge.services.rate_limiter import RateLimiter
from diagram_forge.exporters.excalidraw import export_to_excalidraw
from diagram_forge.exporters.drawio import export_to_drawio
from diagram_forge.exporters.svg import export_to_svg

logger = structlog.get_logger("diagram_forge.routes")

router = APIRouter()
storage = StorageService()
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Generation ──────────────────────────────────────────────────────────────

@router.post("/generate/text", response_model=schemas.GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_text(
    request: Request,
    body: schemas.TextGenerateRequest,
    background_tasks: BackgroundTasks,
) -> schemas.GenerateResponse:
    """Generate a diagram from text description."""

    # Rate limiting
    api_key = request.headers.get("X-API-Key", "")
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.check(api_key, client_ip)
    if not allowed:
        return error_response(
            code="RATE_LIMITED",
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            retryable=True,
            retry_after=retry_after,
        )

    # Create job
    job = job_store.create(
        input_modality="text",
        diagram_type=body.diagram_type,
    )

    # Ensure directories exist
    storage.ensure_directories()

    # Run pipeline in background
    background_tasks.add_task(
        run_job,
        job,
        body.text,
        storage,
    )

    logger.info(
        "generate_text_request",
        job_id=job.job_id,
        diagram_type=body.diagram_type.value,
        text_length=len(body.text),
    )

    return schemas.GenerateResponse(
        job_id=job.job_id,
        status=JobStatus.PENDING,
        message="Job queued for processing",
        poll_url=f"/v1/jobs/{job.job_id}",
    )


# ─── Job Status ──────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=schemas.JobStatusResponse)
async def get_job_status(job_id: str) -> schemas.JobStatusResponse:
    """Get the status of a diagram generation job."""

    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    response = schemas.JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=str(job.created_at),
        updated_at=str(job.updated_at) if job.updated_at else None,
        diagram_type=job.diagram_type,
        error_code=job.error_code,
        error_message=job.error_message,
    )

    if job.status == JobStatus.COMPLETED:
        response.result_url = f"/v1/jobs/{job_id}/download/excalidraw"

    return response


# ─── Download ────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/download/{format}")
async def download_diagram(job_id: str, format: str) -> FileResponse:
    """
    Download the completed diagram.

    Supported formats:
    - excalidraw: Excalidraw JSON file
    - drawio: Draw.io XML file
    - svg: SVG file
    """

    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job not ready. Status: {job.status.value}",
        )

    if job.result_filename is None:
        raise HTTPException(status_code=500, detail="Job has no result file")

    # Read the source Excalidraw JSON
    try:
        source_data = storage.read_output(job_id, job.result_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Result file not found")

    import json
    diagram_data = json.loads(source_data)

    # Export to requested format
    if format == "excalidraw":
        content = export_to_excalidraw(diagram_data)
        filename = f"diagram-{job_id[:8]}.excalidraw.json"
        media_type = "application/json"

    elif format == "drawio":
        content = export_to_drawio(diagram_data)
        filename = f"diagram-{job_id[:8]}.drawio.xml"
        media_type = "application/xml"

    elif format == "svg":
        content = export_to_svg(diagram_data)
        filename = f"diagram-{job_id[:8]}.svg"
        media_type = "image/svg+xml"

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported: excalidraw, drawio, svg",
        )

    # Return as file download
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Data-Retention": "24h",
        },
    )
