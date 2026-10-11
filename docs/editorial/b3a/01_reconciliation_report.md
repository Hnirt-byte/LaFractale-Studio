# Rapport de réconciliation — B3-A

## Verdict de compatibilité

**Compatible pour une branche documentaire uniquement : PASS AVEC DÉCISIONS ÉDITORIALES OUVERTES.**

Aucune divergence ne justifie de modifier `books/` ou les contrats B2-C4. La proposition B3-A est donc importée comme document de travail. Elle ne constitue ni une autorisation de construire les 56 pages, ni une validation humaine, ni une décision KDP.

## Sources contrôlées

| Élément | Référence vérifiée | Résultat |
|---|---|---|
| `origin/main` | commit `397bc32c042dcd5533296ac7fe76b6a3ad749347` | conforme |
| arbre Git | `72215ac28de46795338997be0bb38781274e80f4` | conforme |
| plan B2-B historique | `d77e32327fecd0c4a983ef8298581525842c18fc:books/halloween_2026/page_plan.csv` | SHA-256 `6dcc6d…f6099` |
| plan présent dans `main` | `books/halloween_2026/page_plan.csv` | même SHA-256, octet pour octet |
| `book.yaml`, bible, gates | fichiers de `main` au tree ancré | lus et référencés, non modifiés |
| pack B3-A v1.0 | 12 fichiers du manifeste importé | 12/12 SHA-256 conformes |
| tableur B3-A | onglets « 56 pages » et « Corrigés 4 pages » | équivalents structurellement aux CSV, 56 et 34 lignes |

## Diff sémantique B2-B historique → `main` B2-C4 → B3-A

- **B2-B historique → `main`** : aucune divergence du `page_plan.csv` : 56 pages, titres source et types sont identiques octet pour octet.
- **`main` → proposition B3-A** : aucune modification appliquée. La proposition enrichit chaque ligne par des titres, objectifs, consignes, rôles Pip, candidats d'assets, modalités de corrigé et points de validation ; ces valeurs ne sont pas des entrées du moteur.
- **B2-C4** : l'overlay C4 reste limité à la démo opt-in des pages 04, 06 et 20. Il n'autorise ni route Pip, ni placement, ni mise en page pour les 44 autres fiches d'activité.

## Pages pilotes C4 : réconciliation obligatoire

| Page | Référence canonique C4 | État de la proposition B3-A |
|---:|---|---|
| 04 | scène `Aide Pip à trouver la sortie`; labyrinthe à solution unique | titre aligné. Les consignes B3-A sont une reformulation à soumettre, pas un changement C4. |
| 06 | scène `La lune mystérieuse`; croissant fermé de 8 points; ordre obligatoire `1→8→1` | **décision ouverte** : B3-A propose `Le croissant de lune` et une formulation plus courte. La production devra reprendre C4 ou recevoir une validation humaine explicite. |
| 20 | scène `Retrouve les chapeaux jumeaux`; quatre paires | titre/intention alignés. L'anglais B3-A reste une proposition de relecture. |

## Invariants documentaires contrôlés

- Pagination 01–56 continue et unique : **PASS**.
- Structure : ouverture 2, quatre chapitres d'activités 48 pages dont diplôme p.50, corrigés p.51–54, lexique p.55, clôture p.56 : **PASS**.
- 17 mécaniques d'activité distinctes, sans répétition de mécanique sur deux activités successives : **PASS**.
- Les 18 paires du lexique réel `book.yaml` sont toutes couvertes dans les propositions : **PASS**.
- 34 activités objectivement corrigibles (31 graphiques + 3 chiffrées) correspondent exactement aux 34 lignes de la cartographie : **PASS**.
- Quatre tracés p.09/19/29/38 restent des « modèles facultatifs » et ne sont pas comptés comme réponses fermées : **documenté**.

## Réserve majeure, non contournée

Le document lisible intitule les pages 51–54 par chapitres, mais la cartographie équilibrée `9/9/8/8` répartit volontairement les réponses entre chapitres : p.51 contient aussi p.14–15, p.52 aussi p.24–27, p.53 aussi p.34–40, p.54 aussi p.41–49. Les titres « Invitation / Forêt / Amis / Bonbons et fête » ne décrivent donc pas strictement le contenu réel des quatre pages de solutions.

Cette incohérence est **ouverte et visible** ; elle n'est ni masquée ni appliquée aux fichiers de production. La recommandation documentaire est de renommer provisoirement les pages en « Corrigés 1–4 » avec renvois précis aux pages sources, ou de faire arbitrer une autre répartition avant B3-B.

## Conclusion

Le plan est réconcilié avec `main` pour le seul périmètre B3-A. Les décisions humaines listées dans `05_decisions_ouvertes.md` restent nécessaires avant toute phase de production.
