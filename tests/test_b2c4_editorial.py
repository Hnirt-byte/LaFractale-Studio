"""B2-C4 editorial profile `halloween-editorial-v1`: transform, validation, guards.

The profile is a static, opt-in overlay applied strictly downstream of the C1
revalidation and C2 placement. Historical modes (placeholder B2-B, legacy B2-B,
routed C1, placed C2 V2) stay byte-identical; the 12-point moon is never mutated
in place, and the historical validator still requires 12 points for the moon.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.activities.models import Activity
from lafractale.config.schema import load_book
from lafractale.editorial import (
    EDITORIAL_HALLOWEEN_V1,
    EditorialSpec,
    editorial_spec,
    resolve_editorial_profile,
    transform_editorial,
    validate_editorial_activity,
)
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import ROUTING_HALLOWEEN_PIP_DEMO_V1, build_illustration_route
from lafractale.illustrations.placement import (
    PIP_PLACEMENT_HALLOWEEN_V2,
    build_pip_placement_plan,
)
from lafractale.layout.composition import Rect, compose_page
from lafractale.layout.pdf import (_labels_for_points, _measure, _segment_intersects_rect,
                                   fonts)
from lafractale.quality.checks import validate_collection
from lafractale.story.plan import demo_specs

ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"


def _book(path=HALLOWEEN):
    return load_book(path)


def _activities(book):
    return [generate(spec, stable_seed(book.book_id, spec.id, 2026))
            for spec in demo_specs(book)]


def _transformed(book):
    return [transform_editorial(a, book, EDITORIAL_HALLOWEEN_V1) for a in _activities(book)]


# --- resolution / opt-in -----------------------------------------------------

def test_editorial_profile_is_opt_in():
    assert resolve_editorial_profile(None) == "none"
    assert resolve_editorial_profile(EDITORIAL_HALLOWEEN_V1) == EDITORIAL_HALLOWEEN_V1
    assert editorial_spec(None) is None
    spec = editorial_spec(EDITORIAL_HALLOWEEN_V1)
    assert spec == EditorialSpec(EDITORIAL_HALLOWEEN_V1, 12, 16, 12, 11, 1.0, 1.0)


@pytest.mark.parametrize("value", ["", "unknown", "halloween-editorial-v2",
                                   "halloween-pip-placement-v2", "editorial"])
def test_unknown_editorial_profile_is_refused(value):
    with pytest.raises(IllustrationError):
        resolve_editorial_profile(value)
    with pytest.raises(IllustrationError):
        editorial_spec(value)


# --- transform ---------------------------------------------------------------

def test_transform_produces_canonical_scenes_and_8_point_crescent():
    book = _book()
    acts = _transformed(book)
    by_type = {a.type: a for a in acts}
    assert by_type["maze"].scene == "Aide Pip à trouver la sortie"
    assert by_type["match"].scene == "Retrouve les chapeaux jumeaux"
    moon = by_type["connect_dots"]
    assert moon.scene == "La lune mystérieuse"  # lunar universe preserved
    assert moon.geometry["shape"] == "moon"
    pts = moon.geometry["points"]
    assert len(pts) == 8
    assert [p["n"] for p in pts] == list(range(1, 9))
    assert moon.geometry["closed"] is True
    assert moon.answer == {"order": list(range(1, 9)), "close_to": 1}
    assert moon.prompt_fr == "Relie les points de 1 à 8, puis reviens au 1."
    assert moon.prompt_en == "Connect the dots from 1 to 8, then back to 1."


def test_transform_is_pure_and_deterministic():
    book = _book()
    acts = _activities(book)
    first = [transform_editorial(a, book, EDITORIAL_HALLOWEEN_V1) for a in acts]
    second = [transform_editorial(a, book, EDITORIAL_HALLOWEEN_V1) for a in acts]
    assert first == second
    # id / page / type are stable; only content fields change.
    for before, after in zip(acts, first):
        assert (after.id, after.page, after.type, after.seed) == \
               (before.id, before.page, before.type, before.seed)


def test_transform_requires_halloween_book():
    book = _book()
    christmas = _book(CHRISTMAS)
    act = _activities(book)[0]
    with pytest.raises(IllustrationError):
        transform_editorial(act, christmas, EDITORIAL_HALLOWEEN_V1)


def test_transform_refuses_unknown_activity_and_bad_profile():
    book = _book()
    act = _activities(book)[0]
    with pytest.raises(IllustrationError):
        transform_editorial(act, book, "unknown-profile")
    # An activity identity not covered by the canonical C4 table is refused.
    foreign = replace(act, id="halloween_2026-p099", page=99)
    with pytest.raises(IllustrationError):
        transform_editorial(foreign, book, EDITORIAL_HALLOWEEN_V1)
    forged_type = replace(act, type="coloring")
    with pytest.raises(IllustrationError):
        transform_editorial(forged_type, book, EDITORIAL_HALLOWEEN_V1)


# --- validation --------------------------------------------------------------

def test_crescent_is_validated_by_historical_rules():
    book = _book()
    for act in _transformed(book):
        assert validate_editorial_activity(act) == []


def test_crescent_rejects_a_nine_point_moon():
    book = _book()
    moon = next(a for a in _transformed(book) if a.type == "connect_dots")
    pts = moon.geometry["points"]
    nine = pts + [{"n": 9, "x": 0.5, "y": 0.5}]
    forged = replace(moon, geometry={"shape": "moon", "points": nine, "closed": True},
                     answer={"order": list(range(1, 10)), "close_to": 1})
    errors = validate_editorial_activity(forged)
    assert any("8 points" in e or "numérotation" in e for e in errors)


def test_historical_moon_stays_twelve_points():
    """The no-opt-in engine must keep producing and validating a 12-point moon."""
    book = _book()
    moon = next(a for a in _activities(book) if a.type == "connect_dots")
    assert len(moon.geometry["points"]) == 12
    assert validate_collection(_activities(book)) == []
    # An 8-point moon in the HISTORICAL validator is still refused (moon_len=12).
    shortened = replace(moon, geometry={
        "shape": "moon", "points": moon.geometry["points"][:8], "closed": True})
    assert validate_collection([replace(moon, geometry=shortened.geometry)])


# --- composition -------------------------------------------------------------

def test_no_profile_composition_is_historical():
    book = _book()
    acts = _activities(book)
    regular, bold = fonts()
    hist = compose_page(acts[0], book.data, index=1, count=3, answer_key=False,
                        regular=regular, bold=bold, text_width=_measure)
    assert hist.prompt_en.size == 10  # historical EN size
    edit = compose_page(acts[0], book.data, index=1, count=3, answer_key=False,
                        regular=regular, bold=bold, text_width=_measure,
                        editorial=editorial_spec(EDITORIAL_HALLOWEEN_V1))
    assert edit.prompt_en.size == 12


def test_editorial_composition_fits_without_collision():
    book = _book()
    acts = _transformed(book)
    regular, bold = fonts()
    for index, act in enumerate(acts, 1):
        layout = compose_page(act, book.data, index=index, count=3, answer_key=False,
                              regular=regular, bold=bold, text_width=_measure,
                              editorial=editorial_spec(EDITORIAL_HALLOWEEN_V1))
        # The editorial layout must still accept the canonical C2 placement.
        route = build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                         trusted_approvals_sha256=PIN)
        plan = build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                        trusted_approvals_sha256=PIN)
        from lafractale.illustrations.placement import placed_composition
        placed = placed_composition(layout, plan.anchor_for(act, demo_index=index),
                                    text_width=_measure)
        assert placed.safe.contains(placed.companion_slot)


# --- end-to-end build --------------------------------------------------------

def test_editorial_build_produces_manifest_and_no_helvetica(tmp_path):
    from lafractale.export.builder import build_demo
    book = _book()
    out = tmp_path / "c4"
    build_demo(book, out, illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
               pip_placement=PIP_PLACEMENT_HALLOWEEN_V2,
               editorial_profile=EDITORIAL_HALLOWEEN_V1,
               trusted_approvals_sha256=PIN)
    import json
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["editorial_profile"] == EDITORIAL_HALLOWEEN_V1
    import fitz
    doc = fitz.open(str(out / "interior.pdf"))
    for page in doc:
        font_names = {f[3] for f in page.get_fonts()}
        assert "Helvetica" not in font_names
    doc.close()


def test_editorial_profile_refuses_without_routing_and_placement(tmp_path):
    from lafractale.export.builder import build_demo
    book = _book()
    # Editorial without the C1 route / C2 placement must be refused.
    with pytest.raises(IllustrationError):
        build_demo(book, tmp_path / "c4-noroute",
                   editorial_profile=EDITORIAL_HALLOWEEN_V1,
                   trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        build_demo(book, tmp_path / "c4-noplacement",
                   illustration_routing=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                   editorial_profile=EDITORIAL_HALLOWEEN_V1,
                   trusted_approvals_sha256=PIN)


def test_c4_point_labels_never_intersect_the_closed_solution_path():
    """C4 fixes the inherited label/path collision without changing legacy output."""
    book = _book()
    act = next(activity for activity in _transformed(book) if activity.type == "connect_dots")
    regular, bold = fonts()
    layout = compose_page(act, book.data, index=2, count=3, answer_key=True,
                          regular=regular, bold=bold, text_width=_measure,
                          editorial=editorial_spec(EDITORIAL_HALLOWEEN_V1))
    board = layout.board
    x0, y0 = board.x + 67, board.y + 42
    x_span, y_span = board.width - 134, board.height - 110
    points = [(x0 + point["x"] * x_span, y0 + point["y"] * y_span)
              for point in act.geometry["points"]]
    segments = tuple(zip(points, points[1:] + points[:1]))
    labels = _labels_for_points(points, board, bold, avoid_segments=segments)
    for (tx, ty), point in zip(labels, act.geometry["points"], strict=True):
        width = _measure(str(point["n"]), bold, 11) + 6
        box = Rect(tx - width / 2, ty - 1, width, 13)
        assert not any(_segment_intersects_rect(start, end, box)
                       for start, end in segments), point["n"]
