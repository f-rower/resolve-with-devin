import logging

from app.database import list_jobs, update_job
from app.devin_client import DevinAPIError, get_session
from app.models import JobStatus

logger = logging.getLogger(__name__)

FAILURE_STATUS_DETAILS = {
    "usage_limit_exceeded",
    "out_of_credits",
    "out_of_quota",
    "no_quota_allocation",
    "payment_declined",
    "org_usage_limit_exceeded",
    "total_session_limit_exceeded",
    "error",
}
NON_TERMINAL_STATUS_DETAILS = {"working", "waiting_for_user", "waiting_for_approval", "inactivity"}
NON_TERMINAL_STATUSES = {"new", "claimed", "running", "resuming", "suspended"}


def map_session_to_job_update(session: dict) -> dict:
    """Pure function: turn a raw Devin get_session() response into a dict of
    fields for update_job(). Always carries acus_consumed/status_detail (if
    present) so /metrics stays live mid-run; only sets `status` once terminal.
    Never raises -- an unrecognized status/status_detail is logged and treated
    as still in progress, since a future Devin enum value shouldn't silently
    mark a job failed."""
    fields: dict = {}

    acus_consumed = session.get("acus_consumed")
    if acus_consumed is not None:
        fields["acus_consumed"] = acus_consumed

    status_detail = session.get("status_detail")
    top_level_status = session.get("status")
    fields["status_detail"] = status_detail

    # Checked regardless of terminal state -- Devin can open a PR mid-session
    # (e.g. while waiting_for_user), and pull_requests_created in /metrics
    # should count that even before the session finishes.
    pull_requests = session.get("pull_requests") or []
    if pull_requests:
        fields["pr_url"] = pull_requests[0].get("pr_url")

    if status_detail == "finished":
        fields["status"] = JobStatus.COMPLETED
        if not pull_requests:
            fields["pr_url"] = None
            fields["error_message"] = "session finished but no PR was found"
        return fields

    if status_detail in FAILURE_STATUS_DETAILS:
        fields["status"] = JobStatus.FAILED
        fields["error_message"] = status_detail
        return fields

    if status_detail in NON_TERMINAL_STATUS_DETAILS or top_level_status in NON_TERMINAL_STATUSES:
        return fields

    logger.warning(
        "unrecognized Devin status=%r status_detail=%r -- treating as in progress",
        top_level_status,
        status_detail,
    )
    return fields


async def check_running_sessions() -> None:
    """Poll every `running` job against the Devin API and persist any
    progress or terminal outcome. No GitHub write -- outcome lives in the
    job record only."""
    for job in list_jobs(status=JobStatus.RUNNING):
        try:
            session = await get_session(job.devin_session_id)
        except DevinAPIError as exc:
            if exc.status_code == 404:
                update_job(
                    job.id,
                    status=JobStatus.FAILED,
                    error_message="Devin session not found (404)",
                )
                logger.warning("session %s vanished for job %s", job.devin_session_id, job.id)
            else:
                logger.exception("failed to poll session for job %s", job.id)
            continue

        fields = map_session_to_job_update(session)
        if fields:
            update_job(job.id, **fields)
        if fields.get("status") == JobStatus.COMPLETED:
            logger.info("job %s completed: %s", job.id, fields.get("pr_url"))
        elif fields.get("status") == JobStatus.FAILED:
            logger.info("job %s failed: %s", job.id, fields.get("error_message"))
