# school-lab

Основа системы онлайн-школы: приём сдач лабораторных, валидация и (в этапе Б) расширяемые анализаторы.

**Траектория:** Backend · **Уровень:** основной · **Этап:** А (неделя 1)

## Установка

Требуется Python 3.12+.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
python -m pip install -e ".[dev]"
```

## Проверки

```bash
python -m pytest        # тесты
mypy src                # статическая проверка типов (strict)
ruff check .            # линтер
```

## Пример использования

```python
from pathlib import Path
from school_lab.importer import import_file
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService

service = SubmissionService(InMemorySubmissionRepository())
summary = import_file(Path("data/submissions.jsonl"), service)
print(summary.to_dict())   # {"accepted": [...], "duplicate": [...], "errors": [...]}
```

## Устройство

```text
строка JSON
   ↓  parser.py      json.loads (строгий: без повторов ключей и NaN)
   ↓  schemas.py     Pydantic DTO (strict, extra="forbid") → to_domain()
Submission (models.py, frozen dataclass)
   ↓  service.py     accept(): accepted / duplicate / conflict
Repository (repository.py, Protocol + in-memory)
```

| Модуль | Ответственность |
|---|---|
| `models.py` | Доменные модели `Submission` и `AIDeclaration`: frozen dataclass, без логики валидации |
| `errors.py` | `SubmissionError` с полями `code` / `field` / `message` и `to_dict()` для отчётов |
| `schemas.py` | Входные Pydantic-модели (DTO): типы, обязательные поля, правила полей; `to_domain()` переводит DTO в доменный объект |
| `parser.py` | Строка → `Submission`: строгий разбор JSON, проверка версии, перевод ошибок Pydantic в `SubmissionError` |
| `hashing.py` | Канонический JSON и SHA-256 сдачи: отпечаток содержимого для поиска дубликатов и конфликтов |
| `repository.py` | Протокол хранилища (`get` / `add`) и его in-memory реализация; никогда не перезаписывает запись |
| `service.py` | `SubmissionService.accept()` решает accepted / duplicate / conflict; `accept_payload()` — адаптер «сырой JSON → парсер → сервис» вместо будущего HTTP |
| `importer.py` | Построчный импорт с частичным успехом: отчёт `accepted` / `duplicate` / `errors` с номерами строк |

## Ошибки

Все ошибки — `SubmissionError` с полями `code`, `field`, `message`.

| code | Когда | Пример |
|---|---|---|
| `invalid_json` | Строка не является корректным JSON-объектом: синтаксическая ошибка, пустая строка, массив вместо объекта, повтор ключа, `NaN` / `Infinity` | `{broken`, `{"a": 1, "a": 2}` |
| `unsupported_version` | `schema_version` — целое число, но не `1` | `"schema_version": 2` |
| `schema_error` | JSON корректен, но нарушает схему: нет поля, лишнее поле, неверный тип, пустой id, время без часового пояса, `used=true` без `tool`/`purpose`, пустые и `text`, и `code` | `"student_id": "  "`, `"schema_version": "1"` |
| `conflict` | `submission_id` уже принят с другим содержимым (другой хеш) | тот же `sub-001`, изменённый `code` |

`field` указывает путь к полю (`ai_declaration.used`); для ошибок всего документа — `"$"`.

## Принятые решения

1. **Где валидация и почему аннотаций недостаточно.** Внешние данные проверяются на границе: `parser.py` (формат JSON и версия) и `schemas.py` (Pydantic в strict-режиме). Аннотации типов Python во время выполнения ничего не проверяют — `x: str = 42` выполнится без ошибки; их проверяет только mypy и только в нашем коде, а не во входящем JSON.
2. **`submitted_at` хранится строкой.** Хеш считается от исходного представления. Если превратить строку в `datetime` и обратно, формат может измениться (например, `Z` → `+00:00`), и хеш той же сдачи станет другим. Строка проверяется через `datetime.fromisoformat`, но сохраняется без изменений.
3. **Конфликт — исключение, дубликат — результат.** Дубликат — нормальная ситуация (повторная отправка той же работы), импорт просто отмечает её. Конфликт — отказ: под занятым id пришло другое содержимое, принять его нельзя, а старая версия не должна перезаписываться. Поэтому у `Acceptance.status` только два значения, а конфликт идёт через `raise`.
4. **Проверка версии до Pydantic и через `type(...) is int`.** Версию проверяем первой, чтобы сдача другой версии получила понятный `unsupported_version`, а не набор ошибок схемы. `type(...) is int` нужен, потому что `bool` — подкласс `int`: `isinstance(True, int)` истинно. Всё, что не является настоящим `int` (`"1"`, `true`, отсутствие поля), уходит в Pydantic и даёт `schema_error`.
5. **`field = "$"`.** У ошибок, относящихся ко всему документу (битый JSON, массив вместо объекта, пустые одновременно `text` и `code`), нет конкретного поля; `"$"` — условное обозначение корня документа, как в JSONPath.

## Известные ограничения

- Репозиторий хранится в памяти: после завершения процесса все принятые сдачи исчезают (постоянное хранение — ЛР 3).
- Последовательность `get` → `add` в сервисе не атомарна: при параллельной работе два одинаковых id могут пройти проверку одновременно. Для синхронной ЛР 1 это допустимо.
- Импорт атомарен на уровне одной строки, а не файла: строки, принятые до ошибки, остаются в репозитории.
- Принятый код не исполняется и не проверяется на синтаксис — это данные, а не программа.
- В отчёт об ошибке попадает только первая ошибка Pydantic в строке, а не все сразу.
