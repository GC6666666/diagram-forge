"""Job state model."""

import asyncio
import enum
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger("diagram_forge.job")


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiagramType(str, enum.Enum):
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    FLOWCHART = "flowchart"


@dataclass
class Job:
    """In-memory job state. Persisted to jobs.jsonl for observability."""
    job_id: str
    status: JobStatus
    input_modality: str          # "text" | "voice" | "image"
    diagram_type: DiagramType
    created_at: float = field(default_factory=time.time)
    updated_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_filename: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d["status"] = JobStatus(d["status"])
        d["diagram_type"] = DiagramType(d["diagram_type"])
        return cls(**d)

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_jsonl(cls, line: str) -> "Job":
        return cls.from_dict(json.loads(line))


class JobStore:
    """
    In-memory job store with JSONL persistence for observability.
    v1: in-memory only. Future: Redis-backed.
    """

    def __init__(self, persist_path: Path | None = None):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._persist_path = persist_path
        self._persist_lock = asyncio.Lock()

    def create(self, input_modality: str, diagram_type: DiagramType) -> Job:
        """Create a new job."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            input_modality=input_modality,
            diagram_type=diagram_type,
        )
        self._jobs[job_id] = job
        logger.info("job_created", job_id=job_id, modality=input_modality, diagram_type=diagram_type.value)
        return job

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, job: Job) -> None:
        async with self._lock:
            job.updated_at = time.time()
            self._jobs[job.job_id] = job

    async def list_recent(self, limit: int = 100) -> list[Job]:
        async with self._lock:
            sorted_jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )
            return sorted_jobs[:limit]


# Global job store
job_store = JobStore()
