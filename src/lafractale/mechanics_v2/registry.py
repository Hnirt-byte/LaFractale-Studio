"""Closed registry of the v2 mechanics (kept apart from the historical ``engine.registry``)."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from lafractale.mechanics_v2.connect_dots import (
    CONNECT_DOTS_V2_MECHANIC, CONNECT_DOTS_V2_VERSION, PARAM_SPEC as CONNECT_DOTS_PARAMS, generate_connect_dots_v2,
)
from lafractale.mechanics_v2.connect_dots_verify import verify_connect_dots_v2
from lafractale.mechanics_v2.core import V2Activity, V2Error
from lafractale.mechanics_v2.maze import MAZE_V2_MECHANIC, MAZE_V2_VERSION, PARAM_SPEC as MAZE_PARAMS, generate_maze_v2
from lafractale.mechanics_v2.match import MATCH_V2_MECHANIC, MATCH_V2_VERSION, PARAM_SPEC as MATCH_PARAMS, generate_match_v2
from lafractale.mechanics_v2.match_verify import verify_match_v2
from lafractale.mechanics_v2.maze_verify import verify_maze_v2


@dataclass(frozen=True)
class MechanicV2:
    name: str
    version: str
    params: Mapping[str, Callable[[Any], Any]]
    generate: Callable[[Any, Any, Mapping[str, Any]], V2Activity]
    verify: Callable[[Mapping[str, Any] | V2Activity], list[str]]


MECHANICS_V2: Mapping[str, MechanicV2] = MappingProxyType({
    MAZE_V2_MECHANIC: MechanicV2(MAZE_V2_MECHANIC, MAZE_V2_VERSION, MappingProxyType(dict(MAZE_PARAMS)),
                                 generate_maze_v2, verify_maze_v2),
    CONNECT_DOTS_V2_MECHANIC: MechanicV2(CONNECT_DOTS_V2_MECHANIC, CONNECT_DOTS_V2_VERSION,
                                         MappingProxyType(dict(CONNECT_DOTS_PARAMS)),
                                         generate_connect_dots_v2, verify_connect_dots_v2),
    MATCH_V2_MECHANIC: MechanicV2(MATCH_V2_MECHANIC, MATCH_V2_VERSION, MappingProxyType(dict(MATCH_PARAMS)),
                                  generate_match_v2, verify_match_v2),
})


def _mechanic(name: Any) -> MechanicV2:
    if type(name) is not str or name not in MECHANICS_V2:
        raise V2Error("UNKNOWN_MECHANIC", f"mécanique v2 inconnue : {name!r} (disponibles : {sorted(MECHANICS_V2)})")
    return MECHANICS_V2[name]


def generate_v2(mechanic: Any, activity_id: Any, seed: Any, params: Mapping[str, Any]) -> V2Activity:
    """Generate then independently re-verify; a record that fails its own verification is never returned."""
    entry = _mechanic(mechanic)
    activity = entry.generate(activity_id, seed, params)
    problems = entry.verify(activity)
    if problems:
        raise V2Error("SELF_CHECK_FAILED", "; ".join(problems))
    return activity


def verify_v2(record: Mapping[str, Any] | V2Activity) -> list[str]:
    """Always returns the list of problems (an unknown or missing mechanic is a problem, not an exception)."""
    name = record.mechanic if isinstance(record, V2Activity) else (record.get("mechanic") if isinstance(record, Mapping) else None)
    if type(name) is not str or name not in MECHANICS_V2:
        return [f"mécanique v2 inconnue ou absente : {name!r}"]
    return MECHANICS_V2[name].verify(record)
