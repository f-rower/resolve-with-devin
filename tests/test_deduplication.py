import sqlite3

import pytest

from app.database import DuplicateJobError, create_job, job_exists, list_jobs
from app.models import JobStatus


def test_create_job_succeeds_for_new_issue(db_path):
    job = create_job("owner/repo", 1, path=db_path)
    assert job.status == JobStatus.CLAIMING
    assert job_exists("owner/repo", 1, path=db_path)


def test_create_job_raises_on_duplicate(db_path):
    create_job("owner/repo", 1, path=db_path)
    with pytest.raises(DuplicateJobError):
        create_job("owner/repo", 1, path=db_path)
    assert len(list_jobs(path=db_path)) == 1


def test_create_job_succeeds_for_different_key(db_path):
    create_job("owner/repo", 1, path=db_path)
    create_job("owner/repo", 2, path=db_path)
    create_job("owner/other-repo", 1, path=db_path)
    assert len(list_jobs(path=db_path)) == 3


def test_job_exists_false_for_unclaimed_issue(db_path):
    assert not job_exists("owner/repo", 999, path=db_path)


def test_unique_constraint_is_enforced_at_schema_level(db_path):
    """A raw duplicate INSERT (bypassing create_job entirely) still raises --
    proves the constraint is on the table, not just in application logic."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO jobs (repository, issue_number, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("owner/repo", 5, "claiming", 0.0, 0.0),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO jobs (repository, issue_number, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("owner/repo", 5, "claiming", 0.0, 0.0),
        )
    conn.close()
