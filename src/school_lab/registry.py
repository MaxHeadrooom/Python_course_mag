from collections.abc import Callable

from .analyzers import Analyzer
from .errors import AnalysisFailure


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Analyzer]] = {}

    def register(self, name: str, factory: Callable[[], Analyzer]) -> None:
        if not name.strip():
            raise AnalysisFailure("analyzer name must not be empty")
        if name in self._factories:
            raise AnalysisFailure(f"analyzer already registered: {name}")

        self._factories[name] = factory

    def create(self, name: str) -> Analyzer:
        try:
            factory = self._factories[name]
        except KeyError as e:
            raise AnalysisFailure(f"unknown analyzer: {name}") from e

        analyzer = factory()

        if analyzer.analyzer_id != name:
            raise AnalysisFailure(
                f"registered as {name!r}, but analyzer_id is {analyzer.analyzer_id!r}"
            )

        return analyzer
