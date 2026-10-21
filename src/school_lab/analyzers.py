from dataclasses import asdict, dataclass
from typing import Protocol

from .models import AnalysisReport, Assignment, Submission


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    assignment: Assignment
    config_version: str = "1"

    def config_payload(self) -> dict[str, object]:
        data = asdict(self)
        return data


class Analyzer(Protocol):
    @property
    def analyzer_id(self) -> str: ...

    @property
    def analyzer_version(self) -> str: ...

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport: ...


def nonempty_line_numbers(text: str) -> tuple[int, ...]:
    res: tuple[int, ...] = ()

    lines = text.splitlines()

    for i in range(len(lines)):
        if lines[i].strip():
            res += (i + 1, )

    return res
