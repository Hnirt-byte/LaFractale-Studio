"""Translate an editorial plan into the explicitly supported demo specifications."""
from __future__ import annotations
from lafractale.config.schema import Book, ConfigError, verify_book_snapshot
from lafractale.config.companions import verify_companion_text
from lafractale.activities.models import ActivitySpec

# A demo is a technical proof, not a draft pretending to fill 56/80 pages.
DEMO_TYPES = {"maze", "connect_dots", "match"}


def _shape(terms: tuple[str, ...], explicit: str = "") -> str:
    if explicit:
        return explicit
    lower = {t.casefold() for t in terms}
    for word, aliases in (("moon", {"moon", "lune"}), ("house", {"house", "maison"}), ("star", {"star", "étoile"})):
        if lower.intersection(aliases):
            return word
    raise ConfigError("connect_dots : forme requise (moon, house ou star)")


def demo_specs(book: Book) -> list[ActivitySpec]:
    verify_companion_text(book.root, book.companion, book.data, book.plan)
    specs: list[ActivitySpec] = []
    explicit = book.data.get("demo_activities")
    if explicit is not None:
        if not isinstance(explicit, list) or len(explicit) != 3:
            raise ConfigError("demo_activities : exactement trois activités de démonstration")
        for row in explicit:
            if not isinstance(row, dict):
                raise ConfigError("demo_activities : chaque entrée doit être une table")
            missing = {"page", "type", "scene", "vocabulary"} - row.keys()
            if missing:
                raise ConfigError(f"demo_activities : attributs absents {sorted(missing)}")
            activity_type = row["type"]
            page = row["page"]
            scene = row["scene"]
            vocabulary = row["vocabulary"]
            if (not isinstance(activity_type, str) or activity_type not in DEMO_TYPES or
                    not isinstance(page, int) or isinstance(page, bool) or
                    not 1 <= page <= book.pages or not isinstance(scene, str) or not scene.strip() or
                    not isinstance(vocabulary, list) or not vocabulary or
                    any(not isinstance(term, str) or not term.strip() for term in vocabulary)):
                raise ConfigError("demo_activities : type/page/scene/vocabulary invalide")
            explicit_shape = row.get("shape", "")
            if not isinstance(explicit_shape, str):
                raise ConfigError("demo_activities : shape invalide")
            terms = tuple(vocabulary)
            if any(term not in book.data["vocabulary"] and term not in book.data["vocabulary"].values() for term in terms):
                raise ConfigError(f"demo_activities : mot absent du lexique : {terms}")
            specs.append(ActivitySpec(f"{book.book_id}-p{page:03d}", page, activity_type,
                                      (book.data["audience"]["age_min"],book.data["audience"]["age_max"]),
                                      scene, terms, _shape(terms, explicit_shape) if activity_type == "connect_dots" else "",
                                      companion_name=book.companion.render_name))
    else:
        if not book.plan:
            raise ConfigError("Aucun page_plan.csv ou demo_activities pour produire la démo")
        for activity_type in ("maze", "connect_dots", "match"):
            rows = [r for r in book.plan if r["activity_type"] == activity_type]
            if not rows:
                raise ConfigError(f"Plan : activité de démo absente : {activity_type}")
            row = rows[0]
            terms = tuple(t.strip() for t in row["vocabulary"].split(";") if t.strip())
            specs.append(ActivitySpec(f"{book.book_id}-p{int(row['page']):03d}", int(row["page"]), activity_type,
                                      (book.data["audience"]["age_min"],book.data["audience"]["age_max"]),
                                      row["story_beat"], terms, _shape(terms) if activity_type == "connect_dots" else "",
                                      companion_name=book.companion.render_name))
    if set(s.type for s in specs) != DEMO_TYPES:
        raise ConfigError("La démonstration doit couvrir maze, connect_dots et match")
    if len({s.page for s in specs}) != len(specs) or len({s.scene for s in specs}) != len(specs):
        raise ConfigError("Pages ou scènes de démonstration dupliquées")
    verify_book_snapshot(book)
    return specs


def full_build_blockers(book: Book) -> list[str]:
    blockers = []
    if not book.companion.selected:
        blockers.append("Compagnon non choisi ou non approuvé pour ce livre")
    if not book.plan:
        return blockers + ["page_plan.csv absent : aucun assemblage intégral possible"]
    # Only three activities are implemented, and front matter, glossary, etc. do
    # not yet have approved layout components. No dummy filler is permitted.
    unsupported = [(r["page"], r["activity_type"]) for r in book.plan if r["activity_type"] not in DEMO_TYPES]
    if unsupported:
        summary = ", ".join(f"p{p}:{t}" for p,t in unsupported)
        blockers.append("Mécaniques et pages éditoriales non implémentées V0.2-A : " + summary)
    return blockers
