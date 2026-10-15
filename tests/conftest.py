import pytest

from school_lab.models import AIDeclaration, Submission
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService


@pytest.fixture
def submission() -> Submission:
    return Submission(
        schema_version=1,
        submission_id="sub-001",
        student_id="student-001",
        assignment_id="assignment-01",
        submitted_at="2026-09-01T10:01:00+03:00",
        text="Учебное решение с пояснением алгоритма.",
        code="def solve(values):\n    return sum(x * x for x in values if x >= 0)\n",
        template_id="template-01",
        ai_declaration=AIDeclaration(
            used=False, tool=None, purpose=None, verified_by_student=True
        ),
    )


@pytest.fixture
def repo() -> InMemorySubmissionRepository:
    return InMemorySubmissionRepository()


@pytest.fixture
def service(repo: InMemorySubmissionRepository) -> SubmissionService:
    return SubmissionService(repo)
