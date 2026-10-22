import math
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from .errors import AnalysisFailure
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


FINDING_KINDS = frozenset({"similarity", "rubric_feedback", "processing_error"})
EVIDENCE_FIELDS = frozenset({"text", "code"})


def validate_report(
    report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    """Проверка отчёта на границе: аннотация -> AnalysisReport ничего не гарантирует
    во время выполнения, поэтому отчёт стороннего анализатора проверяется явно."""
    # Часть 1: отчёт в целом
    if not isinstance(report, AnalysisReport):
        raise AnalysisFailure("analyzer must return AnalysisReport")

    if (
        report.submission_id != submission.submission_id
        or report.submission_hash != submission_hash(submission)
    ):
        raise AnalysisFailure("report refers to another version of the submission")

    if report.config_hash != stable_hash(context.config_payload()):
        raise AnalysisFailure("report was made with another configuration")

    if not report.report_id or not report.analyzer_id or not report.analyzer_version:
        raise AnalysisFailure("report_id, analyzer_id and analyzer_version are required")

    if type(report.review_required) is not bool:
        raise AnalysisFailure("review_required must be bool")

    try:
        created = datetime.fromisoformat(report.created_at)
    except (TypeError, ValueError) as e:
        raise AnalysisFailure("created_at must be an ISO datetime") from e
    if created.tzinfo is None:
        raise AnalysisFailure("created_at must contain a timezone")

    # Часть 2: находки и evidence
    for finding in report.findings:
        _validate_finding(finding, submission)


def _validate_finding(finding: Finding, submission: Submission) -> None:
    if finding.kind not in FINDING_KINDS:
        raise AnalysisFailure(f"unknown finding kind: {finding.kind!r}")

    score = finding.score
    if score is not None:
        # bool — подкласс int, поэтому True отсекается проверкой type(...), а не isinstance
        if type(score) not in (int, float):
            raise AnalysisFailure("score must be a number or None")
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise AnalysisFailure("score must be a finite number from 0 to 1")

    if not finding.explanation.strip():
        raise AnalysisFailure("finding explanation is required")

    for evidence in finding.evidence:
        if evidence.submission_id != submission.submission_id:
            raise AnalysisFailure("evidence refers to another submission")
        if evidence.field not in EVIDENCE_FIELDS:
            raise AnalysisFailure(f"unknown evidence field: {evidence.field!r}")
        if type(evidence.start_line) is not int or type(evidence.end_line) is not int:
            raise AnalysisFailure("evidence line numbers must be int")

        lines = getattr(submission, evidence.field).splitlines()
        if not 1 <= evidence.start_line <= evidence.end_line <= len(lines):
            raise AnalysisFailure("evidence is outside the original text")


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


class TemplateAnalyzer:
    analyzer_id = "template"
    analyzer_version = "1.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        if submission.assignment_id != context.assignment.assignment_id:
            raise AnalysisFailure("context belongs to a different assignment")

        ranges = template_ranges(submission.code, context.assignment.allowed_template)

        evidence = tuple(
            Evidence(
                submission_id=submission.submission_id,
                field="code",
                start_line=start,
                end_line=end,
            )
            for start, end in ranges
        )

        if ranges:
            explanation = (
                f"Allowed template blocks found: {len(ranges)}. "
                "This is a permitted match, not a reason for sanctions."
            )
        else:
            explanation = (
                "No exact match with the allowed template. "
                "Fuzzy similarity was not checked."
            )

        finding = Finding(
            kind="similarity",
            score=None,
            evidence=evidence,
            explanation=explanation,
        )

        return make_report(
            submission,
            context,
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            findings=(finding,),
        )
