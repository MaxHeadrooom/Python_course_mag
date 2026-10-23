from collections.abc import Callable
from pathlib import Path

import pytest

from school_lab.sources import (
    InMemorySource,
    JSONLSource,
    SourceRecord,
    SubmissionSource,
)

# --- InMemorySource ---


def test_in_memory_source_yields_records() -> None:
    source = InMemorySource(["a", "b"])

    with source.open() as records:
        result = list(records)

    assert result == [
        SourceRecord(line_no=1, raw="a"),
        SourceRecord(line_no=2, raw="b"),
    ]


def test_in_memory_source_can_be_reopened() -> None:
    source = InMemorySource(["a", "b"])

    with source.open() as records:
        first = list(records)
    with source.open() as records:
        second = list(records)

    assert first == second
    assert len(second) == 2


def test_in_memory_source_keeps_own_copy() -> None:
    lines = ["a", "b"]
    source = InMemorySource(lines)

    lines.append("c")

    with source.open() as records:
        result = list(records)

    assert [r.raw for r in result] == ["a", "b"]


# --- JSONLSource: владение файлом ---


def write_jsonl(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "input.jsonl"
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def test_jsonl_file_closed_after_full_read(tmp_path: Path) -> None:
    source = JSONLSource(write_jsonl(tmp_path, ["a", "b"]))

    with source.open() as records:
        list(records)

    assert source.last_closed is True


def test_jsonl_file_closed_after_early_exit(tmp_path: Path) -> None:
    source = JSONLSource(write_jsonl(tmp_path, ["a", "b", "c"]))

    with source.open() as records:
        first = next(records)  # читаем только первую запись и выходим

    assert first.line_no == 1
    assert source.last_closed is True


def test_jsonl_file_closed_on_consumer_error(tmp_path: Path) -> None:
    source = JSONLSource(write_jsonl(tmp_path, ["a", "b"]))

    with pytest.raises(RuntimeError), source.open() as records:
        next(records)
        raise RuntimeError("consumer failed")

    # ошибка не проглочена (pytest.raises её поймал) и файл всё равно закрыт
    assert source.last_closed is True


def test_jsonl_missing_file_is_source_error(tmp_path: Path) -> None:
    # Отсутствие файла — ошибка источника (продолжать нельзя), а не ошибка одной сдачи
    source = JSONLSource(tmp_path / "missing.jsonl")

    with pytest.raises(OSError), source.open():
        pass


# --- Контракт источника: обе реализации ведут себя одинаково ---

SourceFactory = Callable[[Path, list[str]], SubmissionSource]


def make_in_memory(tmp_path: Path, lines: list[str]) -> SubmissionSource:
    return InMemorySource(lines)


def make_jsonl(tmp_path: Path, lines: list[str]) -> SubmissionSource:
    return JSONLSource(write_jsonl(tmp_path, lines))


@pytest.fixture(params=[make_in_memory, make_jsonl], ids=["in-memory", "jsonl"])
def make_source(request: pytest.FixtureRequest) -> SourceFactory:
    factory: SourceFactory = request.param
    return factory


def test_contract_records_order_and_numbers(
    make_source: SourceFactory, tmp_path: Path
) -> None:
    source = make_source(tmp_path, ['{"a": 1}', "{broken", "", "  last  "])

    with source.open() as records:
        result = list(records)

    assert result == [
        SourceRecord(1, '{"a": 1}'),
        SourceRecord(2, "{broken"),
        SourceRecord(3, ""),  # пустая строка — запись, а не пропуск
        SourceRecord(4, "  last  "),  # пробелы внутри строки не трогаются
    ]


def test_contract_can_be_reopened(make_source: SourceFactory, tmp_path: Path) -> None:
    source = make_source(tmp_path, ["a", "b"])

    with source.open() as records:
        first = list(records)
    with source.open() as records:
        second = list(records)

    assert first == second == [SourceRecord(1, "a"), SourceRecord(2, "b")]


def test_contract_empty_source(make_source: SourceFactory, tmp_path: Path) -> None:
    source = make_source(tmp_path, [])

    with source.open() as records:
        assert list(records) == []
