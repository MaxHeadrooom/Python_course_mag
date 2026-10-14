import json

from pydantic import ValidationError

from .errors import SubmissionError
from .models import Submission
from .schemas import SubmissionIn

SUPPORTED_SCHEMA_VERSION = 1


def parse_submission(raw: str) -> Submission:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SubmissionError("invalid_json", field="$", message=str(e)) from e

    if not isinstance(data, dict):
        raise SubmissionError("invalid_json", field="$", message="expected JSON object")

    if data.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise SubmissionError(
            "unsupported_version",
            field="schema_version",
            message=f"supported version is {SUPPORTED_SCHEMA_VERSION}",
        )

    try:
        submission = SubmissionIn.model_validate(data)
    except ValidationError as e:
        err = e.errors()[0]
        field = ".".join(str(p) for p in err["loc"])
        message = err["msg"]
        raise SubmissionError("schema_error", field, message) from e

    return submission.to_domain()
