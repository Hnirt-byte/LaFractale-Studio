"""Engine capability facts and the technical compatibility of each page.

Technical status is derived ONLY from what the engine really provides and from
the page requirements; it is independent from the editorial validation state.
A matching mechanic name never makes a page compatible on its own.
"""
from __future__ import annotations

from typing import Any, Mapping

from lafractale.activities.engine import SHAPES, SUPPORTED, generate
from lafractale.activities.models import ActivitySpec
from lafractale.editorial import (
    EDITORIAL_HALLOWEEN_V1,
    _CANONICAL_HALLOWEEN_EDITORIAL_V1,
    _PROMPT_CONNECT_EN,
    _PROMPT_CONNECT_FR,
)
from lafractale.engine.registry import MECHANICS
from lafractale.scenario_b import TECH_STATUSES

# Plan page kinds that are not activities.
LAYOUT_TYPES = {
    "front_matter": "front_matter",
    "answers": "answers",
    "glossary typographique": "glossary",
    "diploma + back_matter": "closing",
}
FREE_TYPES = frozenset({"coloring", "creative_color"})

#: mechanic -> (family, short label). Families group the missing developments.
FAMILIES: Mapping[str, str] = {
    "maze": "existing_primitives", "connect_dots": "existing_primitives", "match": "existing_primitives",
    "coloring": "free_drawing", "creative_color": "free_drawing", "trace_paths": "trace_sequence_logic",
    "find_count": "count_search", "count": "count_search",
    "shadow_match": "association_sort", "match_vocabulary": "association_sort",
    "pair_matching": "association_sort", "one_to_one": "association_sort", "sort": "association_sort",
    "pattern": "trace_sequence_logic", "spot_differences": "trace_sequence_logic", "path_logic": "trace_sequence_logic",
}

#: What an absent mechanic needs (technical development only).
MECHANIC_NEEDS: Mapping[str, tuple[str, ...]] = {
    "coloring": ("gabarit de coloriage (grandes zones) sur illustration au trait approuvée",),
    "creative_color": ("gabarit de page libre (zone de création, aucune réponse attendue)",),
    "trace_paths": ("générateur de tracés (guides) et vérificateur de non-croisement/continuité",
                    "corrigé graphique du tracé"),
    "find_count": ("placement déterministe d'objets cibles/leurres dans une scène",
                   "vérificateur de comptage/unicité des cibles", "corrigé avec repérage des cibles"),
    "count": ("générateur d'ensembles dénombrables", "réponse chiffrée vérifiée", "corrigé de type chiffre"),
    "shadow_match": ("paires silhouette/objet avec ombres distinctes", "vérificateur de bijection non triviale"),
    "match_vocabulary": ("paires mot/image lues par un adulte", "pictogrammes approuvés (p.55 sans pictogramme non approuvé)",
                         "lien explicite avec le lexique p.55"),
    "pair_matching": ("détection de paires identiques dans une grille d'objets", "unicité des paires"),
    "one_to_one": ("correspondance terme à terme 1-5 (hétérogène)", "vérificateur de bijection"),
    "sort": ("critère de tri explicite sans couleur (noir et blanc)", "vérificateur de classification unique"),
    "pattern": ("générateur de suites avec élément manquant", "vérificateur de solution unique"),
    "spot_differences": ("deux scènes dérivées avec différences contrôlées", "vérificateur du nombre de différences"),
    "path_logic": ("graphe de chemins avec croisements maîtrisés", "vérificateur de chemin unique non croisé"),
}

#: Page-level gaps for pages whose mechanic exists in the engine.
EXISTING_GAPS: Mapping[str, tuple[str, ...]] = {
    "maze": ("liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement)",
             "scène/habillage et routage d'illustration propres à la page", "paramètre de taille/difficulté absent (grille 5x5 fixe)",
             "ligne de corrigé condensé p.49-54"),
    "connect_dots": ("liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement)",
                     "silhouette et nombre de points propres à la page non spécifiés", "ligne de corrigé condensé p.49-54"),
    "match": ("liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement)",
              "ligne de corrigé condensé p.49-54"),
}


