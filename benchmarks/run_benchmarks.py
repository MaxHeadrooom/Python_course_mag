"""Измерения для отчёта ЛР 1.

Запуск (из папки school-lab, в окружении проекта):
    python benchmarks/run_benchmarks.py

Что измеряется:
  1. Источники: время чтения и пиковая память JSONLSource и InMemorySource.
  2. Импорт целиком (разбор + валидация + хеш + репозиторий).
  3. Анализ: LengthAnalyzer и TemplateAnalyzer, цена проверки отчёта на границе.
  4. Углубление Backend: время сборки приложения с проверкой конфигурации.

Результат печатается и сохраняется в docs/benchmark_results.json.
Корпус генерируется из учебных сдач data/submissions.jsonl с новыми submission_id.
"""

import json
import platform
import statistics
import sys
import tempfile
import tracemalloc
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from pathlib import Path
from time import perf_counter

from school_lab.analyzers import (
    AnalysisContext,
    Analyzer,
    LengthAnalyzer,
    TemplateAnalyzer,
    validate_report,
)
from school_lab.app import AppConfig, build_application, load_assignment
from school_lab.importer import import_source
from school_lab.models import Submission
from school_lab.parser import parse_submission
from school_lab.repository import InMemorySubmissionRepository
from school_lab.service import SubmissionService
from school_lab.sources import InMemorySource, JSONLSource, SubmissionSource

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "benchmark_results.json"

SIZES = (1_000, 10_000, 50_000)
REPEATS = 5


def make_corpus(path: Path, size: int) -> None:
    """JSONL из size корректных сдач: учебные сдачи по кругу с уникальным id."""
    base = (DATA / "submissions.jsonl").read_text(encoding="utf-8").splitlines()
    with path.open("w", encoding="utf-8") as f:
        for i in range(size):
            record = json.loads(base[i % len(base)])
            record["submission_id"] = f"sub-{i:06d}"
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def median_time(action: Callable[[], object], repeats: int = REPEATS) -> float:
    times = []
    for _ in range(repeats):
        start = perf_counter()
        action()
        times.append(perf_counter() - start)
    return statistics.median(times)


def peak_memory(action: Callable[[], object]) -> int:
    tracemalloc.start()
    try:
        action()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def consume(source: SubmissionSource) -> int:
    with source.open() as records:
        return sum(1 for _ in records)


def in_memory_from_file(path: Path) -> InMemorySource:
    # Так выглядит «загрузить всё в память»: все строки файла сразу в списке
    with path.open(encoding="utf-8") as f:
        return InMemorySource([line.rstrip("\n") for line in f])


def read_jsonl(path: Path) -> int:
    return consume(JSONLSource(path))


def read_in_memory(path: Path) -> int:
    return consume(in_memory_from_file(path))


def bench_sources(tmp: Path) -> list[dict[str, float]]:
    rows = []
    for size in SIZES:
        path = tmp / f"corpus_{size}.jsonl"
        make_corpus(path, size)
        rows.append(
            {
                "size": size,
                "file_kb": path.stat().st_size / 1024,
                "jsonl_ms": median_time(partial(read_jsonl, path)) * 1000,
                "memory_ms": median_time(partial(read_in_memory, path)) * 1000,
                "jsonl_peak_kb": peak_memory(partial(read_jsonl, path)) / 1024,
                "memory_peak_kb": peak_memory(partial(read_in_memory, path)) / 1024,
            }
        )
    return rows


def bench_import(tmp: Path) -> list[dict[str, float]]:
    rows = []
    for size in SIZES[:2]:
        path = tmp / f"corpus_{size}.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()

        def full_import(p: Path = path) -> None:
            import_source(
                JSONLSource(p), SubmissionService(InMemorySubmissionRepository())
            )

        def parse_only(ls: list[str] = lines) -> None:
            for line in ls:
                parse_submission(line)

        total = median_time(full_import, repeats=3)
        parse = median_time(parse_only, repeats=3)
        rows.append(
            {
                "size": size,
                "import_ms": total * 1000,
                "parse_ms": parse * 1000,
                "per_record_us": total / size * 1_000_000,
                "records_per_s": size / total,
            }
        )
    return rows


def bench_analysis() -> list[dict[str, float | str]]:
    context = AnalysisContext(load_assignment(DATA / "assignments.json"))
    with (DATA / "submissions.jsonl").open(encoding="utf-8") as f:
        submissions = [parse_submission(line) for line in f]
    # Крупная сдача: 2000 строк кода, чтобы цена анализа была заметна
    big = replace(
        submissions[0], code="from typing import Iterable\n" + "x = 1\n" * 2000
    )

    def run_all(analyzer: Analyzer, items: list[Submission], validate: bool) -> None:
        for submission in items:
            report = analyzer.analyze(submission, context)
            if validate:
                validate_report(report, submission, context)

    rows: list[dict[str, float | str]] = []
    for analyzer in (LengthAnalyzer(), TemplateAnalyzer()):
        for label, items in (("12 учебных", submissions), ("2000 строк", [big])):
            plain = median_time(partial(run_all, analyzer, items, False), repeats=50)
            checked = median_time(partial(run_all, analyzer, items, True), repeats=50)
            rows.append(
                {
                    "analyzer": analyzer.analyzer_id,
                    "input": label,
                    "per_submission_us": plain / len(items) * 1_000_000,
                    "with_validation_us": checked / len(items) * 1_000_000,
                    "validation_overhead_pct": (checked - plain) / plain * 100,
                }
            )
    return rows


def bench_build() -> dict[str, float]:
    return {
        "build_application_us": median_time(
            lambda: build_application(AppConfig()), repeats=200
        )
        * 1_000_000
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        sources = bench_sources(tmp)
        imports = bench_import(tmp)
    results = {
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "sources": sources,
        "import": imports,
        "analysis": bench_analysis(),
        "build": bench_build(),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
