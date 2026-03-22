"""Text → diagram generation pipeline."""

import json
import re
import asyncio
from typing import Callable

import structlog

from diagram_forge.ai.client import ClaudeClient, get_claude_client, ClaudeAPIError
from diagram_forge.exporters.excalidraw import export_to_excalidraw
from diagram_forge.models.job import Job, JobStatus, job_store
from diagram_forge.services.storage import StorageService

logger = structlog.get_logger("diagram_forge.pipeline.text")


def extract_json(text: str) -> dict | None:
    """Extract JSON from Claude response, handling markdown fences."""
    # Try code blocks first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try raw
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def validate_excalidraw(data: dict) -> list[str]:
    """Validate Excalidraw JSON structure. Returns list of errors."""
    errors = []
    if not isinstance(data, dict):
        errors.append("Root must be object")
        return errors
    elements = data.get("elements")
    if elements is None:
        errors.append("Missing 'elements' array")
        return errors
    if not isinstance(elements, list):
        errors.append("'elements' must be array")
        return errors
    if len(elements) == 0:
        errors.append("'elements' array is empty")
        return errors
    valid_types = {"rectangle", "ellipse", "diamond", "text", "arrow", "line"}
    for i, elem in enumerate(elements[:50]):
        if not isinstance(elem, dict):
            errors.append(f"Element {i}: not an object")
            continue
        elem_type = elem.get("type")
        if elem_type not in valid_types:
            errors.append(f"Element {i}: unknown type '{elem_type}'")
    return errors


async def text_to_diagram_pipeline(
    job: Job,
    text: str,
    storage: StorageService,
    on_progress: Callable[[str], None] | None = None,
) -> str:
    """
    Full text → diagram pipeline.

    Steps:
    1. Call Claude with diagram prompt
    2. Parse JSON from response
    3. Validate Excalidraw structure
    4. Export to file

    Returns: path to output file
    """
    async def progress(msg: str):
        if on_progress:
            on_progress(msg)
        logger.info("pipeline_progress", job_id=job.job_id, step=msg)

    await progress("Generating diagram with Claude...")

    # Step 1: Call Claude
    client = get_claude_client()
    raw_response = await client.generate_diagram(
        prompt=text,
        diagram_type=job.diagram_type.value,
        timeout_seconds=20.0,
    )

    await progress("Parsing response...")

    # Step 2: Extract JSON
    parsed = extract_json(raw_response)
    if parsed is None:
        logger.error("json_parse_failed", job_id=job.job_id, raw_preview=raw_response[:200])
        raise ValueError(f"Failed to parse JSON from Claude response: {raw_response[:200]}")

    # Step 3: Validate
    validation_errors = validate_excalidraw(parsed)
    if validation_errors:
        logger.warning(
            "excalidraw_validation_warnings",
            job_id=job.job_id,
            errors=validation_errors[:5],
        )
        # Don't fail on warnings, just log them

    # Step 4: Write to storage
    await progress("Saving diagram...")

    # Ensure Excalidraw JSON structure
    excalidraw_data = {
        "type": "excalidraw",
        "version": 2,
        "source": "diagram-forge",
        "elements": parsed.get("elements", []),
    }

    output_path = storage.write_output(
        job.job_id,
        "diagram.excalidraw.json",
        json.dumps(excalidraw_data, indent=2).encode(),
    )

    await progress("Done!")
    logger.info(
        "pipeline_complete",
        job_id=job.job_id,
        elements=len(excalidraw_data["elements"]),
        output=str(output_path),
    )

    return str(output_path)


async def run_job(
    job: Job,
    text: str,
    storage: StorageService,
) -> None:
    """Run a job end-to-end. Updates job status as it progresses."""
    try:
        job.status = JobStatus.PROCESSING
        job.started_at = job.created_at  # approximate
        await job_store.update(job)

        output_path = await text_to_diagram_pipeline(job, text, storage)

        job.status = JobStatus.COMPLETED
        job.result_filename = "diagram.excalidraw.json"
        job.completed_at = job.created_at  # approximate
        await job_store.update(job)

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_code = getattr(e, "code", "INTERNAL_ERROR")
        job.error_message = str(e)
        await job_store.update(job)
        logger.error("job_failed", job_id=job.job_id, error=str(e))
