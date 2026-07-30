import pytest

from app.models import JobStatus
from app.session_tracker import (
    FAILURE_STATUS_DETAILS,
    NON_TERMINAL_STATUS_DETAILS,
    NON_TERMINAL_STATUSES,
    map_session_to_job_update,
)


def test_finished_with_pr_marks_completed():
    session = {
        "status_detail": "finished",
        "pull_requests": [{"pr_url": "https://github.com/owner/repo/pull/1", "pr_state": "open"}],
        "acus_consumed": 1.5,
    }
    fields = map_session_to_job_update(session)
    assert fields["status"] == JobStatus.COMPLETED
    assert fields["pr_url"] == "https://github.com/owner/repo/pull/1"
    assert "error_message" not in fields
    assert fields["acus_consumed"] == 1.5
    assert fields["status_detail"] == "finished"


def test_finished_without_pr_marks_completed_with_note():
    session = {"status_detail": "finished", "pull_requests": []}
    fields = map_session_to_job_update(session)
    assert fields["status"] == JobStatus.COMPLETED
    assert fields["pr_url"] is None
    assert fields["error_message"] == "session finished but no PR was found"


def test_finished_with_missing_pull_requests_key_marks_completed_with_note():
    session = {"status_detail": "finished"}
    fields = map_session_to_job_update(session)
    assert fields["status"] == JobStatus.COMPLETED
    assert fields["pr_url"] is None
    assert fields["error_message"] == "session finished but no PR was found"


@pytest.mark.parametrize("status_detail", sorted(FAILURE_STATUS_DETAILS))
def test_failure_status_details_mark_failed(status_detail):
    session = {"status_detail": status_detail}
    fields = map_session_to_job_update(session)
    assert fields["status"] == JobStatus.FAILED
    assert fields["error_message"] == status_detail


@pytest.mark.parametrize("status_detail", sorted(NON_TERMINAL_STATUS_DETAILS))
def test_non_terminal_status_details_stay_in_progress(status_detail):
    session = {"status_detail": status_detail}
    fields = map_session_to_job_update(session)
    assert "status" not in fields
    assert "error_message" not in fields
    assert "pr_url" not in fields


@pytest.mark.parametrize("status", sorted(NON_TERMINAL_STATUSES))
def test_non_terminal_top_level_statuses_stay_in_progress(status):
    session = {"status": status, "status_detail": None}
    fields = map_session_to_job_update(session)
    assert "status" not in fields


def test_unrecognized_status_detail_stays_in_progress_and_does_not_raise():
    session = {"status": "some_future_status", "status_detail": "some_future_detail"}
    fields = map_session_to_job_update(session)
    assert "status" not in fields
    assert fields["status_detail"] == "some_future_detail"


def test_acus_consumed_is_carried_through_when_present():
    session = {"status_detail": "working", "acus_consumed": 2.25}
    fields = map_session_to_job_update(session)
    assert fields["acus_consumed"] == 2.25


def test_acus_consumed_omitted_when_absent():
    session = {"status_detail": "working"}
    fields = map_session_to_job_update(session)
    assert "acus_consumed" not in fields
