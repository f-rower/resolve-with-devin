def build_prompt(issue: dict) -> str:
    """Turn a GitHub issue into a Devin prompt. The issue body already has the
    package/version/advisory details and acceptance criteria; this just adds
    framing and an explicit instruction to link the PR back to the issue --
    that's part of the acceptance criteria but won't happen reliably unless
    the prompt says so directly."""
    number = issue["number"]
    title = issue["title"]
    body = issue.get("body") or ""

    return (
        f"Resolve the following GitHub issue (#{number}: {title}) in this repository.\n\n"
        f"{body}\n\n"
        f'Open a pull request that resolves this issue and explicitly references '
        f'issue #{number} (e.g. include "Fixes #{number}" in the PR description) '
        f"so it links back to the issue automatically."
    )
