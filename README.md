# school-lab

Основа системы онлайн-школы: приём сдач лабораторных, валидация и расширяемые анализаторы (ЛР 1).

**Траектория:** Backend · **Уровень:** основной + углубление Backend (сборка из конфигурации, проверка конфигурации до первого запроса) · **Этапы:** А и Б

Отчёт: [`docs/LR1_report.docx`](docs/LR1_report.docx) · использование ИИ: [`AI_USAGE.md`](AI_USAGE.md)

## Установка

Требуется Python 3.12+.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
python -m pip install -e ".[dev]"
```

Проверка установки без `-e` в чистом окружении: `python -m pip install ".[dev]"` в новом venv, затем `python -m pytest`.

## Проверки

```bash
python -m pytest                    # 182 теста
mypy src tests benchmarks           # статическая проверка типов (strict)
ruff check .                        # линтер
python benchmarks/run_benchmarks.py # замеры → docs/benchmark_results.json
```

## Пример использования

```python
from pathlib import Path

from school_lab.analyzers import AnalysisContext
from school_lab.app import build_application, load_assignment
from school_lab.importer import import_file

app = build_application()  # репозиторий, реестр анализаторов, сервисы
summary = import_file(Path("data/submissions.jsonl"), app.submission_service)
print(summary.to_dict())   # {"accepted": [...], "duplicate": [...], "errors": [...]}

context = AnalysisContext(load_assignment(Path("data/assignments.json")))
report = app.analysis_service.run("sub-001", "length", context)
print(report.findings[0].explanation)
```

Подключение нового анализатора — только регистрация, сервис не меняется:

```python
app.registry.register("declaration", DeclarationAnalyzer)
app.analysis_service.run("sub-001", "declaration", context)
```

## Устройство

```text
строка JSONL
   ↓  sources.py     JSONLSource / InMemorySource → SourceRecord(line_no, raw)
   ↓  parser.py      json.loads (строгий: без повторов ключей и NaN), проверка версии
   ↓  schemas.py     Pydantic DTO (strict, extra="forbid") → to_domain()
Submission (models.py, frozen dataclass)
   ↓  service.py     accept(): accepted / duplicate / conflict
Repository (repository.py, Protocol + in-memory)

AnalysisService.run(submission_id, analyzer_name, context)
   ↓  registry.py    AnalyzerRegistry.create(name)
   ↓  analyzers.py   analyzer.analyze(...) → validate_report(...)
