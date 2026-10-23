from school_lab.sources import InMemorySource, SourceRecord


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
