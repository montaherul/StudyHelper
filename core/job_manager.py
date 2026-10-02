"""
Job management, worker thread abstraction, and cancellation tokens for LocalStudy.
Ensures zero GUI blocking and responsive cancellation of long-running operations.
"""

import threading
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any

from utils.logger import logger


class CancellationToken:
    """Thread-safe cancellation and pause token."""

    def __init__(self):
        self._is_cancelled = threading.Event()
        self._is_paused = threading.Event()
        self._is_paused.set()  # Unpaused by default

    def cancel(self) -> None:
        """Signals the worker to abort immediately."""
        self._is_cancelled.set()
        self.resume()  # Ensure unpaused so it can exit cleanly

    def pause(self) -> None:
        """Signals the worker to suspend execution."""
        self._is_paused.clear()

    def resume(self) -> None:
        """Resumes a paused worker."""
        self._is_paused.set()

    def is_cancelled(self) -> bool:
        return self._is_cancelled.is_set()

    def check_pause(self) -> None:
        """Blocks if paused until resume() is called or job is cancelled."""
        self._is_paused.wait()


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class JobContext:
    """Encapsulates execution context and progress reporting for a single task."""

    def __init__(
        self,
        job_id: str,
        name: str,
        cancel_token: CancellationToken,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        finished_callback: Optional[Callable[[bool, Any, Optional[str]], None]] = None
    ):
        self.job_id = job_id
        self.name = name
        self.cancel_token = cancel_token
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.status = JobStatus.QUEUED
        self.progress = 0.0
        self.status_message = "Queued"
        self.error_message: Optional[str] = None
        self.result: Any = None

    def update_progress(self, progress: float, message: str = "") -> None:
        self.progress = max(0.0, min(100.0, progress))
        if message:
            self.status_message = message
        if self.progress_callback:
            try:
                self.progress_callback(self.progress, self.status_message)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def complete(self, result: Any = None) -> None:
        self.status = JobStatus.COMPLETED
        self.progress = 100.0
        self.result = result
        if self.finished_callback:
            self.finished_callback(True, result, None)

    def fail(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error_message = error
        if self.finished_callback:
            self.finished_callback(False, None, error)

    def abort(self) -> None:
        self.status = JobStatus.CANCELLED
        if self.finished_callback:
            self.finished_callback(False, None, "Operation cancelled by user.")


class JobManager:
    """Manages active jobs and thread pooling."""

    def __init__(self):
        self._active_jobs: Dict[str, JobContext] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        name: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        finished_callback: Optional[Callable[[bool, Any, Optional[str]], None]] = None
    ) -> JobContext:
        job_id = str(uuid.uuid4())
        cancel_token = CancellationToken()
        ctx = JobContext(job_id, name, cancel_token, progress_callback, finished_callback)
        with self._lock:
            self._active_jobs[job_id] = ctx
        return ctx

    def get_job(self, job_id: str) -> Optional[JobContext]:
        with self._lock:
            return self._active_jobs.get(job_id)

    def cancel_job(self, job_id: str) -> None:
        ctx = self.get_job(job_id)
        if ctx:
            ctx.cancel_token.cancel()
            ctx.abort()
            logger.info(f"Cancelled job: {ctx.name} ({job_id})")


job_manager = JobManager()
