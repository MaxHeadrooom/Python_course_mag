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
    canonical = canonical_json(dict_sub).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


