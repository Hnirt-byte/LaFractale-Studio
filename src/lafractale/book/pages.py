"""Lecture de pages.csv : une ligne par page du livre, source unique du chemin livre."""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

EXPECTED_PAGES = 56
ANSWER_PAGES = {49: 6, 50: 5, 51: 5, 52: 5, 53: 5, 54: 5}  # répartition canonique, 31 corrigés
FIELDS = ("page", "type", "gabarit", "title", "prompt_fr", "prompt_en", "answer_page",
          "params", "pip_pose", "status", "review")


class BookError(ValueError):
    """Erreur de contenu du livre, formulée pour être lue par l'auteur."""


@dataclass(frozen=True)
class PageRow:
    page: int
    type: str
    gabarit: str
    title: str
    prompt_fr: str
    prompt_en: str
    answer_page: int | None
    params: dict[str, str]
    pip_pose: str
    status: str
    review: str


def _params(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in filter(None, (s.strip() for s in text.split(";"))):
        key, sep, value = item.partition("=")
        if not sep:
            raise BookError(f"paramètre mal formé : {item!r}")
        out[key.strip()] = value.strip()
    return out


def load_pages(path: Path) -> list[PageRow]:
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = set(FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise BookError(f"{path.name} : colonnes absentes {sorted(missing)}")
        raw = list(reader)
    rows = []
    for line, r in enumerate(raw, start=2):
        try:
            rows.append(PageRow(int(r["page"]), r["type"], r["gabarit"], r["title"].strip(),
                                r["prompt_fr"].strip(), r["prompt_en"].strip(),
                                int(r["answer_page"]) if r["answer_page"].strip() else None,
                                _params(r["params"]), r["pip_pose"], r["status"], r["review"]))
        except (ValueError, KeyError) as exc:
            raise BookError(f"{path.name} ligne {line} : {exc}") from exc
    check_pages(rows)
    return rows


def check_pages(rows: list[PageRow]) -> None:
    numbers = [r.page for r in rows]
    if numbers != list(range(1, EXPECTED_PAGES + 1)):
        raise BookError(f"pages.csv doit contenir exactement les pages 1 à {EXPECTED_PAGES}, dans l'ordre "
                        f"(trouvé {len(numbers)} lignes)")
    counts = Counter(r.answer_page for r in rows if r.answer_page is not None)
    if dict(counts) != ANSWER_PAGES:
        raise BookError(f"répartition des corrigés {dict(sorted(counts.items()))} "
                        f"différente de la répartition canonique {ANSWER_PAGES}")
    for r in rows:
        if r.gabarit not in ("chemin", "provisoire"):
            raise BookError(f"page {r.page} : gabarit inconnu {r.gabarit!r}")
        if r.gabarit == "provisoire" and r.type in ("maze", "connect_dots") and r.page in (4, 6):
            raise BookError(f"page {r.page} : page C4 verrouillée, gabarit chemin obligatoire")
