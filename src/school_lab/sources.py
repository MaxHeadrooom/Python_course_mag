from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SourceRecord:
    line_no: int
    raw: str


class SubmissionSource(Protocol):
    def open(self) -> AbstractContextManager[Iterator[SourceRecord]]: ...


class InMemorySource:
    def __init__(self, lines: list[str]) -> None:
        self.lines = list(lines)

    @contextmanager
    def open(self) -> Iterator[Iterator[SourceRecord]]:
        def record_generator() -> Iterator[SourceRecord]:
            for line_no, raw in enumerate(self.lines, start=1):
                yield SourceRecord(line_no=line_no, raw=raw)

        yield record_generator()