# B3-B.3b — Mécaniques v2 (incrément B3-B.3b.1 : socle commun + `maze_v2`)

```text
kind                  = SYNTHETIC_NON_PRODUCTION
production_authorized = false   (constante du code)
ready_for_kdp         = false
MAJOR-03              = OPEN
MAJOR-04              = OPEN
EDITORIAL             = PENDING
KDP                   = FORBIDDEN
PRODUCTION_GENERATION = FORBIDDEN
```

Package `src/lafractale/mechanics_v2/` : `core.py` (socle), `maze.py` (spécification et générateur), `maze_verify.py` (vérification
indépendante), `registry.py` (registre fermé `MECHANICS_V2`). Seul `maze_v2` existe dans cet incrément ; `connect_dots_v2` et `match_v2`
viennent dans B3-B.3b.2 et B3-B.3b.3, après validation.

## Périmètre et séparation

* **Aucune donnée éditoriale réelle.** Ni `PageRecord`, ni CSV, ni statut de validation ne déclenchent ou ne paramètrent une génération :
  le package n'importe pas `scenario_b`, ne lit aucun fichier, aucune variable d'environnement, aucun argument. L'identifiant d'activité
  doit être explicitement synthétique (`syn-…`) : `P03-ACTIVITY`, un titre de page ou un nom de livre sont refusés.
* **Pas de rendu** (D3) : géométrie, solution, mesures et vérification uniquement. Rien n'est écrit sur disque.
* **Aucune modification historique** : `activities/engine.py`, `engine/registry.py`, `engine/solvers.py`, `editorial.py`, le profil C4 et le
  contrat B3-B.1 sont inchangés ; aucun module historique n'importe `mechanics_v2` (testé). `maze_v2` réutilise seulement
  `engine.solvers.maze_unique_path` comme second avis de vérification.
* **Aucune autorisation de production** : `production_authorized` est `False` partout, constante du code, non paramétrable.

## API

```python
from lafractale.mechanics_v2.registry import generate_v2, verify_v2
activity = generate_v2("maze_v2", "syn-demo", seed=1, params={"size": 5, "difficulty": "medium"})
verify_v2(activity)          # [] si valide ; accepte aussi un dict (JSON relu)
activity.canonical_bytes()   # octets canoniques ; activity.fingerprint = SHA-256
```

`generate_v2` régénère puis **revérifie** : un enregistrement qui échoue à sa propre vérification n'est jamais renvoyé (`SELF_CHECK_FAILED`).
Les paramètres sont un ensemble fermé : toute clé inconnue ou absente est refusée (`UNKNOWN_PARAM`, `MISSING_PARAM`).

| Entrée | Contrainte | Erreur |
|---|---|---|
| `activity_id` | `syn-` puis minuscules/chiffres/tirets, ≤ 50 car. | `BAD_ACTIVITY_ID` |
| `seed` | entier (pas booléen) entre 0 et 2⁶³−1 | `BAD_SEED` |
| `size` | entier de 3 à 12 inclus | `BAD_SIZE` |
| `difficulty` | `easy`, `medium` ou `hard` | `BAD_DIFFICULTY` |

## `maze_v2`

Labyrinthe parfait (arbre couvrant de la grille N×N : N²−1 passages), départ (0,0), arrivée (N−1,N−1), chemin unique.

### Niveaux de difficulté — critères techniques mesurables

Mesures : `L` = nombre de pas du chemin solution (toujours pair : grille bipartite, coins opposés) ; `Lmin = 2(N−1)` ; excès `E = L − Lmin`
comparé à `span = (N−1)²` (excès maximal) ; `D` = impasses (cellules à un seul passage, départ et arrivée exclus) ; `B` = points de
choix sur le chemin (cellules du chemin offrant au moins un passage qui en sort).

