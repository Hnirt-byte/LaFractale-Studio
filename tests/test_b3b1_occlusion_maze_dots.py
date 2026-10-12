"""Residual MINOR-4: maze walls and numbered dots hidden by a later drawing, text or clipping.

Faults are injected in memory into the historical renderer; the repository code is untouched.
"""
import pytest

import lafractale.layout.pdf as pdfmod
from b3b1_support import FIXTURE, qa_failures
from lafractale.engine.contracts import load_spec_set
from lafractale.engine.pipeline import build_activities

KEY = "pdf.answer_matches_activity"


@pytest.fixture(scope="module")
def case():
    spec = load_spec_set(FIXTURE)
    return spec, build_activities(spec).activities


def detected(case, tmp_path):
    spec, activities = case
    return qa_failures(spec, activities, tmp_path).get(KEY, "")


def after_board(monkeypatch, name, decorate, *, only_answer=False):
    """Run ``decorate(c, board)`` right AFTER the historical ``_maze`` / ``_dots`` drew its page."""
    original = getattr(pdfmod, name)

    def wrapper(c, act, board, solution, *args, **kwargs):
        original(c, act, board, solution, *args, **kwargs)
        if solution or not only_answer:
            c.saveState()
            decorate(c, board)
            c.restoreState()

    monkeypatch.setattr(pdfmod, name, wrapper)


def cover(gray=1.0, w=0.5, h=0.5):
    def draw(c, board):
        c.setFillGray(gray)
        c.rect(board.x + board.width * (1 - w) / 2, board.y + board.height * (1 - h) / 2,
               board.width * w, board.height * h, stroke=0, fill=1)
    return draw


def patch_wall_points(c, board):  # a white bar across the lower-left of the board
    c.setStrokeGray(1.0)
    c.setLineWidth(9)
    c.line(board.x, board.y + board.height * 0.4, board.x + board.width, board.y + board.height * 0.4)


def test_nominal_render_is_not_rejected(case, tmp_path):
    assert detected(case, tmp_path) == ""


@pytest.mark.parametrize("name,kind", [("_maze", "labyrinthe"), ("_dots", "points")])
def test_light_fill_over_the_board_is_detected(case, tmp_path, monkeypatch, name, kind):
    after_board(monkeypatch, name, cover(0.99))
    detail = detected(case, tmp_path)
    assert kind in detail and "masqué" in detail


@pytest.mark.parametrize("name,kind", [("_maze", "labyrinthe"), ("_dots", "points")])
def test_occlusion_only_on_the_answer_key_is_detected(case, tmp_path, monkeypatch, name, kind):
    after_board(monkeypatch, name, cover(1.0), only_answer=True)
    # the extra cover is already an unexpected second drawing of the corrigé (reported before the occlusion layers)
    assert kind in detected(case, tmp_path)


def test_white_stroke_across_the_maze_is_detected(case, tmp_path, monkeypatch):
    after_board(monkeypatch, "_maze", patch_wall_points)
    assert "mur masqué" in detected(case, tmp_path)


@pytest.mark.parametrize("name,kind", [("_maze", "labyrinthe"), ("_dots", "points")])
def test_invisible_white_text_over_the_board_is_detected(case, tmp_path, monkeypatch, name, kind):
    def text(c, board):
        c.setFillGray(1.0)
        c.setFont("Helvetica-Bold", 200)
        c.drawString(board.x + 20, board.y + board.height / 2 - 60, "WWW")
    after_board(monkeypatch, name, text)
    assert "masqué" in detected(case, tmp_path)


@pytest.mark.parametrize("name,kind", [("_maze", "labyrinthe"), ("_dots", "points")])
def test_clipping_that_crops_the_board_is_detected_by_the_pixel_probe(case, tmp_path, monkeypatch, name, kind):
    original = getattr(pdfmod, name)

    def cropped(c, act, board, solution, *args, **kwargs):
        c.saveState()
        path = c.beginPath()
        path.rect(board.x, board.y, board.width, board.height * 0.45)  # keeps only the lower part
        c.clipPath(path, stroke=0, fill=0)
        original(c, act, board, solution, *args, **kwargs)
        c.restoreState()

    monkeypatch.setattr(pdfmod, name, cropped)
    detail = detected(case, tmp_path)
    assert kind in detail and "masqué" in detail
