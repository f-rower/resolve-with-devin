import httpx

from app.config import settings

DEVIN_API_BASE = "https://api.devin.ai/v3"


class DevinAPIError(Exception):
    """Raised for non-2xx responses from the Devin API. Carries the status
    code and response body for debugging."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Devin API error: {status_code} {body}")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.devin_api_token}",
        "Content-Type": "application/json",
    }


def _sessions_url(session_id: str | None = None) -> str:
    base = f"{DEVIN_API_BASE}/organizations/{settings.devin_org_id}/sessions"
    return f"{base}/{session_id}" if session_id else base


async def create_session(
    prompt: str,
    title: str | None = None,
    tags: list[str] | None = None,
    max_acu_limit: int | None = None,
    repos: list[str] | None = None,
) -> dict:
    payload = {"prompt": prompt}
    if title is not None:
        payload["title"] = title
    if tags is not None:
        payload["tags"] = tags
    if max_acu_limit is not None:
        payload["max_acu_limit"] = max_acu_limit
    if repos is not None:
        payload["repos"] = repos

    async with httpx.AsyncClient(headers=_headers()) as client:
        response = await client.post(_sessions_url(), json=payload)

    if not response.is_success:
        raise DevinAPIError(response.status_code, response.text)
    return response.json()


async def get_session(session_id: str) -> dict:
    async with httpx.AsyncClient(headers=_headers()) as client:
        response = await client.get(_sessions_url(session_id))

    if not response.is_success:
        raise DevinAPIError(response.status_code, response.text)
    return response.json()
