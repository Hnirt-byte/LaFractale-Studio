"""Strict JSON decoding at every untrusted wire-format boundary.

The Python default decoder silently implements last-key-wins for duplicate object
members, while other JSON consumers may implement first-key-wins. Never make
security decisions on such ambiguous input, even when its checksum is pinned.
"""
from __future__ import annotations

import json
import math
from typing import Any


class StrictJSONError(ValueError):
    """Non-canonical or ambiguous JSON, including a repeated object member."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"Clé JSON dupliquée interdite : {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"Constante JSON non standard interdite : {value}")


def _finite_float(value: str) -> float:
    decoded = float(value)
    if not math.isfinite(decoded):
        raise StrictJSONError(f"Nombre JSON non fini interdit : {value[:64]}")
    return decoded


MAX_JSON_DEPTH = 64


def _verify_depth_and_unicode(parsed: Any) -> Any:
    # Iterative walk, so nested arrays cannot exhaust the Python call stack
    # during validation. Reject lone surrogate escapes that are not UTF-8 text.
    stack: list[tuple[Any, int]] = [(parsed, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise StrictJSONError("Profondeur JSON excessive")
        if isinstance(value, dict):
            for key, item in value.items():
                try:
                    key.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise StrictJSONError("Clé JSON Unicode invalide") from exc
                stack.append((item, depth + 1))
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise StrictJSONError("Chaîne JSON Unicode invalide") from exc
    return parsed


def loads_strict(payload: str | bytes) -> Any:
    """Parse UTF-8 RFC JSON without duplicate keys at any object nesting level.

    Names with JSON escapes are decoded *before* checking duplicates, so
    ``"a"`` and ``"\\u0061"`` are recognized as the same member.
    Nonstandard NaN/Infinity tokens are rejected as well.
    """
    try:
        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if not isinstance(raw, str):
            raise StrictJSONError("JSON attendu sous forme de texte UTF-8")
        # Avoid silently accepting non-standard Unicode replacement text.
        raw.encode("utf-8")
        return _verify_depth_and_unicode(json.loads(
            raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant,
            parse_float=_finite_float))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise StrictJSONError(f"JSON UTF-8 invalide : {exc}") from exc