AnalysisReport (findings + evidence по исходным строкам)
```

| Модуль | Ответственность |
|---|---|
| `models.py` | Доменные модели `Submission`, `AIDeclaration`, `Assignment`, `Evidence`, `Finding`, `AnalysisReport`: frozen dataclass, коллекции — кортежи |
| `errors.py` | `SubmissionError` с полями `code` / `field` / `message` и `to_dict()`; `AnalysisFailure` для ошибок анализа |
| `schemas.py` | Входные Pydantic-модели (DTO): типы, обязательные поля, правила полей; `to_domain()` переводит DTO в доменный объект |
| `parser.py` | Строка → `Submission`: строгий разбор JSON, проверка версии, перевод ошибок Pydantic в `SubmissionError` |
| `hashing.py` | Канонический JSON, `stable_hash`, SHA-256 сдачи для поиска дубликатов и конфликтов |
| `repository.py` | Протокол хранилища (`get` / `add`) и его in-memory реализация; никогда не перезаписывает запись |
| `service.py` | `SubmissionService.accept()` решает accepted / duplicate / conflict; `accept_payload()` — адаптер «сырой JSON → парсер → сервис» вместо будущего HTTP |
| `sources.py` | Протокол `SubmissionSource`; `InMemorySource` (копия списка) и `JSONLSource` (построчное чтение, владеет файлом) |
| `importer.py` | `import_source`: импорт из любого источника с частичным успехом и номерами строк |
| `analyzers.py` | `AnalysisContext`, протокол `Analyzer`, `make_report`, `validate_report`, `LengthAnalyzer`, `TemplateAnalyzer` |
| `registry.py` | Реестр фабрик анализаторов `AnalyzerRegistry` |
| `analysis_service.py` | `AnalysisService.run`: анализатор по имени из реестра, проверка отчёта |
| `app.py` | Точка сборки `build_application`, `AppConfig`, загрузка конфигурации и задания |

## Ошибки

Ошибки данных — `SubmissionError` с полями `code`, `field`, `message`; ошибки анализа — `AnalysisFailure`.

| code | Когда | Пример |
|---|---|---|
| `invalid_json` | Строка не является корректным JSON-объектом: синтаксическая ошибка, пустая строка, массив вместо объекта, повтор ключа, `NaN` / `Infinity` | `{broken`, `{"a": 1, "a": 2}` |
| `unsupported_version` | `schema_version` — целое число, но не `1` | `"schema_version": 2` |
| `schema_error` | JSON корректен, но нарушает схему: нет поля, лишнее поле, неверный тип, пустой id, время без часового пояса, `used=true` без `tool`/`purpose`, пустые и `text`, и `code` | `"student_id": "  "`, `"schema_version": "1"` |
| `conflict` | `submission_id` уже принят с другим содержимым (другой хеш) | тот же `sub-001`, изменённый `code` |

`field` указывает путь к полю (`ai_declaration.used`); для ошибок всего документа — `"$"`.

## Принятые решения

1. **Где валидация и почему аннотаций недостаточно.** Внешние данные проверяются на границе: `parser.py` (формат JSON и версия) и `schemas.py` (Pydantic в strict-режиме). Аннотации типов Python во время выполнения ничего не проверяют — `x: str = 42` выполнится без ошибки; их проверяет только mypy и только в нашем коде, а не во входящем JSON. По той же причине отчёт стороннего анализатора проверяется `validate_report`: `-> AnalysisReport` ничего не гарантирует.
2. **`submitted_at` хранится строкой.** Хеш считается от исходного представления. Если превратить строку в `datetime` и обратно, формат может измениться (например, `Z` → `+00:00`), и хеш той же сдачи станет другим. Строка проверяется через `datetime.fromisoformat`, но сохраняется без изменений.
3. **Конфликт — исключение, дубликат — результат.** Дубликат — нормальная ситуация (повторная отправка той же работы), импорт просто отмечает её. Конфликт — отказ: под занятым id пришло другое содержимое, принять его нельзя, а старая версия не должна перезаписываться. Поэтому у `Acceptance.status` только два значения, а конфликт идёт через `raise`.
4. **Проверка версии до Pydantic и через `type(...) is int`.** Версию проверяем первой, чтобы сдача другой версии получила понятный `unsupported_version`, а не набор ошибок схемы. `type(...) is int` нужен, потому что `bool` — подкласс `int`: `isinstance(True, int)` истинно. Всё, что не является настоящим `int` (`"1"`, `true`, отсутствие поля), уходит в Pydantic и даёт `schema_error`.
5. **`field = "$"`.** У ошибок, относящихся ко всему документу (битый JSON, массив вместо объекта, пустые одновременно `text` и `code`), нет конкретного поля; `"$"` — условное обозначение корня документа, как в JSONPath.
6. **Протокол, а не наследование.** `Analyzer`, `SubmissionRepository`, `SubmissionSource` — протоколы: реализация подходит, если у неё есть нужные методы, наследоваться не нужно. Протокол проверяет только форму, поэтому поведение реализаций проверяют контрактные тесты (`test_analyzer_contract.py`, контракт источников в `test_sources.py`).
7. **Реестр вместо ветвления.** `AnalysisService` получает анализатор по имени из `AnalyzerRegistry` и не содержит `if name == ...`. Новый анализатор подключается регистрацией; реестр проверяет пустые и повторные имена и совпадение имени с `analyzer_id`.
8. **Ресурсом управляет источник.** `JSONLSource.open()` открывает файл и закрывает его в `finally`: при полном чтении, раннем выходе из `with` и исключении потребителя. Импорт только потребляет записи, ловит лишь `SubmissionError`; неожиданный дефект не превращается в «ошибку строки».
9. **Точка сборки без глобального состояния.** `build_application` выбирает конкретные классы и передаёт их в сервисы через конструктор; каждый вызов создаёт независимое приложение. Некорректная конфигурация (`AppConfig`) отклоняется при сборке, до первого запроса.
10. **Пустые строки JSONL.** Пустая строка — это запись источника, которая при разборе даёт `invalid_json`; импорт продолжается. Шаблон задания сравнивается по полным строкам без нормализации пробелов; завершающий перевод строки не создаёт лишней строки.

## Известные ограничения

- Репозиторий хранится в памяти: после завершения процесса все принятые сдачи исчезают (постоянное хранение — ЛР 3).
- Последовательность `get` → `add` в сервисе не атомарна: при параллельной работе два одинаковых id могут пройти проверку одновременно. Для синхронной ЛР 1 это допустимо.
- Импорт атомарен на уровне одной строки, а не файла: строки, принятые до ошибки, остаются в репозитории.
- Принятый код не исполняется и не проверяется на синтаксис — это данные, а не программа.
- В отчёт об ошибке попадает только первая ошибка Pydantic в строке, а не все сразу.
- `TemplateAnalyzer` ищет только точное совпадение строк; нечёткое сходство и переименования не учитываются.
- `validate_report` проверяет результат анализатора, но не защищает от вредоносного плагина: он выполняется с правами процесса.
