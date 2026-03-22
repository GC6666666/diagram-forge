"""Storage and temp file management with 24h TTL cleanup."""

import os
import uuid
import asyncio
import threading
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger("diagram_forge.storage")


class StorageService:
    """
    Manages temporary file storage with 24h TTL.

    Directory layout:
      $DF_DATA_ROOT/
      ├── tmp/        — ephemeral input/output files
      ├── input/      — uploaded files during processing
      ├── output/     — completed diagrams
      └── logs/       — structured log files

    Files are cleaned up by:
    1. Immediate deletion after processing (success or failure)
    2. Background thread sweeping every 10 minutes for orphaned files
    """

    TTL_HOURS = 24

    def __init__(self, root: str | None = None):
        self.root = Path(root or os.environ.get("DF_DATA_ROOT", "/tmp/diagram-forge"))
        self.tmp = self.root / "tmp"
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

    def ensure_directories(self) -> None:
        """Create all required directories with correct permissions."""
        for d in [self.tmp, self.input_dir, self.output_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
            # Restrict to owner-only access
            d.chmod(0o700)
        logger.info("storage_directories_created", root=str(self.root))

    def start_cleanup_thread(self) -> None:
        """Start background thread that sweeps for expired files."""
        if self._cleanup_thread is not None:
            return
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("cleanup_thread_started", interval_minutes=10)

    def _cleanup_loop(self) -> None:
        """Background cleanup loop — runs every 10 minutes."""
        while not self._stop_cleanup.wait(timeout=600):  # 10 minutes
            self._sweep_expired()

    def _sweep_expired(self) -> int:
        """Delete all files older than 24 hours. Returns count deleted."""
        cutoff = datetime.now() - timedelta(hours=self.TTL_HOURS)
        deleted = 0
        for directory in [self.tmp, self.input_dir, self.output_dir]:
            for file in directory.iterdir():
                try:
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < cutoff:
                        file.unlink()
                        deleted += 1
                except OSError:
                    pass
        if deleted:
            logger.info("cleanup_sweep", deleted=deleted)
        return deleted

    def create_job_dirs(self, job_id: str) -> tuple[Path, Path]:
        """Create input and output directories for a job. Returns (input, output)."""
        job_input = self.input_dir / job_id
        job_output = self.output_dir / job_id
        job_input.mkdir(parents=True, exist_ok=True)
        job_output.mkdir(parents=True, exist_ok=True)
        return job_input, job_output

    def save_temp(self, job_id: str, filename: str, data: bytes) -> Path:
        """Save temp data. File is ephemeral — cleanup thread handles deletion."""
        path = self.tmp / f"{job_id}_{filename}"
        path.write_bytes(data)
        path.chmod(0o600)
        return path

    def cleanup_job(self, job_id: str) -> None:
        """Immediately delete all files for a job."""
        for directory in [self.tmp, self.input_dir, self.output_dir]:
            for file in directory.glob(f"{job_id}*"):
                try:
                    file.unlink()
                except OSError:
                    pass
        logger.info("job_cleaned_up", job_id=job_id)

    def get_output_path(self, job_id: str, filename: str) -> Path:
        return self.output_dir / job_id / filename

    def output_exists(self, job_id: str, filename: str) -> bool:
        return self.get_output_path(job_id, filename).exists()

    def read_output(self, job_id: str, filename: str) -> bytes:
        return self.get_output_path(job_id, filename).read_bytes()

    def write_output(self, job_id: str, filename: str, data: bytes) -> Path:
        path = self.get_output_path(job_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o600)
        return path
