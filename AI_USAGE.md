# Использование ИИ

**Инструмент:** Claude (Claude Code)

## Что сделано с помощью ИИ

- **Тесты в `tests/test_hashing.py`**: по TODO-комментариям дописаны проверки в четырёх тестах:
  - `test_extra_newline_in_code_changes_hash`: лишний `\n` в `code` меняет хеш;
  - `test_other_student_changes_hash`: другой `student_id` даёт другой хеш;
  - `test_canonical_json_ignores_key_order`: порядок ключей не влияет на `canonical_json`;
  - `test_declaration_change_changes_hash`: изменение `verified_by_student` в AI-декларации меняет хеш.
- **`.gitignore`**: убраны пробелы в начале строк, из-за которых шаблоны не работали; `__pycache__` и `*.egg-info` убраны из репозитория.
- **Настройка PyCharm**: помощь с выбором интерпретатора `.venv`, чтобы IDE видела пакет `school_lab`.

## Проверка

Тесты я прочитал и понимаю, что проверяет каждый из них. Запуск `pytest`: все 5 тестов проходят.
