import html

from app.models import Job


def _issue_url(repository: str, issue_number: int) -> str:
    return f"https://github.com/{repository}/issues/{issue_number}"


def _row_html(job: Job) -> str:
    issue_url = html.escape(_issue_url(job.repository, job.issue_number))

    status_text = job.status.value
    if job.status_detail:
        status_text = f"{status_text}:{job.status_detail}"
    status_html = html.escape(status_text)
    if job.pr_url:
        status_html += f' &middot; <a href="{html.escape(job.pr_url)}">go to PR</a>'

    if job.devin_session_url:
        session_html = f'<a href="{html.escape(job.devin_session_url)}" title="Devin session">\U0001f517</a>'
    else:
        session_html = "-"

    return (
        "<tr>"
        f'<td><a href="{issue_url}">#{job.issue_number}</a></td>'
        f"<td>{status_html}</td>"
        f"<td>{session_html}</td>"
        "</tr>"
    )


def render_dashboard(jobs: list[Job]) -> str:
    """Render the job list as a simple HTML table. `jobs` is expected newest
    first (list_jobs()'s default ordering) so new issues show up at the top."""
    rows = "\n".join(_row_html(job) for job in jobs)
    return f"""<!DOCTYPE html>
<html>
<head>
<title>Devin Issue Resolver</title>
<meta http-equiv="refresh" content="10">
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }}
</style>
</head>
<body>
<h1>Devin Issue Resolution Progress</h1>
<table>
<thead>
<tr><th>Issue</th><th>Status</th><th>Devin Session</th></tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>"""
