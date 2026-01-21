"""
Job Tracking

Track analysis jobs from submission to completion.
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"           # Queued, not started
    COLLECTING = "collecting"     # Phase 1-4 data collection
    ANALYZING = "analyzing"       # Claude AI analysis loops
    GENERATING = "generating"     # PDF report generation
    DELIVERING = "delivering"     # Email delivery
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"            # Failed with error
    CANCELLED = "cancelled"       # User cancelled


@dataclass
class Job:
    """Analysis job data model."""
    job_id: str
    domain: str
    api_key_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    # Configuration
    market: str = "Sweden"
    language: str = "sv"
    email: Optional[str] = None
    company_name: Optional[str] = None
    options: Dict = field(default_factory=dict)

    # Progress tracking
    current_phase: Optional[str] = None
    progress_percent: int = 0
    phases_completed: List[str] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Results
    collection_result_key: Optional[str] = None
    analysis_result_key: Optional[str] = None
    external_report_key: Optional[str] = None
    internal_report_key: Optional[str] = None
    external_report_url: Optional[str] = None
    internal_report_url: Optional[str] = None

    # Costs
    api_cost: float = 0.0
    ai_cost: float = 0.0
    tokens_used: int = 0

    # Quality
    quality_score: Optional[float] = None
    quality_passed: bool = False

    # Errors
    error_message: Optional[str] = None
    error_details: Optional[Dict] = None

    # Metadata
    metadata: Dict = field(default_factory=dict)

    def total_cost(self) -> float:
        """Calculate total cost."""
        return self.api_cost + self.ai_cost

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Job":
        """Create from dictionary."""
        data["status"] = JobStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)

    def update_status(self, status: JobStatus, phase: Optional[str] = None, progress: Optional[int] = None):
        """Update job status and progress."""
        self.status = status
        self.updated_at = datetime.now()

        if phase:
            self.current_phase = phase
            if phase not in self.phases_completed and status != JobStatus.FAILED:
                self.phases_completed.append(phase)

        if progress is not None:
            self.progress_percent = progress

        if status == JobStatus.COLLECTING and not self.started_at:
            self.started_at = datetime.now()

        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            self.completed_at = datetime.now()
            if self.started_at:
                self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


class JobTracker:
    """
    Tracks analysis jobs.

    Provides job lifecycle management and status queries.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize job tracker.

        Args:
            storage_path: Directory for job data.
                         Defaults to ~/.authoricy/jobs/
        """
        if storage_path is None:
            storage_path = os.getenv(
                "AUTHORICY_JOBS_PATH",
                str(Path.home() / ".authoricy" / "jobs")
            )

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache of active jobs
        self._jobs: Dict[str, Job] = {}
        self._load_active_jobs()

    def _get_job_path(self, job_id: str) -> Path:
        """Get path for job file."""
        return self.storage_path / f"{job_id}.json"

    def _load_active_jobs(self):
        """Load active (non-completed) jobs from storage."""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    job = Job.from_dict(json.load(f))

                # Keep active jobs in memory
                if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    self._jobs[job.job_id] = job

            except Exception as e:
                logger.warning(f"Failed to load job from {file_path}: {e}")

        logger.info(f"Loaded {len(self._jobs)} active jobs")

    def _save_job(self, job: Job):
        """Persist job to storage."""
        path = self._get_job_path(job.job_id)
        try:
            with open(path, "w") as f:
                json.dump(job.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job {job.job_id}: {e}")

    def create_job(
        self,
        domain: str,
        api_key_id: str,
        market: str = "Sweden",
        language: str = "sv",
        email: Optional[str] = None,
        company_name: Optional[str] = None,
        options: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Job:
        """
        Create a new analysis job.

        Returns:
            The created Job object
        """
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        now = datetime.now()

        job = Job(
            job_id=job_id,
            domain=domain,
            api_key_id=api_key_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            market=market,
            language=language,
            email=email,
            company_name=company_name,
            options=options or {},
            metadata=metadata or {}
        )

        self._jobs[job_id] = job
        self._save_job(job)

        logger.info(f"Created job {job_id} for {domain}")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        # Check cache first
        if job_id in self._jobs:
            return self._jobs[job_id]

        # Load from storage
        path = self._get_job_path(job_id)
        if path.exists():
            try:
                with open(path, "r") as f:
                    return Job.from_dict(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load job {job_id}: {e}")

        return None

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        phase: Optional[str] = None,
        progress: Optional[int] = None,
        **kwargs
    ) -> Optional[Job]:
        """
        Update a job's status and/or fields.

        Args:
            job_id: Job ID
            status: New status
            phase: Current phase name
            progress: Progress percentage (0-100)
            **kwargs: Additional fields to update

        Returns:
            Updated Job or None if not found
        """
        job = self.get_job(job_id)
        if not job:
            return None

        if status:
            job.update_status(status, phase, progress)
        elif phase:
            job.current_phase = phase
            job.updated_at = datetime.now()
        elif progress is not None:
            job.progress_percent = progress
            job.updated_at = datetime.now()

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
                job.updated_at = datetime.now()

        # Update cache and save
        self._jobs[job_id] = job
        self._save_job(job)

        return job

    def complete_job(
        self,
        job_id: str,
        quality_score: Optional[float] = None,
        quality_passed: bool = True,
        external_report_key: Optional[str] = None,
        internal_report_key: Optional[str] = None,
        api_cost: float = 0.0,
        ai_cost: float = 0.0,
        tokens_used: int = 0
    ) -> Optional[Job]:
        """Mark job as completed."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.update_status(JobStatus.COMPLETED, "completed", 100)
        job.quality_score = quality_score
        job.quality_passed = quality_passed
        job.external_report_key = external_report_key
        job.internal_report_key = internal_report_key
        job.api_cost = api_cost
        job.ai_cost = ai_cost
        job.tokens_used = tokens_used

        # Remove from active cache
        self._jobs.pop(job_id, None)
        self._save_job(job)

        logger.info(f"Completed job {job_id} (score: {quality_score})")
        return job

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        error_details: Optional[Dict] = None
    ) -> Optional[Job]:
        """Mark job as failed."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.update_status(JobStatus.FAILED)
        job.error_message = error_message
        job.error_details = error_details

        # Remove from active cache
        self._jobs.pop(job_id, None)
        self._save_job(job)

        logger.error(f"Failed job {job_id}: {error_message}")
        return job

    def cancel_job(self, job_id: str) -> Optional[Job]:
        """Cancel a pending or active job."""
        job = self.get_job(job_id)
        if not job:
            return None

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            return None  # Can't cancel completed jobs

        job.update_status(JobStatus.CANCELLED)

        # Remove from active cache
        self._jobs.pop(job_id, None)
        self._save_job(job)

        logger.info(f"Cancelled job {job_id}")
        return job

    def list_jobs(
        self,
        api_key_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        domain: Optional[str] = None,
        limit: int = 100,
        include_completed: bool = False
    ) -> List[Job]:
        """
        List jobs with optional filters.

        Args:
            api_key_id: Filter by API key
            status: Filter by status
            domain: Filter by domain
            limit: Maximum number of jobs to return
            include_completed: Include completed/failed jobs from storage

        Returns:
            List of matching jobs
        """
        jobs = list(self._jobs.values())

        # Optionally load completed jobs from storage
        if include_completed:
            for file_path in self.storage_path.glob("*.json"):
                job_id = file_path.stem
                if job_id not in self._jobs:
                    try:
                        with open(file_path, "r") as f:
                            job = Job.from_dict(json.load(f))
                            jobs.append(job)
                    except Exception:
                        pass

        # Apply filters
        if api_key_id:
            jobs = [j for j in jobs if j.api_key_id == api_key_id]
        if status:
            jobs = [j for j in jobs if j.status == status]
        if domain:
            jobs = [j for j in jobs if j.domain == domain]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def get_active_jobs_count(self) -> int:
        """Get count of active (non-completed) jobs."""
        return len(self._jobs)

    def get_job_stats(self, api_key_id: Optional[str] = None) -> Dict[str, Any]:
        """Get job statistics."""
        all_jobs = self.list_jobs(api_key_id=api_key_id, include_completed=True, limit=10000)

        total = len(all_jobs)
        completed = len([j for j in all_jobs if j.status == JobStatus.COMPLETED])
        failed = len([j for j in all_jobs if j.status == JobStatus.FAILED])
        active = len([j for j in all_jobs if j.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)])

        completed_jobs = [j for j in all_jobs if j.status == JobStatus.COMPLETED and j.duration_seconds]
        avg_duration = sum(j.duration_seconds for j in completed_jobs) / len(completed_jobs) if completed_jobs else 0

        total_cost = sum(j.total_cost() for j in all_jobs)

        return {
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "active": active,
            "success_rate": (completed / total * 100) if total else 0,
            "avg_duration_seconds": avg_duration,
            "total_cost": round(total_cost, 2),
        }
