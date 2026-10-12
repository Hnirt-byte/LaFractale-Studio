# Harmonisation p.06 et traçabilité CI

## Canon actif p.06

| Élément | Valeur |
|---|---|
| Titre | `La lune mystérieuse` |
| Tracé | croissant fermé `1→2→3→4→5→6→7→8→1` |
| FR | `Relie les points de 1 à 8, puis reviens au 1.` |
| EN | `Connect the dots from 1 to 8, then back to 1.` |
| Statut | `C4_LOCKED` |

Les documents actifs corrigés comprennent le chemin de fer consolidé et le CSV des corrigés B3-A.2. Les mentions historiques de `Le croissant de lune` dans `source_pack/` et dans les constats historiques restent des traces de provenance, explicitement non actives.

## CI GitHub observée sur le commit exact

Commit : `bb4c97f5b0ed0e618b436663b80b82b7aee2a012`.

| Run | Événement | Job | Résultat |
|---:|---|---:|---|
| 38158153595 | pull_request | 114525293145 | SUCCESS |
| 38158148098 | push | 114525278483 | SUCCESS |

Toute modification B3-A.3 postérieure à ce commit impose une nouvelle lecture CI ; ces preuves ne pré-approuvent pas un commit futur.
