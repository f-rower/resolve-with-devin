import pytest

from app.database import init_db


@pytest.fixture
def db_path(tmp_path):
    """Path to a fresh, initialized SQLite DB, isolated per test."""
    path = str(tmp_path / "jobs.db")
    init_db(path)
    return path
