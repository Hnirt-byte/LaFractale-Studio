"""Strict, closed source contract of the B3-B.1 engine slice.

The source is JSON read with the repository's strict decoder (duplicate keys and
non-finite numbers refused). Every key is checked against a closed list: an
unknown key is an error, never ignored. Only synthetic fixtures are accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping

from lafractale.engine import SPEC_KIND, ContractError, EngineError
from lafractale.engine.registry import MECHANICS
from lafractale.security.strict_json import loads_strict
from lafractale.security.text import UnsafeEditorialText, verify_text_policy

SCHEMA = "lafractale-engine-slice-v1"
MAX_PAGES = 12
MAX_SOURCE_BYTES = 200_000
MAX_SCENE, MAX_PROMPT_FR, MAX_PROMPT_EN = 60, 120, 80
SUPPORTED_TRIM = (8.5, 11.0)  # US Letter: the only layout the slice composes

#: Real book identities and characters: refused anywhere in a synthetic source.
# Denylist of exact name tokens (accent variants listed explicitly): a guard, not a proof.
SYNTHETIC_FORBIDDEN_NAMES = ("Pip", "Halloween", "Christmas", "Noël", "Noel")

_TOP_KEYS = ("schema", "kind", "spec_id", "title", "publisher", "trim", "age_band", "seed", "pages")
_PAGE_KEYS = ("page", "unit_id", "mechanic", "params", "scene", "prompt_fr", "prompt_en")
# Keys that would smuggle production, approval, character or asset semantics.
_FORBIDDEN_KEYS = frozenset({
    "production", "ready_for_kdp", "kdp", "gates", "approved", "human_approved", "approval",
    "companion", "mascot", "illustration", "illustrations", "illustration_routing",
    "pip_placement", "editorial_profile", "asset", "assets", "asset_refs", "book_id",
})
_SPEC_ID = re.compile(r"synthetic_[a-z0-9_]{1,40}\Z")
_UNIT_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,31}\Z")


@dataclass(frozen=True)
class PageSpec:
    page: int
    unit_id: str
    mechanic: str
    params: Mapping[str, str]
    scene: str
    prompt_fr: str
    prompt_en: str


@dataclass(frozen=True)
class SpecSet:
    schema: str
    kind: str
    spec_id: str
    title: str
    publisher: str
    trim: tuple[float, float]
    age_band: tuple[int, int]
    seed: int
    pages: tuple[PageSpec, ...]
    source_sha256: str

    def book_dict(self) -> dict[str, Any]:
        """Minimal book mapping consumed by the existing PDF writer."""
        return {"title": self.title, "publisher": self.publisher,
                "trim": {"width_in": self.trim[0], "height_in": self.trim[1]}}


def canonical_json_bytes(data: Any) -> bytes:
    """The single JSON encoding used for every emitted JSON file."""
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_int(value: Any) -> bool:
    return type(value) is int


def _check_keys(obj: Any, expected: tuple[str, ...], where: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where} : objet attendu")
        return False
    forbidden = sorted(set(obj) & _FORBIDDEN_KEYS)
    if forbidden:
        errors.append(f"{where} : clé interdite en mode synthétique : {', '.join(forbidden)}")
    unknown = sorted(set(obj) - set(expected) - _FORBIDDEN_KEYS)
    if unknown:
        errors.append(f"{where} : clé inconnue : {', '.join(unknown)}")
    missing = [key for key in expected if key not in obj]
    if missing:
        errors.append(f"{where} : clé obligatoire absente : {', '.join(missing)}")
    return not (forbidden or unknown or missing)


def _check_text(value: Any, where: str, limit: int, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where} : chaîne non vide attendue")
    elif value != value.strip() or any(ch in value for ch in "\t\r\n\x00") or len(value) > limit:
        errors.append(f"{where} : espaces de bord, retour à la ligne ou plus de {limit} caractères")


def parse_spec_set(payload: bytes) -> SpecSet:
    """Validate a source and return an immutable SpecSet, or raise ContractError."""
    if not isinstance(payload, (bytes, bytearray)):
        raise ContractError("source : octets attendus")
    if len(payload) > MAX_SOURCE_BYTES:
        raise ContractError(f"source : plus de {MAX_SOURCE_BYTES} octets")
    try:
        data = loads_strict(bytes(payload))
    except ValueError as exc:
        raise ContractError(f"JSON strict refusé : {exc}") from exc
    errors: list[str] = []
    if not _check_keys(data, _TOP_KEYS, "source", errors):
        raise ContractError(errors)
    if data["schema"] != SCHEMA:
        errors.append(f"schema : {SCHEMA!r} attendu")
    if data["kind"] != SPEC_KIND:
        errors.append(f"kind : {SPEC_KIND!r} attendu (seules les fixtures synthétiques sont acceptées)")
    if not isinstance(data["spec_id"], str) or not _SPEC_ID.fullmatch(data["spec_id"]):
        errors.append("spec_id : doit commencer par 'synthetic_' (minuscules, chiffres, '_')")
    _check_text(data["title"], "title", 80, errors)
    _check_text(data["publisher"], "publisher", 80, errors)
    trim = data["trim"]
    trim_ok = _check_keys(trim, ("width_in", "height_in"), "trim", errors)
    if trim_ok and not (all(type(trim[k]) in (int, float) for k in trim)
                        and (float(trim["width_in"]), float(trim["height_in"])) == SUPPORTED_TRIM):
        errors.append("trim : seul le format 8.5 x 11 pouces est pris en charge")
    band = data["age_band"]
    if not (isinstance(band, list) and len(band) == 2 and all(_is_int(v) and 3 <= v <= 12 for v in band)
            and band[0] <= band[1]):
        errors.append("age_band : [min, max] entiers entre 3 et 12")
    if not _is_int(data["seed"]) or not -(2**31) <= data["seed"] < 2**31:
        errors.append("seed : entier 32 bits attendu")
    pages = data["pages"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        errors.append(f"pages : liste de 1 à {MAX_PAGES} fiches attendue")
        raise ContractError(errors)
    seen_units: set[str] = set()
    parsed: list[PageSpec] = []
    for index, page in enumerate(pages, start=1):
        where = f"pages[{index - 1}]"
        if not _check_keys(page, _PAGE_KEYS, where, errors):
            continue
        if page["page"] != index or not _is_int(page["page"]):
            errors.append(f"{where}.page : numérotation continue 1..N attendue (attendu {index})")
        unit = page["unit_id"]
        if not isinstance(unit, str) or not _UNIT_ID.fullmatch(unit):
            errors.append(f"{where}.unit_id : identifiant invalide")
        elif unit in seen_units:
            errors.append(f"{where}.unit_id : doublon {unit}")
        else:
            seen_units.add(unit)
        mechanic = MECHANICS.get(page["mechanic"]) if isinstance(page["mechanic"], str) else None
        if mechanic is None:
            errors.append(f"{where}.mechanic : mécanique non prise en charge ({', '.join(MECHANICS)})")
        params = page["params"]
        if not isinstance(params, dict):
            errors.append(f"{where}.params : objet attendu")
        elif mechanic is not None:
            errors.extend(f"{where}.params : {message}" for message in mechanic.check_params(params))
        _check_text(page["scene"], f"{where}.scene", MAX_SCENE, errors)
        _check_text(page["prompt_fr"], f"{where}.prompt_fr", MAX_PROMPT_FR, errors)
        _check_text(page["prompt_en"], f"{where}.prompt_en", MAX_PROMPT_EN, errors)
        if mechanic is not None and isinstance(params, dict):
            parsed.append(PageSpec(page["page"], str(unit), mechanic.name, MappingProxyType(dict(params)),
                                   str(page["scene"]), str(page["prompt_fr"]), str(page["prompt_en"])))
    try:
        verify_text_policy(data, forbidden_names=SYNTHETIC_FORBIDDEN_NAMES, location="source")
    except UnsafeEditorialText as exc:
        errors.append(f"politique de texte : {exc}")
    if errors:
        raise ContractError(errors)
    return SpecSet(data["schema"], data["kind"], data["spec_id"], data["title"], data["publisher"],
                   (float(trim["width_in"]), float(trim["height_in"])), (band[0], band[1]), data["seed"],
                   tuple(parsed), sha256_hex(bytes(payload)))


def read_bounded(path: str | os.PathLike, max_bytes: int, *, label: str, error=EngineError) -> bytes:
    """Read a regular file of at most ``max_bytes``, validated on the OPENED descriptor.

    The file is opened once with O_NOFOLLOW | O_NONBLOCK (a symlink is refused, a FIFO does
    not block), ``fstat`` runs on that same descriptor (regular file, size limit) and at most
    ``max_bytes + 1`` bytes are read from it, so a file that grows after the size check is
    still refused. Nothing larger than the limit is ever loaded.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise error(f"{label} : illisible ou lien symbolique refusé ({exc.strerror or exc})") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise error(f"{label} : fichier régulier requis (tube, périphérique ou répertoire refusé)")
        if info.st_size > max_bytes:
            raise error(f"{label} : fichier trop volumineux ({info.st_size} octets, limite {max_bytes})")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(max_bytes + 1)
    finally:
        os.close(fd)
    if len(data) > max_bytes:
        raise error(f"{label} : fichier trop volumineux ou grossi pendant la lecture (limite {max_bytes})")
    return data


def read_source_file(path: str | os.PathLike) -> bytes:
    """Read a source file: regular file, no symlink, bounded size."""
    return read_bounded(path, MAX_SOURCE_BYTES, label="source", error=ContractError)


def load_spec_set(path: str | os.PathLike) -> SpecSet:
    return parse_spec_set(read_source_file(path))
