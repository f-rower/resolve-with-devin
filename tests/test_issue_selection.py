from app.config import settings
from app.poller import select_eligible_issues


def _issue(number: int, is_pr: bool = False) -> dict:
    issue = {"number": number, "title": f"issue {number}"}
    if is_pr:
        issue["pull_request"] = {"url": "https://example.com/pr"}
    return issue


def test_returns_all_issues_when_none_claimed():
    issues = [_issue(1), _issue(2)]
    assert select_eligible_issues(issues, already_claimed=set()) == issues


def test_filters_out_already_claimed_issues():
    issues = [_issue(1), _issue(2)]
    already_claimed = {(settings.github_repository, 1)}
    assert select_eligible_issues(issues, already_claimed) == [_issue(2)]


def test_filters_out_pull_requests():
    issues = [_issue(1), _issue(2, is_pr=True)]
    assert select_eligible_issues(issues, already_claimed=set()) == [_issue(1)]


def test_returns_empty_list_for_no_issues():
    assert select_eligible_issues([], already_claimed=set()) == []


def test_claimed_key_for_different_repository_does_not_filter():
    issues = [_issue(1)]
    already_claimed = {("some-other/repo", 1)}
    assert select_eligible_issues(issues, already_claimed) == issues
