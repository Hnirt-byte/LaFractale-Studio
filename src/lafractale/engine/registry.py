"""Closed registry of the mechanics the slice may use.

Each entry adapts an EXISTING generator (``lafractale.activities.engine``); no
generator is duplicated. Parameters are closed enumerations: anything not listed
here is refused by the contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping

from lafractale.activities.models import Activity, ActivitySpec
from lafractale.engine import solvers

# The historical ``match`` generator selects its symbol family from the
# vocabulary of the spec; this table is the only place that relies on it.
# Only the neutral geometric family is open: ``hats`` / ``gifts`` are seasonal
# symbol sets and stay closed until real content is in scope.
_MATCH_FAMILY_VOCABULARY = {"shapes": ()}


@dataclass(frozen=True)
class Mechanic:
    name: str
    #: parameter name -> closed set of allowed values
    params: Mapping[str, tuple[str, ...]]
    required: tuple[str, ...]
    #: (spec_kwargs, params) -> ActivitySpec
    build_spec: Callable[..., ActivitySpec]
    verify: Callable[[Activity], list[str]]
    #: parameter the generator must echo back in ``activity.geometry`` (same key)
    echo: str | None = None

    def check_params(self, params: Mapping[str, object]) -> list[str]:
        errors = []
        for key in params:
            if key not in self.params:
                errors.append(f"paramètre non autorisé pour {self.name} : {key}")
        for key in self.required:
            if key not in params:
                errors.append(f"paramètre obligatoire absent pour {self.name} : {key}")
        for key, allowed in self.params.items():
            if key in params and params[key] not in allowed:
                errors.append(f"valeur non autorisée pour {self.name}.{key} : {params[key]!r}")
        return errors

    def expected_geometry_key(self, params: Mapping[str, object]) -> tuple[str, object] | None:
        """(geometry key, value) the generated activity must echo back, if any."""
        return (self.echo, params[self.echo]) if self.echo else None


def _maze_spec(common: dict, params: Mapping[str, object]) -> ActivitySpec:
    return ActivitySpec(type="maze", **common)


def _dots_spec(common: dict, params: Mapping[str, object]) -> ActivitySpec:
    return ActivitySpec(type="connect_dots", shape=str(params["shape"]), **common)


def _match_spec(common: dict, params: Mapping[str, object]) -> ActivitySpec:
    return ActivitySpec(type="match", **{**common, "vocabulary": _MATCH_FAMILY_VOCABULARY[str(params["family"])]})


def _verify(solver: Callable[[Activity], list[str]]) -> Callable[[Activity], list[str]]:
    return lambda activity: solvers.verify_with_existing_rules(activity, solver)


MECHANICS: Mapping[str, Mechanic] = MappingProxyType({
    "maze": Mechanic("maze", MappingProxyType({}), (), _maze_spec, _verify(solvers.verify_maze)),
    "connect_dots": Mechanic(
        "connect_dots", MappingProxyType({"shape": ("moon", "house", "star")}), ("shape",),
        _dots_spec, _verify(solvers.verify_connect_dots), echo="shape"),
    "match": Mechanic(
        "match", MappingProxyType({"family": ("shapes",)}), ("family",),
        _match_spec, _verify(solvers.verify_match), echo="family"),
})
