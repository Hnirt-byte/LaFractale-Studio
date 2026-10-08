"""Configuration/plan validation; a planned book is NOT a finished book."""
from __future__ import annotations

import csv
import hashlib
import json
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml
from .companions import CompanionProfile, CompanionError, resolve_companion, verify_companion_text, _read_file


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Book:
    path: Path
    root: Path
    data: dict[str, Any]
    plan: tuple[dict[str, str], ...]
    companion: CompanionProfile
    # Source provenance pins the book content and plan read by load_book.
    source_sha256: str = ""
    data_sha256: str = ""
    plan_sha256: str = ""
    source_plan_sha256: str | None = None

    @property
    def book_id(self) -> str:
        return self.data["book_id"]

    @property
    def pages(self) -> int:
        return self.data["interior"]["pages"]


def find_root(path: Path) -> Path:
    for parent in (path.parent, *path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent.resolve()
    raise ConfigError("Racine du projet introuvable (pyproject.toml)")


def within_root(root: Path, name: str) -> Path:
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ConfigError(f"Chemin hors du projet interdit : {name}")
    return p


def _hash_data(data: Any) -> str:
    try:
        encoded = json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CompanionError(f"Données du livre non canoniques : {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def verify_book_snapshot(book: Book) -> None:
    """Reject memory forgery/cross-book substitution and changed source bytes.

    The Python Book object is NOT an authorization token. A build may only use
    the exact YAML and page plan that were validated at load_book().
    """
    if type(book) is not Book or not all((book.source_sha256, book.data_sha256,
                                         book.plan_sha256)):
        raise CompanionError("Profil source du livre absent ou falsifié")
    try:
        root = book.root.resolve(strict=True)
        if root != find_root(book.path):
            raise CompanionError("Racine du livre modifiée depuis le chargement")
        rel = book.path.relative_to(root).as_posix()
        current = _read_file(root, rel, max_bytes=2_000_000)
    except (ValueError, OSError) as exc:
        raise CompanionError("Chemin de configuration du livre non fiable") from exc
    try:
        # Compare against the actual source, not only a mutable/replayable hash
        # stored in a dataclass. The latter can be forged with replace().
        source_data = yaml.safe_load(current.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CompanionError("Configuration source du livre invalide") from exc
    if (hashlib.sha256(current).hexdigest() != book.source_sha256
            or _hash_data(book.data) != book.data_sha256
            or _hash_data(book.data) != _hash_data(source_data)
            or _hash_data(book.plan) != book.plan_sha256):
        raise CompanionError("Configuration du livre modifiée depuis le chargement")
    plan_file = book.path.with_name("page_plan.csv")
    if book.source_plan_sha256 is not None:
        plan_rel = plan_file.relative_to(root).as_posix()
        plan_bytes = _read_file(root, plan_rel, max_bytes=2_000_000)
        try:
            source_plan = list(csv.DictReader(io.StringIO(plan_bytes.decode("utf-8-sig"), newline="")))
        except UnicodeDecodeError as exc:
            raise CompanionError("Plan éditorial invalide") from exc
        if (hashlib.sha256(plan_bytes).hexdigest() != book.source_plan_sha256
                or _hash_data(book.plan) != _hash_data(source_plan)):
            raise CompanionError("Plan éditorial modifié depuis le chargement")
    elif plan_file.exists() or plan_file.is_symlink():
        raise CompanionError("Plan éditorial ajouté depuis le chargement")


def load_book(source: str | Path, *, require_plan: bool = False) -> Book:
    path = Path(source).resolve()
    if not path.is_file():
        raise ConfigError(f"Configuration absente : {path}")
    root = find_root(path)
    source_bytes = _read_file(root, path.relative_to(root).as_posix(), max_bytes=2_000_000)
    try:
        data = yaml.safe_load(source_bytes.decode("utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise ConfigError(f"YAML invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("La racine YAML doit être un objet")
    errors: list[str] = []
    for key in ("book_id", "publisher", "title", "audience", "interior", "trim", "vocabulary", "companion"):
        if key not in data:
            errors.append(f"Champ obligatoire absent : {key}")
    if errors:
        raise ConfigError("; ".join(errors))
    for key in ("publisher", "title"):
        if not isinstance(data[key], str) or not data[key].strip():
            errors.append(f"{key} doit être une chaîne non vide")
    if not isinstance(data["book_id"], str) or not data["book_id"].replace("_", "").replace("-", "").isalnum():
        errors.append("book_id non valide")
    age = data["audience"]
    if not isinstance(age, dict) or any(not isinstance(age.get(k), int) or isinstance(age.get(k), bool) for k in ("age_min", "age_max")) or age.get("age_min", 100) > age.get("age_max", -1):
        errors.append("audience.age_min/age_max non valides")
    interior = data["interior"]
    if not isinstance(interior, dict) or not isinstance(interior.get("pages"), int) or isinstance(interior.get("pages"), bool) or not 1 <= interior["pages"] <= 300:
        errors.append("interior.pages doit être un entier entre 1 et 300")
    trim = data["trim"]
    if not isinstance(trim, dict) or any(not isinstance(trim.get(k), (float, int)) or isinstance(trim.get(k), bool) or not 4 <= trim[k] <= 15 for k in ("width_in", "height_in")):
        errors.append("trim.width_in/height_in hors limites")
    voc = data["vocabulary"]
    if not isinstance(voc, dict) or not voc or any(not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip() for k, v in voc.items()):
        errors.append("vocabulary doit être une table de traductions non vides")
    elif len({value.casefold() for value in voc.values()}) != len(voc):
        errors.append("Traductions anglaises en double dans vocabulary")
    if "mascot" in data:
        errors.append("mascot V0.1 obsolète : utiliser companion et le catalogue par livre")
    companion = None
    try:
        companion = resolve_companion(root, data["book_id"], data["companion"])
    except (CompanionError, KeyError) as exc:
        errors.append(str(exc) if str(exc) else "companion invalide")
    plan_file = path.with_name("page_plan.csv")
    rows: list[dict[str, str]] = []
    plan_bytes: bytes | None = None
    if plan_file.exists():
        plan_bytes = _read_file(root, plan_file.relative_to(root).as_posix(), max_bytes=2_000_000)
        with io.StringIO(plan_bytes.decode("utf-8-sig"), newline="") as fh:
            reader = csv.DictReader(fh)
            required = {"page", "chapter", "story_beat", "activity_type", "vocabulary", "status"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                errors.append("page_plan.csv : colonnes obligatoires absentes")
            else:
                rows = list(reader)
                if any(any(row.get(column) is None for column in required) for row in rows):
                    errors.append("page_plan.csv : ligne incomplète")
        if rows and isinstance(interior, dict) and isinstance(interior.get("pages"), int):
            try:
                numbers = [int(row["page"]) for row in rows]
                if numbers != list(range(1, interior["pages"] + 1)):
                    errors.append("page_plan.csv : pagination non continue ou nombre de pages incohérent")
            except (ValueError, TypeError):
                errors.append("page_plan.csv : index de page non entier")
    elif require_plan:
        errors.append("page_plan.csv manquant pour une construction complète")
    if errors:
        raise ConfigError("\n".join(errors))
    assert companion is not None
    try:
        verify_companion_text(root, companion, data, rows)
    except CompanionError as exc:
        raise ConfigError(str(exc)) from exc
    return Book(path, root, data, tuple(rows), companion,
                hashlib.sha256(source_bytes).hexdigest(), _hash_data(data),
                _hash_data(tuple(rows)),
                hashlib.sha256(plan_bytes).hexdigest() if plan_bytes is not None else None)


def validate_plan_vocabulary(book: Book) -> list[str]:
    """Unknown evaluated words are blockers; editorial-only placeholders are ignored."""
    vocabulary = book.data.get("vocabulary")
    if not isinstance(vocabulary, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in vocabulary.items()):
        return ["vocabulary invalide"]
    known = {word.casefold().strip() for word in (*vocabulary.keys(), *vocabulary.values())}
    meta = {"revision", "all", "well_done", "présentation", "", book.book_id.split("_", 1)[0].casefold()}
    if book.companion.selected and book.companion.render_name:
        meta.add(f"mission de {book.companion.render_name.casefold()}")
    errors = []
    for row in book.plan:
        raw_terms = row.get("vocabulary")
        if not isinstance(raw_terms, str):
            errors.append(f"Page {row.get('page', '?')} : vocabulaire de plan invalide")
            continue
        for term in raw_terms.split(";"):
            word = term.strip().casefold()
            if word not in known | meta:
                errors.append(f"Page {row.get('page', '?')} : vocabulaire absent du lexique : {term}")
    return errors
