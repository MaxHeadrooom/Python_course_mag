from typing import Literal

ErrorCode = Literal["invalid_json", "schema_error", "unsupported_version", "conflict"]

class SubmissionError(Exception):
    def __init__(self, code: ErrorCode, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code":self.code, "field":self.field, "message":self.message}