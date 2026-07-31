import html
from datetime import datetime

from app.models import Job, JobStatus
from app.session_tracker import NON_TERMINAL_STATUS_DETAILS

STAGES = ["Working", "PR Created", "Awaiting User Review"]
# Same "blocked on a human" set session_tracker treats as non-terminal, minus
# "working" itself -- kept derived so the two never drift apart.
AWAITING_REVIEW_STATUS_DETAILS = NON_TERMINAL_STATUS_DETAILS - {"working"}


def _issue_url(repository: str, issue_number: int) -> str:
    return f"https://github.com/{repository}/issues/{issue_number}"


def _format_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _status_text(job: Job) -> str:
    detail = "awaiting review" if job.status_detail == "inactivity" else job.status_detail
    return f"{job.status.value}:{detail}" if detail else job.status.value


def _status_colors(job: Job) -> tuple[str, str]:
    """(text_color, background_color) for the status badge."""
    if job.status == JobStatus.FAILED:
        return "#b91c1c", "#fee2e2"
    if job.status == JobStatus.COMPLETED:
        return "#15803d", "#dcfce7"
    if job.status_detail in AWAITING_REVIEW_STATUS_DETAILS:
        return "#b45309", "#fef3c7"
    if job.status == JobStatus.RUNNING:
        return "#1d4ed8", "#dbeafe"
    return "#6b7280", "#f3f4f6"


def _stage(job: Job) -> str | None:
    """Which of the three summary buckets a job currently belongs to, most
    complete first -- a job with an open PR is bucketed as such even if the
    underlying session is technically still `running`."""
    if job.pr_url:
        return "PR Created"
    if job.status_detail in AWAITING_REVIEW_STATUS_DETAILS:
        return "Awaiting User Review"
    if job.status == JobStatus.RUNNING:
        return "Working"
    return None


def _summary_html(jobs: list[Job]) -> str:
    counts = dict.fromkeys(STAGES, 0)
    for job in jobs:
        stage = _stage(job)
        if stage:
            counts[stage] += 1

    cards = "\n".join(
        f'<div class="stat"><div class="stat-value">{counts[stage]}</div>'
        f'<div class="stat-label">{html.escape(stage)}</div></div>'
        for stage in STAGES
    )
    return f'<div class="stats">{cards}</div>'


def _row_html(job: Job) -> str:
    issue_url = html.escape(_issue_url(job.repository, job.issue_number))
    text_color, bg_color = _status_colors(job)
    status_badge = (
        f'<span class="badge" style="color:{text_color};background:{bg_color};">'
        f"{html.escape(_status_text(job))}</span>"
    )

    pr_cell = f'<a href="{html.escape(job.pr_url)}">go to PR</a>' if job.pr_url else ""

    if job.devin_session_url:
        session_cell = f'<a href="{html.escape(job.devin_session_url)}" title="Devin session">\U0001f517</a>'
    else:
        session_cell = "-"

    return (
        "<tr>"
        f'<td><a href="{issue_url}">#{job.issue_number}</a></td>'
        f"<td>{status_badge}</td>"
        f"<td>{pr_cell}</td>"
        f"<td>{session_cell}</td>"
        f"<td>{_format_dt(job.created_at)}</td>"
        f"<td>{_format_dt(job.updated_at)}</td>"
        "</tr>"
    )


def render_dashboard(jobs: list[Job]) -> str:
    """Render the job list as an HTML table. `jobs` is expected newest first
    (list_jobs()'s default ordering) so new issues show up at the top."""
    rows = "\n".join(_row_html(job) for job in jobs)
    if not rows:
        rows = '<tr><td colspan="6" class="empty">No jobs yet</td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head>
<title>Devin Issue Resolver</title>
<meta http-equiv="refresh" content="10">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f9fafb;
    color: #111827;
    margin: 0;
    padding: 2rem 1rem;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 1.25rem; }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }}
  .stat {{
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 0.85rem 1rem;
  }}
  .stat-value {{ font-size: 1.5rem; font-weight: 600; }}
  .stat-label {{ font-size: 0.8rem; color: #6b7280; margin-top: 0.15rem; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    overflow: hidden;
  }}
  th, td {{ text-align: left; padding: 0.6rem 0.9rem; font-size: 0.9rem; }}
  th {{
    background: #f3f4f6;
    color: #374151;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}
  tbody tr {{ border-top: 1px solid #e5e7eb; }}
  tbody tr:hover {{ background: #f9fafb; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
    white-space: nowrap;
  }}
  .empty {{ text-align: center; color: #6b7280; padding: 1.5rem; }}
</style>
</head>
<body>
<div class="container">
<h1>Devin Issue Resolution Progress</h1>
{_summary_html(jobs)}
<table>
<thead>
<tr>
  <th>Issue</th>
  <th>Status</th>
  <th>PR</th>
  <th>Devin Session</th>
  <th>Created At</th>
  <th>Updated At</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</div>
</body>
</html>"""
