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


def tree(path) -> dict:
    """{relative posix path: bytes} of every regular file below ``path``."""
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()}


def render_in_process(spec, activities, out_dir):
    """Render with the historical writer IN this process (fault-injection tests only).

    The engine itself renders in an isolated worker; this helper exists so tests can
    monkeypatch ``lafractale.layout.pdf`` and observe how the QA reacts.
    """
    from lafractale.layout.pdf import write_pdf
    interior, answer = out_dir / "interior.pdf", out_dir / "answer.pdf"
    write_pdf(interior, list(activities), spec.book_dict(), answer_key=False)
    write_pdf(answer, list(activities), spec.book_dict(), answer_key=True)
    return interior, answer
