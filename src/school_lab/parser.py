import json

from pydantic import ValidationError

from .errors import SubmissionError
from .models import Submission
from .schemas import SubmissionIn

SUPPORTED_SCHEMA_VERSION = 1


def reject_repeated_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    # json.loads вызывает эту функцию для КАЖДОГО объекта {...} и передаёт ей
    # список пар (ключ, значение) в том порядке, как они записаны в тексте.
    # Обычный json.loads при повторе ключа молча оставляет последнее значение:
    #   json.loads('{"a": 1, "a": 2}')  ->  {'a': 2}
    # TODO 5: собрать dict из pairs; если ключ уже встречался ->
    #         raise SubmissionError("invalid_json", key, "duplicate key")
    return dict(pairs)


def reject_constant(value: str) -> object:
    # json.loads вызывает эту функцию, когда встречает NaN, Infinity или -Infinity.
    # Это не стандартный JSON, а расширение Python. Мы такое не принимаем.
    # TODO 6: raise SubmissionError("invalid_json", "$", f"non-standard value: {value}")
    return float(value)


def parse_submission(raw: str) -> Submission:
    try:
        # TODO 7: передать в json.loads два доп. аргумента:
        #         object_pairs_hook=reject_repeated_keys, parse_constant=reject_constant
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SubmissionError("invalid_json", field="$", message=str(e)) from e

    if not isinstance(data, dict):
        raise SubmissionError("invalid_json", field="$", message="expected JSON object")

    # TODO 8: сейчас "1" (строка) даёт unsupported_version, хотя это ошибка ТИПА.
    #         Проверяй версию только если это настоящий int:
    #         version = data.get("schema_version")
    #         if type(version) is int and version != SUPPORTED_SCHEMA_VERSION: ...
    #         (type(...) is int, а не isinstance: True — тоже int в Python!)
    #         Остальное (строку, True, отсутствие поля) поймает Pydantic как schema_error.
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
        # TODO 9: у ошибок из model_validator (TODO 4) loc пустой -> field получится "".
        #         Если loc пустой, подставь "$" (весь документ). Подсказка: ... or "$"
        field = ".".join(str(p) for p in err["loc"])
        message = err["msg"]
        raise SubmissionError("schema_error", field, message) from e

    return submission.to_domain()
