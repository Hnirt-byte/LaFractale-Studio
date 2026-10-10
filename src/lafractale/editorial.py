"""Closed, source-backed B2-C4 editorial profile ``halloween-editorial-v1``.

A static, opt-in content/composition overlay applied to the three canonical
Halloween demo activities. It runs strictly DOWNSTREAM of the canonical C1
revalidation (``activity == generate(spec, seed)``) and of the C2 Pip placement
(``intro_right`` 48 pt); it never mutates the historical ``generate`` output or
``validate_collection`` behaviour, and it is never read from YAML/JSON/manifest/
environment. No arbitrary size, pose, coordinate, text or point count is exposed.

The overlay, for the Halloween book only:

- fiche 04 (maze)        : scene ``Aide Pip à trouver la sortie``
- fiche 06 (connect_dots): 8-point crescent moon (1..8, back to 1) + FR/EN
                           consignes stating the ``1 -> 8 -> 1`` order
- fiche 20 (match)       : scene ``Retrouve les chapeaux jumeaux``

plus the editorial typography/fill spec used by the renderer (EN 12 pt,
activity label 12 pt, D/A legend 11 pt, white header/board fills).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from lafractale.activities.models import Activity
from lafractale.config.schema import Book, verify_book_snapshot
from lafractale.illustrations.registry import IllustrationError
from lafractale.quality.checks import validate_activity

EDITORIAL_HALLOWEEN_V1 = "halloween-editorial-v1"

# 8-point crescent moon (bulge left, bite right, opening right), consistent with
# the historical MOON_12 silhouette. Static, audited in code, unit-normalized.
_MOON_8 = (
    (.70, .90), (.40, .95), (.18, .65), (.18, .35),
    (.40, .10), (.55, .28), (.52, .50), (.55, .72),
)

# (demo_index, activity_id, source_page, activity_type)
_CANONICAL_HALLOWEEN_EDITORIAL_V1 = (
    (1, "halloween_2026-p004", 4, "maze"),
    (2, "halloween_2026-p006", 6, "connect_dots"),
    (3, "halloween_2026-p020", 20, "match"),
)

_SCENE_OVERRIDES = {
    "halloween_2026-p004": "Aide Pip à trouver la sortie",
    "halloween_2026-p020": "Retrouve les chapeaux jumeaux",
}

_PROMPT_CONNECT_FR = "Relie les points de 1 à 8, puis reviens au 1."
_PROMPT_CONNECT_EN = "Connect the dots from 1 to 8, then back to 1."


@dataclass(frozen=True)
class EditorialSpec:
    profile_id: str
    prompt_en_size: int
    prompt_en_leading: int
    board_label_size: int
    legend_size: int
    header_fill: float
    board_fill: float


_EDITORIAL_SPEC_V1 = EditorialSpec(
    profile_id=EDITORIAL_HALLOWEEN_V1,
    prompt_en_size=12,
    prompt_en_leading=16,
    board_label_size=12,
    legend_size=11,
    header_fill=1.0,
    board_fill=1.0,
)


def resolve_editorial_profile(profile: str | None) -> str:
    """Resolve the explicit opt-in before any staging directory exists."""
    if profile is None:
        return "none"
    if profile == EDITORIAL_HALLOWEEN_V1:
        return profile
    raise IllustrationError("Profil éditorial inconnu ou non autorisé")


def editorial_spec(profile: str | None) -> EditorialSpec | None:
    """Return the static editorial spec, or None for the historical path."""
    if profile is None:
        return None
    if profile == EDITORIAL_HALLOWEEN_V1:
        return _EDITORIAL_SPEC_V1
    raise IllustrationError("Profil éditorial inconnu ou non autorisé")


def _canonical_identity(activity: Activity) -> tuple[int, str, int, str] | None:
    for demo_index, activity_id, source_page, activity_type in _CANONICAL_HALLOWEEN_EDITORIAL_V1:
        if (activity.id, activity.page, activity.type) == (activity_id, source_page, activity_type):
            return (demo_index, activity_id, source_page, activity_type)
    return None


def transform_editorial(activity: Activity, book: Book, profile: str) -> Activity:
    """Apply the static C4 overlay to one already-canonically-validated activity.

    Pure and deterministic: same activity + book + profile => same result.
    """
    if profile != EDITORIAL_HALLOWEEN_V1:
        raise IllustrationError("Profil éditorial inconnu ou non autorisé")
    verify_book_snapshot(book)
    if book.book_id != "halloween_2026":
        raise IllustrationError("Profil éditorial interdit hors Halloween")
    if _canonical_identity(activity) is None:
        raise IllustrationError("Activité non couverte par le profil éditorial C4")
    scene = activity.scene
    prompt_fr = activity.prompt_fr
    prompt_en = activity.prompt_en
    geometry = activity.geometry
    answer = activity.answer
    if activity.type in ("maze", "match"):
        scene = _SCENE_OVERRIDES[activity.id]
    elif activity.type == "connect_dots":
        points = [{"n": i, "x": round(x, 6), "y": round(y, 6)}
                  for i, (x, y) in enumerate(_MOON_8, 1)]
        geometry = {"shape": "moon", "points": points, "closed": True}
        answer = {"order": list(range(1, 9)), "close_to": 1}
        prompt_fr = _PROMPT_CONNECT_FR
        prompt_en = _PROMPT_CONNECT_EN
    else:
        raise IllustrationError("Type d'activité non couvert par le profil C4")
    return replace(activity, scene=scene, prompt_fr=prompt_fr, prompt_en=prompt_en,
                   geometry=geometry, answer=answer)


def validate_editorial_activity(activity: Activity) -> list[str]:
    """Validate one C4 activity.

    The 8-point crescent is validated by the SAME historical geometry rules as
    the 12-point moon, with the moon length parameterized to 8 (``validate_activity
    (activity, moon_len=8)``). maze/match geometry is untouched and validated
    identically. This wrapper never weakens the historical validator.
    """
    if activity.type in ("maze", "match", "connect_dots"):
        return validate_activity(activity, moon_len=8)
    return [f"{activity.id}: type non couvert par le profil éditorial C4"]
