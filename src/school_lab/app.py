"""Точка сборки приложения (composition root).

Здесь — и только здесь — решается, какие конкретные классы используются:
какой репозиторий, какие анализаторы попадают в реестр. Сервисы получают
готовые зависимости через конструктор и не знают о конкретных реализациях.
Глобального изменяемого состояния нет: каждый вызов build_application
создаёт независимое приложение (отдельный репозиторий и реестр).
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .analysis_service import AnalysisService
from .analyzers import Analyzer, LengthAnalyzer, TemplateAnalyzer
from .errors import AnalysisFailure
from .models import Assignment
from .registry import AnalyzerRegistry
from .repository import InMemorySubmissionRepository
from .service import SubmissionService

# Все анализаторы, которые приложение умеет создавать.
# Новый анализатор подключается строкой здесь; сервисы не меняются.
AVAILABLE_ANALYZERS: Mapping[str, Callable[[], Analyzer]] = {
    "length": LengthAnalyzer,
    "template": TemplateAnalyzer,
}


DEFAULT_ANALYZERS: tuple[str, ...] = ("length", "template")


@dataclass(frozen=True, slots=True)
class AppConfig:
    analyzers: tuple[str, ...] = DEFAULT_ANALYZERS

    @classmethod
    def from_dict(cls, data: object) -> "AppConfig":
        """Строгий разбор конфигурации: ошибка видна до первого запроса."""
        if not isinstance(data, dict):
            raise AnalysisFailure("config must be a JSON object")
        unknown_keys = set(data) - {"analyzers"}
        if unknown_keys:
            raise AnalysisFailure(f"unknown config keys: {sorted(unknown_keys)}")

        names = data.get("analyzers", list(DEFAULT_ANALYZERS))
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise AnalysisFailure("config.analyzers must be a list of strings")
        return cls(analyzers=tuple(names))


@dataclass(frozen=True, slots=True)
class Application:
    repository: InMemorySubmissionRepository
    registry: AnalyzerRegistry
    submission_service: SubmissionService
    analysis_service: AnalysisService


def build_application(
    config: AppConfig | None = None,
    available: Mapping[str, Callable[[], Analyzer]] = AVAILABLE_ANALYZERS,
) -> Application:
    config = config or AppConfig()

    if not config.analyzers:
        raise AnalysisFailure("config must enable at least one analyzer")
    if len(set(config.analyzers)) != len(config.analyzers):
        raise AnalysisFailure("analyzers in config must not repeat")

    registry = AnalyzerRegistry()
    for name in config.analyzers:
        if name not in available:
            raise AnalysisFailure(f"unknown analyzer in config: {name}")
        registry.register(name, available[name])
        # Проверка при сборке: фабрика создаётся и её analyzer_id совпадает с именем.
        registry.create(name)

    repository = InMemorySubmissionRepository()
    return Application(
        repository=repository,
        registry=registry,
        submission_service=SubmissionService(repository),
        analysis_service=AnalysisService(repository, registry),
    )


def load_config(path: Path) -> AppConfig:
    with path.open(encoding="utf-8") as f:
        return AppConfig.from_dict(json.load(f))


def load_assignment(path: Path) -> Assignment:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return Assignment(
        assignment_id=data["assignment_id"],
        allowed_template=data["allowed_template"],
        requirements=tuple(data["requirements"]),
    )