| Niveau | Bande d'excès | Contraintes de ramification |
|---|---|---|
| `easy` | 4·E ≤ span | B ≤ N |
| `medium` | 4·E > span et 2·E ≤ span | B ≥ ⌊N/2⌋ |
| `hard` | 2·E > span | B ≥ ⌊(N−3)/2⌋ et D ≥ ⌊(N−3)/2⌋ |

Arithmétique entière uniquement ; les trois bandes sont disjointes et couvrent tous les cas. **Ce sont des paramètres techniques, pas un
jugement pédagogique** : aucune relecture humaine de l'adéquation à l'âge n'a été faite (`human_pedagogical_validation = "NONE"`).
Les 30 couples taille × niveau sont satisfaisables (testés sur plusieurs graines ; au plus 142 tentatives observées sur 1 200 générations).

### Recherche déterministe bornée, échec explicite

La tentative `i` (0 ≤ i < `MAX_ATTEMPTS` = 5 000) dérive son flux pseudo-aléatoire de `(activity_id, seed, size, difficulty, i)` et utilise
tour à tour trois algorithmes d'arbre couvrant (`backtracker`, `kruskal`, `prim`). Le premier labyrinthe qui satisfait **toutes** les
contraintes du niveau est renvoyé. Sinon : `V2Error` de code `UNSATISFIABLE`. **Aucune contrainte n'est jamais assouplie.** Le PRNG est un
générateur SHA-256 en mode compteur (`DetRng`) : le flux ne dépend pas de la version de Python (empreintes identiques en 3.11 et 3.13).

### Vérification indépendante

`verify_maze_v2` ne s'appuie sur aucun élément du générateur : passages canoniques (triés, uniques, adjacents, dans la grille), arbre couvrant
(union-find : N²−1 passages, aucun cycle, une composante), chemin unique (parcours en profondeur itératif) comparé au chemin déclaré **et** à
`maze_unique_path` (vérificateur historique), mesures et niveau recalculés, `params`/`search` cohérents, empreinte recalculée.

## Sérialisation canonique (schéma `lafractale-mechanics-v2-activity-v1`)

UTF-8 ; JSON avec clés triées lexicographiquement à tous les niveaux, séparateurs `,` et `:` sans espace, `ensure_ascii=False` ; entiers,
chaînes, booléens, `null`, tableaux et objets uniquement (flottants, NaN, clés non textuelles refusés). Champs de premier niveau :
`activity_id`, `fingerprint`, `geometry`, `human_pedagogical_validation`, `kind`, `measures`, `mechanic`, `params`, `production_authorized`,
`schema`, `search`, `seed`, `solution`, `version`. `fingerprint` = SHA-256 hexadécimal minuscule des octets canoniques de l'enregistrement
**sans** la clé `fingerprint`. `loads_record` relit strictement (clés dupliquées refusées) et exige que les octets soient déjà canoniques.

Pour `maze_v2` : `geometry = {size, start, goal, open_edges}` (passages `[[x,y],[x,y]]`, plus petite cellule d'abord, triés), `solution = {path,
steps}`, `measures = {path_length, dead_ends, decisions, minimum_path_length, span}`, `search = {algorithm, attempts, max_attempts}`.
Les objets Python (`V2Activity`, `FrozenDict`) sont profondément immuables ; `to_dict()` renvoie une copie indépendante.

## Limites

* Aucune validation pédagogique humaine : les niveaux mesurent la structure du labyrinthe, pas sa difficulté pour un enfant de 4–5 ans.
* Pas de rendu, pas de lisibilité graphique : les épaisseurs de murs, le masquage et l'occultation relèvent de l'issue #15 et de la QA du moteur.
* La recherche borne le coût (5 000 tentatives) ; le seul résultat négatif possible est l'échec explicite `UNSATISFIABLE`.
* Les pages réelles (p.14, p.43) ne sont pas branchées : leurs paramètres éditoriaux (départ, parcours, taille) restent à fixer par les humains.
