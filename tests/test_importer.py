import json
from dataclasses import asdict, replace
from pathlib import Path

from school_lab.importer import import_file, import_lines
from school_lab.models import Submission
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService

DATA_DIR = Path(__file__).parent.parent / "data"


def to_line(submission: Submission) -> str:
    return json.dumps(asdict(submission), ensure_ascii=False)


# Образец: смешанный файл из памятки (ячейка 54)
def test_mixed_lines(
    service: SubmissionService, repo: InMemorySubmissionRepository, submission: Submission
) -> None:
    second = replace(submission, submission_id="sub-002", student_id="student-002")
    lines = [
        to_line(submission),                                         # 1: принята
        "{broken",                                                   # 2: битый JSON
        to_line(submission),                                         # 3: дубликат
        to_line(replace(submission, text="Другое содержимое")),      # 4: конфликт
        to_line(replace(submission, submission_id="bad", student_id="")),  # 5: пустой student_id
        to_line(second),                                             # 6: принята
    ]

    summary = import_lines(lines, service)

    assert summary.accepted == ["sub-001", "sub-002"]
    assert summary.duplicate == ["sub-001"]
    assert [e["line_no"] for e in summary.errors] == [2, 4, 5]
    assert [e["code"] for e in summary.errors] == ["invalid_json", "conflict", "schema_error"]
    assert len(repo) == 2


def test_empty_line_is_error(service: SubmissionService, submission: Submission) -> None:
    lines =[
        to_line(submission),
        "",
        to_line(replace(submission, submission_id="sub-002"))
    ]
    summary = import_lines(lines, service)

    assert summary.accepted == ["sub-001", "sub-002"]
    assert summary.errors[0]["line_no"] == 2


def test_import_public_file(service: SubmissionService) -> None:
    summary = import_file(DATA_DIR / "submissions.jsonl", service)
    assert len(summary.accepted) == 12
    assert summary.errors == []


def test_reimport_gives_only_duplicates(service: SubmissionService) -> None:
    summary = import_file(DATA_DIR / "submissions.jsonl", service)
    summary_2 = import_file(DATA_DIR / "submissions.jsonl", service)

    assert summary_2.accepted == []
    assert len(summary_2.duplicate) == 12


def test_import_file_from_tmp(service: SubmissionService, tmp_path: Path, submission: Submission) -> None:
    path = tmp_path / "input.jsonl"
    path.write_text(to_line(submission) + "\n" + "{broken\n", encoding="utf-8")
    summary = import_file(path, service)

    assert summary.accepted == ["sub-001"]
    assert summary.errors[0]["line_no"] == 2
