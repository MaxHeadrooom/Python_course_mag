from copy import deepcopy
from dataclasses import replace

import pytest

from school_lab.analysis_service import AnalysisService
from school_lab.analyzers import (
    AnalysisContext,
    LengthAnalyzer,
    TemplateAnalyzer,
    make_report,
)
from school_lab.errors import AnalysisFailure
from school_lab.models import AnalysisReport, Assignment, Finding, Submission
from school_lab.registry import AnalyzerRegistry
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService


@pytest.fixture
def context() -> AnalysisContext:
    return AnalysisContext(
        Assignment(
            "assignment-01", "from typing import Iterable\n", ("Наличие функции solve",)
        )
    )


@pytest.fixture
def registry() -> AnalyzerRegistry:
    registry = AnalyzerRegistry()
    registry.register("length", LengthAnalyzer)
    registry.register("template", TemplateAnalyzer)
    return registry


@pytest.fixture
def analysis(
    repo: InMemorySubmissionRepository,
    service: SubmissionService,
    registry: AnalyzerRegistry,
    submission: Submission,
) -> AnalysisService:
    service.accept(submission)
    return AnalysisService(repo, registry)


class LyingIdAnalyzer:
    analyzer_id = "liar"
    analyzer_version = "1.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        return make_report(
            submission, context, "someone-else", self.analyzer_version, ()
        )


class LyingVersionAnalyzer:
    analyzer_id = "old"
    analyzer_version = "2.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        return make_report(submission, context, self.analyzer_id, "1.0", ())


class DeclarationAnalyzer:
    analyzer_id = "declaration"
    analyzer_version = "1.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        declaration = submission.ai_declaration
        if declaration.used:
            explanation = f"AI use declared. Tool: {declaration.tool}; purpose: {declaration.purpose}."
        else:
            explanation = (
                "AI use not declared. Authorship was not determined automatically."
            )
        finding = Finding("rubric_feedback", None, (), explanation)
        return make_report(
            submission,
            context,
            self.analyzer_id,
            self.analyzer_version,
            (finding,),
            review_required=declaration.used and not declaration.verified_by_student,
        )


@pytest.mark.parametrize("name", ["length", "template"])
def test_run_returns_report_of_called_analyzer(
    analysis: AnalysisService,
    context: AnalysisContext,
    submission: Submission,
    name: str,
) -> None:
    report = analysis.run(submission.submission_id, name, context)

    assert report.analyzer_id == name
    assert report.submission_id == submission.submission_id
    assert len(report.findings) == 1


def test_run_does_not_change_stored_submission(
    analysis: AnalysisService,
    repo: InMemorySubmissionRepository,
    context: AnalysisContext,
    submission: Submission,
) -> None:
    before = deepcopy(repo.get(submission.submission_id))

    analysis.run(submission.submission_id, "length", context)
    analysis.run(submission.submission_id, "template", context)

    assert repo.get(submission.submission_id) == before
    assert len(repo) == 1


def test_run_unknown_submission_fails(
    analysis: AnalysisService, context: AnalysisContext
) -> None:
    with pytest.raises(AnalysisFailure):
        analysis.run("sub-404", "length", context)


def test_run_unknown_analyzer_fails(
    analysis: AnalysisService, context: AnalysisContext, submission: Submission
) -> None:
    with pytest.raises(AnalysisFailure):
        analysis.run(submission.submission_id, "unknown", context)


def test_run_context_of_other_assignment_fails(
    analysis: AnalysisService, context: AnalysisContext, submission: Submission
) -> None:
    other = AnalysisContext(replace(context.assignment, assignment_id="assignment-99"))

    with pytest.raises(AnalysisFailure):
        analysis.run(submission.submission_id, "length", other)


def test_run_rejects_report_with_foreign_analyzer_id(
    analysis: AnalysisService,
    registry: AnalyzerRegistry,
    context: AnalysisContext,
    submission: Submission,
) -> None:
    registry.register("liar", LyingIdAnalyzer)

    with pytest.raises(AnalysisFailure):
        analysis.run(submission.submission_id, "liar", context)


def test_run_rejects_report_with_wrong_version(
    analysis: AnalysisService,
    registry: AnalyzerRegistry,
    context: AnalysisContext,
    submission: Submission,
) -> None:
    registry.register("old", LyingVersionAnalyzer)

    with pytest.raises(AnalysisFailure):
        analysis.run(submission.submission_id, "old", context)


def test_failed_analyzer_does_not_change_stored_submission(
    analysis: AnalysisService,
    repo: InMemorySubmissionRepository,
    registry: AnalyzerRegistry,
    context: AnalysisContext,
    submission: Submission,
) -> None:
    registry.register("liar", LyingIdAnalyzer)
    before = deepcopy(repo.get(submission.submission_id))

    with pytest.raises(AnalysisFailure):
        analysis.run(submission.submission_id, "liar", context)

    assert repo.get(submission.submission_id) == before


def test_third_analyzer_plugs_in_by_registration_only(
    analysis: AnalysisService,
    registry: AnalyzerRegistry,
    context: AnalysisContext,
    submission: Submission,
) -> None:
    registry.register("declaration", DeclarationAnalyzer)

    report = analysis.run(submission.submission_id, "declaration", context)

    assert report.analyzer_id == "declaration"
    assert "not declared" in report.findings[0].explanation
    assert report.review_required is False
