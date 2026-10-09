"""Single fail-closed Unicode policy for all editorial and generated text.

NFKC is checked, not silently substituted: the bytes approved by editors must
be the bytes used for rendering. Default-ignorable and format chars are rejected
before name matching, so they cannot split visually identical names.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import re
import string
import unicodedata
from typing import Any


class UnsafeEditorialText(ValueError):
    """Invisible/control/noncanonical Unicode in editable or emitted text."""


# The current editorial scope is French and English. Review and version this
# allowlist before adding other languages: 'Latin script' alone is too broad
# because dotless-i, small-capital letters etc. can spoof ASCII names.
_ALLOWED_LATIN_LETTERS = frozenset(
    string.ascii_letters
    + "ÀàÂâÄäÁáÃãÅåÆæÇçÈèÉéÊêËëÌìÍíÎîÏïÑñÒòÓóÔôÖöØøŒœÙùÚúÛûÜüÝýŸÿÐðÞþß"
)


# Default-Ignorable_Code_Point includes more than Unicode category Cf.
# Reject these non-Cf ranges as well (variation selectors, soft fillers, etc.).
_NON_CF_IGNORABLE_RANGES = (
    (0x034F, 0x034F), (0x115F, 0x1160), (0x17B4, 0x17B5),
    (0x180B, 0x180D), (0x180F, 0x180F),
    (0x2065, 0x2065), (0x2800, 0x2800), (0x3164, 0x3164), (0xFFA0, 0xFFA0),
    (0xFE00, 0xFE0F), (0xFFF0, 0xFFF8),
    (0xE0000, 0xE0FFF), (0xE0100, 0xE01EF),
)


def _disallowed_char(char: str) -> bool:
    cp = ord(char)
    category = unicodedata.category(char)
    return (category in {"Cf", "Cs", "Mn", "Mc", "Me"}
            or (category == "Cc" and char not in "\t\r\n")
            or any(start <= cp <= end for start, end in _NON_CF_IGNORABLE_RANGES))


def canonical_text(value: str, *, location: str = "texte") -> str:
    """Enforce one representation. Valid French accents and punctuation stay."""
    if not isinstance(value, str):
        raise UnsafeEditorialText(f"{location} : chaîne attendue")
    for char in value:
        if _disallowed_char(char):
            raise UnsafeEditorialText(
                f"{location} : caractère invisible/de contrôle/combinant interdit U+{ord(char):04X}")
        # This first bilingual FR/EN edition uses only the Latin script.
        # Non-Latin letters would allow visually deceptive Cyrillic/Greek names,
        # e.g. P + CYRILLIC i + p, without any invisible character.
        if unicodedata.category(char).startswith("L") and char not in _ALLOWED_LATIN_LETTERS:
            raise UnsafeEditorialText(
                f"{location} : lettre hors alphabet éditorial latin autorisé U+{ord(char):04X}")
    canonical = unicodedata.normalize("NFKC", value)
    if canonical != value:
        raise UnsafeEditorialText(f"{location} : texte Unicode non canonique (NFKC)")
    return canonical.casefold()


def checked_strings(value: Any, *, location: str = "texte"):
    """Validate keys and values recursively; yield normalized strings."""
    if isinstance(value, str):
        yield canonical_text(value, location=location)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from checked_strings(key, location=f"{location}.clé")
            yield from checked_strings(item, location=f"{location}[{key!s}]")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            yield from checked_strings(item, location=f"{location}[{index}]")


def _tokens(text: str) -> list[str]:
    """Editorial-letter tokens only, from previously validated/casefolded text.

    Python's \\w groups digits and underscores with alphabetic characters and
    thereby misses reserved names such as Pip_ or Pip2. Here *only* Unicode
    letters may extend a token. Digits, connectors and punctuation delimit
    tokens; combining marks are rejected by canonical_text BEFORE this step.
    """
    tokens: list[str] = []
    current: list[str] = []
    for char in text:
        if unicodedata.category(char).startswith("L"):
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def blocked_name_fingerprints(names: tuple[str, ...] | list[str]) -> tuple[tuple[int, str], ...]:
    """Digest-only QA policy: Noël manifests never contain Pip in cleartext."""
    entries = []
    for name in names:
        normalized = canonical_text(name, location="nom de compagnon")
        words = _tokens(normalized)
        if not words:
            raise UnsafeEditorialText("Nom de compagnon vide après normalisation")
        entries.append((len(words), sha256(" ".join(words).encode("utf-8")).hexdigest()))
    return tuple(sorted(set(entries)))


def rejected_name(normalized_text: str, fingerprints: tuple[tuple[int, str], ...]) -> bool:
    words = _tokens(normalized_text)
    for length, digest in fingerprints:
        for start in range(len(words) - length + 1):
            candidate = " ".join(words[start:start + length])
            if sha256(candidate.encode("utf-8")).hexdigest() == digest:
                return True
    return False


def verify_text_policy(value: Any, *, forbidden_names: tuple[str, ...] = (),
                       fingerprints: tuple[tuple[int, str], ...] | None = None,
                       location: str = "texte") -> None:
    """Validate all strings even if no companion name is forbidden."""
    blocked = (blocked_name_fingerprints(forbidden_names)
               if fingerprints is None else fingerprints)
    for normalized in checked_strings(value, location=location):
        if rejected_name(normalized, blocked):
            matched = next((name for name in forbidden_names
                            if rejected_name(normalized, blocked_name_fingerprints((name,)))), None)
            suffix = f" : {matched}" if matched else ""
            raise UnsafeEditorialText(f"Compagnon non autorisé dans le texte {location}{suffix}")


def parse_fingerprints(raw: Any) -> tuple[tuple[int, str], ...]:
    """Strictly parse the manifest's digest-only, immutable QA policy."""
    if not isinstance(raw, list) or len(raw) > 256:
        raise UnsafeEditorialText("Manifeste : politique de noms absente/invalide")
    fingerprints = []
    for item in raw:
        if (not isinstance(item, list) or len(item) != 2
                or type(item[0]) is not int or not 1 <= item[0] <= 12
                or not isinstance(item[1], str)
                or re.fullmatch(r"[0-9a-f]{64}", item[1]) is None):
            raise UnsafeEditorialText("Manifeste : empreinte de nom réservée invalide")
        fingerprints.append((item[0], item[1]))
    if fingerprints != sorted(set(fingerprints)):
        raise UnsafeEditorialText("Manifeste : liste d'empreintes non canonique")
    return tuple(fingerprints)
