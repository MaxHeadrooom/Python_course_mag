from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .errors import SubmissionError
from .service import SubmissionService, accept_payload
from .sources import InMemorySource, JSONLSource, SubmissionSource


@dataclass
class ImportSummary:
    accepted: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def import_source(
    source: SubmissionSource, service: SubmissionService
) -> ImportSummary:
    """Импорт из любого источника. Источник владеет ресурсом (файлом),
    импорт только потребляет записи внутри with."""
    summary = ImportSummary()

    with source.open() as records:
        for record in records:
            try:
                res = accept_payload(service, record.raw)
            except SubmissionError as e:
                # Ловим только ошибки данных: неожиданный дефект не должен
                # тихо превращаться в «ошибку строки».
                summary.errors.append({"line_no": record.line_no, **e.to_dict()})
            else:
                if res.status == "accepted":
                    summary.accepted.append(res.submission_id)
                elif res.status == "duplicate":
                    summary.duplicate.append(res.submission_id)

    return summary


def import_lines(lines: Iterable[str], service: SubmissionService) -> ImportSummary:
    return import_source(InMemorySource(list(lines)), service)


def import_file(path: Path, service: SubmissionService) -> ImportSummary:
    return import_source(JSONLSource(path), service)
