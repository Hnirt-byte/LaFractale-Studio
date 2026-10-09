"""Independent reproductions of B1 security review findings and adjacent variants.

Threat model: malicious/surprising paths and mutable activity data. This is not
an in-process sandbox for arbitrary Python code with the same privileges.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import fitz
import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.export.builder import build_demo, audit_output
from lafractale.export.securefs import UnsafeOutputPath
from lafractale.layout.pdf import write_pdf
from lafractale.story.plan import demo_specs

ROOT = Path(__file__).resolve().parents[1]


def christmas():
    return load_book(ROOT / "books/christmas_2026/book.yaml")


def activities(book):
    return [generate(spec, stable_seed(book.book_id, spec.id, 2026))
            for spec in demo_specs(book)]


def test_build_rejects_parent_symlink_and_writes_nothing_outside(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(external, target_is_directory=True)
    with pytest.raises(UnsafeOutputPath):
        build_demo(christmas(), parent_link / "redirected-output")
    assert list(external.iterdir()) == []


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_build_rejects_symlink_at_any_ancestor(tmp_path, depth):
    external = tmp_path / "outside"
    external.mkdir()
    link = tmp_path / "link"
    link.symlink_to(external, target_is_directory=True)
    output = link.joinpath(*[f"p{i}" for i in range(depth)], "demo")
    with pytest.raises(UnsafeOutputPath):
        build_demo(christmas(), output)
    assert list(external.iterdir()) == []


def test_build_rejects_output_leaf_symlink(tmp_path):
    target = tmp_path / "external"
    target.mkdir()
    link = tmp_path / "demo"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(UnsafeOutputPath):
        build_demo(christmas(), link)
    assert list(target.iterdir()) == []


def test_build_rejects_parent_traversal_components(tmp_path):
    with pytest.raises(UnsafeOutputPath):
        build_demo(christmas(), tmp_path / "a" / ".." / "demo")


def test_write_pdf_rejects_symlink_output_file_without_overwriting(tmp_path):
    book = christmas()
    victim = tmp_path / "victim.txt"
    victim.write_bytes(b"DO NOT OVERWRITE")
    link = tmp_path / "demo.pdf"
    link.symlink_to(victim)
    with pytest.raises(UnsafeOutputPath):
        write_pdf(link, activities(book), book.data, answer_key=False)
    assert victim.read_bytes() == b"DO NOT OVERWRITE"


def test_write_pdf_rejects_regular_existing_pdf_without_overwriting(tmp_path):
    book = christmas()
    path = tmp_path / "demo.pdf"
    path.write_bytes(b"PRESERVE")
    with pytest.raises(UnsafeOutputPath):
        write_pdf(path, activities(book), book.data, answer_key=False)
    assert path.read_bytes() == b"PRESERVE"


def test_write_pdf_rejects_symlink_parent(tmp_path):
    book = christmas()
    external = tmp_path / "elsewhere"
    external.mkdir()
    (tmp_path / "link").symlink_to(external, target_is_directory=True)
    with pytest.raises(UnsafeOutputPath):
        write_pdf(tmp_path / "link" / "outside.pdf", activities(book), book.data, answer_key=False)
    assert list(external.iterdir()) == []


def test_post_composition_mutation_cannot_reach_dots_or_json(tmp_path, monkeypatch):
    from lafractale.layout import pdf as renderer
    original = renderer.compose_page
    observed = []

    def malicious_compose(act, *args, **kwargs):
        layout = original(act, *args, **kwargs)
        if act.type == "connect_dots":
            observed.append(True)
            # The exact attack: mutate geometry after compose_page, before _dots.
            act.geometry["points"][0]["n"] = "PIP-INJECTED"
        return layout

    monkeypatch.setattr(renderer, "compose_page", malicious_compose)
    output = tmp_path / "christmas"
    with pytest.raises(TypeError):
        build_demo(christmas(), output)
    assert observed
    assert not output.exists()


def test_external_original_activity_mutation_cannot_reach_writer(tmp_path, monkeypatch):
    from lafractale.layout import pdf as renderer
    book = christmas()
    data = activities(book)
    original = renderer.compose_page

    def mutate_source(act, *args, **kwargs):
        if act.type == "connect_dots":
            external = next(a for a in data if a.type == "connect_dots")
            external.geometry["points"][0]["n"] = "PIP-INJECTED"
        return original(act, *args, **kwargs)

    monkeypatch.setattr(renderer, "compose_page", mutate_source)
    path = tmp_path / "independent.pdf"
    write_pdf(path, data, book.data, answer_key=False)
    with fitz.open(path) as doc:
        assert all("PIP-INJECTED" not in p.get_text() for p in doc)


def test_rendered_reserved_name_is_detected_even_if_drawn_directly(tmp_path, monkeypatch):
    from lafractale.layout import pdf as renderer
    original = renderer._dots

    def malicious_dots(canvas, act, board, answer, bold):
        canvas.setFont(bold, 12)
        canvas.drawString(board.x + 40, board.y + 30, "PIP-INJECTED")
        return original(canvas, act, board, answer, bold)

    monkeypatch.setattr(renderer, "_dots", malicious_dots)
    out = tmp_path / "christmas"
    with pytest.raises(ValueError, match="Compagnon non autorisé"):
        build_demo(christmas(), out)
    assert not out.exists()


def test_injected_name_does_not_replace_existing_valid_demo(tmp_path, monkeypatch):
    from lafractale.layout import pdf as renderer
    book = christmas()
    out = tmp_path / "christmas"
    build_demo(book, out)
    before = {name: (out / name).read_bytes() for name in
              ("interior.pdf", "answer_key.pdf", "activities.json", "manifest.json")}
    original = renderer._dots

    def malicious_dots(canvas, act, board, answer, bold):
        canvas.setFont(bold, 12)
        canvas.drawString(board.x + 30, board.y + 30, "PIP-INJECTED")
        return original(canvas, act, board, answer, bold)

    monkeypatch.setattr(renderer, "_dots", malicious_dots)
    with pytest.raises(ValueError, match="Compagnon non autorisé"):
        build_demo(book, out)
    assert all((out / name).read_bytes() == data for name, data in before.items())
    assert audit_output(out, book=book) == []


def test_pdf_writer_removes_partial_file_after_render_exception(tmp_path, monkeypatch):
    from lafractale.layout import pdf as renderer
    book = christmas()
    original = renderer._dots

    def fail(*args, **kwargs):
        raise ValueError("rendu volontairement interrompu")

    monkeypatch.setattr(renderer, "_dots", fail)
    path = tmp_path / "partial.pdf"
    with pytest.raises(ValueError, match="interrompu"):
        write_pdf(path, activities(book), book.data, answer_key=False)
    assert not path.exists()


def test_write_pdf_safely_creates_missing_parent_directories(tmp_path):
    book = christmas()
    path = tmp_path / "nested" / "directory" / "demo.pdf"
    write_pdf(path, activities(book), book.data, answer_key=False)
    with fitz.open(path) as document:
        assert len(document) == 3
