from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
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


class JSONLSource:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.last_closed: bool | None = None

    @contextmanager
    def open(self) -> Iterator[Iterator[SourceRecord]]:
        handle = self.path.open("r", encoding="utf-8")

        try:
            def record_generator() -> Iterator[SourceRecord]:
                for line_no, raw in enumerate(handle, start=1):
                    yield SourceRecord(line_no=line_no, raw=raw.rstrip("\n"))
            yield record_generator()
        finally:
            handle.close()
            self.last_closed = handle.closed