"""MAJOR-2: the QA must check the symbols actually DRAWN in a match activity, not only the links.

Faults are injected into the historical renderer in memory (monkeypatch); the repository
code itself is never modified. Renders use the in-process writer on purpose.
"""
from dataclasses import replace
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

import lafractale.layout.pdf as pdfmod
from b3b1_support import FIXTURE, patch_match as _patch_match, patch_symbol, qa_failures, render_in_process
from lafractale.engine import qa
from lafractale.engine.contracts import load_spec_set
from lafractale.engine.pipeline import build_activities

KEY = "pdf.answer_matches_activity"


@pytest.fixture(scope="module")
def case():
    spec = load_spec_set(FIXTURE)
    return spec, build_activities(spec).activities


def failures(case, tmp_path):
    spec, activities = case
    return qa_failures(spec, activities, tmp_path)


def patch_match(monkeypatch, transform):  # kept as a local alias for readability
    _patch_match(monkeypatch, transform)


def test_nominal_association_passes_with_matching_symbols_and_answer(case, tmp_path):
    assert failures(case, tmp_path) == {}


def test_left_symbols_drawn_in_reverse_order_are_detected(case, tmp_path, monkeypatch):
    patch_match(monkeypatch, lambda a: replace(a, geometry={**a.geometry,
                "left_symbols": a.geometry["left_symbols"][::-1]}))
    assert "association" in failures(case, tmp_path).get(KEY, "")


def test_right_symbols_drawn_in_reverse_order_are_detected(case, tmp_path, monkeypatch):
    patch_match(monkeypatch, lambda a: replace(a, geometry={**a.geometry,
                "right_symbols": a.geometry["right_symbols"][::-1]}))
    assert "association" in failures(case, tmp_path).get(KEY, "")


def test_simultaneous_permutation_of_both_columns_cannot_hide_a_source_mismatch(case, tmp_path, monkeypatch):
    """Both columns reversed AND the links remapped: the page is internally consistent
    (every link joins twins) yet differs from the activity regenerated from the source."""
    def both(a):
        n = len(a.geometry["left_symbols"])
        pairs = a.answer["left_to_right"]
        return replace(a, geometry={**a.geometry, "left_symbols": a.geometry["left_symbols"][::-1],
                                    "right_symbols": a.geometry["right_symbols"][::-1]},
                       answer={"left_to_right": [n - 1 - pairs[n - 1 - i] for i in range(n)]})
    patch_match(monkeypatch, both)
    detail = failures(case, tmp_path).get(KEY, "")
    assert "association" in detail and "attendu" in detail


def test_links_joining_different_symbols_are_detected(case, tmp_path, monkeypatch):
    def swapped(a):
        pairs = list(a.answer["left_to_right"])
        pairs[0], pairs[1] = pairs[1], pairs[0]
        return replace(a, answer={"left_to_right": pairs})
    patch_match(monkeypatch, swapped)
    assert "association" in failures(case, tmp_path).get(KEY, "")


@pytest.mark.parametrize("call_index", range(8))
def test_a_symbol_replaced_by_another_shape_is_detected(case, tmp_path, monkeypatch, call_index):
    swap = {"circle": "square", "square": "diamond", "triangle": "hexagon", "star": "hexagon",
            "diamond": "square", "hexagon": "triangle"}
    patch_symbol(monkeypatch, lambda i, name: [(swap[name] if i == call_index else name, 0)])
    assert "association" in failures(case, tmp_path).get(KEY, "")


def test_a_missing_symbol_is_detected(case, tmp_path, monkeypatch):
    patch_symbol(monkeypatch, lambda i, name: [] if i == 3 else [(name, 0)])
    detail = failures(case, tmp_path).get(KEY, "")
    assert "association" in detail and "manquant" in detail


def test_an_extra_symbol_is_detected(case, tmp_path, monkeypatch):
    patch_symbol(monkeypatch, lambda i, name: [(name, 0), ("circle", 0)] if i == 5 else [(name, 0)])
    detail = failures(case, tmp_path).get(KEY, "")
    assert "association" in detail and "supplémentaire" in detail


def test_a_valid_answer_key_is_consistent_with_the_activity(case, tmp_path):
    """Both PDFs of the nominal render: links join twins, columns follow the activity."""
    spec, activities = case
    interior, answer = render_in_process(spec, activities, tmp_path)
    with fitz.open(interior) as fiche, fitz.open(answer) as corrige:
        for index, activity in enumerate(activities):
            if activity.type == "match":
                assert qa._match_coherence(activity, fiche[index], corrige[index]) == []


SYMBOLS = ("circle", "square", "triangle", "diamond", "star", "hexagon")


def _drawn_signatures():
    """One page per symbol, drawn by the historical renderer's own ``_symbol``."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(300, 300), invariant=1)
    for name in SYMBOLS:
        pdfmod._symbol(c, name, 150, 150, 26)
        c.showPage()
    c.save()
    signatures = []
    with fitz.open(stream=buffer.getvalue(), filetype="pdf") as doc:
        for page in doc:
            drawings = [d for d in page.get_drawings() if d.get("width") and abs(d["width"] - 2.6) < 0.05]
            assert len(drawings) == 1
            signatures.append(qa._drawn_signature(drawings[0]))
    return signatures


def test_expected_signatures_match_every_symbol_the_renderer_draws():
    drawn = _drawn_signatures()
    assert len(drawn) == len(SYMBOLS)
    for name, signature in zip(SYMBOLS, drawn):
        expected = qa._expected_signature(name)
        assert expected is not None and qa._same_signature(signature, expected), name
        others = [n for n in SYMBOLS if n != name]
        assert not any(qa._same_signature(signature, qa._expected_signature(o)) for o in others), name


def test_unknown_symbol_names_have_no_expected_signature():
    assert qa._expected_signature("hat_star") is None
    assert qa._expected_signature("gift_circle") is None


def test_a_stray_drawing_of_another_style_inside_a_row_is_detected(case, tmp_path, monkeypatch):
    """A decoy glyph that does not mimic the symbol stroke width must not go unnoticed."""
    original = pdfmod._symbol

    def with_decoy(c, name, x, y, r):
        original(c, name, x, y, r)
        c.saveState()
        c.setFillGray(0.2)
        c.rect(x + 40, y - 4, 8, 8, stroke=0, fill=1)
        c.restoreState()

    monkeypatch.setattr(pdfmod, "_symbol", with_decoy)
    detail = failures(case, tmp_path).get(KEY, "")
    assert "association" in detail and "style" in detail


def test_columns_are_split_at_the_anchors_not_at_the_page_middle(case, tmp_path, monkeypatch):
    """Shift the whole board sideways: the check follows the anchors, not the page centre."""
    original = pdfmod._match

    def shifted(c, act, board, solution):
        from lafractale.layout.composition import Rect
        original(c, act, Rect(board.x + 150, board.y, board.width, board.height), solution)

    monkeypatch.setattr(pdfmod, "_match", shifted)
    assert failures(case, tmp_path).get(KEY, "") == ""
