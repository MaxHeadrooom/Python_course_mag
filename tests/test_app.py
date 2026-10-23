from pathlib import Path

import pytest

from school_lab.analyzers import AnalysisContext, validate_report
from school_lab.app import (
    AppConfig,
    build_application,
    load_assignment,
    load_config,
)
from school_lab.errors import AnalysisFailure
from school_lab.importer import import_file
from school_lab.sources import InMemorySource

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture
def context() -> AnalysisContext:
    return AnalysisContext(load_assignment(DATA_DIR / "assignments.json"))


# --- Сборка ---


def test_default_application_has_both_analyzers() -> None:
    app = build_application()

    assert app.registry.create("length").analyzer_id == "length"
    assert app.registry.create("template").analyzer_id == "template"


def test_applications_do_not_share_state() -> None:
    # Нет глобального состояния: два приложения — два независимых репозитория
    first = build_application()
    second = build_application()

    import_file(DATA_DIR / "submissions.jsonl", first.submission_service)

    assert len(first.repository) == 12
    assert len(second.repository) == 0


def test_config_selects_analyzers() -> None:
    app = build_application(AppConfig(analyzers=("length",)))

    app.registry.create("length")
    with pytest.raises(AnalysisFailure):
        app.registry.create("template")


# --- Некорректная конфигурация обнаруживается при сборке, до первого запроса ---


@pytest.mark.parametrize(
    "config",
    [
        AppConfig(analyzers=("unknown",)),
        AppConfig(analyzers=()),
        AppConfig(analyzers=("length", "length")),
    ],
    ids=["unknown-name", "empty", "duplicate"],
)
def test_bad_config_fails_at_build_time(config: AppConfig) -> None:
    with pytest.raises(AnalysisFailure):
        build_application(config)


def test_factory_with_wrong_id_fails_at_build_time() -> None:
    from school_lab.analyzers import LengthAnalyzer

    with pytest.raises(AnalysisFailure):
        build_application(
            AppConfig(analyzers=("template",)),
            available={"template": LengthAnalyzer},  # фабрика под чужим именем
        )


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"analyzers": "length"},
        {"analyzers": ["length", 1]},
        {"analyzers": ["length"], "debug": True},
    ],
    ids=["not-object", "not-list", "not-string", "unknown-key"],
)
def test_bad_config_data_is_rejected(data: object) -> None:
    with pytest.raises(AnalysisFailure):
        AppConfig.from_dict(data)


def test_load_config_from_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"analyzers": ["template"]}', encoding="utf-8")

    assert load_config(path) == AppConfig(analyzers=("template",))


def test_load_assignment() -> None:
    assignment = load_assignment(DATA_DIR / "assignments.json")

    assert assignment.assignment_id == "assignment-01"
    assert assignment.allowed_template == "from typing import Iterable\n"
    assert assignment.requirements == ("Наличие функции solve",)


# --- Сквозной сценарий (памятка, раздел 28) ---


def test_end_to_end(context: AnalysisContext) -> None:
    app = build_application()

    first = import_file(DATA_DIR / "submissions.jsonl", app.submission_service)
    second = import_file(DATA_DIR / "submissions.jsonl", app.submission_service)

    assert len(first.accepted) == 12 and not first.errors
    assert len(second.duplicate) == 12 and not second.accepted and not second.errors

    reports = 0
    for submission_id in first.accepted:
        original = app.repository.get(submission_id)
        assert original is not None
        for name in ("length", "template"):
            report = app.analysis_service.run(submission_id, name, context)
            validate_report(report, original, context)
            assert app.repository.get(submission_id) == original
            reports += 1

    assert reports == 24


def test_source_can_be_replaced_in_application(context: AnalysisContext) -> None:
    # Источник подменяется через контракт, а не глобальной подменой функций
    from school_lab.importer import import_source

    app = build_application()
    with (DATA_DIR / "submissions.jsonl").open(encoding="utf-8") as f:
        first_line = f.readline().rstrip("\n")

    summary = import_source(InMemorySource([first_line]), app.submission_service)

    assert summary.accepted == ["sub-001"]
    assert app.analysis_service.run("sub-001", "length", context).findings
