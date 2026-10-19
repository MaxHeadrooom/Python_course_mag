# Использование ИИ

**Инструмент:** Claude (Claude Code)
**Формат работы:** ИИ выдаёт заготовки файлов с TODO-комментариями и объясняет непонятные места; код в TODO пишу я, ИИ проверяет и указывает на ошибки. Отдельно ниже отмечено, что ИИ написал или исправил сам.

## Что написал ИИ

- **Заготовки модулей с TODO:** `schemas.py`, `parser.py`, `repository.py`, `service.py`, `importer.py` — структура, сигнатуры, комментарии-подсказки.
- **README.md целиком:** установка, проверки, схема модулей, таблица ошибок, раздел «Принятые решения» и известные ограничения (по моей просьбе; объяснения я прочитал и проверил на своём коде).
- **Исправления по ruff:** `dict()` → `{}` в `parser.py`, удалены неиспользуемые переменные в тестах, в `test_reimport_gives_only_duplicates` добавлена проверка первого импорта.
- **Проверка установки в чистое окружение** (`pip install ".[dev]"` без `-e` в новом venv), запуск mypy и ruff; `build/`, `dist/` добавлены в `.gitignore`.
- **Тесты:**
  - `tests/test_hashing.py` — проверки в четырёх тестах по TODO (лишний `\n`, другой `student_id`, порядок ключей, изменение декларации);
  - `tests/test_parser.py` — все тесты парсера: случаи из приёмки этапа А и из памятки (пустые поля, часовой пояс, неизвестное поле, неверные типы, `used=true` без `tool`/`purpose`, пустые `text`+`code`, повтор ключа, `NaN`, версия-строка и версия-`bool`);
  - `tests/conftest.py` (fixtures);
  - `tests/test_service.py`, `tests/test_importer.py` — тесты-образцы (`test_new_submission_accepted`, `test_mixed_lines` и тесты репозитория) и TODO-заготовки остальных тестов.
- **`data/submissions.jsonl`, `data/assignments.json`** — выгружены из учебной памятки (ячейка 4), не реальные работы студентов.
- **`.gitignore`** — убраны пробелы в начале строк, из-за которых шаблоны не работали; `__pycache__` и `*.egg-info` убраны из репозитория.

## Что написал я (с объяснениями и проверкой ИИ)

- `schemas.py`: `model_config` (`strict`, `extra="forbid"`), `to_domain()`, валидаторы `not_blank`, `has_timezone`, `optional_not_blank`, `model_validator` для `used`/`tool`/`purpose` и для пустых `text`+`code`.
- `parser.py`: разбор JSON и разделение ошибок `invalid_json` / `unsupported_version` / `schema_error`, `reject_repeated_keys`, `reject_constant`, проверка версии через `type(...) is int`, пустой `loc` → `"$"`.
- `repository.py`: `get` и `add` in-memory репозитория (с отказом `conflict` при повторном id).
- `service.py`: метод `accept` (accepted / duplicate / conflict по хешу) и адаптер `accept_payload`.
- `importer.py`: `import_lines` (цикл с `enumerate`, `try/except SubmissionError`, раскладка по статусам) и `import_file`.
- Тесты по TODO-заготовкам: дубликат, конфликт без перезаписи, новая версия с новым id, неверная схема ничего не сохраняет; пустая строка в импорте, импорт учебного файла, повторный импорт, импорт из временного файла.

## Что ИИ исправил в моём коде

- `parser.py`: код ошибки для неверной версии (`invalid_json` → `unsupported_version`), опечатка `massage`, текст ошибки JSON (`str(e)`).
- `schemas.py`: аргументы `to_domain()` переданы по именам вместо позиционных; переименованы переменные.

## Ошибки, найденные при разборе с ИИ

- `raise ValidationError(...)` внутри валидатора → нужен `ValueError` (его Pydantic сам оборачивает в `ValidationError`).
- Перевёрнутое условие в проверке `text`/`code` (не хватало `not`).
- `data.get(key, 0)` для поиска повтора ключа пропускает дубликаты с «ложным» значением (`false`, `null`) → нужен `key in data`.
- `err["loc" or "$"]` → `or` применяется к строке `"loc"`, а не к результату; правильно `".".join(...) or "$"`.
- Сравнение с несуществующим атрибутом `previous.content_hash` (`content_hash` есть у `Acceptance`, а не у `Submission`) → нужно `submission_hash(previous)`.
- Конфликт проверялся как `result.status == "conflict"` → конфликт — исключение, ловится через `pytest.raises`.
- `import_file`: `f.readlines()`, а затем передача уже прочитанного `f` → импорт ничего не принимал; найдено запуском на учебном файле.

## Проверка

Код, сгенерированный ИИ, я прочитал и могу объяснить, что проверяет каждый тест и почему валидация устроена именно так. Все тесты запускаются командой `pytest`.
