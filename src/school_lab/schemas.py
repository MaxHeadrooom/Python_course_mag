from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from .models import AIDeclaration, Submission


class AIDeclarationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    used: bool
    tool: str | None
    purpose: str | None
    verified_by_student: bool

    def to_domain(self) -> AIDeclaration:
        return AIDeclaration(
            used=self.used,
            tool=self.tool,
            purpose=self.purpose,
            verified_by_student=self.verified_by_student,
        )


class SubmissionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: int
    submission_id: str
    student_id: str
    assignment_id: str
    submitted_at: str
    text: str
    code: str
    template_id: str | None
    ai_declaration: AIDeclarationIn

    @field_validator("submission_id", "student_id", "assignment_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("submitted_at")
    @classmethod
    def has_timezone(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            raise ValueError("timezone is required")

        return value

    def to_domain(self) -> Submission:
        return Submission(
            schema_version=self.schema_version,
            submission_id=self.submission_id,
            student_id=self.student_id,
            assignment_id=self.assignment_id,
            submitted_at=self.submitted_at,
            text=self.text,
            code=self.code,
            template_id=self.template_id,
            ai_declaration=self.ai_declaration.to_domain(),
        )
