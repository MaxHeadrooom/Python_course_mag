from dataclasses import dataclass
from typing import Literal

from .errors import SubmissionError
from .hashing import submission_hash
from .models import Submission
from .parser import parse_submission
from .repository import SubmissionRepository


@dataclass(frozen=True, slots=True)
class Acceptance:
    status: Literal["accepted", "duplicate"]
    submission_id: str
    content_hash: str


class SubmissionService:
    def __init__(self, repository: SubmissionRepository) -> None:
        self.repository = repository

    def accept(self, submission: Submission) -> Acceptance:
        digest = submission_hash(submission)

        previous = self.repository.get(submission.submission_id)

        if not previous is None:
            if digest != submission_hash(previous):
                raise SubmissionError("conflict", "submission_id", "id already exists")
            else:
                return Acceptance("duplicate", submission.submission_id, digest)
        else:
            self.repository.add(submission)
            return Acceptance("accepted", submission.submission_id, digest)


def accept_payload(service: SubmissionService, raw: str) -> Acceptance:
    data = parse_submission(raw)

    return service.accept(data)
