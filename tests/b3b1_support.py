"""Shared helpers for the B3-B.1 engine-slice tests (synthetic data only)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "b3b1" / "synthetic_slice_v1.json"


def spec_dict() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def dumps(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def mutated(mutator) -> bytes:
    data = copy.deepcopy(spec_dict())
    mutator(data)
    return dumps(data)
