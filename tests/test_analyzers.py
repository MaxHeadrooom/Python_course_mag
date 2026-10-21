from dataclasses import replace
from datetime import datetime

from school_lab import analyzers
from school_lab.analyzers import AnalysisContext, make_report
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
