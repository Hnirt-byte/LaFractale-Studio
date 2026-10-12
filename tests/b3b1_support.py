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


def qa_failures(spec, activities, tmp_path) -> dict:
    """{check id: detail} of every FAIL when the in-process render is analysed by the QA."""
    from lafractale.engine import qa
    interior, answer = render_in_process(spec, activities, tmp_path)
    return {c["id"]: c["detail"] for c in qa.content_checks(spec, activities, interior, answer)
            if c["status"] == "FAIL"}


def patch_match(monkeypatch, transform):
    """Transform the activity handed to the historical ``_match`` renderer (in memory only)."""
    import lafractale.layout.pdf as pdfmod
    original = pdfmod._match

    def wrapper(c, act, board, solution):
        original(c, transform(act), board, solution)

    monkeypatch.setattr(pdfmod, "_match", wrapper)


def patch_symbol(monkeypatch, per_call):
    """per_call(index_in_page, name) -> list of (name, dx) to draw (default: [(name, 0)])."""
    import lafractale.layout.pdf as pdfmod
    original = pdfmod._symbol
    counter = {"n": 0}

    def wrapper(c, name, x, y, r):
        index = counter["n"] % 8  # four left + four right symbols per match page
        counter["n"] += 1
        for drawn, dx in per_call(index, name):
            original(c, drawn, x + dx, y, r)

    monkeypatch.setattr(pdfmod, "_symbol", wrapper)


def after_each_symbol(monkeypatch, decorate, *, only_answer=False):
    """Run ``decorate(c, x, y)`` right AFTER every symbol is drawn (z-order: on top of it).

    ``only_answer`` restricts the fault to the corrigé render.
    """
    import lafractale.layout.pdf as pdfmod
    original_symbol, original_match = pdfmod._symbol, pdfmod._match
    state = {"answer": False}

    def match_wrapper(c, act, board, solution):
        state["answer"] = bool(solution)
        original_match(c, act, board, solution)

    def symbol_wrapper(c, name, x, y, r):
        original_symbol(c, name, x, y, r)
        if state["answer"] or not only_answer:
            c.saveState()
            decorate(c, x, y)
            c.restoreState()

    monkeypatch.setattr(pdfmod, "_match", match_wrapper)
    monkeypatch.setattr(pdfmod, "_symbol", symbol_wrapper)
