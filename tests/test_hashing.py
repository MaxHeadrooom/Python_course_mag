from dataclasses import replace
from school_lab.hashing import canonical_json, submission_hash
from school_lab.models import AIDeclaration, Submission


def make_submission() -> Submission:
    return Submission(
        schema_version=1,
        submission_id="sub-001",
        student_id="student-001",
        assignment_id="assignment-01",
        submitted_at="2026-09-01T10:01:00+03:00",
        text="Учебное решение с пояснением алгоритма.",
        code="def solve(values):\n    return sum(x * x for x in values if x >= 0)\n",
        template_id="template-01",
        ai_declaration=AIDeclaration(
            used=False, tool=None, purpose=None, verified_by_student=True
        ),
    )


def test_same_submission_same_hash() -> None:
    assert submission_hash(make_submission()) == submission_hash(make_submission())


def test_extra_newline_in_code_changes_hash() -> None:
    original = make_submission()
    changed = replace(original, code=original.code + "\n")
    assert submission_hash(original) != submission_hash(changed)


def test_other_student_changes_hash() -> None:
    original = make_submission()
    changed = replace(original, student_id="student-002")
    assert submission_hash(original) != submission_hash(changed)


def test_canonical_json_ignores_key_order() -> None:
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


def test_declaration_change_changes_hash() -> None:
    original = make_submission()
    new_decl = replace(original.ai_declaration, verified_by_student=False)
    changed = replace(original, ai_declaration=new_decl)
    assert submission_hash(original) != submission_hash(changed)