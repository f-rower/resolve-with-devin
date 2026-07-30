import asyncio
import contextlib
import logging

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.database import get_job, init_db, list_jobs
from app.models import Job, JobStatus
from app.poller import poll_for_issues
from app.session_tracker import check_running_sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run_poll_loop() -> None:
    while True:
        try:
            await poll_for_issues()
        except Exception:
            logger.exception("poll_for_issues iteration failed")
        await asyncio.sleep(settings.poll_interval_seconds)


async def _run_session_tracker_loop() -> None:
    while True:
        try:
            await check_running_sessions()
        except Exception:
            logger.exception("check_running_sessions iteration failed")
        await asyncio.sleep(settings.session_poll_interval_seconds)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    poll_task = asyncio.create_task(_run_poll_loop())
    session_tracker_task = asyncio.create_task(_run_session_tracker_loop())
    yield
    poll_task.cancel()
    session_tracker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await poll_task
    with contextlib.suppress(asyncio.CancelledError):
        await session_tracker_task


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/jobs")
async def get_jobs(status: JobStatus | None = None) -> list[Job]:
    return list_jobs(status=status)


@app.get("/jobs/{job_id}")
async def get_job_by_id(job_id: int) -> Job:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/metrics")
async def get_metrics() -> dict:
    jobs = list_jobs()
    with_pr = [job for job in jobs if job.pr_url]
    # A PR can exist before the session is done (e.g. while waiting_for_user),
    # so this stays broader than "completed" -- see completed_with_pr below.
    completed_with_pr = [job for job in with_pr if job.status == JobStatus.COMPLETED]
    average_time_to_pr = (
        sum(job.updated_at - job.created_at for job in completed_with_pr) / len(completed_with_pr)
        if completed_with_pr
        else None
    )

    return {
        "issues_detected": len(jobs),
        "sessions_started": sum(1 for job in jobs if job.devin_session_id is not None),
        "sessions_running": sum(1 for job in jobs if job.status == JobStatus.RUNNING),
        "pull_requests_created": len(with_pr),
        "sessions_failed": sum(1 for job in jobs if job.status == JobStatus.FAILED),
        "average_time_to_pr_seconds": average_time_to_pr,
        "total_acus_consumed": sum(job.acus_consumed or 0.0 for job in jobs),
    }
