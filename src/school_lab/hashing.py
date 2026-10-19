import hashlib
import json
from dataclasses import asdict

from .models import Submission


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    )

def submission_hash(submission: Submission) -> str:
    dict_sub = asdict(submission)
    return stable_hash(dict_sub)

def stable_hash(value: object) -> str:
    canonical = canonical_json(value).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()