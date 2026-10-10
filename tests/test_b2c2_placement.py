"""B2-C2 placement policy: canonical table, immutability and geometry rules."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.illustrations.placement import (
    LOWER_LEFT,
    LOWER_RIGHT,
    MIN_BAND_SLACK_PT,
    MIN_CLEARANCE_PT,
    PIP_PLACEMENT_HALLOWEEN_V1,
    PipPlacementBinding,
    PipPlacementPlan,
    SCENE_RIGHT,
    build_pip_placement_plan,
    placed_composition,
    placed_slot,
    resolve_pip_placement_mode,
    verify_pip_placement_plan,
)
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    IllustrationRoute,
    build_illustration_route,
)
from lafractale.layout.composition import Rect, compose_page
from lafractale.layout.pdf import _measure, fonts
from lafractale.story.plan import demo_specs


ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"
CANONICAL_ANCHORS = (
    (1, "halloween_2026-p004", 4, "maze", SCENE_RIGHT),
    (2, "halloween_2026-p006", 6, "connect_dots", LOWER_RIGHT),
    (3, "halloween_2026-p020", 20, "match", LOWER_LEFT),
)


def _book():
    return load_book(HALLOWEEN)


def _route(book):
    return build_illustration_route(book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                    trusted_approvals_sha256=PIN)


def _plan(book=None, route=None):
    book = book or _book()
    route = route or _route(book)
    return build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
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
    assert plan.policy_id == PIP_PLACEMENT_HALLOWEEN_V1
    assert tuple((binding.demo_index, binding.activity_id, binding.source_page,
                  binding.activity_type, binding.anchor) for binding in plan.bindings) == CANONICAL_ANCHORS
    with pytest.raises((AttributeError, TypeError)):
        plan.bindings += ()  # type: ignore[misc]
    binding = plan.bindings[0]
    assert isinstance(binding, PipPlacementBinding)
    with pytest.raises((AttributeError, TypeError)):
        binding.anchor = LOWER_LEFT  # type: ignore[misc]
    assert plan.manifest_entry() == {
        "policy_id": PIP_PLACEMENT_HALLOWEEN_V1,
        "bindings": [
            {"demo_index": 1, "activity_id": "halloween_2026-p004", "source_page": 4,
             "activity_type": "maze", "anchor": SCENE_RIGHT},
            {"demo_index": 2, "activity_id": "halloween_2026-p006", "source_page": 6,
             "activity_type": "connect_dots", "anchor": LOWER_RIGHT},
            {"demo_index": 3, "activity_id": "halloween_2026-p020", "source_page": 20,
             "activity_type": "match", "anchor": LOWER_LEFT},
        ],
    }


@pytest.mark.parametrize("value,expected", [
    (None, "none"),
    (PIP_PLACEMENT_HALLOWEEN_V1, PIP_PLACEMENT_HALLOWEEN_V1),
])
def test_explicit_placement_opt_in_is_resolved(value, expected):
    assert resolve_pip_placement_mode(value) == expected


@pytest.mark.parametrize("value", ["", "unknown", "halloween-pip-placement-v2", "SCENE_RIGHT",
                                   "halloween-pip-demo-v1", "pip-placement"])
def test_unknown_placement_policy_is_refused(value):
    with pytest.raises(IllustrationError):
        resolve_pip_placement_mode(value)


def test_plan_requires_the_canonical_route_and_pin_and_halloween_book():
    book, christmas = _book(), load_book(CHRISTMAS)
    route = _route(book)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id="unknown-policy",
                                 trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                 trusted_approvals_sha256=None)  # type: ignore[arg-type]
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                 trusted_approvals_sha256="a" * 63)
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(book, "not-a-route",  # type: ignore[arg-type]
                                 policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                 trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        build_illustration_route(christmas, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
                                 trusted_approvals_sha256=PIN)
    # A route bound to another book can never satisfy the placement plan.
    with pytest.raises(IllustrationError):
        build_pip_placement_plan(christmas, route, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                 trusted_approvals_sha256=PIN)


def test_forged_or_reordered_plan_is_refused_by_strict_equality():
    book = _book()
    route = _route(book)
    plan = _plan(book, route)
    assert verify_pip_placement_plan(book, route, plan, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                     trusted_approvals_sha256=PIN) is None
    reordered = PipPlacementPlan(plan.policy_id, tuple(reversed(plan.bindings)))
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, reordered, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                  trusted_approvals_sha256=PIN)
    forged = replace(plan.bindings[1], anchor=LOWER_LEFT)
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(
            book, route, replace(plan, bindings=(plan.bindings[0], forged, plan.bindings[2])),
            policy_id=PIP_PLACEMENT_HALLOWEEN_V1, trusted_approvals_sha256=PIN)
    partial = PipPlacementPlan(plan.policy_id, plan.bindings[:2])
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, partial, policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                  trusted_approvals_sha256=PIN)
    with pytest.raises(IllustrationError):
        verify_pip_placement_plan(book, route, ("not", "a", "plan"),  # type: ignore[arg-type]
                                  policy_id=PIP_PLACEMENT_HALLOWEEN_V1,
                                  trusted_approvals_sha256=PIN)


def test_anchor_for_rejects_substituted_activity_identity():
    book = _book()
    plan = _plan(book)
    activities, _ = _layouts(book)
    assert plan.anchor_for(activities[1], demo_index=2) == LOWER_RIGHT
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
        placed = placed_composition(layout, anchor, text_width=_measure)
        slot = placed.companion_slot
        if anchor == SCENE_RIGHT:
            assert slot == layout.companion_slot
        else:
            assert slot.width == layout.companion_slot.width
            assert slot.height == layout.companion_slot.height
            gap = (layout.board.y - layout.footer.top - slot.height) / 2
            assert gap == pytest.approx(5.5, abs=0.01) and gap >= MIN_CLEARANCE_PT
            assert slot.y - layout.footer.top >= MIN_CLEARANCE_PT
            assert layout.board.y - slot.top >= MIN_CLEARANCE_PT
            if anchor == LOWER_LEFT:
                assert slot.x - layout.board.x == pytest.approx(MIN_CLEARANCE_PT)
            else:
                assert layout.board.right - slot.right == pytest.approx(MIN_CLEARANCE_PT)
        assert placed.safe.contains(slot)
        for name, region in placed.regions().items():
            if name != "companion_slot":
                assert not region.overlaps(slot)


@pytest.mark.parametrize("anchor", [LOWER_LEFT, LOWER_RIGHT])
def test_placed_slot_refuses_a_band_too_small(anchor):
    book = _book()
    _, layouts = _layouts(book)
    layout = layouts[1]
    cramped = replace(layout, board=Rect(layout.board.x, layout.footer.top + layout.companion_slot.height + 2,
                                         layout.board.width, layout.board.height))
    with pytest.raises(IllustrationError):
        placed_slot(cramped, anchor)
    exact = replace(layout, board=Rect(layout.board.x,
                                       layout.footer.top + layout.companion_slot.height + MIN_BAND_SLACK_PT - 0.5,
                                       layout.board.width, layout.board.height))
    with pytest.raises(IllustrationError):
        placed_slot(exact, anchor)


def test_placed_slot_refuses_unknown_anchor_and_non_finite_band():
    book = _book()
    _, layouts = _layouts(book)
    with pytest.raises(IllustrationError):
        placed_slot(layouts[1], "middle")
    broken = replace(layouts[1], board=Rect(layouts[1].board.x, float("nan"),
                                            layouts[1].board.width, layouts[1].board.height))
    with pytest.raises(IllustrationError):
        placed_slot(broken, LOWER_RIGHT)


def test_placed_composition_refuses_a_slot_outside_the_safe_margin():
    book = _book()
    _, layouts = _layouts(book)
    layout = layouts[2]
    shifted = replace(layout, footer=Rect(layout.footer.x, layout.footer.y, layout.footer.width, 300.0))
    with pytest.raises(IllustrationError):
        placed_composition(shifted, LOWER_LEFT, text_width=_measure)


def test_placed_composition_never_mutates_the_source_layout():
    book = _book()
    _, layouts = _layouts(book)
    before = layouts[1].companion_slot
    placed_composition(layouts[1], LOWER_RIGHT, text_width=_measure)
    assert layouts[1].companion_slot == before


def test_no_api_accepts_a_rectangle_or_free_coordinates():
    """The C2 surface is a policy name; geometry is never caller-supplied."""
    import inspect

    from lafractale.layout import pdf

    signature = inspect.signature(pdf.write_pdf)
    assert "pip_placement" in signature.parameters
    for forbidden in ("placement", "placement_rect", "pip_rect", "companion_slot", "x", "y"):
        assert forbidden not in signature.parameters
    plan_signature = inspect.signature(build_pip_placement_plan)
    assert "rect" not in str(plan_signature).lower()
    assert "anchor" not in plan_signature.parameters
