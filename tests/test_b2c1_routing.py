"""B2-C1 fixed Pip routing policy and command-mode gates."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

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
