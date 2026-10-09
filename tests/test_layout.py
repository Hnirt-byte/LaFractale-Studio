"""Adversarial and regression tests for the V0.2-B print composition layer."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import fitz
import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.export.builder import audit_output, build_demo
from lafractale.layout.composition import Rect, compose_page, validate_composition
from lafractale.layout.pdf import _labels_for_points, _measure, fonts, write_pdf
from lafractale.story.plan import demo_specs

ROOT = Path(__file__).resolve().parents[1]


def _activities(book):
    return [generate(s, stable_seed(book.book_id, s.id, 2026)) for s in demo_specs(book)]


def _compose(activity, book, *, answer_key=False):
    regular, bold = fonts()
    return compose_page(activity, book.data, index=1, count=3, answer_key=answer_key,
                        regular=regular, bold=bold, text_width=_measure)


def test_all_activity_layouts_fit_and_do_not_overlap(halloween):
    for activity in _activities(halloween):
        for answer_key in (False, True):
            layout = _compose(activity, halloween, answer_key=answer_key)
            assert layout.safe.contains(layout.board)
            assert layout.safe.contains(layout.companion_slot)
            assert not layout.companion_slot.overlaps(layout.scene.region)
            validate_composition(layout, text_width=_measure)


def test_non_halloween_layout_is_neutral():
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    for activity in _activities(book):
        layout = _compose(activity, book)
        assert "Pip" not in " ".join(layout.title.lines + layout.scene.lines +
                                     layout.prompt_fr.lines + layout.prompt_en.lines)


def test_footer_inside_safe_area(halloween):
    layout = _compose(_activities(halloween)[0], halloween)
    assert layout.safe.contains(layout.footer)
    assert layout.board.y > layout.footer.top


def test_fake_overlapping_zone_detected(halloween):
    layout = _compose(_activities(halloween)[0], halloween)
    bad = replace(layout, footer=layout.board)
    with pytest.raises(ValueError, match="chevauchent"):
        validate_composition(bad, text_width=_measure)


def test_fake_unsafe_board_rejected(halloween):
    layout = _compose(_activities(halloween)[0], halloween)
    bad = replace(layout, board=Rect(-1, layout.board.y, layout.board.width, layout.board.height))
    with pytest.raises(ValueError, match="sécurité"):
        validate_composition(bad, text_width=_measure)


def test_long_scene_refused_without_truncation(halloween):
    act = replace(_activities(halloween)[0], scene="trèslong" * 50)
    with pytest.raises(ValueError, match="Mot trop long"):
        _compose(act, halloween)


def test_many_words_refused_without_hidden_overflow(halloween):
    act = replace(_activities(halloween)[0], scene="Une grande histoire " * 24)
    with pytest.raises(ValueError, match="Texte débordant"):
        _compose(act, halloween)


def test_small_trim_refused_instead_of_unsafe_scaling(halloween):
    small = dict(halloween.data)
    small["trim"] = {"width_in": 4, "height_in": 6}
    act = _activities(halloween)[0]
    regular, bold = fonts()
    with pytest.raises(ValueError, match="limité au format"):
        compose_page(act, small, index=1, count=3, answer_key=False,
                     regular=regular, bold=bold, text_width=_measure)


def test_dots_labels_do_not_collide_for_all_supported_shapes(tmp_path):
    from lafractale.activities.engine import generate_connect
    import random
    from lafractale.layout.composition import Rect
    regular, bold = fonts()
    board = Rect(50, 150, 510, 397)
    for shape in ("moon", "house", "star"):
        for seed in range(20):
            geometry, _ = generate_connect(random.Random(seed), shape)
            coords = [(board.x + 67 + p["x"] * (board.width - 134),
                       board.y + 42 + p["y"] * (board.height - 110))
                      for p in geometry["points"]]
            labels = _labels_for_points(coords, board, bold)
            assert len(labels) == len(geometry["points"])
            assert len(set(labels)) == len(labels)


def test_halloween_pdf_has_no_spoiler_label_and_no_embedded_unapproved_art(tmp_path, halloween):
    out = tmp_path / "halloween"
    build_demo(halloween, out)
    assert audit_output(out, book=halloween) == []
    for filename in ("interior.pdf", "answer_key.pdf"):
        with fitz.open(out / filename) as doc:
            assert len(doc) == 3
            assert all(not page.get_images(full=True) for page in doc)
            assert all("Forme :" not in page.get_text() for page in doc)
            assert "VISUEL À VALIDER" in doc[0].get_text()


def test_christmas_pdf_remains_free_of_pip(tmp_path):
    book = load_book(ROOT / "books/christmas_2026/book.yaml")
    out = tmp_path / "christmas"
    build_demo(book, out)
    assert audit_output(out, book=book) == []
    for filename in ("interior.pdf", "answer_key.pdf"):
        with fitz.open(out / filename) as doc:
            assert all("Pip" not in page.get_text() for page in doc)
            assert all(not page.get_images(full=True) for page in doc)


def test_pdf_native_text_stays_inside_page_bounds(tmp_path, halloween):
    out = tmp_path / "layout"
    build_demo(halloween, out)
    with fitz.open(out / "interior.pdf") as doc:
        for page in doc:
            for word in page.get_text("words"):
                x0, y0, x1, y1 = word[:4]
                assert x0 > 35 and y0 > 35
                assert x1 < page.rect.width - 35 and y1 < page.rect.height - 35


def test_pdf_raises_before_replacing_existing_valid_demo(tmp_path, halloween, monkeypatch):
    from lafractale.layout import pdf as pdf_module
    out = tmp_path / "existing"
    build_demo(halloween, out)
    pdf_bytes_before = (out / "interior.pdf").read_bytes()
    manifest_before = (out / "manifest.json").read_bytes()
    original = pdf_module.compose_page

    def error_in_second_page(activity, *args, **kwargs):
        if activity.type == "connect_dots":
            raise ValueError("Fault injected after first worksheet")
        return original(activity, *args, **kwargs)

    monkeypatch.setattr(pdf_module, "compose_page", error_in_second_page)
    with pytest.raises(ValueError, match="Fault injected"):
        build_demo(halloween, out)
    assert (out / "interior.pdf").read_bytes() == pdf_bytes_before
    assert (out / "manifest.json").read_bytes() == manifest_before
    # Replay now requires the original trusted renderer, not the fault-injected hook.
    monkeypatch.setattr(pdf_module, "compose_page", original)
    assert audit_output(out, book=halloween) == []


def test_pdf_bytes_reproduce_with_frozen_epoch(tmp_path, halloween, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1780000000")
    build_demo(halloween, tmp_path / "a", seed=13)
    build_demo(halloween, tmp_path / "b", seed=13)
    for name in ("interior.pdf", "answer_key.pdf", "activities.json", "manifest.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