def engine_facts() -> dict[str, Any]:
    """Facts measured on the real engine (generation is deterministic and in-memory)."""
    maze_geo = generate(ActivitySpec("probe-maze", 1, "maze", (4, 5), "probe", ()), 1).geometry
    match_geo = generate(ActivitySpec("probe-match", 1, "match", (4, 5), "probe", ()), 1).geometry
    families = sorted({generate(ActivitySpec("probe-match", 1, "match", (4, 5), "probe", vocab), 1).geometry["family"]
                       for vocab in ((), ("hat",), ("gift",))})
    return {
        "generators": sorted(SUPPORTED),
        "registry_mechanics": {
            name: {"params": {k: list(v) for k, v in mech.params.items()}, "required": list(mech.required)}
            for name, mech in sorted(MECHANICS.items())},
        "maze": {"size_fixed": maze_geo["size"], "size_parameter": "size" in MECHANICS["maze"].params,
                 "uniqueness_verifier": True},
        "connect_dots": {"shapes": {name: len(points) for name, points in sorted(SHAPES.items())},
                         "editorial_override": f"{EDITORIAL_HALLOWEEN_V1}: croissant à 8 points (p.06 seulement)"},
        "match": {"pairs_fixed": len(match_geo["left_symbols"]), "relation": "jumeaux identiques (colonnes de mêmes symboles)",
                  "registry_families": list(MECHANICS["match"].params["family"]),
                  "generator_families": families},
        "editorial_profile": {"id": EDITORIAL_HALLOWEEN_V1,
                              "pages": sorted(page for _, _, page, _ in _CANONICAL_HALLOWEEN_EDITORIAL_V1)},
        "production_contract": "B3-B.1 : sources synthétiques uniquement, 12 fiches maximum, aucun asset ni livre réel",
    }


def c4_pilot_pages() -> dict[int, str]:
    return {page: kind for _, _, page, kind in _CANONICAL_HALLOWEEN_EDITORIAL_V1}


def c4_connect_prompts() -> tuple[str, str]:
    return _PROMPT_CONNECT_FR, _PROMPT_CONNECT_EN


def _result(status: str, family: str | None, reasons: list[str], missing: list[str],
            questions: list[str] | None = None) -> dict[str, Any]:
    assert status in TECH_STATUSES
    return {"status": status, "family": family, "reasons": reasons, "missing_capabilities": missing,
            "open_questions": questions or []}


def evaluate_page(page: int, plan_type: str, demand_level: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    """Technical compatibility of one page. Pure function of engine facts and page requirements."""
    pilots = {p: k for p, k in c4_pilot_pages().items()}
    if plan_type in LAYOUT_TYPES:
        return _result("UNSUPPORTED", "special_layouts",
                       [f"Aucune composition pour la page '{plan_type}' : le moteur ne compose que des fiches d'activité et leur corrigé."],
                       ["composition de page spéciale (hors fiche d'activité)"])
    mechanic = plan_type
    family = FAMILIES.get(mechanic)
    if family is None:
        return _result("UNKNOWN", None, [f"Type '{plan_type}' inconnu du lecteur : capacité non évaluable."], [],
                       [f"Définir les exigences techniques du type '{plan_type}'."])
    if mechanic not in facts["generators"]:
        return _result("UNSUPPORTED", family,
                       [f"Mécanique '{mechanic}' absente du moteur (générateurs : {', '.join(facts['generators'])})."],
                       list(MECHANIC_NEEDS.get(mechanic, ("générateur et vérificateur indépendant de la mécanique",))))
    # The mechanic exists: judge the page, not the name.
    if pilots.get(page) == mechanic:
        return _result("SUPPORTED", family,
                       [f"Pilote C4 couvert de bout en bout par le profil {facts['editorial_profile']['id']} "
                        f"(génération, vérification indépendante de la solution, rendu, corrigé)."], [])
    reasons = [f"Générateur '{mechanic}' disponible, mais la page n'est pas couverte de bout en bout "
               f"(profil éditorial limité aux pages {facts['editorial_profile']['pages']})."]
    missing = list(EXISTING_GAPS[mechanic])
    questions: list[str] = []
    if mechanic == "maze" and demand_level.strip().upper() == "HIGH":
        reasons.append("Exigence élevée (labyrinthe final) : aucun paramètre de taille/difficulté, grille 5x5 fixe.")
    if mechanic == "connect_dots":
        shapes = facts["connect_dots"]["shapes"]
        reasons.append(f"Formes disponibles : {', '.join(f'{k} ({v} pts)' for k, v in shapes.items())} ; "
                       "le nombre de points exigé par la page n'est pas spécifié.")
        questions.append("Nombre de points et silhouette attendus pour cette page ?")
    if mechanic == "match":
        if page == 46:
            reasons.append("Le moteur associe des jumeaux identiques (4 paires fixes), non des éléments hétérogènes.")
            missing.append("association hétérogène invité→objet avec indices narratifs (le vérificateur exige des colonnes identiques)")
        else:
            reasons.append("Le moteur associe des jumeaux identiques (4 paires fixes) ; la famille 'hats' n'est pas ouverte dans le registre B3-B.1.")
            missing.append("famille de symboles 'hats' non ouverte dans le registre (seule 'shapes' l'est)")
    return _result("PARTIAL", family, reasons, missing, questions)
