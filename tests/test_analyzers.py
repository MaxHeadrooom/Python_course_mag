from copy import deepcopy
from dataclasses import replace
from datetime import datetime

from school_lab import analyzers
from school_lab.analyzers import AnalysisContext, Analyzer, LengthAnalyzer, make_report
from school_lab.hashing import stable_hash, submission_hash
from school_lab.models import Assignment, Finding, Submission


def test_nonempty_line_numbers() -> None:
    test_str = "\n a \n\n b\n"

    assert analyzers.nonempty_line_numbers(test_str) == (2, 4)

def test_empty_line_numbers() -> None:
    test_str = ""

    assert analyzers.nonempty_line_numbers(test_str) == ()

def test_without_spaces_numbers() -> None:
    test_str = "a\nb"

    assert analyzers.nonempty_line_numbers(test_str) == (1, 2)

def test_spaces_and_newlines_numbers() -> None:
    test_str = "          \n     \n"

    assert analyzers.nonempty_line_numbers(test_str) == ()

def make_assignment() -> Assignment:
    return Assignment("assignment-01", "from typing import Iterable\n", ("Наличие функции solve",))

def test_config_hash_changes_with_assignment() -> None:
    assignment = make_assignment()

    context = AnalysisContext(assignment)

    hash1 = stable_hash(context.config_payload())

    assignment2 = replace(make_assignment(), requirements=("Наличие функции main",))

    context2 = AnalysisContext(assignment2)

    hash2 = stable_hash(context2.config_payload())

    assert hash1 != hash2


def test_config_hash_changes() -> None:
    assignment = make_assignment()

    context = AnalysisContext(assignment)

    hash1 = stable_hash(context.config_payload())

    assignment2 = replace(make_assignment(), allowed_template="brbr paptapim")

    context2 = AnalysisContext(assignment2)

    hash2 = stable_hash(context2.config_payload())

    assert hash1 != hash2

def make_context() -> AnalysisContext:
    return AnalysisContext(make_assignment())


def make_finding() -> Finding:
    return Finding("rubric_feedback", None, (), "тест")

def test_report_ids_are_unique(submission: Submission) -> None:
    context = make_context()
    report1 = make_report(submission, context, "length", "1.0", (make_finding(),))
    report2 = make_report(submission, context, "length", "1.0", (make_finding(),))

    assert report1.report_id != report2.report_id


def test_report_has_submission_hash(submission: Submission) -> None:
    report = make_report(submission, make_context(), "length", "1.0", (make_finding(),))

    assert report.submission_hash == submission_hash(submission)
    assert report.submission_id == submission.submission_id


def test_report_created_at_has_timezone(submission: Submission) -> None:
    report = make_report(submission, make_context(), "length", "1.0", (make_finding(),))

    created = datetime.fromisoformat(report.created_at)
    assert created.tzinfo is not None


def test_report_config_hash(submission: Submission) -> None:
    context = make_context()
    report = make_report(submission, context, "length", "1.0", (make_finding(),))

    assert report.config_hash == stable_hash(context.config_payload())


def test_length_report_metadata(submission: Submission) -> None:
    report = LengthAnalyzer().analyze(submission, make_context())
    assert report.analyzer_id == "length" and report.analyzer_version == "1.0"
    assert report.submission_id == submission.submission_id


def test_length_single_rubric_finding(submission: Submission) -> None:
    report = LengthAnalyzer().analyze(submission, make_context())

    assert len(report.findings) == 1

    finding = report.findings[0]
    assert finding.kind == "rubric_feedback"
    assert finding.score is None


def test_length_evidence_count(submission: Submission) -> None:
    report = LengthAnalyzer().analyze(submission, make_context())

    evidence = report.findings[0].evidence

    count = [e for e in evidence if e.field == "code"]
    count2 = analyzers.nonempty_line_numbers(submission.code)

    assert len(count) == len(count2)


def make_tricky(submission: Submission) -> Submission:

    return replace(submission, text="\nПояснение\n", code="a = 1\n\n   \nb = 2\n")


def test_length_evidence_points_to_nonempty_lines(submission: Submission) -> None:
    tricky = make_tricky(submission)
    report = LengthAnalyzer().analyze(tricky, make_context())

    for e in report.findings[0].evidence:
        lines = getattr(tricky, e.field).splitlines()
        assert e.submission_id == tricky.submission_id
        assert 1 <= e.start_line <= e.end_line <= len(lines)
        assert lines[e.start_line - 1].strip()


def test_length_evidence_line_numbers_are_original(submission: Submission) -> None:
    report = LengthAnalyzer().analyze(make_tricky(submission), make_context())
    evidence = report.findings[0].evidence

    assert [e.start_line for e in evidence if e.field == "text"] == [2]
    assert [e.start_line for e in evidence if e.field == "code"] == [1, 4]


def test_length_does_not_change_submission(submission: Submission) -> None:
    before = deepcopy(submission)

    LengthAnalyzer().analyze(submission, make_context())

    assert submission == before
    assert submission_hash(submission) == submission_hash(before)


def test_length_matches_protocol(submission: Submission) -> None:
    analyzer: Analyzer = LengthAnalyzer()

    report = analyzer.analyze(submission, make_context())
    assert report.analyzer_id == analyzer.analyzer_id
    assert report.analyzer_version == analyzer.analyzer_version
