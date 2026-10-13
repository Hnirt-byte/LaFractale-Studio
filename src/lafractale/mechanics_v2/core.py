"""Common foundation of the v2 mechanics: errors, immutable values, canonical form, PRNG.

Canonical form (``lafractale-mechanics-v2-activity-v1``): UTF-8 JSON, object keys sorted
lexicographically, separators ``,`` and ``:`` without spaces, ``ensure_ascii=False``, integers
only (floats, NaN and non-string keys are refused), arrays keep their order. The fingerprint is
the SHA-256 (lowercase hex) of the canonical bytes of the record WITHOUT its ``fingerprint`` key.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from lafractale.mechanics_v2 import HUMAN_PEDAGOGICAL_VALIDATION, PRODUCTION_AUTHORIZED, V2_KIND, V2_SCHEMA
from lafractale.security.strict_json import StrictJSONError, loads_strict

MAX_SEED = 2**63 - 1
MAX_DEPTH = 16
ACTIVITY_ID = re.compile(r"\Asyn-[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?\Z")


class V2Error(ValueError):
    """A v2 request or record is refused. ``code`` is stable; nothing is ever silently relaxed."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# ---- immutable values ------------------------------------------------------------------------
class FrozenDict(Mapping):
    """Read-only mapping with a stable order (sorted keys); values are themselves frozen."""

    __slots__ = ("_items",)

    def __init__(self, data: Mapping[str, Any]):
        object.__setattr__(self, "_items", tuple(sorted((k, freeze(v)) for k, v in data.items())))

    def __getitem__(self, key: str) -> Any:
        for k, v in self._items:
            if k == key:
                return v
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (k for k, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._items)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("FrozenDict est immuable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("FrozenDict est immuable")

    def __repr__(self) -> str:
        return f"FrozenDict({dict(self._items)!r})"


def freeze(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise V2Error("TOO_DEEP", "structure trop profonde")
    if isinstance(value, FrozenDict):
        return value
    if isinstance(value, Mapping):
        if not all(type(k) is str for k in value):
            raise V2Error("BAD_KEY", "clés de mapping : chaînes uniquement")
        return FrozenDict({k: freeze(v, depth + 1) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v, depth + 1) for v in value)
    if value is None or type(value) in (str, int, bool):
        return value
    raise V2Error("BAD_VALUE", f"type non autorisé dans une sortie v2 : {type(value).__name__} (entiers, chaînes, booléens, None)")


def thaw(value: Any) -> Any:
    """Fresh plain copy (dict/list) of a frozen structure."""
    if isinstance(value, FrozenDict):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [thaw(v) for v in value]
    return value


def canonical_bytes(data: Mapping[str, Any]) -> bytes:
    plain = thaw(freeze(data))
    return json.dumps(plain, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---- the output record -------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class V2Activity:
    """Immutable synthetic activity: geometry, solution and measures, fingerprinted."""

    mechanic: str
    version: str
    activity_id: str
    seed: int
    params: FrozenDict
    geometry: FrozenDict
    solution: FrozenDict
    measures: FrozenDict
    search: FrozenDict
    fingerprint: str

    @property
    def production_authorized(self) -> bool:
        return PRODUCTION_AUTHORIZED

    def body_dict(self) -> dict[str, Any]:
        return {
            "schema": V2_SCHEMA, "kind": V2_KIND, "mechanic": self.mechanic, "version": self.version,
            "activity_id": self.activity_id, "seed": self.seed,
            "human_pedagogical_validation": HUMAN_PEDAGOGICAL_VALIDATION, "production_authorized": False,
            "params": thaw(self.params), "geometry": thaw(self.geometry), "solution": thaw(self.solution),
            "measures": thaw(self.measures), "search": thaw(self.search),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.body_dict(), "fingerprint": self.fingerprint}

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())


def build_activity(*, mechanic: str, version: str, activity_id: str, seed: int, params: Mapping[str, Any],
                   geometry: Mapping[str, Any], solution: Mapping[str, Any], measures: Mapping[str, Any],
                   search: Mapping[str, Any]) -> V2Activity:
    draft = V2Activity(mechanic, version, activity_id, seed, freeze(params), freeze(geometry), freeze(solution),
                       freeze(measures), freeze(search), "")
    digest = sha256_hex(canonical_bytes(draft.body_dict()))
    return V2Activity(mechanic, version, activity_id, seed, draft.params, draft.geometry, draft.solution,
                      draft.measures, draft.search, digest)


def record_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint recomputed from a plain record (used by independent verification)."""
    return sha256_hex(canonical_bytes({k: v for k, v in record.items() if k != "fingerprint"}))


def loads_record(data: bytes) -> dict[str, Any]:
    """Strict parse of a canonical record; the bytes must already be canonical."""
    try:
        record = loads_strict(data)
    except (StrictJSONError, ValueError) as exc:
        raise V2Error("BAD_JSON", f"JSON strict refusé : {exc}") from exc
    if not isinstance(record, dict):
        raise V2Error("BAD_JSON", "objet JSON attendu")
    try:
        again = canonical_bytes(record)
    except (V2Error, ValueError) as exc:
        raise V2Error("BAD_JSON", f"valeur non canonique : {exc}") from exc
    if again != data:
        raise V2Error("NOT_CANONICAL", "les octets ne sont pas la forme canonique v2")
    return record


# ---- request validation --------------------------------------------------------------------------
def check_activity_id(activity_id: Any) -> str:
    if type(activity_id) is not str or not ACTIVITY_ID.match(activity_id):
        raise V2Error("BAD_ACTIVITY_ID", "identifiant synthétique obligatoire : « syn- » puis minuscules/chiffres/tirets (≤ 50 car.)")
    return activity_id


def check_seed(seed: Any) -> int:
    if type(seed) is not int or not 0 <= seed <= MAX_SEED:
        raise V2Error("BAD_SEED", f"graine entière attendue entre 0 et {MAX_SEED}")
    return seed


def check_params(params: Any, spec: Mapping[str, Callable[[Any], Any]]) -> dict[str, Any]:
    """Closed parameter set: every key declared, none missing, none extra; each value validated."""
    if not isinstance(params, Mapping) or type(params) not in (dict, FrozenDict):
        raise V2Error("BAD_PARAMS", "mapping de paramètres attendu")
    extra = sorted(str(k) for k in params if k not in spec)
    if extra:
        raise V2Error("UNKNOWN_PARAM", f"paramètre(s) non autorisé(s) : {', '.join(extra)}")
    missing = sorted(k for k in spec if k not in params)
    if missing:
        raise V2Error("MISSING_PARAM", f"paramètre(s) obligatoire(s) absent(s) : {', '.join(missing)}")
    return {k: spec[k](params[k]) for k in spec}


# ---- deterministic PRNG (stable across Python versions) -----------------------------------------
class DetRng:
    """SHA-256 counter-mode generator: same material → same stream on every Python version."""

    __slots__ = ("_material", "_counter", "_buffer")

    def __init__(self, material: str):
        self._material = material.encode("utf-8")
        self._counter = 0
        self._buffer: list[int] = []

    def _word(self) -> int:
        if not self._buffer:
            block = hashlib.sha256(self._material + b"|" + str(self._counter).encode()).digest()
            self._counter += 1
            self._buffer = [int.from_bytes(block[i:i + 8], "big") for i in range(24, -1, -8)]
        return self._buffer.pop()

    def below(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n > 0 attendu")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            word = self._word()
            if word < limit:
                return word % n

    def shuffle(self, items: list) -> None:
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]

    def choice(self, items: list):
        return items[self.below(len(items))]
