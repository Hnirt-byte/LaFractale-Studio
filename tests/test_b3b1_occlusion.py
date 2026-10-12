"""MINOR-3 (stray drawings that imitate an anchor) and MINOR-4 (symbols hidden by a later drawing).

Faults are injected in memory into the historical renderer; the repository code is untouched.
Scope: the symbols of the synthetic ``match`` activity (maze walls and dots are not covered).
"""
import pytest

import lafractale.layout.pdf as pdfmod
from b3b1_support import FIXTURE, after_each_symbol, qa_failures
from lafractale.engine import qa
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


# ----------------------------------------------------------------------------- MINOR-3

def _fill(c, gray=0.11):
    c.setFillGray(gray)


STRAYS = {
    "barre pleine 6,8 x 20": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 10, 6.8, 20, stroke=0, fill=1)),
    "barre pleine 20 x 6,8": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 3.4, 20, 6.8, stroke=0, fill=1)),
    "rectangle plein 6,8 x 7,5": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 3.7, 6.8, 7.5, stroke=0, fill=1)),
    "rectangle plein 7,5 x 6,8": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 3.4, 7.5, 6.8, stroke=0, fill=1)),
    "disque plein 7,4": lambda c, x, y: (_fill(c), c.circle(x + 44, y, 3.7, stroke=0, fill=1)),
    "disque plein 6,2": lambda c, x, y: (_fill(c), c.circle(x + 44, y, 3.1, stroke=0, fill=1)),
    "carré plein 6,8 x 6,8": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 3.4, 6.8, 6.8, stroke=0, fill=1)),
    "disque 6,8 plein mais contour en plus": lambda c, x, y: (_fill(c), c.setStrokeGray(0.5),
                                                              c.circle(x + 44, y, 3.4, stroke=1, fill=1)),
    "disque 6,8 plein mais gris clair": lambda c, x, y: (_fill(c, 0.9), c.circle(x + 44, y, 3.4, stroke=0, fill=1)),
    "disque 6,8 creux (contour seul)": lambda c, x, y: (c.setStrokeGray(0.11), c.circle(x + 44, y, 3.4, stroke=1, fill=0)),
    # near-size decoys that the former 0.3 pt tolerance accepted as anchors
    "disque plein 6,9": lambda c, x, y: (_fill(c), c.circle(x + 44, y, 3.45, stroke=0, fill=1)),
    "disque plein 7,0": lambda c, x, y: (_fill(c), c.circle(x + 44, y, 3.5, stroke=0, fill=1)),
    "rectangle plein 6,8 x 6,9": lambda c, x, y: (_fill(c), c.rect(x + 40, y - 3.4, 6.8, 6.9, stroke=0, fill=1)),
}
#: Decoys that draw like a symbol are reported as an extra symbol; every other one as an unexpected stroke.
AS_SYMBOL = {"disque 6,8 plein mais contour en plus", "disque 6,8 creux (contour seul)"}


@pytest.mark.parametrize("name", sorted(STRAYS))
def test_stray_drawing_close_to_an_anchor_is_refused(case, tmp_path, monkeypatch, name):
    after_each_symbol(monkeypatch, STRAYS[name])
    expected = "symbole supplémentaire" if name in AS_SYMBOL else "tracé(s) de style inattendu"
    assert expected in detected(case, tmp_path), name


def test_an_extra_true_looking_anchor_is_refused(case, tmp_path, monkeypatch):
    """A perfect disc 6.8 x 6.8 gray 0.11 is an anchor: there are then too many of them."""
    after_each_symbol(monkeypatch, lambda c, x, y: (_fill(c), c.circle(x + 44, y, 3.4, stroke=0, fill=1)))
    assert "points d'ancrage" in detected(case, tmp_path)


def test_nominal_render_is_not_rejected(case, tmp_path):
    assert detected(case, tmp_path) == ""


def test_anchor_recognition_requires_both_dimensions_the_fill_and_no_stroke():
    class R:
        def __init__(self, w, h):
            self.width, self.height = w, h

    disc = {"items": [("c",)] * 4, "type": "f", "fill": (0.11,) * 3, "fill_opacity": 1.0, "rect": R(6.8, 6.8)}
    assert qa._is_anchor(disc)
    for change in ({"rect": R(6.8, 20)}, {"rect": R(20, 6.8)}, {"rect": R(7.2, 6.8)}, {"type": "fs"},
                   {"type": "s"}, {"fill": (0.9,) * 3}, {"fill": None}, {"fill_opacity": 0.5},
                   {"items": [("re",)]}, {"items": [("l",)] * 4}):
        assert not qa._is_anchor({**disc, **change}), change


