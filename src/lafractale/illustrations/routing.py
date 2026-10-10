"""Closed, source-backed B2-C1 routing for the Halloween Pip technical demo.

The route is deliberately not configurable from YAML, JSON, manifests or caller
mappings.  It is reconstructed from the verified Book, demo specifications,
static policy and the external approval-registry pin at every trust boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from lafractale.activities.models import Activity
from lafractale.config.companions import verify_companion_text
from lafractale.config.schema import Book, verify_book_snapshot
from lafractale.illustrations.registry import (
    IllustrationError,
    VerifiedArtwork,
    load_approved_artwork,
    verify_approved_artwork,
)
from lafractale.story.plan import demo_specs


ROUTING_HALLOWEEN_PIP_DEMO_V1 = "halloween-pip-demo-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# (demo_index, activity_id, source_page, activity_type, asset_id)
_CANONICAL_HALLOWEEN_PIP_DEMO_V1 = (
    (1, "halloween_2026-p004", 4, "maze", "pip-reflexion-v2"),
    (2, "halloween_2026-p006", 6, "connect_dots", "pip-indication-v1"),
    (3, "halloween_2026-p020", 20, "match", "pip-encouragement-v1"),
)


@dataclass(frozen=True)
class PageArtworkBinding:
    demo_index: int
    activity_id: str
    source_page: int
    activity_type: str
    asset_id: str
    artwork: VerifiedArtwork

    def manifest_entry(self) -> dict:
        return {
            "demo_index": self.demo_index,
            "activity_id": self.activity_id,
            "source_page": self.source_page,
            "activity_type": self.activity_type,
            "artwork": self.artwork.manifest_entry(),
        }


@dataclass(frozen=True)
class IllustrationRoute:
    policy_id: str
    bindings: tuple[PageArtworkBinding, ...]

    def manifest_entry(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "bindings": [binding.manifest_entry() for binding in self.bindings],
        }

    def artwork_for(self, activity: Activity, *, demo_index: int) -> VerifiedArtwork:
        if type(demo_index) is not int or not 1 <= demo_index <= len(self.bindings):
            raise IllustrationError("Index de démonstration routée invalide")
        binding = self.bindings[demo_index - 1]
        if (binding.demo_index != demo_index or binding.activity_id != activity.id
                or binding.source_page != activity.page or binding.activity_type != activity.type):
            raise IllustrationError("Liaison activité/illustration routée non conforme")
        if binding.artwork.asset_id != binding.asset_id:
            raise IllustrationError("Profil graphique routé non conforme")
        return binding.artwork


def _valid_pin(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def resolve_illustration_mode(illustration_id: str | None, illustration_routing: str | None,
                              trusted_approvals_sha256: str | None) -> str:
    """Resolve the exclusive CLI/API truth table before a staging directory exists."""
    if illustration_id is None and illustration_routing is None and trusted_approvals_sha256 is None:
        return "placeholder"
    if illustration_id is not None and illustration_routing is None and _valid_pin(trusted_approvals_sha256):
        return "legacy_illustration"
    if (illustration_id is None and illustration_routing == ROUTING_HALLOWEEN_PIP_DEMO_V1
            and _valid_pin(trusted_approvals_sha256)):
        return "routed"
    raise IllustrationError("Mode d'illustration absent, ambigu ou non autorisé")


def _verified_specs(book: Book):
    verify_book_snapshot(book)
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    return demo_specs(book)


def build_illustration_route(book: Book, *, policy_id: str,
                             trusted_approvals_sha256: str) -> IllustrationRoute:
    """Construct the sole permitted route from trusted sources and a PIN external."""
    if policy_id != ROUTING_HALLOWEEN_PIP_DEMO_V1:
        raise IllustrationError("Politique de routage inconnue")
    if not _valid_pin(trusted_approvals_sha256):
        raise IllustrationError("Empreinte externe du registre d'approbation obligatoire")
    if book.book_id != "halloween_2026":
        raise IllustrationError("Routage Pip interdit hors Halloween")
    specs = _verified_specs(book)
    if len(specs) != len(_CANONICAL_HALLOWEEN_PIP_DEMO_V1):
        raise IllustrationError("Couverture de démonstration routée incomplète ou supplémentaire")
    bindings: list[PageArtworkBinding] = []
    for spec, expected in zip(specs, _CANONICAL_HALLOWEEN_PIP_DEMO_V1, strict=True):
        demo_index, activity_id, source_page, activity_type, asset_id = expected
        if (spec.id, spec.page, spec.type) != (activity_id, source_page, activity_type):
            raise IllustrationError("Identité d'activité incompatible avec la politique C1")
        artwork = load_approved_artwork(
            book, asset_id, trusted_approvals_sha256=trusted_approvals_sha256,
        )
        bindings.append(PageArtworkBinding(
            demo_index, activity_id, source_page, activity_type, asset_id, artwork,
        ))
    if len({binding.asset_id for binding in bindings}) != len(bindings):
        raise IllustrationError("Politique de routage duplique un asset")
    if len({binding.artwork.pixels for binding in bindings}) != len(bindings):
        raise IllustrationError("Politique de routage utilise des pixels dupliqués")
    return IllustrationRoute(policy_id, tuple(bindings))


def verify_illustration_route(book: Book, route: IllustrationRoute, *, policy_id: str,
                              trusted_approvals_sha256: str) -> None:
    """Rebuild and compare the whole route; reject forged/flexible route objects."""
    if type(route) is not IllustrationRoute:
        raise IllustrationError("Objet de routage non canonique")
    expected = build_illustration_route(
        book, policy_id=policy_id, trusted_approvals_sha256=trusted_approvals_sha256,
    )
    if route != expected:
        raise IllustrationError("Route d'illustrations falsifiée ou non canonique")
    for binding in route.bindings:
        verify_approved_artwork(
            book, binding.artwork, trusted_approvals_sha256=trusted_approvals_sha256,
        )
