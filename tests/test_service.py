import json
from dataclasses import asdict, replace

import pytest

from school_lab.errors import SubmissionError
from school_lab.models import Submission
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService, accept_payload


# --- Репозиторий ---


def test_repo_get_missing_returns_none(repo: InMemorySubmissionRepository) -> None:
    assert repo.get("nope") is None


def test_repo_add_then_get(repo: InMemorySubmissionRepository, submission: Submission) -> None:
    repo.add(submission)
    assert repo.get("sub-001") == submission
    assert len(repo) == 1


def test_repo_add_same_id_twice_is_conflict(
    repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    repo.add(submission)
    with pytest.raises(SubmissionError) as exc_info:
        repo.add(submission)
    assert exc_info.value.code == "conflict"


# --- Сервис: три исхода ---


# Образец
def test_new_submission_accepted(service: SubmissionService, submission: Submission) -> None:
    result = service.accept(submission)
    assert result.status == "accepted"
    assert result.submission_id == "sub-001"


def test_same_submission_twice_is_duplicate(
    service: SubmissionService, repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    result1 = service.accept(submission)
    result2 = service.accept(submission)

    assert result2.status == "duplicate"
    assert len(repo) == 1


def test_changed_content_same_id_is_conflict(
    service: SubmissionService, repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    service.accept(submission)

    changed = replace(submission, code="print('diff version of code')\n")
    with pytest.raises(SubmissionError) as exc_info:
        service.accept(changed)

    assert exc_info.value.code == "conflict"
    assert repo.get("sub-001") == submission


def test_new_version_new_id_both_kept(
    service: SubmissionService, repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    res = service.accept(submission)

    changed = replace(submission, submission_id="sub-001-v2", code="for _ in range(10)\n")
    res2 = service.accept(changed)
    assert len(repo) == 2
    assert res.status == "accepted"
    assert res2.status == "accepted"


def test_accept_payload_valid(service: SubmissionService, submission: Submission) -> None:
    raw = json.dumps(asdict(submission))
    assert accept_payload(service, raw).status == "accepted"


def test_accept_payload_invalid_saves_nothing(
    service: SubmissionService, repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    payload = asdict(submission)
    payload["student_id"] = ""

    with pytest.raises(SubmissionError) as exc_info:
        res = accept_payload(service, json.dumps(payload))

    assert exc_info.value.code == "schema_error"
    assert len(repo) == 0

