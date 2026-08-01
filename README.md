# Resolve with Devin
A FastAPI application that resolves issues from a GitHub repository using Devin, an AI software engineer.

# Set up

Prerequisites:
- Python 3.12
- Docker Desktop, for the containerized run
- A GitHub fine-grained PAT scoped to the target repository, with `Issues: Read-only` permission
- A Devin service user (app.devin.ai -> Settings -> Service Users), for `DEVIN_API_TOKEN` and `DEVIN_ORG_ID`
- The target repository connected to Devin's GitHub App (app.devin.ai -> Settings -> Integrations -> GitHub), so Devin can push and open pull requests there. This is separate from the PAT above.
- One label on the target repository: `devin-resolve`
- Copy `.env.template` to `.env` and fill in the values.
- Install dependencies in a virtual environment:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

# Run the application

Locally:
```bash
uvicorn app.main:app --reload
```

With Docker:
```bash
mkdir -p data
docker compose up --build
```

Run the tests:
```bash
pytest
```

Check on it:
```bash
curl localhost:8000/health
curl localhost:8000/jobs
curl localhost:8000/jobs/1
curl localhost:8000/metrics
```

Open `http://localhost:8000` in a browser for a live view of issue resolution progress.

# Architecture

```
Engineer
  creates GitHub issues
  adds the devin-resolve label
        |
        v
Polling loop (every POLL_INTERVAL_SECONDS)
  lists open issues labelled devin-resolve
  skips anything already claimed
  creates a job record, then a Devin session
        |
        v
Session-tracker loop (every SESSION_POLL_INTERVAL_SECONDS)
  polls the Devin session
  updates the job record: running -> completed / failed
```

The app never writes back to GitHub - no relabeling, no comments. Progress lives entirely in the job store and is exposed through `/health`, `/jobs`, `/jobs/{id}`, `/metrics`.

# File tree

```
app/
  __init__.py
  config.py           env-based settings
  models.py           Job model, JobStatus enum
  database.py         SQLite job store, dedup
  github_client.py    read-only issue listing
  devin_client.py     create/get Devin sessions
  prompts.py          build Devin session prompt
  poller.py           claim issues, start Devin sessions
  session_tracker.py  poll sessions, update jobs
  dashboard.py        render HTML progress dashboard
  main.py             FastAPI app, background loops
tests/
  __init__.py
  conftest.py              shared pytest fixtures
  test_deduplication.py    job store dedup tests
  test_issue_selection.py  eligibility filter tests
  test_status_mapping.py   Devin status mapping tests
.env
.env.template
.dockerignore
.gitignore
Dockerfile
docker-compose.yml
pyproject.toml
README.md
```

# Key Design Decisions

- **Devin API v3**, not v1. v1 is simpler but deprecated and has no ACU-consumption field. v3 needs a service-user credential and org ID, but gives real `acus_consumed` and a granular `status_detail` on failure.
- **No GitHub write-back.** Only `devin-resolve` needs to exist as a label, and the PAT only needs read access. Dedup is enforced by a unique constraint on `(repository, issue_number)` in the job store, not by relabeling - labels were never the real guard, since the process can crash between creating a Devin session and updating GitHub.
- **SQLite**, not a database server. This is a single-process demo; a local file is enough.
- Devin sessions are bound to the target repository via the `repos` parameter at creation, rather than relying on the prompt text alone.

Known limitations: single repository per instance, no concurrent writers beyond this one process, no auth on the app's own endpoints, no GitHub-visible signal of progress - check `/jobs` instead. The job store is also the only record of what's already been processed - deleting it (or losing it) makes every `devin-resolve`-labelled issue look brand new again, including ones that already have an open PR, since nothing on GitHub itself reflects prior work. Also polling-based, not webhook-driven: a newly-labelled issue or a Devin session update is only picked up on the next poll cycle, not instantly - up to `POLL_INTERVAL_SECONDS` / `SESSION_POLL_INTERVAL_SECONDS` of latency.