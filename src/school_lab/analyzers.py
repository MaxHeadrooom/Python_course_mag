import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from .hashing import stable_hash, submission_hash
from .models import AnalysisReport, Assignment, Finding, Submission


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    assignment: Assignment
    config_version: str = "1"

    def config_payload(self) -> dict[str, object]:
        data = asdict(self)
        return data


class Analyzer(Protocol):
    @property
    def analyzer_id(self) -> str: ...

    @property
    def analyzer_version(self) -> str: ...

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport: ...


def nonempty_line_numbers(text: str) -> tuple[int, ...]:
    res: tuple[int, ...] = ()

    lines = text.splitlines()

    for i in range(len(lines)):
        if lines[i].strip():
            res += (i + 1, )

    return res

def make_report(submission: Submission, context: AnalysisContext, analyzer_id: str, analyzer_version: str, findings: tuple[Finding, ...],
                *, review_required: bool = False) -> AnalysisReport:
    report_id = str(uuid.uuid4())

    sub_hash = submission_hash(submission)

    config_hash = stable_hash(context.config_payload())

    created_at = datetime.now(UTC).isoformat()

    submission_id = submission.submission_id

    return AnalysisReport(
        report_id=report_id,
        submission_hash=sub_hash,
        analyzer_id=analyzer_id,
        analyzer_version=analyzer_version,
        findings=findings,
        review_required=review_required,
        config_hash=config_hash,
        created_at=created_at,
        submission_id=submission_id,
    )