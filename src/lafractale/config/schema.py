"""Configuration/plan validation; a planned book is NOT a finished book."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Book:
    path: Path
    root: Path
    data: dict[str, Any]
    plan: tuple[dict[str, str], ...]

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


def load_book(source: str | Path, *, require_plan: bool = False) -> Book:
    path = Path(source).resolve()
    if not path.is_file():
        raise ConfigError(f"Configuration absente : {path}")
    root = find_root(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("La racine YAML doit être un objet")
    errors: list[str] = []
    for key in ("book_id", "publisher", "title", "audience", "interior", "trim", "vocabulary"):
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
    mascot = data.get("mascot", {})
    if not isinstance(mascot, dict):
        errors.append("mascot doit être une table")
    elif mascot:
        ref = mascot.get("approved_reference")
        if not isinstance(ref, str) or not ref:
            errors.append("mascot.approved_reference doit pointer vers une ressource officielle")
        else:
            p = within_root(root, ref)
            if not p.is_file():
                errors.append(f"Asset officiel absent : {ref}")
        if mascot.get("require_bow_tie") is not True:
            errors.append("mascot.require_bow_tie doit être true pour Pip")
    plan_file = path.with_name("page_plan.csv")
    rows: list[dict[str, str]] = []
    if plan_file.exists():
        with plan_file.open(encoding="utf-8-sig", newline="") as fh:
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
    return Book(path, root, data, tuple(rows))


def validate_plan_vocabulary(book: Book) -> list[str]:
    """Unknown evaluated words are blockers; editorial-only placeholders are ignored."""
    vocabulary = book.data.get("vocabulary")
    if not isinstance(vocabulary, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in vocabulary.items()):
        return ["vocabulary invalide"]
    known = {word.casefold().strip() for word in (*vocabulary.keys(), *vocabulary.values())}
    meta = {"revision", "all", "halloween", "well_done", "présentation", "mission de pip", ""}
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
