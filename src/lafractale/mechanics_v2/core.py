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
from types import MappingProxyType
from typing import Any, Callable, Iterator

from lafractale.mechanics_v2 import HUMAN_PEDAGOGICAL_VALIDATION, PRODUCTION_AUTHORIZED, V2_KIND, V2_SCHEMA
from lafractale.security.strict_json import StrictJSONError, loads_strict

MAX_SEED = 2**63 - 1
MAX_DEPTH = 16
# Bounds of the pre-validation of a record handed to a verifier (B3-B.3c.1). The largest valid record of the three
# mechanics stays far below them (about 1 500 nodes for a 12x12 maze); anything beyond is hostile by definition.
MAX_RECORD_DEPTH = 8
MAX_RECORD_NODES = 4096
MAX_RECORD_KEY = 64
MAX_RECORD_STRING = 256
MAX_RECORD_INT_BITS = 4096  # about 1 230 decimal digits: under CPython's default 4 300-digit int/str conversion limit
MAX_REPORTED_PROBLEMS = 100
ACTIVITY_ID = re.compile(r"\Asyn-[a-z0-9](?:[a-z0-9-]{0,44}[a-z0-9])?\Z")  # at most 50 characters in all


class V2Error(ValueError):
    """A v2 request or record is refused. ``code`` is stable; nothing is ever silently relaxed."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# ---- bounded rendering and hostile-shape guard (B3-B.3c.1) ---------------------------------------------
def bounded_repr(value: Any, limit: int = 80, _depth: int = 0) -> str:
    """Short, total rendering of ANY value for an error message: never recursive beyond 3 levels, never raises.

    Only exact built-in JSON types are rendered; every other object is shown by its (truncated) type name, so a
    hostile ``__repr__``, a huge integer or a deeply nested container cannot cause an exception or a huge message.
    """
    kind = type(value)
    if value is None or kind is bool:
        return repr(value)
    if kind is int:
        bits = value.bit_length()
        return repr(value) if bits <= 64 else f"<entier de {bits} bits>"
    if kind is float:
        return repr(value)
    if kind is str:
        shown = repr(value[:limit])
        return shown if len(value) <= limit else f"{shown}…(+{len(value) - limit} car.)"
    if kind in (list, dict) and _depth < 3:
        if kind is list:
            parts = [bounded_repr(v, limit, _depth + 1) for v in value[:6]]
            text = "[" + ", ".join(parts) + (", …" if len(value) > 6 else "") + "]"
        else:
            parts = [f"{bounded_repr(k, limit, _depth + 1)}: {bounded_repr(v, limit, _depth + 1)}"
                     for k, v in list(value.items())[:6]]
            text = "{" + ", ".join(parts) + (", …" if len(value) > 6 else "") + "}"
        return text if len(text) <= 4 * limit else text[:4 * limit] + "…"
    if kind in (list, dict):
        return f"<{kind.__name__} de {len(value)} éléments>"
    return f"<{kind.__name__[:40]}>"


_TOP_LEVEL_MAPPINGS: tuple[type, ...] = ()  # completed below, once FrozenDict exists


def hostile_shape(data: Any) -> str | None:
    """First reason why ``data`` is not an ordinary, bounded JSON-like record; ``None`` if it is acceptable.

    Iterative (no recursion, so no ``RecursionError``), bounded in depth, in number of nodes visited (a shared or
    cyclic reference is counted at every visit, so it cannot loop or blow up), in key/string length and in
    integer size. Containers must be exact ``dict`` / ``list``; leaves exact ``None``, ``bool``, ``int``, ``float``
    or ``str``. Anything else (subclasses, tuples, sets, bytes, arbitrary objects, non-string keys) is refused
    WITHOUT being inspected, converted or rendered. Only the top level may also be a ``FrozenDict`` or a
    ``MappingProxyType`` (exact types), read through ``items()`` once.
    """
    nodes = 0
    stack: list[tuple[Any, int]] = [(data, 0)]
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_RECORD_NODES:
            return f"enregistrement hostile : plus de {MAX_RECORD_NODES} éléments"
        if depth > MAX_RECORD_DEPTH:
            return f"enregistrement hostile : imbrication supérieure à {MAX_RECORD_DEPTH} niveaux"
        kind = type(value)
        if kind is dict or (depth == 0 and kind in _TOP_LEVEL_MAPPINGS) or kind is list:
            if nodes + len(stack) + len(value) > MAX_RECORD_NODES:  # refuse BEFORE pushing a huge container
                return f"enregistrement hostile : plus de {MAX_RECORD_NODES} éléments"
        if kind is dict or (depth == 0 and kind in _TOP_LEVEL_MAPPINGS):
            for key, item in value.items():
                if type(key) is not str:
                    return "enregistrement hostile : clé non textuelle"
                if len(key) > MAX_RECORD_KEY:
                    return f"enregistrement hostile : clé de plus de {MAX_RECORD_KEY} caractères"
                stack.append((item, depth + 1))
        elif kind is list:
            stack.extend((item, depth + 1) for item in value)
        elif kind is str:
            if len(value) > MAX_RECORD_STRING:
                return f"enregistrement hostile : chaîne de plus de {MAX_RECORD_STRING} caractères"
        elif kind is int:
            if value.bit_length() > MAX_RECORD_INT_BITS:
                return f"enregistrement hostile : entier de plus de {MAX_RECORD_INT_BITS} bits"
        elif value is None or kind is bool or kind is float:
            continue
        else:
            return f"enregistrement hostile : type non pris en charge ({kind.__name__[:40]})"
    return None


def cap_problems(problems: list[str]) -> list[str]:
    """At most ``MAX_REPORTED_PROBLEMS`` problems plus one summary line: a non-empty list stays non-empty."""
    if len(problems) <= MAX_REPORTED_PROBLEMS:
        return problems
    return problems[:MAX_REPORTED_PROBLEMS] + [f"… {len(problems) - MAX_REPORTED_PROBLEMS} autre(s) problème(s) non listé(s)"]


def keys_summary(data: Mapping[str, Any]) -> str:
    """Sorted keys of a (shape-checked) mapping, at most 12 shown."""
    keys = sorted(data)
    return str(keys[:12]) + (f" … (+{len(keys) - 12})" if len(keys) > 12 else "")


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


_TOP_LEVEL_MAPPINGS = (FrozenDict, MappingProxyType)


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

    def __post_init__(self) -> None:
        # Direct construction freezes too: no mutable container can enter a V2Activity.
        for name in ("params", "geometry", "solution", "measures", "search"):
            value = freeze(getattr(self, name))
            if not isinstance(value, FrozenDict):
                raise V2Error("BAD_VALUE", f"{name} : mapping attendu")
            object.__setattr__(self, name, value)

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
        raise V2Error("BAD_ACTIVITY_ID", "identifiant synthétique obligatoire : « syn- » puis minuscules/chiffres/tirets, 50 caractères au plus, sans tiret final")
    return activity_id


def check_seed(seed: Any) -> int:
    if type(seed) is not int or not 0 <= seed <= MAX_SEED:
        raise V2Error("BAD_SEED", f"graine entière attendue entre 0 et {MAX_SEED}")
    return seed


def check_params(params: Any, spec: Mapping[str, Callable[[Any], Any]]) -> dict[str, Any]:
    """Closed parameter set: every key declared, none missing, none extra; each value validated."""
    if not isinstance(params, Mapping) or type(params) not in (dict, FrozenDict):
        raise V2Error("BAD_PARAMS", "mapping de paramètres attendu")
    extra = [k for k in params if k not in spec]
    if extra:
        shown = ", ".join(sorted(k[:40] if type(k) is str else bounded_repr(k, 40) for k in extra[:8])) + (" …" if len(extra) > 8 else "")
        raise V2Error("UNKNOWN_PARAM", f"paramètre(s) non autorisé(s) : {shown}")
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
