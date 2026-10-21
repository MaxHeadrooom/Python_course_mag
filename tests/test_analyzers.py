from dataclasses import replace

from school_lab import analyzers
from school_lab.analyzers import AnalysisContext
from school_lab.hashing import stable_hash
from school_lab.models import Assignment


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