import json
from typing import Any

import pytest

from school_lab.errors import SubmissionError
from school_lab.models import Submission
from school_lab.parser import parse_submission


def valid_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "submission_id": "sub-001",
        "student_id": "student-001",
        "assignment_id": "assignment-01",
        "submitted_at": "2026-09-01T10:01:00+03:00",
        "text": "Учебное решение.",
        "code": "print(1)\n",
        "template_id": "template-01",
        "ai_declaration": {
            "used": False,
            "tool": None,
            "purpose": None,
            "verified_by_student": True,
        },
    }


def test_valid_submission_is_parsed() -> None:
    result = parse_submission(json.dumps(valid_payload()))
    assert isinstance(result, Submission)
    assert result.student_id == "student-001"


# Образец: как проверять, что функция бросает ошибку с нужными code и field
def test_broken_json_is_invalid_json() -> None:
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission('{"schema_version": 1,')
    assert exc_info.value.code == "invalid_json"


def test_json_array_is_invalid_json() -> None:
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission("[1, 2, 3]")
    assert exc_info.value.code == "invalid_json"


def test_unknown_version() -> None:
    payload = valid_payload()
    payload["schema_version"] = 2
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "unsupported_version"
    assert exc_info.value.field == "schema_version"


def test_empty_student_id() -> None:
    payload = valid_payload()
    payload["student_id"] = "   "
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "student_id"


def test_timestamp_without_timezone() -> None:
    payload = valid_payload()
    payload["submitted_at"] = "2026-09-01T10:01:00"
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "submitted_at"


def test_garbage_timestamp() -> None:
    payload = valid_payload()
    payload["submitted_at"] = "вчера"
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "submitted_at"


def test_unknown_field() -> None:
    payload = valid_payload()
    payload["grade"] = 5
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "grade"


def test_wrong_type() -> None:
    payload = valid_payload()
    payload["ai_declaration"]["used"] = "yes"
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(json.dumps(payload))
    assert exc_info.value.code == "schema_error"
    assert exc_info.value.field == "ai_declaration.used"


def test_input_is_not_mutated() -> None:
    payload = valid_payload()
    snapshot = json.dumps(payload)
    parse_submission(json.dumps(payload))
    assert json.dumps(payload) == snapshot


# --- Требования из памятки (ячейки 3, 33, 35) ---


def expect_error(raw: str, code: str, field: str) -> None:
    with pytest.raises(SubmissionError) as exc_info:
        parse_submission(raw)
    assert exc_info.value.code == code
    assert exc_info.value.field == field


def test_blank_tool_rejected() -> None:
    payload = valid_payload()
    payload["ai_declaration"]["tool"] = "  "
    expect_error(json.dumps(payload), "schema_error", "ai_declaration.tool")


def test_used_without_tool_and_purpose() -> None:
    payload = valid_payload()
    payload["ai_declaration"]["used"] = True
    expect_error(json.dumps(payload), "schema_error", "ai_declaration")


def test_used_with_tool_and_purpose_ok() -> None:
    payload = valid_payload()
    payload["ai_declaration"] = {
        "used": True,
        "tool": "учебный помощник",
        "purpose": "обсуждение решения",
        "verified_by_student": True,
    }
    assert parse_submission(json.dumps(payload)).ai_declaration.used is True


def test_blank_template_id() -> None:
    payload = valid_payload()
    payload["template_id"] = " "
    expect_error(json.dumps(payload), "schema_error", "template_id")


def test_null_template_id_ok() -> None:
    payload = valid_payload()
    payload["template_id"] = None
    assert parse_submission(json.dumps(payload)).template_id is None


def test_empty_text_and_code() -> None:
    payload = valid_payload()
    payload["text"] = " "
    payload["code"] = "\n"
    expect_error(json.dumps(payload), "schema_error", "$")


def test_only_code_is_enough() -> None:
    payload = valid_payload()
    payload["text"] = ""
    assert parse_submission(json.dumps(payload)).code == "print(1)\n"


def test_repeated_key() -> None:
    raw = json.dumps(valid_payload())[:-1] + ', "student_id": "other"}'
    expect_error(raw, "invalid_json", "student_id")


def test_nan_rejected() -> None:
    expect_error('{"schema_version": NaN}', "invalid_json", "$")


def test_version_as_bool() -> None:
    payload = valid_payload()
    payload["schema_version"] = True
    expect_error(json.dumps(payload), "schema_error", "schema_version")


def test_version_as_string() -> None:
    payload = valid_payload()
    payload["schema_version"] = "1"
    expect_error(json.dumps(payload), "schema_error", "schema_version")


def test_missing_nested_field() -> None:
    payload = valid_payload()
    del payload["ai_declaration"]["verified_by_student"]
    expect_error(json.dumps(payload), "schema_error", "ai_declaration.verified_by_student")
