"""B2-C1 fixed Pip routing policy and command-mode gates."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lafractale.activities.engine import generate, stable_seed
from lafractale.config.schema import load_book
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    ROUTING_HALLOWEEN_PIP_DEMO_V1,
    IllustrationRoute,
    PageArtworkBinding,
    build_illustration_route,
    resolve_illustration_mode,
    verify_illustration_route,
)
from lafractale.layout.pdf import write_pdf
from lafractale.story.plan import demo_specs


ROOT = Path(__file__).resolve().parents[1]
HALLOWEEN = ROOT / "books/halloween_2026/book.yaml"
CHRISTMAS = ROOT / "books/christmas_2026/book.yaml"
PIN = "93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61"


def test_route_policy_is_canonical_complete_ordered_and_immutable():
    route = build_illustration_route(
        load_book(HALLOWEEN),
        policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    assert isinstance(route, IllustrationRoute)
    assert route.policy_id == ROUTING_HALLOWEEN_PIP_DEMO_V1
    assert tuple((binding.demo_index, binding.activity_id, binding.source_page,
                  binding.activity_type, binding.asset_id) for binding in route.bindings) == (
        (1, "halloween_2026-p004", 4, "maze", "pip-reflexion-v2"),
        (2, "halloween_2026-p006", 6, "connect_dots", "pip-indication-v1"),
        (3, "halloween_2026-p020", 20, "match", "pip-encouragement-v1"),
    )
    assert len({binding.artwork.sha256 for binding in route.bindings}) == 3
    assert len({binding.artwork.pixels for binding in route.bindings}) == 3
    with pytest.raises((AttributeError, TypeError)):
        route.bindings += ()
    assert verify_illustration_route(
        load_book(HALLOWEEN), route, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    ) is None


@pytest.mark.parametrize(
    ("illustration_id", "routing", "pin"),
    [
        (None, None, None),
        ("pip-reflexion-v2", None, PIN),
        (None, ROUTING_HALLOWEEN_PIP_DEMO_V1, PIN),
    ],
)
def test_only_three_explicit_illustration_modes_are_accepted(illustration_id, routing, pin):
    assert resolve_illustration_mode(illustration_id, routing, pin) in {
        "placeholder", "legacy_illustration", "routed",
    }


@pytest.mark.parametrize(
    ("illustration_id", "routing", "pin"),
    [
        ("pip-reflexion-v2", ROUTING_HALLOWEEN_PIP_DEMO_V1, PIN),
        ("pip-reflexion-v2", None, None),
        (None, ROUTING_HALLOWEEN_PIP_DEMO_V1, None),
        (None, None, PIN),
        (None, "unknown-policy", PIN),
    ],
)
def test_partial_or_ambiguous_modes_fail_closed(illustration_id, routing, pin):
    with pytest.raises(IllustrationError):
        resolve_illustration_mode(illustration_id, routing, pin)


def test_christmas_and_forged_or_reordered_routes_are_refused():
    halloween = load_book(HALLOWEEN)
    route = build_illustration_route(
        halloween, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    with pytest.raises(IllustrationError):
        build_illustration_route(
            load_book(CHRISTMAS), policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
            trusted_approvals_sha256=PIN,
        )
    with pytest.raises(IllustrationError):
        verify_illustration_route(
            halloween, IllustrationRoute(route.policy_id, tuple(reversed(route.bindings))),
            policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN,
        )
    forged = replace(route.bindings[0], asset_id="pip-indication-v1")
    with pytest.raises(IllustrationError):
        verify_illustration_route(
            halloween, IllustrationRoute(route.policy_id, (forged, *route.bindings[1:])),
            policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1, trusted_approvals_sha256=PIN,
        )


def _canonical_activities(book):
    return [generate(spec, stable_seed(book.book_id, spec.id, 2026))
            for spec in demo_specs(book)]


def _write_routed(path, *, book, activities, route, answer_key):
    write_pdf(path, activities, book.data, answer_key=answer_key,
              illustration_route=route, approved_book=book,
              trusted_approvals_sha256=PIN)


@pytest.mark.parametrize("answer_key", [False, True])
@pytest.mark.parametrize("case", [
    "one",
    "two",
    "empty",
    "four",
    "reordered",
    "duplicated",
    "substituted",
    "falsified_metadata",
    "forged_route",
])
@pytest.mark.parametrize("preexisting", [False, True])
def test_routed_renderer_rejects_noncanonical_activity_sequence_before_creating_pdf(
    tmp_path, answer_key, case, preexisting,
):
    book = load_book(HALLOWEEN)
    activities = _canonical_activities(book)
    route = build_illustration_route(
        book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    if case == "one":
        activities = activities[:1]
    elif case == "two":
        activities = activities[:2]
    elif case == "empty":
        activities = []
    elif case == "four":
        activities = [*activities, activities[0]]
    elif case == "reordered":
        activities = [activities[1], activities[0], activities[2]]
    elif case == "duplicated":
        activities = [activities[0], activities[0], activities[2]]
    elif case == "substituted":
        activities[1] = replace(activities[1], id="halloween_2026-p999")
    elif case == "falsified_metadata":
        activities[1] = replace(activities[1], vocabulary=("ghost",))
    elif case == "forged_route":
        route = IllustrationRoute(route.policy_id, tuple(reversed(route.bindings)))
    else:
        raise AssertionError(case)
    path = tmp_path / f"{case}-{answer_key}-{preexisting}.pdf"
    if preexisting:
        path.write_bytes(b"PRESERVE")
    with pytest.raises((IllustrationError, ValueError)):
        _write_routed(path, book=book, activities=activities, route=route, answer_key=answer_key)
    assert path.read_bytes() == b"PRESERVE" if preexisting else not path.exists()


@pytest.mark.parametrize("answer_key", [False, True])
def test_routed_renderer_accepts_only_complete_canonical_sequence(tmp_path, answer_key):
    book = load_book(HALLOWEEN)
    route = build_illustration_route(
        book, policy_id=ROUTING_HALLOWEEN_PIP_DEMO_V1,
        trusted_approvals_sha256=PIN,
    )
    path = tmp_path / f"canonical-{answer_key}.pdf"
    _write_routed(path, book=book, activities=_canonical_activities(book),
                  route=route, answer_key=answer_key)
    assert path.is_file() and path.stat().st_size > 0
