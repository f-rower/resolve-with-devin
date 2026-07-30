import logging

from app.config import settings
from app.database import create_job, list_jobs, update_job
from app.devin_client import create_session
from app.github_client import list_open_issues
from app.models import JobStatus
from app.prompts import build_prompt

logger = logging.getLogger(__name__)

RESOLVE_LABEL = "devin-resolve"


def select_eligible_issues(
    issues: list[dict], already_claimed: set[tuple[str, int]]
) -> list[dict]:
    """Pure filter: drop issues already claimed and anything still PR-shaped
    (github_client already filters PRs, but a caller
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
    """Detect issues labelled devin-resolve, claim them, and start a Devin
    session for each."""
    issues = await list_open_issues(settings.github_repository, RESOLVE_LABEL)

    already_claimed = {(job.repository, job.issue_number) for job in list_jobs()}
    eligible = select_eligible_issues(issues, already_claimed)
    print(eligible)
    for issue in eligible:
        try:
            job = create_job(settings.github_repository, issue["number"])
            logger.info("claimed issue #%s", issue["number"])
        except Exception:
            logger.exception("failed to claim issue #%s", issue["number"])
            continue

        try:
            logger.info(f"Creating Devin session for issue #{issue['number']}")
            session = await create_session(
                prompt=build_prompt(issue),
                title=f"Resolve {settings.github_repository}#{issue['number']}",
                tags=["github-issue", f"issue-{issue['number']}"],
                max_acu_limit=settings.max_acu_limit,
                repos=[f"https://github.com/{settings.github_repository}"],
            )
            update_job(
                job.id,
                status=JobStatus.RUNNING,
                devin_session_id=session["session_id"],
                devin_session_url=session["url"],
            )
            logger.info(
                "started Devin session for issue #%s: %s", issue["number"], session["url"]
            )
        except Exception as exc:
            update_job(job.id, status=JobStatus.FAILED, error_message=str(exc))
            logger.exception("failed to start Devin session for issue #%s", issue["number"])
