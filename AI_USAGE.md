# Использование ИИ

**Инструмент:** Claude (Claude Code)

**Формат работы:**
- **Этап А:** ИИ выдавал заготовки файлов с TODO-комментариями и подробными подсказками; код в TODO писал я, ИИ проверял и указывал на ошибки.
- **Этап Б:** заготовок файлов нет. ИИ описывает задачу словами (что сделать, где читать в памятке, какие сценарии проверить), классы, функции и тесты пишу я; ИИ проверяет и даёт подсказки. Отдельные куски, которые ИИ написал по моей просьбе, отмечены ниже.

---

## Этап А — приём и валидация

### Что написал ИИ

- **Заготовки модулей с TODO:** `schemas.py`, `parser.py`, `repository.py`, `service.py`, `importer.py` — структура, сигнатуры, комментарии-подсказки.
- **README.md целиком:** установка, проверки, схема модулей, таблица ошибок, раздел «Принятые решения» и известные ограничения (по моей просьбе; объяснения я прочитал и проверил на своём коде).
- **Исправления по ruff:** `dict()` → `{}` в `parser.py`, удалены неиспользуемые переменные в тестах, в `test_reimport_gives_only_duplicates` добавлена проверка первого импорта.
- **Проверка установки в чистое окружение** (`pip install ".[dev]"` без `-e` в новом venv), запуск mypy и ruff; `build/`, `dist/` добавлены в `.gitignore`.
- **Тесты:**
  - `tests/test_hashing.py` — проверки в четырёх тестах по TODO (лишний `\n`, другой `student_id`, порядок ключей, изменение декларации);
  - `tests/test_parser.py` — все тесты парсера: случаи из приёмки этапа А и из памятки (пустые поля, часовой пояс, неизвестное поле, неверные типы, `used=true` без `tool`/`purpose`, пустые `text`+`code`, повтор ключа, `NaN`, версия-строка и версия-`bool`);
  - `tests/conftest.py` (fixtures);
  - `tests/test_service.py`, `tests/test_importer.py` — тесты-образцы (`test_new_submission_accepted`, `test_mixed_lines` и тесты репозитория) и TODO-заготовки остальных тестов.
- **`data/submissions.jsonl`, `data/assignments.json`** — выгружены из учебной памятки, не реальные работы студентов.
- **`.gitignore`** — убраны пробелы в начале строк, из-за которых шаблоны не работали; `__pycache__` и `*.egg-info` убраны из репозитория.

### Что написал я (с объяснениями и проверкой ИИ)

- `schemas.py`: `model_config` (`strict`, `extra="forbid"`), `to_domain()`, валидаторы `not_blank`, `has_timezone`, `optional_not_blank`, `model_validator` для `used`/`tool`/`purpose` и для пустых `text`+`code`.
- `parser.py`: разбор JSON и разделение ошибок `invalid_json` / `unsupported_version` / `schema_error`, `reject_repeated_keys`, `reject_constant`, проверка версии через `type(...) is int`, пустой `loc` → `"$"`.
- `repository.py`: `get` и `add` in-memory репозитория (с отказом `conflict` при повторном id).
- `service.py`: метод `accept` (accepted / duplicate / conflict по хешу) и адаптер `accept_payload`.
- `importer.py`: `import_lines` (цикл с `enumerate`, `try/except SubmissionError`, раскладка по статусам) и `import_file`.
- Тесты по TODO-заготовкам: дубликат, конфликт без перезаписи, новая версия с новым id, неверная схема ничего не сохраняет; пустая строка в импорте, импорт учебного файла, повторный импорт, импорт из временного файла.

### Что ИИ исправил в моём коде

- `parser.py`: код ошибки для неверной версии (`invalid_json` → `unsupported_version`), опечатка `massage`, текст ошибки JSON (`str(e)`).
- `schemas.py`: аргументы `to_domain()` переданы по именам вместо позиционных; переименованы переменные.

### Ошибки, найденные при разборе с ИИ

- `raise ValidationError(...)` внутри валидатора → нужен `ValueError` (его Pydantic сам оборачивает в `ValidationError`).
- Перевёрнутое условие в проверке `text`/`code` (не хватало `not`).
- `data.get(key, 0)` для поиска повтора ключа пропускает дубликаты с «ложным» значением (`false`, `null`) → нужен `key in data`.
- `err["loc" or "$"]` → `or` применяется к строке `"loc"`, а не к результату; правильно `".".join(...) or "$"`.
- Сравнение с несуществующим атрибутом `previous.content_hash` (`content_hash` есть у `Acceptance`, а не у `Submission`) → нужно `submission_hash(previous)`.
- Конфликт проверялся как `result.status == "conflict"` → конфликт — исключение, ловится через `pytest.raises`.
- `import_file`: `f.readlines()`, а затем передача уже прочитанного `f` → импорт ничего не принимал; найдено запуском на учебном файле.

