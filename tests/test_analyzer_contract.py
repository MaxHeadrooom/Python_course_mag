"""Контрактные тесты анализаторов: один набор проверок для всех реализаций протокола.

Protocol проверяет только форму (есть analyze, analyzer_id, analyzer_version).
Поведение — отчёт про эту сдачу, корректные evidence, неизменность входа —
проверяют эти тесты. Новый анализатор достаточно добавить в ANALYZERS.
"""

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest

from school_lab.analyzers import (
    AnalysisContext,
    Analyzer,
    LengthAnalyzer,
    TemplateAnalyzer,
    validate_report,
)
from school_lab.models import Assignment, Submission
from school_lab.parser import parse_submission

DATA_DIR = Path(__file__).parent.parent / "data"

ANALYZERS: list[Callable[[], Analyzer]] = [LengthAnalyzer, TemplateAnalyzer]


def load_public_submissions() -> list[Submission]:
    with (DATA_DIR / "submissions.jsonl").open(encoding="utf-8") as f:
        return [parse_submission(line) for line in f]


PUBLIC_SUBMISSIONS = load_public_submissions()


@pytest.fixture(params=ANALYZERS, ids=lambda factory: factory().analyzer_id)
def analyzer(request: pytest.FixtureRequest) -> Analyzer:
    factory: Callable[[], Analyzer] = request.param
    return factory()


@pytest.fixture
def context() -> AnalysisContext:
    return AnalysisContext(
        Assignment(
            "assignment-01", "from typing import Iterable\n", ("Наличие функции solve",)
        )
    )


@pytest.mark.parametrize(
    "submission", PUBLIC_SUBMISSIONS, ids=[s.submission_id for s in PUBLIC_SUBMISSIONS]
)
def test_report_is_valid_for_every_public_submission(
    analyzer: Analyzer, context: AnalysisContext, submission: Submission
) -> None:
    report = analyzer.analyze(submission, context)

    validate_report(report, submission, context)
    assert report.analyzer_id == analyzer.analyzer_id
    assert report.analyzer_version == analyzer.analyzer_version
    assert report.findings, "отчёт должен содержать хотя бы одно наблюдение"


def test_analysis_does_not_change_submission(
    analyzer: Analyzer, context: AnalysisContext, submission: Submission
) -> None:
    before = deepcopy(submission)

    analyzer.analyze(submission, context)

    assert submission == before


def test_repeated_analysis_gives_same_findings(
    analyzer: Analyzer, context: AnalysisContext, submission: Submission
) -> None:
    # Повторяемость — по смыслу (findings), а не по всему отчёту:
    # report_id и created_at у каждого запуска свои.
    first = analyzer.analyze(submission, context)
    second = analyzer.analyze(submission, context)

    assert first.findings == second.findings
    assert first.report_id != second.report_id


def test_score_is_none_without_justified_metric(
    analyzer: Analyzer, context: AnalysisContext, submission: Submission
) -> None:
    # В ЛР 1 ни у одного анализатора нет обоснованной численной метрики
    report = analyzer.analyze(submission, context)

    assert all(finding.score is None for finding in report.findings)
