import httpx

from app.config import settings

GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    """Raised for non-2xx responses from the GitHub API."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when the GitHub API responds with a rate-limit error (403/429)."""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def list_open_issues(repository: str, label: str) -> list[dict]:
    """Open issues on `repository` carrying `label`, excluding pull requests --
    GitHub's issues endpoint returns PRs too, distinguishable by a "pull_request" key."""
    async with httpx.AsyncClient(base_url=GITHUB_API_BASE, headers=_headers()) as client:
        response = await client.get(
            f"/repos/{repository}/issues",
            params={"state": "open", "labels": label},
        )

    if response.status_code in (403, 429):
        raise GitHubRateLimitError(f"GitHub rate limit hit: {response.status_code} {response.text}")
    if not response.is_success:
        raise GitHubAPIError(f"GitHub API error: {response.status_code} {response.text}")

    issues = response.json()
    return [issue for issue in issues if "pull_request" not in issue]
