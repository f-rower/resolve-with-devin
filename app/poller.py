import logging

from app.config import settings
from app.database import create_job, list_jobs
from app.github_client import list_open_issues

logger = logging.getLogger(__name__)

RESOLVE_LABEL = "devin-resolve"


def select_eligible_issues(
    issues: list[dict], already_claimed: set[tuple[str, int]]
) -> list[dict]:
    """Pure filter: drop issues already claimed and anything still PR-shaped
    (defense-in-depth -- github_client already filters PRs, but a caller
    passing raw GitHub API data directly shouldn't have to know that)."""
    eligible = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        key = (settings.github_repository, issue["number"])
        if key in already_claimed:
            continue
        eligible.append(issue)
    return eligible


async def poll_for_issues() -> None:
    """Detect issues labelled devin-resolve and claim them into the job store.
    Devin session creation is wired in here separately once devin_client.py
    and prompts.py exist."""
    issues = await list_open_issues(settings.github_repository, RESOLVE_LABEL)

    already_claimed = {(job.repository, job.issue_number) for job in list_jobs()}
    eligible = select_eligible_issues(issues, already_claimed)

    for issue in eligible:
        try:
            create_job(settings.github_repository, issue["number"])
            logger.info("claimed issue #%s", issue["number"])
        except Exception:
            logger.exception("failed to claim issue #%s", issue["number"])
