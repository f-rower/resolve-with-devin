from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    CLAIMING = "claiming"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    id: int | None = None
    repository: str
    issue_number: int
    status: JobStatus
    devin_session_id: str | None = None
    devin_session_url: str | None = None
    pr_url: str | None = None
    acus_consumed: float | None = None
    error_message: str | None = None
    status_detail: str | None = None
    created_at: datetime
    updated_at: datetime