# ----------------------------------------------------------------------------- MINOR-4

def _cover(width, height, gray=0.99, dx=0, dy=0):
    def draw(c, x, y):
        c.setFillGray(gray)
        c.rect(x + dx - width / 2, y + dy - height / 2, width, height, stroke=0, fill=1)
    return draw


def test_light_fill_drawn_over_the_symbols_is_detected(case, tmp_path, monkeypatch):
    after_each_symbol(monkeypatch, _cover(100, 60, 0.98))
    detail = detected(case, tmp_path)
    assert "association" in detail and "masqué" in detail


def test_fill_of_100_by_60_points_is_detected(case, tmp_path, monkeypatch):
    after_each_symbol(monkeypatch, _cover(100, 60, 1.0))
    assert "masqué" in detected(case, tmp_path)


def test_partial_occlusion_of_one_corner_is_detected(case, tmp_path, monkeypatch):
    # 14 x 14 pt patch over the upper-left part of every symbol
    after_each_symbol(monkeypatch, _cover(14, 14, 1.0, dx=-20, dy=18))
    assert "masqué" in detected(case, tmp_path)


def test_white_stroke_line_across_the_symbol_is_detected(case, tmp_path, monkeypatch):
    def line(c, x, y):
        c.setStrokeGray(1.0)
        c.setLineWidth(6)
        c.line(x - 30, y, x + 30, y)
    after_each_symbol(monkeypatch, line)
    assert "masqué" in detected(case, tmp_path)


def test_invisible_white_text_over_the_symbol_is_detected(case, tmp_path, monkeypatch):
    def text(c, x, y):
        c.setFillGray(1.0)
        c.setFont("Helvetica-Bold", 44)
        c.drawString(x - 24, y - 12, "WW")
    after_each_symbol(monkeypatch, text)
    assert "masqué" in detected(case, tmp_path)


def test_clipping_that_crops_a_symbol_is_detected_by_the_pixel_probe(case, tmp_path, monkeypatch):
    original = pdfmod._symbol

    def cropped(c, name, x, y, r):
        c.saveState()
        path = c.beginPath()
        path.rect(x - 40, y - 40, 80, 38)  # keeps only the lower part of the symbol
        c.clipPath(path, stroke=0, fill=0)
        original(c, name, x, y, r)
        c.restoreState()

    monkeypatch.setattr(pdfmod, "_symbol", cropped)
    assert "masqué" in detected(case, tmp_path)


def test_occlusion_only_on_the_answer_key_is_detected(case, tmp_path, monkeypatch):
    after_each_symbol(monkeypatch, _cover(100, 60, 1.0), only_answer=True)
    assert "masqué" in detected(case, tmp_path)


def test_an_image_over_the_symbols_is_refused_by_the_no_image_rule(case, tmp_path, monkeypatch):
    from io import BytesIO
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    png = BytesIO()
    Image.new("L", (4, 4), 255).save(png, format="PNG")

    def image(c, x, y):
        c.drawImage(ImageReader(BytesIO(png.getvalue())), x - 30, y - 30, 60, 60)
    after_each_symbol(monkeypatch, image)
    spec, activities = case
    assert "pdf.no_image" in qa_failures(spec, activities, tmp_path)


def test_visibility_probe_runs_on_every_symbol_and_passes_on_the_nominal_render(case, tmp_path):
    import pymupdf as fitz
    from b3b1_support import render_in_process
    spec, activities = case
    interior, answer = render_in_process(spec, activities, tmp_path)
    with fitz.open(interior) as doc, fitz.open(answer) as key:
        for index, activity in enumerate(activities):
            if activity.type != "match":
                continue
            for page in (doc[index], key[index]):
                symbols = [d for d in page.get_drawings() if d.get("width") and abs(d["width"] - 2.6) < 0.05]
                result = qa._occlusion_errors(page, symbols)
                assert result.errors == [] and result.probes >= 8 * 3, (result.probes, result.errors)
