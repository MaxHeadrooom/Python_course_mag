from .models import Submission

def canonical_json(value: object) -> str:
    # TODO: json.dumps с sort_keys, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ...

def submission_hash(submission: Submission) -> str:
    # TODO: asdict → canonical_json → encode utf-8 → sha256 → hexdigest
    ...