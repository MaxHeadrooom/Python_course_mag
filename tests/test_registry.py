import pytest

from school_lab.analyzers import LengthAnalyzer
from school_lab.errors import AnalysisFailure
from school_lab.registry import AnalyzerRegistry


def test_registry_register() -> None:
    registry = AnalyzerRegistry()

    registry.register("length", LengthAnalyzer)

    analyzer = registry.create("length")

    assert analyzer.analyzer_id == "length"


def test_create_returns_new_instance() -> None:
    registry = AnalyzerRegistry()

    registry.register("length", LengthAnalyzer)

    analyzer = registry.create("length")

    analyzer2 = registry.create("length")

    assert analyzer is not analyzer2


def test_create_unknown_fails() -> None:
    registry = AnalyzerRegistry()
    with pytest.raises(AnalysisFailure):
        registry.create("unknown")


def test_register_again() -> None:
    registry = AnalyzerRegistry()
    registry.register("length", LengthAnalyzer)

    with pytest.raises(AnalysisFailure):
        registry.register("length", LengthAnalyzer)


def test_empty_name() -> None:
    registry = AnalyzerRegistry()
    with pytest.raises(AnalysisFailure):
        registry.register("", LengthAnalyzer)


def test_blank_name() -> None:
    registry = AnalyzerRegistry()
    with pytest.raises(AnalysisFailure):
        registry.register("   ", LengthAnalyzer)


def test_name_mismatch_fails() -> None:
    registry = AnalyzerRegistry()
    registry.register("template", LengthAnalyzer)

    with pytest.raises(AnalysisFailure):
        registry.create("template")
