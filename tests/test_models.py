from dataclasses import FrozenInstanceError

import pytest

from school_lab import hashing, models


def test_evidence_is_frozen() -> None:
    evidence = models.Evidence("id1", "text", 1, 12)
    with pytest.raises(FrozenInstanceError):
        evidence.submission_id = "sub-001"  # type: ignore[misc]

def test_coincidence_of_keys() -> None:
    data1 = {"a" : 1, "b" : 2}
    hash1 = hashing.stable_hash(data1)

    data2 = {"b": 2, "a": 1}
    hash2 = hashing.stable_hash(data2)

    assert hash1 == hash2

def test_value_change_changes_hash() -> None:
    data = {"a" : 1, "b" : 2}
    hash1 = hashing.stable_hash(data)

    data = {"a": 4, "b": 2}
    hash2 = hashing.stable_hash(data)

    assert hash1 != hash2