---

## Этап Б — анализаторы (в процессе)

### Что написал ИИ

- Описание шагов словами: состав моделей отчёта, протокола и функций, ссылки на разделы памятки, списки сценариев для тестов.
- `tests/test_analyzers.py`: каркас тестов `make_report` (вспомогательные `make_context`, `make_finding`, заготовки с TODO) и, по моей просьбе, три теста целиком: `test_report_has_submission_hash`, `test_report_created_at_has_timezone`, `test_report_config_hash`.
- **`TemplateAnalyzer` целиком по моей просьбе** (тело `analyze` в моей заготовке класса): проверка задания, evidence по найденным блокам, два варианта объяснения; исключение `AnalysisFailure` в `errors.py`; тесты `test_template_no_match`, `test_template_match_found`, `test_template_match_not_on_first_line`, `test_template_other_assignment_fails`, `test_template_matches_protocol`.
- `tests/test_analyzers.py`, тесты `LengthAnalyzer` по моей просьбе: `make_tricky` (сдача с пустыми строками в середине), `test_length_evidence_points_to_nonempty_lines`, `test_length_evidence_line_numbers_are_original`, `test_length_does_not_change_submission`, `test_length_matches_protocol`; в `test_length_single_rubric_finding` — исправленный вариант после двух моих попыток.

### Что написал я (по описанию и подсказкам ИИ)

- `models.py`: модели `Assignment`, `Evidence`, `Finding`, `AnalysisReport` (frozen dataclass, `Literal`, кортежи вместо списков).
- `hashing.py`: функция `stable_hash`; `submission_hash` переписан через неё (проверено, что хеш сдачи не изменился).
- `analyzers.py`: `AnalysisContext` с `config_payload()`, протокол `Analyzer` (`@property` для id и версии), `nonempty_line_numbers`, `make_report`, `LengthAnalyzer`, `template_ranges` (поиск блоков шаблона по срезам строк).
- Тесты `template_ranges`: два совпадения, нет совпадения, шаблон из пробелов, совпадение не с первой строки, отличие в отступе.
- Тесты `LengthAnalyzer`: `test_length_report_metadata`, `test_length_evidence_count`.
- `tests/test_models.py`: неизменяемость `Evidence` (`FrozenInstanceError`), независимость `stable_hash` от порядка ключей, изменение хеша при изменении значения.
- `tests/test_analyzers.py`: тесты `nonempty_line_numbers` (включая пустой текст и строки из пробелов), изменение `config_hash` при изменении требований и шаблона задания, уникальность `report_id`.

### Ошибки, найденные при разборе с ИИ

- Поля моделей не соответствовали контракту: `int` вместо строкового id, `list` вместо `tuple` во frozen-модели, `int` для оценки 0–1, необязательное `explanation`, имя поля `type` (затеняет встроенную функцию).
- Импорт `DataclassInstance` из `dataclasses` — существует только для mypy, во время выполнения `ImportError`.
- `submission_hash` передавал в `stable_hash` уже готовую JSON-строку (двойная сериализация), затем канонизация оказалась не в той функции → `stable_hash` должен сам делать канонический JSON.
- Проверка неизменяемости через `try/except AssertionError` — не та ошибка и тест проходил бы без исключения → `pytest.raises(FrozenInstanceError)`.
- `text.splitlines()` вызывался на каждой итерации цикла; пустой кортеж без аннотации типа (ошибка mypy).
- `@dataclass` над `Protocol` и `pass` вместо `...` в теле членов протокола.
- `make_report`: в `submission_id` записывался id анализатора; не переданы 4 поля `AnalysisReport`; имя аргумента `finding` вместо `findings`.
- Переменная `hash` затеняла встроенную функцию.
- `LengthAnalyzer`: присваивание `Evidence = ...` затирало имя класса; объекты `Evidence` создавались, но не сохранялись; `kind="similarity"` и `score=len(...)` вместо `rubric_feedback` и `None`.
- Тесты: `kind`/`score` искались у отчёта, а не у находки (`report.findings[0]`); в `analyze` передавалась находка вместо контекста; сравнивался список `Evidence` с кортежем чисел вместо длин.
- Лишние автоимпорты PyCharm (`pygments`, `mypy`, `mypyc`) — удалены.

---

## Проверка

Код, сгенерированный ИИ, я прочитал и могу объяснить, что проверяет каждый тест и почему валидация устроена именно так. Все проверки запускаются командами `pytest`, `mypy src tests`, `ruff check .`.
