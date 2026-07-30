import os
import sqlite3
from datetime import UTC, datetime

from app.config import settings
from app.models import Job, JobStatus


class DuplicateJobError(Exception):
    """Raised when a job already exists for (repository, issue_number)."""


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = settings.database_path) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = _connect(path)
    try:
        # Multiple background loops + API handlers share this file.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                devin_session_id TEXT,
                devin_session_url TEXT,
                pr_url TEXT,
                acus_consumed REAL,
                error_message TEXT,
                status_detail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(repository, issue_number)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        repository=row["repository"],
        issue_number=row["issue_number"],
        status=JobStatus(row["status"]),
        devin_session_id=row["devin_session_id"],
        devin_session_url=row["devin_session_url"],
        pr_url=row["pr_url"],
        acus_consumed=row["acus_consumed"],
        error_message=row["error_message"],
        status_detail=row["status_detail"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def job_exists(repository: str, issue_number: int, path: str = settings.database_path) -> bool:
    conn = _connect(path)
    try:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE repository = ? AND issue_number = ?",
            (repository, issue_number),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def create_job(repository: str, issue_number: int, path: str = settings.database_path) -> Job:
    """Insert a new job in the `claiming` state. Raises DuplicateJobError if one
    already exists for (repository, issue_number) -- this is the real dedup guard,
    not job_exists(), which is only a cheap pre-check."""
    now = datetime.now(UTC).isoformat()
    conn = _connect(path)
    try:
        try:
            cursor = conn.execute(
                """
                INSERT INTO jobs (repository, issue_number, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (repository, issue_number, JobStatus.CLAIMING.value, now, now),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise DuplicateJobError(
                f"job already exists for {repository}#{issue_number}"
            ) from exc
        return Job(
            id=cursor.lastrowid,
            repository=repository,
            issue_number=issue_number,
            status=JobStatus.CLAIMING,
            created_at=now,
            updated_at=now,
        )
    finally:
        conn.close()


def update_job(job_id: int, path: str = settings.database_path, **fields) -> None:
    if not fields:
        return
    if "status" in fields and isinstance(fields["status"], JobStatus):
        fields["status"] = fields["status"].value
    fields["updated_at"] = datetime.now(UTC).isoformat()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = [*fields.values(), job_id]
    conn = _connect(path)
    try:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: int, path: str = settings.database_path) -> Job | None:
    conn = _connect(path)
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_job(row) if row else None
    finally:
        conn.close()


def list_jobs(status: JobStatus | None = None, path: str = settings.database_path) -> list[Job]:
    conn = _connect(path)
    try:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [_row_to_job(row) for row in rows]
    finally:
        conn.close()
