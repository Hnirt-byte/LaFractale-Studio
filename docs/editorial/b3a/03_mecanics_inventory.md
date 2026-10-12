# Inventaire des mécaniques et des frontières de production

## État réellement présent sur `main`

Le moteur ne génère actuellement que trois mécaniques : `maze`, `connect_dots` et `match`. La fonction de planification bloque explicitement un assemblage complet lorsqu'une page utilise tout autre type. Le cahier 56 pages ne peut donc pas être construit à ce stade.

| État | Mécaniques / surface | Limite vérifiée |
|---|---|---|
| Implémenté pour la démo | `maze`, `connect_dots`, `match` | Trois générateurs structurés et déterministes uniquement. |
| Démo C4 canonique | p.04 `maze`, p.06 `connect_dots`, p.20 `match` | Overlay C4 opt-in, strictement limité à ces identités ; la lune p.06 est un croissant fermé à 8 points. |
| Partiel / non généralisé | Routage et placement Pip | C1/C2/C4 n'autorisent que les trois pages de démo. Les rôles Pip B3-A des autres pages ne sont pas activables. |
| Absent du moteur | `front_matter`, `coloring`, `find_count`, `shadow_match`, `creative_color`, `trace_paths`, `count`, `match_vocabulary`, `spot_differences`, `pattern`, `path_logic`, `pair_matching`, `sort`, `one_to_one`, `mini_logic`, `diploma`, `answers`, `glossary`, `back_matter` | Aucun générateur, layout ou QA de production complet ne doit être supposé. |

## Conséquence

B3-A ne propose aucune implémentation. Toute future phase devra établir, mécanique par mécanique, les règles de génération, les réponses non ambiguës, les tests, le rendu, l'accessibilité 4–5 ans et les contrôles d'impression. Les 56 lignes documentaires ne donnent pas de permission d'appeler le moteur pour un livre complet.
