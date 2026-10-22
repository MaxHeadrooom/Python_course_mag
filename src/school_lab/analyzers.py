import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from .hashing import stable_hash, submission_hash
from .models import AnalysisReport, Assignment, Evidence, Finding, Submission


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

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport: ...


def nonempty_line_numbers(text: str) -> tuple[int, ...]:
    res: tuple[int, ...] = ()

    lines = text.splitlines()

    for i in range(len(lines)):
        if lines[i].strip():
            res += (i + 1,)

    return res


def template_ranges(source_code: str, template: str) -> tuple[tuple[int, int], ...]:
    if not template.strip():
        return ()

    lines_of_code = source_code.splitlines()
    lines_of_template = template.splitlines()

    res = []

    len_code = len(lines_of_code)
    len_template = len(lines_of_template)

    for i in range(len_code - len_template + 1):
        if lines_of_code[i: i + len_template] == lines_of_template:
            start_line = i + 1
            end_line = len_template + i
            res.append((start_line, end_line))

    return tuple(res)


def make_report(
    submission: Submission,
    context: AnalysisContext,
    analyzer_id: str,
    analyzer_version: str,
    findings: tuple[Finding, ...],
    *,
    review_required: bool = False,
) -> AnalysisReport:
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


class LengthAnalyzer:
    analyzer_id = "length"
    analyzer_version = "1.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        lines_text = nonempty_line_numbers(submission.text)
        lines_code = nonempty_line_numbers(submission.code)

        evidence = []

        for line in lines_text:
            evidence.append(
                Evidence(
                    submission_id=submission.submission_id,
                    field="text",
                    start_line=line,
                    end_line=line,
                )
            )

        for line in lines_code:
            evidence.append(
                Evidence(
                    submission_id=submission.submission_id,
                    field="code",
                    start_line=line,
                    end_line=line,
                )
            )

        result = tuple(evidence)

        finding = Finding(
            kind="rubric_feedback",
            score=None,
            evidence=result,
            explanation=f"not empty lines: text={len(lines_text)}, "
            f"code={len(lines_code)} Length does not measure correctness.",
        )

        return make_report(
            submission,
            context,
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            findings=(finding,),
        )
