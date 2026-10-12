"""Grouping of the missing developments and the dependency-based implementation order."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

# id -> definition. ``mechanics`` are plan types; ``depends_on`` are real build dependencies.
COMPONENTS: tuple[dict[str, Any], ...] = (
    {"id": "C1", "key": "page_contract", "label": "Contrat de page de production et chargeur du scénario B",
     "mechanics": (), "depends_on": (), "priority": 0,
     "reuses": ("lafractale.scenario_b.sources (B3-B.2)", "engine.contracts (JSON strict, JSON canonique, SHA-256)",
                "security.text (politique Unicode)"),
     "work": ("schéma fermé de page (type, payload, réponse, FR/EN, assets, approbations, page source/finale)",
              "chargeur du scénario B actif en remplacement de books/halloween_2026/page_plan.csv, sans l'écraser",
              "levée contrôlée de la restriction « fixtures synthétiques » pour des sources réelles, sans génération de production"),
     "rationale": "Tous les autres composants lisent ce schéma ; aucune page réelle n'est productible tant que le contrat refuse les sources non synthétiques."},
    {"id": "C2", "key": "primitives_generalisation", "label": "Généralisation de maze, connect_dots et match",
     "mechanics": ("maze", "connect_dots", "match"), "depends_on": ("C1",), "priority": 1,
     "reuses": ("activities.engine (générateurs)", "engine.solvers (vérification indépendante)", "profil éditorial C4"),
     "work": ("maze : paramètre de taille/difficulté (p.43 exigence élevée), scènes par page",
              "connect_dots : silhouette maison à nombre de points déclaré (p.17), croissant C4 inchangé",
              "match : famille 'hats' ouverte au registre, association hétérogène invité→objet (p.46), 4 paires fixes à confirmer"),
     "rationale": "Débloque 7 pages avec le code déjà vérifié ; fournit la bijection et le graphe de labyrinthe réutilisés ensuite."},
    {"id": "C3", "key": "assets_registry", "label": "Registre d'assets multi-rôles (scènes, objets, pictogrammes)",
     "mechanics": (), "depends_on": ("C1",), "priority": 2,
     "reuses": ("illustrations.registry (SHA-256, approbation séparée)", "assets/illustrations/approvals.json"),
     "work": ("rôles scène/objet/pictogramme/trait de coloriage avec provenance, droits et SHA-256",
              "routage et placement par page ; les assets C4 ne deviennent pas réutilisables par défaut"),
     "rationale": "Quatre familles sur cinq dépendent d'illustrations approuvées ; l'approbation humaine est le chemin le plus long, à lancer tôt."},
    {"id": "C4", "key": "answers_condensed", "label": "Corrigés condensés p.49-54 (31 entrées, 6/5/5/5/5/5)",
     "mechanics": ("answers",), "depends_on": ("C1", "C2"), "priority": 3,
     "reuses": ("fiche/corrigé du moteur", "layout.composition"),
     "work": ("mise en page condensée avec renvoi à la page source", "rendu de solution par mécanique (incrémental)",
              "aucune activité libre dans les corrigés"),
     "rationale": "Se construit avec les solutions de chaque famille ; le cadre peut être posé dès que C2 fournit trois rendus de solution."},
    {"id": "C5", "key": "association_sort", "label": "Famille associations et tri",
     "mechanics": ("shadow_match", "match_vocabulary", "pair_matching", "one_to_one", "sort"),
     "depends_on": ("C2", "C3"), "priority": 4,
     "reuses": ("vérification de bijection de match", "registre de pictogrammes"),
     "work": ("paires silhouette/objet, mot/image, objets identiques, 1:1 et tri sans couleur",
              "vérificateurs de solution unique", "lien avec le lexique p.55"),
     "rationale": "Famille la plus proche de match : réutilise directement la bijection et son vérificateur (C2)."},
    {"id": "C6", "key": "count_search", "label": "Famille comptage et recherche",
     "mechanics": ("find_count", "count"), "depends_on": ("C1", "C3"), "priority": 5,
     "reuses": ("placement déterministe de scène", "réponse chiffrée"),
     "work": ("placement d'objets cibles et leurres sans chevauchement", "vérification des comptes", "corrigé chiffré ou repéré"),
     "rationale": "Aucune mécanique voisine à réutiliser ; dépend des objets approuvés de C3."},
    {"id": "C7", "key": "trace_sequence_logic", "label": "Famille tracés, séquences et logique",
     "mechanics": ("trace_paths", "path_logic", "pattern", "spot_differences"),
     "depends_on": ("C2", "C3"), "priority": 6,
     "reuses": ("graphe de labyrinthe de maze", "vérificateur de croisements de connect_dots"),
     "work": ("tracés guidés et chemins sans croisement", "suites avec élément manquant", "scènes à différences contrôlées"),
     "rationale": "Réutilise le graphe de maze et la géométrie de connect_dots ; p.22 reste soumise à revue humaine des données."},
    {"id": "C8", "key": "free_drawing", "label": "Famille dessin libre et coloriage",
     "mechanics": ("coloring", "creative_color"), "depends_on": ("C3",), "priority": 7,
     "reuses": ("composition de fiche",),
     "work": ("gabarits à grandes zones et zones de création libre", "aucune réponse ni corrigé"),
     "rationale": "Techniquement simple mais entièrement conditionné par les traits approuvés de C3 ; p.42, p.45 et p.47 sont des respirations sans corrigé."},
    {"id": "C9", "key": "special_layouts", "label": "Layouts spéciaux (ouverture, lexique 18 paires, diplôme/clôture)",
     "mechanics": ("front_matter", "glossary typographique", "diploma + back_matter"),
     "depends_on": ("C1",), "priority": 8,
     "reuses": ("layout.composition", "politique de texte"),
     "work": ("p.01-02 ouverture", "p.55 lexique 18 paires sans pictogramme non approuvé",
              "p.56 diplôme protégeant la zone prénom/cercle/consigne à 100 %"),
     "rationale": "Indépendant des mécaniques mais bloqué par les copies de production absentes (blocage éditorial, pas technique)."},
    {"id": "C10", "key": "closed_export", "label": "Export fermé, manifeste et préflight",
     "mechanics": (), "depends_on": ("C4", "C5", "C6", "C7", "C8", "C9"), "priority": 9,
     "reuses": ("export.builder", "inventaire fermé des sorties", "tools/preflight_b2c3.py"),
     "work": ("intérieur 56 pages, aperçus, manifeste complet, inventaire de sortie versionné",),
     "rationale": "Dernier maillon ; reste interdit tant que les statuts permanents n'ont pas été levés par décision humaine."},
)


def implementation_order(page_counts: Mapping[str, int]) -> list[dict[str, Any]]:
    """Topological order (Kahn), ties broken by the static priority."""
    by_id = {c["id"]: c for c in COMPONENTS}
    done: set[str] = set()
    order: list[dict[str, Any]] = []
    pending = sorted(by_id.values(), key=lambda c: c["priority"])
    while pending:
        ready = [c for c in pending if all(d in done for d in c["depends_on"])]
        if not ready:  # defensive: the static graph is acyclic
            raise ValueError("dépendances cycliques dans le catalogue de composants")
        nxt = ready[0]
        pending.remove(nxt)
        done.add(nxt["id"])
        order.append({
            "rank": len(order) + 1, "component": nxt["id"], "key": nxt["key"], "label": nxt["label"],
            "pages_covered": page_counts.get(nxt["id"], 0), "depends_on": list(nxt["depends_on"]),
            "reuses": list(nxt["reuses"]), "work": list(nxt["work"]), "rationale": nxt["rationale"],
        })
    return order


def component_for_mechanic(plan_type: str) -> str | None:
    for component in COMPONENTS:
        if plan_type in component["mechanics"]:
            return component["id"]
    return None


def group_pages(pages: Iterable[Mapping[str, Any]]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for page in pages:
        plan_type = page.get("plan_type")
        if plan_type is None:
            continue
        component = component_for_mechanic(plan_type)
        if component is not None:
            grouped.setdefault(component, []).append(page["page"])
    return {key: sorted(value) for key, value in sorted(grouped.items())}
