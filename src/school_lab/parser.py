import json

from pydantic import ValidationError

from .errors import SubmissionError
from .models import Submission
from .schemas import SubmissionIn

SUPPORTED_SCHEMA_VERSION = 1


def reject_repeated_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {}

    for key, word in pairs:
        if key not in data:
            data[key] = word
        else:
            raise SubmissionError("invalid_json", key, "duplicate key")

    return data


def reject_constant(value: str) -> object:
    raise SubmissionError("invalid_json", "$", f"non-standard value: {value}")


def parse_submission(raw: str) -> Submission:
    try:
        data = json.loads(raw, object_pairs_hook=reject_repeated_keys, parse_constant=reject_constant)
    except json.JSONDecodeError as e:
        raise SubmissionError("invalid_json", field="$", message=str(e)) from e

    if not isinstance(data, dict):
        raise SubmissionError("invalid_json", field="$", message="expected JSON object")

    if type(data.get("schema_version", None)) is int and data["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        raise SubmissionError(
            "unsupported_version",
            field="schema_version",
            message=f"supported version is {SUPPORTED_SCHEMA_VERSION}",
        )

    try:
        submission = SubmissionIn.model_validate(data)
    except ValidationError as e:
        err = e.errors()[0]
        field = ".".join(str(p) for p in err["loc"] or "$")
        message = err["msg"]
        raise SubmissionError("schema_error", field, message) from e

    return submission.to_domain()
