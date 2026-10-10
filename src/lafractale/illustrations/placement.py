"""Closed, source-backed B2-C2 Pip placement: opt-in, bound to the C1 route.

The placement is a static table frozen in audited code and tied to the canonical
Halloween C1 illustration route.  It is never read from YAML, JSON, a manifest, a
PDF, a caller mapping or an environment variable, and no rectangle, offset or
coordinate is exposed as an API: a caller may only name the policy, and the
canonical plan is recomputed from the verified Book, ``demo_specs``, the C1 route
and the external approval pin.

Placement is a pure function of the trusted C1 composition ``L0``
(``composition.compose_page``): ``scene_right`` reuses the C1 slot unchanged,
while ``lower_left``/``lower_right`` derive a slot in the free band between the
board and the footer.  The historical ``artwork=`` path and the C1 routed path
without this option are untouched.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
import re

from lafractale.activities.models import Activity
from lafractale.config.companions import verify_companion_text
from lafractale.config.schema import Book, verify_book_snapshot
from lafractale.illustrations.registry import IllustrationError
from lafractale.illustrations.routing import (
    IllustrationRoute,
    build_illustration_route,
    verify_illustration_route,
)
from lafractale.layout.composition import (
    PageComposition,
    Rect,
    TextWidth,
    validate_composition,
)
from lafractale.story.plan import demo_specs


PIP_PLACEMENT_HALLOWEEN_V1 = "halloween-pip-placement-v1"

SCENE_RIGHT = "scene_right"
LOWER_LEFT = "lower_left"
LOWER_RIGHT = "lower_right"
_ANCHORS = frozenset({SCENE_RIGHT, LOWER_LEFT, LOWER_RIGHT})

# Minimum separation demanded by the contract, in PDF points.
MIN_CLEARANCE_PT = 4.0
# The free band must exceed the slot height by this margin before a slot fits.
MIN_BAND_SLACK_PT = 8.0

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# (demo_index, activity_id, source_page, activity_type, anchor)
_CANONICAL_HALLOWEEN_PIP_PLACEMENT_V1 = (
    (1, "halloween_2026-p004", 4, "maze", SCENE_RIGHT),
    (2, "halloween_2026-p006", 6, "connect_dots", LOWER_RIGHT),
    (3, "halloween_2026-p020", 20, "match", LOWER_LEFT),
)


@dataclass(frozen=True)
class PipPlacementBinding:
    demo_index: int
    activity_id: str
    source_page: int
    activity_type: str
    anchor: str

    def manifest_entry(self) -> dict:
        return {
            "demo_index": self.demo_index,
            "activity_id": self.activity_id,
            "source_page": self.source_page,
            "activity_type": self.activity_type,
            "anchor": self.anchor,
        }


@dataclass(frozen=True)
class PipPlacementPlan:
    policy_id: str
    bindings: tuple[PipPlacementBinding, ...]

    def manifest_entry(self) -> dict:
        return {"policy_id": self.policy_id,
                "bindings": [binding.manifest_entry() for binding in self.bindings]}

    def anchor_for(self, activity: Activity, *, demo_index: int) -> str:
        """Return the canonical anchor for this activity, or fail closed."""
        if type(demo_index) is not int or not 1 <= demo_index <= len(self.bindings):
            raise IllustrationError("Index de démonstration du placement Pip invalide")
        binding = self.bindings[demo_index - 1]
        if (binding.demo_index != demo_index or binding.activity_id != activity.id
                or binding.source_page != activity.page
                or binding.activity_type != activity.type):
            raise IllustrationError("Liaison activité/placement Pip non conforme")
        if binding.anchor not in _ANCHORS:
            raise IllustrationError("Ancrage de placement Pip non autorisé")
        return binding.anchor


def _valid_pin(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def resolve_pip_placement_mode(pip_placement: str | None) -> str:
    """Resolve the explicit opt-in before any staging directory exists."""
    if pip_placement is None:
        return "none"
    if pip_placement == PIP_PLACEMENT_HALLOWEEN_V1:
        return PIP_PLACEMENT_HALLOWEEN_V1
    raise IllustrationError("Politique de placement Pip inconnue ou non autorisée")


def placed_slot(layout: PageComposition, anchor: str) -> Rect:
    """Derive the C2 slot from a trusted C1 composition; never from caller data."""
    if anchor not in _ANCHORS:
        raise IllustrationError("Ancrage de placement Pip inconnu")
    if anchor == SCENE_RIGHT:
        return layout.companion_slot
    gap_bottom = layout.footer.top
    gap_top = layout.board.y
    gap_height = gap_top - gap_bottom
    slot_width = layout.companion_slot.width
    slot_height = layout.companion_slot.height
    values = (gap_bottom, gap_top, gap_height, slot_width, slot_height)
    if (any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
            for value in values)
            or slot_width <= 0 or slot_height <= 0):
        raise IllustrationError("Bande de placement Pip non finie ou vide")
    if gap_height < slot_height + MIN_BAND_SLACK_PT:
        raise IllustrationError("Bande inférieure insuffisante pour le placement Pip")
    y = gap_bottom + (gap_height - slot_height) / 2
    if anchor == LOWER_LEFT:
        x = layout.board.x + MIN_CLEARANCE_PT
    else:
        x = layout.board.right - slot_width - MIN_CLEARANCE_PT
    return Rect(x, y, slot_width, slot_height)


def placed_composition(layout: PageComposition, anchor: str, *, text_width: TextWidth) -> PageComposition:
    """Return an immutable copy of ``layout`` whose only change is the slot.

    Refuses any slot outside the safe margin, any clearance below the contract
    minimum and any overlap with another named region, then re-runs the full
    composition validation.  ``layout`` itself is never mutated.
    """
    slot = placed_slot(layout, anchor)
    placed = replace(layout, companion_slot=slot)
    if not placed.safe.contains(slot):
        raise IllustrationError("Slot Pip de placement hors marge de sécurité")
    if anchor != SCENE_RIGHT:
        if slot.y - layout.footer.top < MIN_CLEARANCE_PT - 1e-9:
            raise IllustrationError("Séparation Pip/pied de page insuffisante")
        if layout.board.y - slot.top < MIN_CLEARANCE_PT - 1e-9:
            raise IllustrationError("Séparation Pip/plateau insuffisante")
        if anchor == LOWER_LEFT:
            if slot.x - layout.board.x < MIN_CLEARANCE_PT - 1e-9:
                raise IllustrationError("Retrait latéral gauche du placement Pip insuffisant")
        elif layout.board.right - slot.right < MIN_CLEARANCE_PT - 1e-9:
            raise IllustrationError("Retrait latéral droit du placement Pip insuffisant")
    for name, region in placed.regions().items():
        if name == "companion_slot":
            continue
        if region.overlaps(slot):
            raise IllustrationError(f"Slot Pip de placement en collision avec {name}")
    validate_composition(placed, text_width=text_width)
    return placed


def _verified_specs(book: Book):
    verify_book_snapshot(book)
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    return demo_specs(book)


def build_pip_placement_plan(book: Book, route: IllustrationRoute, *, policy_id: str,
                             trusted_approvals_sha256: str) -> PipPlacementPlan:
    """Construct the sole permitted placement plan from trusted sources."""
    if policy_id != PIP_PLACEMENT_HALLOWEEN_V1:
        raise IllustrationError("Politique de placement Pip inconnue")
    if type(route) is not IllustrationRoute:
        raise IllustrationError("Objet de routage non canonique")
    if not _valid_pin(trusted_approvals_sha256):
        raise IllustrationError("Empreinte externe du registre d'approbation obligatoire")
    if book.book_id != "halloween_2026":
        raise IllustrationError("Placement Pip interdit hors Halloween")
    verify_illustration_route(book, route, policy_id=route.policy_id,
                              trusted_approvals_sha256=trusted_approvals_sha256)
    specs = _verified_specs(book)
    if len(specs) != len(_CANONICAL_HALLOWEEN_PIP_PLACEMENT_V1) or len(route.bindings) != len(specs):
        raise IllustrationError("Couverture de placement routée incomplète ou supplémentaire")
    bindings: list[PipPlacementBinding] = []
    for spec, route_binding, expected in zip(
            specs, route.bindings, _CANONICAL_HALLOWEEN_PIP_PLACEMENT_V1, strict=True):
        demo_index, activity_id, source_page, activity_type, anchor = expected
        if (spec.id, spec.page, spec.type) != (activity_id, source_page, activity_type):
            raise IllustrationError("Identité d'activité incompatible avec la politique C2")
        if (route_binding.demo_index, route_binding.activity_id, route_binding.source_page,
                route_binding.activity_type) != (demo_index, activity_id, source_page, activity_type):
            raise IllustrationError("Liaison de route incompatible avec la politique C2")
        bindings.append(PipPlacementBinding(demo_index, activity_id, source_page,
                                            activity_type, anchor))
    if len({binding.demo_index for binding in bindings}) != len(bindings):
        raise IllustrationError("Politique de placement duplique un index de démonstration")
    if len({binding.anchor for binding in bindings}) != len(bindings):
        raise IllustrationError("Politique de placement duplique un ancrage")
    return PipPlacementPlan(policy_id, tuple(bindings))


def verify_pip_placement_plan(book: Book, route: IllustrationRoute, plan: PipPlacementPlan, *,
                              policy_id: str, trusted_approvals_sha256: str) -> None:
    """Rebuild and compare the whole plan; reject forged or flexible plans."""
    if type(plan) is not PipPlacementPlan:
        raise IllustrationError("Objet de placement Pip non canonique")
    expected = build_pip_placement_plan(
        book, route, policy_id=policy_id, trusted_approvals_sha256=trusted_approvals_sha256,
    )
    if plan != expected:
        raise IllustrationError("Placement Pip falsifié ou non canonique")
