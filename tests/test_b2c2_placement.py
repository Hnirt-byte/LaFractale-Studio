"""B2-C2 V2 placement policy: canonical table, immutability and `intro_right` geometry.

Policy V1 (`scene_right` / `lower_left` / `lower_right`, lower band) is replaced by
the single-anchor V2 policy: see `docs/SECURITY_CONTRACT_B2C2_ADDENDUM_B_v1.1.md`.
Expectations that described V1 are adapted here; no test case is removed.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.illustrations.placement import (
    H_INSET_PT,
    INSET_RIGHT_PT,
    INSET_TOP_PT,
    INTRO_RIGHT,
    MIN_CLEARANCE_PT,
    PIP_PLACEMENT_HALLOWEEN_V1,
    PIP_PLACEMENT_HALLOWEEN_V2,
    PIP_SIDE_PT,
    PipPlacementBinding,
    PipPlacementPlan,
    V_INSET_PT,
    build_pip_placement_plan,
    placed_composition,
    placed_image_box,
    placed_slot,
    resolve_pip_placement_mode,
    verify_pip_placement_plan,
)
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    build_illustration_route,
)
from lafractale.layout.composition import Rect, compose_page
from lafractale.layout.pdf import _measure, fonts
from lafractale.story.plan import demo_specs


ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
# V2: all three canonical pages share the single `intro_right` anchor.
CANONICAL_ANCHORS = (
    (1, "halloween_2026-p004", 4, "maze", INTRO_RIGHT),
    (2, "halloween_2026-p006", 6, "connect_dots", INTRO_RIGHT),
    (3, "halloween_2026-p020", 20, "match", INTRO_RIGHT),
)
# Anchors refused by the V2 policy (legacy V1 geometry and any other name).
REFUSED_ANCHORS = ("scene_right", "lower_left", "lower_right", "middle", "INTRO_RIGHT")


def _book():
    return load_book(HALLOWEEN)


def _route(book):
    return build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                    trusted_approvals_sha256=PIN)


def _plan(book=None, route=None):
    book = book or _book()
    route = route or _route(book)
    return build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                    trusted_approvals_sha256=PIN)


def _layouts(book, answer_key=False):
    specs = demo_specs(book)
    activities = [generate(spec, stable_seed(book.book_id, spec.id, 2026)) for spec in specs]
    regular, bold = fonts()
    return activities, [compose_page(activity, book.data, index=index, count=len(activities),
                                     answer_key=answer_key, regular=regular, bold=bold,
                                     text_width=_measure)
                        for index, activity in enumerate(activities, 1)]


def test_placement_policy_is_canonical_complete_ordered_and_immutable():
    plan = _plan()
    assert isinstance(plan, PipPlacementPlan)
    assert plan.policy_id == PIP_PLACEMENT_HALLOWEEN_V2
    assert tuple((binding.demo_index, binding.activity_id, binding.source_page,
                  binding.activity_type, binding.anchor) for binding in plan.bindings) == CANONICAL_ANCHORS
    with pytest.raises((AttributeError, TypeError)):
        plan.bindings += ()  # type: ignore[misc]
    binding = plan.bindings[0]
    assert isinstance(binding, PipPlacementBinding)
    with pytest.raises((AttributeError, TypeError)):
        binding.anchor = "lower_left"  # type: ignore[misc]
    assert plan.manifest_entry() == {
        "policy_id": PIP_PLACEMENT_HALLOWEEN_V2,
        "bindings": [
            {"demo_index": 1, "activity_id": "halloween_2026-p004", "source_page": 4,
             "activity_type": "maze", "anchor": INTRO_RIGHT},
            {"demo_index": 2, "activity_id": "halloween_2026-p006", "source_page": 6,
             "activity_type": "connect_dots", "anchor": INTRO_RIGHT},
            {"demo_index": 3, "activity_id": "halloween_2026-p020", "source_page": 20,
             "activity_type": "match", "anchor": INTRO_RIGHT},
        ],
    }


@pytest.mark.parametrize("value,expected", [
    (None, "none"),
    (PIP_PLACEMENT_HALLOWEEN_V2, PIP_PLACEMENT_HALLOWEEN_V2),
])
def test_explicit_placement_opt_in_is_resolved(value, expected):
    assert resolve_pip_placement_mode(value) == expected


@pytest.mark.parametrize("value", ["", "unknown", PIP_PLACEMENT_HALLOWEEN_V1, "INTRO_RIGHT",
                                   "halloween-pip-demo-v1", "pip-placement"])
def test_unknown_placement_policy_is_refused(value):
    with pytest.raises(IllustrationError):
        resolve_pip_placement_mode(value)


@pytest.mark.parametrize("value", ["", "unknown", PIP_PLACEMENT_HALLOWEEN_V1,
                                   "halloween-pip-placement-v3"])
def test_legacy_and_unknown_policies_never_build_a_plan(value):
    """V1 is replaced: it must be refused by the plan builder, not silently accepted."""
    book = _book()
    route = _route(book)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id=value,
                                 trusted_approvals_sha256=PIN)


def test_plan_requires_the_canonical_route_and_pin_and_halloween_book():
    book, christmas = _book(), load_book(CHRISTMAS)
    route = _route(book)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id="unknown-policy",
                                 trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                 trusted_approvals_sha256=None)  # type: ignore[arg-type]
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                 trusted_approvals_sha256="a" * 63)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, "not-a-route",  # type: ignore[arg-type]
                                 policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                 trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        build_illustration_route(christmas, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                 trusted_approvals_sha256=PIN)
    # A route bound to another book can never satisfy the placement plan.
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(christmas, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                 trusted_approvals_sha256=PIN)


def test_forged_or_reordered_plan_is_refused_by_strict_equality():
    book = _book()
    route = _route(book)
    plan = _plan(book, route)
    assert verify_pip_placement_plan(book, route, plan, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                     trusted_approvals_sha256=PIN) is None
    reordered = PipPlacementPlan(plan.policy_id, tuple(reversed(plan.bindings)))
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, reordered, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                  trusted_approvals_sha256=PIN)
    # A legacy V1 anchor can never be smuggled into a verified plan.
    for forged_anchor in ("lower_left", "lower_right", "scene_right"):
        forged = replace(plan.bindings[1], anchor=forged_anchor)
        with pytest.raises(IllustrationError):
            verify_pip_placement_plan(
                book, route, replace(plan, bindings=(plan.bindings[0], forged, plan.bindings[2])),
                policy_id=PIP_PLACEMENT_HALLOWEEN_V2, trusted_approvals_sha256=PIN)
    partial = PipPlacementPlan(plan.policy_id, plan.bindings[:2])
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, partial, policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                  trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, ("not", "a", "plan"),  # type: ignore[arg-type]
                                  policy_id=PIP_PLACEMENT_HALLOWEEN_V2,
                                  trusted_approvals_sha256=PIN)


def test_anchor_for_rejects_substituted_activity_identity():
    book = _book()
    plan = _plan(book)
    activities, _ = _layouts(book)
    assert plan.anchor_for(activities[1], demo_index=2) == INTRO_RIGHT
    with pytest.raises(IllustrationError):
        plan.anchor_for(activities[0], demo_index=2)
    with pytest.raises(IllustrationError):
        plan.anchor_for(activities[1], demo_index=4)
    with pytest.raises(IllustrationError):
        plan.anchor_for(activities[1], demo_index="2")  # type: ignore[arg-type]
    with pytest.raises(IllustrationError):
        plan.anchor_for(replace(activities[1], page=99), demo_index=2)
    with pytest.raises(IllustrationError):
        plan.anchor_for(replace(activities[1], type="maze"), demo_index=2)


@pytest.mark.parametrize("answer_key", [False, True])
def test_placed_geometry_matches_the_contract_for_all_six_compositions(answer_key):
    book = _book()
    _, layouts = _layouts(book, answer_key)
    for index, layout in enumerate(layouts, 1):
        anchor = CANONICAL_ANCHORS[index - 1][4]
        image = placed_image_box(layout, anchor)
        placed = placed_composition(layout, anchor, text_width=_measure)
        slot = placed.companion_slot
        # V2 image box: 48 pt, right edge on the header badge axis, top 4 pt under the header.
        assert image.width == image.height == PIP_SIDE_PT
        assert layout.header.right - image.right == pytest.approx(INSET_RIGHT_PT)
        assert layout.header.y - image.top == pytest.approx(INSET_TOP_PT)
        assert (image.x, image.y) == pytest.approx((495.98, 615.98), abs=0.01)
        # Technical slot: the visible image expanded by the inverted C1 insets.
        assert (slot.x, slot.y) == pytest.approx((image.x - H_INSET_PT, image.y - V_INSET_PT))
        assert slot.width == pytest.approx(PIP_SIDE_PT + 2 * H_INSET_PT)
        assert slot.height == pytest.approx(PIP_SIDE_PT + 2 * V_INSET_PT)
        assert (slot.x, slot.y, slot.width, slot.height) == pytest.approx(
            (491.98, 612.98, 56.0, 54.0), abs=0.01)
        # V2 replaces the C1 slot everywhere, including the first page.
        assert slot != layout.companion_slot
        # Clearances are measured on the visible image, not on the technical slot.
        assert layout.header.y - image.top >= MIN_CLEARANCE_PT - 1e-9
        assert image.y - layout.prompt_fr.region.top >= MIN_CLEARANCE_PT - 1e-9
        assert layout.header.y - image.top == pytest.approx(4.0, abs=0.01)
        assert image.y - layout.prompt_fr.region.top == pytest.approx(4.0, abs=0.01)
        # The technical slot keeps 1 pt with both neighbours (documented, not contractual).
        assert layout.header.y - slot.top == pytest.approx(1.0, abs=0.01)
        assert slot.y - layout.prompt_fr.region.top == pytest.approx(1.0, abs=0.01)
        # Local band tolerance of the addendum §4.2: 1 pt below and 6 pt above `scene`.
        band = placed.regions()["scene"]
        assert image.y - band.y == pytest.approx(-1.0, abs=0.01)
        assert image.top - band.top == pytest.approx(6.0, abs=0.01)
        assert placed.safe.contains(slot)
        for name, region in placed.regions().items():
            if name != "companion_slot":
                assert not region.overlaps(slot), name
                assert not region.overlaps(image), name


@pytest.mark.parametrize("legacy_anchor", ["lower_left", "lower_right"])
def test_intro_right_slot_does_not_depend_on_the_low_band(legacy_anchor):
    """V1 fitted the slot in the footer/board band; V2 must ignore that band entirely.

    The two V1 band anchors are still exercised, as refused identifiers.
    """
    book = _book()
    _, layouts = _layouts(book)
    layout = layouts[1]
    canonical = placed_slot(layout, INTRO_RIGHT)
    cramped = replace(layout, board=Rect(layout.board.x, layout.footer.top + 2.0,
                                         layout.board.width, layout.board.height))
    assert placed_slot(cramped, INTRO_RIGHT) == canonical
    tall_footer = replace(layout, footer=Rect(layout.footer.x, layout.footer.y,
                                             layout.footer.width, 300.0))
    assert placed_slot(tall_footer, INTRO_RIGHT) == canonical
    with pytest.raises(IllustrationError):
        placed_slot(layout, legacy_anchor)
    for anchor_name in REFUSED_ANCHORS:
        with pytest.raises(IllustrationError):
            placed_slot(layout, anchor_name)


def test_placed_slot_refuses_unknown_anchor_and_non_finite_band():
    book = _book()
    _, layouts = _layouts(book)
    with pytest.raises(IllustrationError):
        placed_slot(layouts[1], "middle")
    broken = replace(layouts[1], header=Rect(layouts[1].header.x, float("nan"),
                                             layouts[1].header.width, layouts[1].header.height))
    with pytest.raises(IllustrationError):
        placed_slot(broken, INTRO_RIGHT)
    broken_right = replace(layouts[1], header=Rect(layouts[1].header.x, layouts[1].header.y,
                                                   float("inf"), layouts[1].header.height))
    with pytest.raises(IllustrationError):
        placed_image_box(broken_right, INTRO_RIGHT)


def test_placed_composition_refuses_a_slot_outside_the_safe_margin():
    book = _book()
    _, layouts = _layouts(book)
    layout = layouts[2]
    # A header running past the safe area pushes the V2 slot out of the safe margin.
    widened = replace(layout, header=Rect(layout.header.x, layout.header.y, 600.0,
                                          layout.header.height))
    with pytest.raises(IllustrationError):
        placed_composition(widened, INTRO_RIGHT, text_width=_measure)


@pytest.mark.parametrize("delta,expected", [
    (1.0, "en-tête"),
    (-1.0, "consigne"),
])
def test_placed_composition_refuses_a_lost_image_clearance(monkeypatch, delta, expected):
    """A 1 pt error on the visible image must be refused, up or down."""
    from lafractale.illustrations import placement as placement_module

    book = _book()
    _, layouts = _layouts(book)
    layout = layouts[1]
    original_image = placement_module.placed_image_box

    def shifted_image(target_layout, anchor):
        image = original_image(target_layout, anchor)
        return type(image)(image.x, image.y + delta, image.width, image.height)

    def shifted_slot(target_layout, anchor):
        image = shifted_image(target_layout, anchor)
        return Rect(image.x - H_INSET_PT, image.y - V_INSET_PT,
                    image.width + 2 * H_INSET_PT, image.height + 2 * V_INSET_PT)

    monkeypatch.setattr(placement_module, "placed_image_box", shifted_image)
    monkeypatch.setattr(placement_module, "placed_slot", shifted_slot)
    with pytest.raises(IllustrationError) as excinfo:
        placed_composition(layout, INTRO_RIGHT, text_width=_measure)
    assert expected in str(excinfo.value)


def test_placed_composition_never_mutates_the_source_layout():
    book = _book()
    _, layouts = _layouts(book)
    before = layouts[1].companion_slot
    placed_composition(layouts[1], INTRO_RIGHT, text_width=_measure)
    assert layouts[1].companion_slot == before


def test_no_api_accepts_a_rectangle_or_free_coordinates():
    """The V2 surface is a policy name; geometry is never caller-supplied."""
    import inspect

    from lafractale.layout import pdf

    signature = inspect.signature(pdf.write_pdf)
    assert "pip_placement" in signature.parameters
    for forbidden in ("placement", "placement_rect", "pip_rect", "companion_slot", "x", "y"):
        assert forbidden not in signature.parameters
    plan_signature = inspect.signature(build_pip_placement_plan)
    assert "rect" not in str(plan_signature).lower()
    assert "anchor" not in plan_signature.parameters
    for helper in (placed_image_box, placed_slot, placed_composition):
        parameters = set(inspect.signature(helper).parameters)
        assert parameters <= {"layout", "anchor", "text_width"}, helper
