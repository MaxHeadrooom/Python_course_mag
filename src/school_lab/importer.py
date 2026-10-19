from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .errors import SubmissionError
from .service import SubmissionService, accept_payload


@dataclass
class ImportSummary:
    accepted: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def import_lines(lines: Iterable[str], service: SubmissionService) -> ImportSummary:
    summary = ImportSummary()

    for line_no, line in enumerate(lines, start=1):
        try:
            res = accept_payload(service, line)
        except SubmissionError as e:
            summary.errors.append({"line_no": line_no, **e.to_dict()})
        else:
            if res.status == "accepted":
                summary.accepted.append(res.submission_id)
            if res.status == "duplicate":
                summary.duplicate.append(res.submission_id)

    return summary


def import_file(path: Path, service: SubmissionService) -> ImportSummary:
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        return import_lines(lines, service)
