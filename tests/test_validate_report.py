from dataclasses import replace

import pytest

from school_lab.analyzers import (
    AnalysisContext,
    LengthAnalyzer,
    TemplateAnalyzer,
    validate_report,
)
from school_lab.errors import AnalysisFailure
from school_lab.models import AnalysisReport, Assignment, Evidence, Submission


@pytest.fixture
def context() -> AnalysisContext:
    return AnalysisContext(
        Assignment("assignment-01", "from typing import Iterable\n", ())
    )


@pytest.fixture
def good_report(submission: Submission, context: AnalysisContext) -> AnalysisReport:
    return LengthAnalyzer().analyze(submission, context)


def with_finding(report: AnalysisReport, **changes: object) -> AnalysisReport:
    """Копия отчёта, в которой у первой находки изменены поля."""
    finding = replace(report.findings[0], **changes)  # type: ignore[arg-type]
    return replace(report, findings=(finding,))


def with_evidence(report: AnalysisReport, evidence: Evidence) -> AnalysisReport:
    return with_finding(report, evidence=(evidence,))


# --- Правильные отчёты проходят ---


@pytest.mark.parametrize("analyzer", [LengthAnalyzer(), TemplateAnalyzer()])
def test_reports_of_real_analyzers_are_valid(
    analyzer: LengthAnalyzer | TemplateAnalyzer,
    submission: Submission,
    context: AnalysisContext,
) -> None:
    validate_report(analyzer.analyze(submission, context), submission, context)


@pytest.mark.parametrize("score", [None, 0, 0.5, 1, 1.0])
def test_allowed_scores(
    good_report: AnalysisReport,
    submission: Submission,
    context: AnalysisContext,
    score: object,
) -> None:
    validate_report(with_finding(good_report, score=score), submission, context)


# --- Часть 1: отчёт в целом ---


def test_not_a_report(submission: Submission, context: AnalysisContext) -> None:
    with pytest.raises(AnalysisFailure):
        validate_report("not a report", submission, context)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"submission_id": "sub-999"},
        {"submission_hash": "0" * 64},
        {"config_hash": "other"},
        {"report_id": ""},
        {"analyzer_id": ""},
        {"analyzer_version": ""},
        {"review_required": 1},
        {"created_at": "вчера"},
        {"created_at": "2026-09-01T10:00:00"},  # без часового пояса
    ],
)
def test_broken_report_fields(
    good_report: AnalysisReport,
    submission: Submission,
    context: AnalysisContext,
    changes: dict[str, object],
) -> None:
    bad = replace(good_report, **changes)  # type: ignore[arg-type]

    with pytest.raises(AnalysisFailure):
        validate_report(bad, submission, context)


def test_report_for_other_version_of_submission(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    # Отчёт сделан для старой версии; сдача с тем же id, но другим кодом — не та версия
    newer = replace(submission, code=submission.code + "# changed\n")

    with pytest.raises(AnalysisFailure):
        validate_report(good_report, newer, context)


def test_report_for_other_config(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    other = AnalysisContext(context.assignment, config_version="2")

    with pytest.raises(AnalysisFailure):
        validate_report(good_report, submission, other)


# --- Часть 2: находки ---


@pytest.mark.parametrize("score", [1.5, -0.1, True, float("nan"), float("inf"), "0.5"])
def test_bad_scores(
    good_report: AnalysisReport,
    submission: Submission,
    context: AnalysisContext,
    score: object,
) -> None:
    with pytest.raises(AnalysisFailure):
        validate_report(with_finding(good_report, score=score), submission, context)


def test_unknown_kind(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    with pytest.raises(AnalysisFailure):
        validate_report(with_finding(good_report, kind="verdict"), submission, context)


def test_empty_explanation(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    with pytest.raises(AnalysisFailure):
        validate_report(
            with_finding(good_report, explanation="   "), submission, context
        )


# --- Часть 2: evidence ---


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (0, 1),  # строки нумеруются с 1
        (1, 99),  # за концом поля
        (2, 1),  # начало после конца
    ],
)
def test_evidence_out_of_range(
    good_report: AnalysisReport,
    submission: Submission,
    context: AnalysisContext,
    start: int,
    end: int,
) -> None:
    bad = with_evidence(
        good_report, Evidence(submission.submission_id, "code", start, end)
    )

    with pytest.raises(AnalysisFailure):
        validate_report(bad, submission, context)


def test_evidence_last_line_is_allowed(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    last = len(submission.code.splitlines())
    ok = with_evidence(good_report, Evidence(submission.submission_id, "code", 1, last))

    validate_report(ok, submission, context)


def test_evidence_of_other_submission(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    bad = with_evidence(good_report, Evidence("sub-999", "code", 1, 1))

    with pytest.raises(AnalysisFailure):
        validate_report(bad, submission, context)


def test_evidence_unknown_field(
    good_report: AnalysisReport, submission: Submission, context: AnalysisContext
) -> None:
    bad = with_evidence(
        good_report,
        Evidence(submission.submission_id, "student_id", 1, 1),  # type: ignore[arg-type]
    )

    with pytest.raises(AnalysisFailure):
        validate_report(bad, submission, context)
