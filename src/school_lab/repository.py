from typing import Protocol

from .errors import SubmissionError
from .models import Submission


class SubmissionRepository(Protocol):
        def get(self, submission_id: str) -> Submission | None: ...
        def add(self, submission: Submission) -> None: ...


class InMemorySubmissionRepository:
    def __init__(self) -> None:
        self._items: dict[str, Submission] = {}

    def get(self, submission_id: str) -> Submission | None:
        return self._items.get(submission_id, None)

    def add(self, submission: Submission) -> None:
        if submission.submission_id not in self._items:
            self._items[submission.submission_id] = submission
        else:
            raise SubmissionError("conflict", "submission_id", "id already exists")


    def __len__(self) -> int:
        return len(self._items)
