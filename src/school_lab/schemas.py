from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .models import AIDeclaration, Submission


class AIDeclarationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    used: bool
    tool: str | None
    purpose: str | None
    verified_by_student: bool

    @field_validator("tool", "purpose")
    @classmethod
    def optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("must be null or non-empty")

        return value

    @model_validator(mode="after")
    def tool_and_purpose_when_used(self) -> "AIDeclarationIn":
        if self.used and (self.tool is None or self.purpose is None):
            raise ValueError("tool and purpose are required when used=true")

        return self

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

    # TODO 3: по памятке template_id тоже не может быть пустой строкой (но может быть None).
    #         Добавь "template_id" в список полей ниже и поправь not_blank,
    #         чтобы None проходил без ошибки (сейчас None.strip() упадёт).
    #         Не забудь поправить аннотации: value: str | None -> str | None
    @field_validator("submission_id", "student_id", "assignment_id", "template_id")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None

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

    @model_validator(mode="after")
    def text_or_code(self) -> "SubmissionIn":
        if not self.text.strip() and not self.code.strip():
            raise ValueError("text or code must be non-empty")
        return self

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
