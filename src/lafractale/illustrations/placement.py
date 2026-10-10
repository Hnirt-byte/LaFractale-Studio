"""Closed, source-backed B2-C2 Pip placement V2 (`intro_right`): opt-in, bound to the C1 route.

The placement is a static table frozen in audited code and tied to the canonical
Halloween C1 illustration route.  It is never read from YAML, JSON, a manifest, a
PDF, a caller mapping or an environment variable, and no rectangle, offset or
coordinate is exposed as an API: a caller may only name the policy, and the
canonical plan is recomputed from the verified Book, ``demo_specs``, the C1 route
and the external approval pin.

Placement is a pure function of the trusted C1 composition ``L0``
(``composition.compose_page``): the three canonical demo pages place Pip in the
upper-right introduction row (``intro_right``, 48 pt side) derived from the header
badge axis.  The historical ``artwork=`` path and the C1 routed path without this
option are untouched.

V2 contract: ``docs/SECURITY_CONTRACT_B2C2_ADDENDUM_B_v1.1.md``.  Any other
placement (V1 ``halloween-pip-placement-v1``, caller-supplied rectangle or
coordinate, or anchor) is refused.
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


PIP_PLACEMENT_HALLOWEEN_V2 = "halloween-pip-placement-v2"
# The V1 policy is kept only as a refused identifier: it must never resolve.
PIP_PLACEMENT_HALLOWEEN_V1 = "halloween-pip-placement-v1"

# V2 geometry: a single authorised anchor.
INTRO_RIGHT = "intro_right"
_ANCHORS = frozenset({INTRO_RIGHT})

# Minimum separation demanded by the contract, in PDF points.
MIN_CLEARANCE_PT = 4.0
# Visible Pip image side, in PDF points (48 pt = 16.93 mm).
PIP_SIDE_PT = 48.0
# Visible image right edge = L0.header.right - 16 pt (header badge axis).
INSET_RIGHT_PT = 16.0
# Visible image top edge = L0.header.y - 4 pt (minimum clearance to the header).
INSET_TOP_PT = 4.0
# C1 technical insets, inverted to rebuild the slot around the 48 pt image.
H_INSET_PT = 4.0
V_INSET_PT = 3.0

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

# (demo_index, activity_id, source_page, activity_type, anchor)
_CANONICAL_HALLOWEEN_PIP_PLACEMENT_V2 = (
    (1, "halloween_2026-p004", 4, "maze", INTRO_RIGHT),
    (2, "halloween_2026-p006", 6, "connect_dots", INTRO_RIGHT),
    (3, "halloween_2026-p020", 20, "match", INTRO_RIGHT),
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
    if pip_placement == PIP_PLACEMENT_HALLOWEEN_V2:
        return PIP_PLACEMENT_HALLOWEEN_V2
    if pip_placement == PIP_PLACEMENT_HALLOWEEN_V1:
        raise IllustrationError("Politique de placement Pip V1 remplacée et refusée")
    raise IllustrationError("Politique de placement Pip inconnue ou non autorisée")


def placed_image_box(layout: PageComposition, anchor: str) -> Rect:
    """Derive the visible V2 image box from the trusted C1 composition."""
    if anchor not in _ANCHORS:
        raise IllustrationError("Ancrage de placement Pip inconnu")
    values = (layout.header.right, layout.header.y, PIP_SIDE_PT, INSET_RIGHT_PT, INSET_TOP_PT)
    if (any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
            for value in values)
            or PIP_SIDE_PT <= 0 or INSET_RIGHT_PT < 0 or INSET_TOP_PT < 0):
        raise IllustrationError("Régions de placement Pip non finies ou invalides")
    return Rect(layout.header.right - INSET_RIGHT_PT - PIP_SIDE_PT,
                layout.header.y - INSET_TOP_PT - PIP_SIDE_PT,
                PIP_SIDE_PT, PIP_SIDE_PT)


def placed_slot(layout: PageComposition, anchor: str) -> Rect:
    """Derive the technical V2 slot from a trusted C1 composition; never from caller data."""
    image = placed_image_box(layout, anchor)
    return Rect(image.x - H_INSET_PT, image.y - V_INSET_PT,
                image.width + 2 * H_INSET_PT, image.height + 2 * V_INSET_PT)


def placed_composition(layout: PageComposition, anchor: str, *, text_width: TextWidth) -> PageComposition:
    """Return an immutable copy of ``layout`` whose only change is the slot.

    Refuses any slot outside the safe margin, any visible-image clearance below the
    contract minimum (header above, prompt region below) and any overlap between the
    slot and another named region, then re-runs the full composition validation.
    ``layout`` itself is never mutated.  ``intro_right`` places Pip in the free row
    between the prompt block and the header; the visible image is anchored to the
    header badge axis and the technical slot, larger by the C1 insets, is the only
    rectangle handed to the renderer.
    """
    slot = placed_slot(layout, anchor)
    image = placed_image_box(layout, anchor)
    placed = replace(layout, companion_slot=slot)
    if not placed.safe.contains(slot):
        raise IllustrationError("Slot Pip de placement hors marge de sécurité")
    if layout.header.y - image.top < MIN_CLEARANCE_PT - 1e-9:
        raise IllustrationError("Séparation Pip/en-tête insuffisante")
    if image.y - layout.prompt_fr.region.top < MIN_CLEARANCE_PT - 1e-9:
        raise IllustrationError("Séparation Pip/consigne insuffisante")
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
    if policy_id != PIP_PLACEMENT_HALLOWEEN_V2:
        if policy_id == PIP_PLACEMENT_HALLOWEEN_V1:
            raise IllustrationError("Politique de placement Pip V1 remplacée et refusée")
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
    if len(specs) != len(_CANONICAL_HALLOWEEN_PIP_PLACEMENT_V2) or len(route.bindings) != len(specs):
        raise IllustrationError("Couverture de placement routée incomplète ou supplémentaire")
    bindings: list[PipPlacementBinding] = []
    for spec, route_binding, expected in zip(
            specs, route.bindings, _CANONICAL_HALLOWEEN_PIP_PLACEMENT_V2, strict=True):
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
