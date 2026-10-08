"""Activity data remains independent from composition and rendering."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import hashlib
import json


@dataclass(frozen=True)
class ActivitySpec:
    id: str
    page: int
    type: str
    age_band: tuple[int, int]
    scene: str
    vocabulary: tuple[str, ...]
    shape: str = ""
    asset_refs: tuple[str, ...] = ()
    pedagogy: str = "Observation et motricité fine"
    difficulty: str = "débutant"
    companion_pose: str = "not_rendered"
    companion_name: str | None = None


@dataclass(frozen=True)
class Activity:
    id: str
    page: int
    type: str
    age_band: tuple[int, int]
    scene: str
    vocabulary: tuple[str, ...]
    prompt_fr: str
    prompt_en: str
    assets: tuple[str, ...]
    geometry: dict[str, Any]
    answer: dict[str, Any]
    seed: int
    pedagogy: str
    difficulty: str
    companion_pose: str
    companion_name: str | None = None
    graphic_status: str = "needs_visual_review"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def content_fingerprint(activity: Activity) -> str:
    # Exclude identifiers, story and seeds: only pedagogical puzzle data.
    body = {"type": activity.type, "geometry": activity.geometry, "answer": activity.answer}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
