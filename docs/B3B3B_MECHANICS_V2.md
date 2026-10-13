# B3-B.3b — Mécaniques v2 (B3-B.3b.1 : socle commun + `maze_v2` ; B3-B.3b.2 : `connect_dots_v2` ; B3-B.3b.3 : `match_v2`)

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

Package `src/lafractale/mechanics_v2/` : `core.py` (socle), `maze.py` / `maze_verify.py` (`maze_v2` : spécification, générateur, vérification
indépendante), `connect_dots.py` / `connect_dots_verify.py` (`connect_dots_v2`), `match.py` / `match_verify.py` (`match_v2`), `registry.py` (registre fermé `MECHANICS_V2`). Le registre
contient `maze_v2` (B3-B.3b.1), `connect_dots_v2` (B3-B.3b.2) et `match_v2` (B3-B.3b.3).

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
| `activity_id` | `syn-` puis minuscules/chiffres/tirets, 50 caractères au plus, sans tiret final | `BAD_ACTIVITY_ID` |
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
Les 30 couples taille × niveau sont satisfaisables : les tests parcourent chaque couple sur plusieurs graines et exigent un effort de recherche inférieur au dixième de la borne (quelques dizaines de tentatives en pratique).

### Recherche déterministe bornée, échec explicite

La tentative `i` (0 ≤ i < `MAX_ATTEMPTS` = 5 000) dérive son flux pseudo-aléatoire de `(activity_id, seed, size, difficulty, i)` et utilise
tour à tour trois algorithmes d'arbre couvrant (`backtracker`, `kruskal`, `prim`). Le premier labyrinthe qui satisfait **toutes** les
contraintes du niveau est renvoyé. Sinon : `V2Error` de code `UNSATISFIABLE`. **Aucune contrainte n'est jamais assouplie.** Le PRNG est un
générateur SHA-256 en mode compteur (`DetRng`) : le flux ne dépend pas de la version de Python (empreintes identiques en 3.11 et 3.13).

### Vérification indépendante

`verify_maze_v2` ne s'appuie sur aucun algorithme ni mesure du générateur. Il partage seulement avec lui la *spécification* des niveaux (`band`, `meets`, `minimum_path`, `span`), vérifiée séparément par un tableau calculé à la main dans les tests. Il recalcule : passages canoniques (triés, uniques, adjacents, dans la grille), arbre couvrant
(union-find : N²−1 passages, aucun cycle, une composante), chemin unique (parcours en profondeur itératif) comparé au chemin déclaré **et** à
`maze_unique_path` (vérificateur historique), mesures et niveau, `params`, `search` (la tentative déclarée et l'algorithme doivent correspondre à la rotation ; le nombre de tentatives lui-même n'est pas rejoué), graine bornée, empreinte. Les comparaisons sont **strictes** (`False` n'est pas `0`, `1.0` n'est pas `1`) : un labyrinthe n'a qu'une seule forme canonique valide. `verify_v2` renvoie toujours une liste de problèmes (mécanique inconnue ou absente comprise).

## `connect_dots_v2` (B3-B.3b.2)

Points numérotés à relier, famille `radial`, **géométrie entière exacte**. Paramètres (jeu fermé) : `points` entier de 5 à 24 inclus,
`closed` booléen strict (polygone fermé P1→…→PN→P1, ou ligne brisée ouverte P1→…→PN), `shape` = `"radial"` (seule famille ouverte ; `star`,
`moon`, `house`, familles saisonnières, etc. sont refusées). `generate_v2("connect_dots_v2", "syn-…", seed, {"points": 12, "closed": True,
"shape": "radial"})`. Aucun rendu, aucune donnée éditoriale : le nombre de points de la p.17 réelle n'est ni lu ni deviné.

### Repère et arithmétique

Grille de côté `GRID = 1000`, repère abstrait (axe y vers le haut ; le rendu n'est pas traité ici), marge `MARGIN = 50` : tout point et le centre
sont dans [50, 950]². **Aucun flottant, aucun epsilon, aucune trigonométrie** dans un critère de validité ni dans le générateur (testé par analyse du
code) : produits en croix, produits scalaires et comparaisons de fractions d'entiers.

### Critères de validité (tous obligatoires, aucun n'est jamais assoupli)

| # | Critère | Seuil |
|---|---|---|
| C1 | deux points quelconques | carré de distance ≥ 60² |
| C2 | chaque segment tracé | carré de longueur ≥ 60² |
| C3 | deux segments non adjacents | ni croisement ni contact (segments fermés, extrémités comprises), test exact |
| C4 | un point et un segment qui ne l'a pas pour extrémité | distance exacte ≥ 40 |
| C5 | trois points consécutifs (cycliques si `closed`) | non alignés ; deux segments adjacents ne partagent que leur extrémité |
| C6 | départ et sens canoniques | P1 = point de plus petit (y, x) ; numérotation anti-horaire autour du centre ; aire signée > 0 si `closed` |
| C7 | numérotation et solution | `n` = 1..N continus ; `order` = [1..N] ; `close_to` = 1 si fermé, `null` sinon |

**Distance point-segment (C4).** Le carré de la distance est une fraction exacte d'entiers : extrémité la plus proche si la projection tombe
hors du segment, sinon `produit_en_croix² / longueur²`. Le test est `numérateur ≥ 40² × dénominateur`. `measures.min_clearance_sq_floor` publie
la **partie entière** du minimum, c'est-à-dire ⌊min d²⌋ (convention : troncature d'une fraction positive, jamais d'arrondi). Comme 40² est entier,
`min d² ≥ 40²` ⇔ `⌊min d²⌋ ≥ 40²` : le plancher publié ne perd rien pour le test ; il n'est qu'une valeur d'information.

**Point P1 et sens (C6), pour les deux modes.** P1 est le point de plus petit `y`, puis de plus petit `x`. La numérotation tourne dans le sens
anti-horaire autour du centre publié ; en mode fermé l'aire signée (formule du lacet, `twice_area`) doit être strictement positive. Le
vérificateur contrôle cette convention seul, à partir des points publiés.

**Propriétés `radial` (conservées dans la sortie par `geometry.center`).** Le centre `C` (entier) est publié. Les points sont strictement
croissants en angle polaire autour de `C` à partir de P1, aucun point ne coïncide avec `C`, et chaque écart angulaire entre points consécutifs,
**y compris PN→P1 dans les deux modes**, est strictement compris entre 0 et π (`cross(Pi−C, Pi+1−C) > 0`). Un écart exactement égal à π (arête
passant par le centre) est refusé. Une telle figure est étoilée par rapport à `C` donc simple ; C3 est néanmoins vérifié indépendamment. En
mode ouvert l'écart PN→P1 n'est pas tracé mais reste contraint : les deux modes partagent la même propriété, c'est un choix de simplicité
documenté. Le vérificateur contrôle l'ordre angulaire par un pseudo-angle rationnel exact (« diamant » dans [0, 4)), pas par les demi-plans du générateur.

### Génération déterministe et recherche bornée

Candidat `i` (0 ≤ i < `MAX_ATTEMPTS` = 2000) : flux dérivé de (id, graine, forme, points, mode, i). Le centre est tiré dans [450, 550]² ; le périmètre
d'un carré de demi-côté 400 est découpé en N tranches égales décalées d'une phase aléatoire ; un point est tiré par tranche (échelle 40–100 %), puis
la liste est tournée pour commencer à P1. Tout est entier. Le premier candidat qui satisfait **tous** les critères est retourné ; sinon `V2Error`
`UNSATISFIABLE`. Les empreintes de référence (3 combinaisons figées dans les tests) sont identiques sous Python 3.11, 3.12 et 3.13, vérifié à la main lors de la livraison ; la CI du dépôt ne teste que Python 3.11, donc cette égalité inter-versions n'est pas protégée automatiquement contre une régression.

### Benchmark (tentatives nécessaires, 5 à 24 points, deux modes)

1000 graines (0 à 999) × 20 nombres de points × 2 modes = 40 000 figures générées **et** revérifiées par le vérificateur indépendant ; identifiant `syn-bench`. **0 échec.** Pire cas : 59 tentatives sur 2 000 autorisées. Reproductible avec l'API publique (`generate_v2(...).search["attempts"]`).

| points | fermé : moyenne | p95 | p99 | max | ouvert : moyenne | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1.0 | 1 | 2 | 3 | 1.0 | 1 | 2 | 2 |
| 6 | 1.0 | 1 | 2 | 2 | 1.0 | 1 | 2 | 2 |
| 7 | 1.1 | 2 | 2 | 4 | 1.0 | 1 | 2 | 3 |
| 8 | 1.1 | 2 | 2 | 3 | 1.1 | 2 | 2 | 3 |
| 9 | 1.1 | 2 | 3 | 4 | 1.1 | 2 | 3 | 5 |
| 10 | 1.2 | 2 | 3 | 3 | 1.1 | 2 | 3 | 4 |
| 11 | 1.2 | 2 | 3 | 4 | 1.2 | 2 | 3 | 4 |
| 12 | 1.3 | 3 | 3 | 5 | 1.3 | 2 | 3 | 5 |
| 13 | 1.4 | 3 | 4 | 7 | 1.4 | 3 | 4 | 6 |
| 14 | 1.5 | 3 | 4 | 6 | 1.5 | 3 | 5 | 8 |
| 15 | 1.7 | 4 | 6 | 8 | 1.7 | 4 | 6 | 10 |
| 16 | 1.8 | 5 | 6 | 9 | 1.9 | 4 | 7 | 10 |
| 17 | 2.1 | 5 | 7 | 11 | 2.1 | 5 | 7 | 10 |
| 18 | 2.5 | 6 | 9 | 13 | 2.4 | 6 | 8 | 14 |
| 19 | 2.8 | 7 | 11 | 21 | 2.9 | 7 | 11 | 18 |
| 20 | 3.6 | 10 | 14 | 26 | 3.4 | 10 | 14 | 22 |
| 21 | 4.5 | 12 | 20 | 30 | 4.2 | 11 | 17 | 29 |
| 22 | 5.3 | 15 | 24 | 30 | 5.4 | 15 | 22 | 35 |
| 23 | 7.3 | 20 | 30 | 46 | 7.2 | 21 | 30 | 53 |
| 24 | 9.1 | 29 | 41 | 53 | 9.4 | 26 | 42 | 59 |

La borne 24 est donc praticable sans assouplir aucun des sept critères (moyenne 9 tentatives, p99 ≈ 41–42, max 59).

### Vérification indépendante

`verify_connect_dots_v2` ne réutilise aucune fonction géométrique du générateur : contact de segments par boîtes englobantes et signes
d'orientation ; dégagement par projection avec `fractions.Fraction` ; ordre angulaire par pseudo-angle rationnel. Il recalcule C1 à C7,
`measures` (dont `min_clearance_sq_floor`), `search`, `params` et l'empreinte, avec des comparaisons strictes (`True` n'est pas `1`, `1.0` n'est
pas `1`). `verify_connect_dots_v2` ne lève jamais d'exception sur une géométrie hostile (segment dégénéré compris) ; `diagnose_connect_dots_v2` renvoie une liste vide dès qu'une coordonnée sort de la grille. Un test différentiel compare le verdict du
générateur et celui du vérificateur sur plusieurs milliers de figures mutées, et chaque seuil est testé à sa frontière exacte (seuil = mesure :
valide ; seuil = mesure + 1 : refusé).

**Le verdict entier exact fait autorité.** `diagnose_connect_dots_v2` compare en plus avec l'assistant historique `engine.solvers.segments_touch`
(flottants) à titre de diagnostic secondaire : un désaccord est signalé dans cette liste d'information et ne provoque jamais, à lui seul, le rejet
d'un enregistrement (testé en forçant l'assistant à répondre l'inverse).

### Sortie canonique

`geometry = {shape, closed, grid, center, points: [{n, x, y}]}` ; `solution = {order, close_to}` ; `measures = {point_count, segment_count,
min_point_dist_sq, min_segment_sq, min_clearance_sq_floor, twice_area}` (`twice_area` = `null` en mode ouvert) ; `search = {attempts,
max_attempts}`. Version `b3b3b2-connect-dots-v2-1.0`. Même schéma, même encodage et même empreinte que `maze_v2`.

### Limites propres à `connect_dots_v2`

* **« Ordre unique » n'est pas un théorème d'unicité du dessin.** Il signifie : départ canonique, sens canonique, contour simple. Plusieurs
  polygones simples passent par le même nuage de points ; on ne prétend pas que celui-ci est le seul.
* Aucune validation pédagogique humaine ; **aucun niveau de difficulté** n'est modélisé pour cette mécanique.
* Le dessin obtenu est une figure étoilée tirée au hasard : rien ne garantit qu'elle représente un objet reconnaissable pour un enfant.
* Pas de rendu : les numéros peuvent se chevaucher visuellement si la taille d'écriture est grande ; les seuils (60 et 40 sur 1000) sont des
  paramètres techniques, pas un contrôle de lisibilité graphique (issue #15).
* Une seule famille (`radial`) ; les formes historiques `moon`/`house`/`star` et le croissant C4 restent hors de v2.
* `search.attempts` n'est pas rejoué indépendamment (dette technique non bloquante, comme pour `maze_v2`). L'empreinte SHA-256 garantit
  l'intégrité du contenu, **pas** une provenance authentifiée.

## `match_v2` (B3-B.3b.3)

Paires de **symboles géométriques synthétiques** à relier, avec une bijection dont chaque lien est déterminé par une propriété **observable** de la géométrie, jamais par un identifiant. Ni chapeaux, ni cadeaux, ni pictogrammes réels, ni assets : les familles saisonnières (`hats`, `gifts`, `hat_*`, `gift_*`) sont refusées (`BAD_FAMILY`) et la génération historique `generate_match` n'est ni utilisée ni modifiée.

| Paramètre | Domaine | Erreur |
|---|---|---|
| `pairs` | entier strict de 3 à 6 inclus | `BAD_PAIRS` |
| `relation` | `twin` ou `count` | `BAD_RELATION` |
| `family` | `polygon`, `star` ou `mixed` | `BAD_FAMILY` |
| combinaison | `star` limitée à 3 classes (`pairs` ≤ 3) ; `count` réservé à `polygon` | `BAD_COMBINATION` |

Treize combinaisons sont valides (sur 24 : onze refusées explicitement, rien n'est dégradé en silence).

### Vocabulaire fermé : tables d'entiers dans un cadre local 100 × 100

Chaque symbole est une table littérale de sommets entiers, dans un cadre local `[0, 100]²`, sens anti-horaire, premier sommet = plus petit `(y, x)`. Aucune trigonométrie, aucun flottant : `polygon` = polygone convexe de 3 à 8 côtés, `star` = étoile à 4, 5 ou 6 branches (neuf classes). Signature d'une classe = (nombre de sommets, nombre de sommets rentrants), toutes distinctes (octogone (8, 0) ≠ étoile à 4 branches (8, 4)). Pour `count`, le côté droit est un motif de *k* points (tables de 3 à 8 points, distants d'au moins 30 dans le cadre, à 15 au moins du bord).

### Relations

* **`twin`** : le symbole de droite a *exactement* la même liste de sommets que celui de gauche **dans le repère local normalisé**. C'est une égalité de listes d'entiers, pas une congruence par rotation ou translation : un symbole translaté de 1, tourné (liste décalée), réfléchi ou réduit n'est pas jumeau.
* **`count`** : un polygone à *k* sommets à gauche, un motif de *k* points à droite.

Le vérificateur **recalcule les signatures depuis les coordonnées** (produits en croix, simplicité par test exact, convexité) ; le champ `label` est informatif : il n'intervient jamais dans la décision de correspondance, il est seulement contrôlé séparément (M8). Permuter ou falsifier des étiquettes ne change ni la relation recalculée ni l'unicité, et produit uniquement des erreurs M8.

### Critères (neuf : M1 à M9 ; tous exacts, aucun n'est jamais assoupli)

| # | Critère |
|---|---|
| M1 | `left_to_right` est une permutation de 0..N−1 **différente de l'identité** ; les points fixes individuels sont autorisés |
| M2 | dans une colonne, deux symboles ont des signatures différentes (pour `count` : des nombres de points différents, voir M9) |
| M3 | **unicité bilatérale** : chaque symbole de gauche est en relation avec exactement un symbole de droite et réciproquement, et c'est l'association de la solution (matrice recalculée depuis les coordonnées) |
| M4 | contours bien formés : entiers, dans le cadre, anti-horaires, simples, strictement convexes (`polygon`) ou avec exactement *k* sommets rentrants (`star`), égaux à la table fermée |
| M5 | rapport aire / boîte englobante : deux symboles de gauche diffèrent d'au moins δ = 5 000 millionièmes (comparaison exacte en `Fraction`) ; **indicateur géométrique seulement**, aucune garantie de discrimination visuelle humaine |
| M6 | aucun triplet de liens concourants en un point intérieur (test exact en fractions, sur tous les triplets) |
| M7 | mise en page : la **boîte englobante réelle** de chaque symbole translaté à sa position, et non la cellule nominale, reste dans les marges de la grille (50..950), les boîtes d'une colonne sont à 30 au moins l'une de l'autre, les symboles sont à 20 au moins des ancrages |
| M8 | étiquettes cohérentes avec les signatures recalculées |
| M9 | `count` : motifs égaux aux tables fermées, dans le cadre, points distants d'au moins 30, nombres de points tous différents |

À six paires le pas entre rangées est de 150 : les symboles (hauteur réelle ≤ 96) laissent toujours au moins 54 entre deux boîtes, quelle que soit la combinaison (testé sur chaque combinaison valide à six paires). Le nombre de croisements de liens (`crossings` = inversions de la permutation) est une mesure d'information, pas une contrainte.

**Sur M5 (limite à connaître).** δ a été fixé à partir des tables **avant** le benchmark de validation : le plus petit écart entre les neuf classes est 3/364 ≈ 0,00824 (hexagone 0,75 contre heptagone 0,7418). δ = 0,005 est donc *inférieur* à tout écart possible : sur le vocabulaire actuel M5 est toujours satisfait (0 rejet en 13 000 générations) et n'agit que comme garde contre une régression des tables. Des tables inclinées pourraient atteindre environ 0,030, au prix de symboles moins lisibles ; ce choix, et le fait qu'un écart de 1 % de remplissage ne garantit pas qu'un enfant distingue deux formes, restent à arbitrer. La garantie principale est la signature de M2 (nombre de sommets et de sommets rentrants).

### Géométrie, solution, mesures

`geometry = {relation, family, grid: 1000, rows, anchors: {left_x: 260, right_x: 740, ys}, left, right}` avec `ys[i] = 50 + (2i+1)·900 // (2N)` ; chaque entrée `{row, label, origin, vertices | dots}` (origine monde du cadre local : `[100, ys[i]−50]` à gauche, `[800, ys[j]−50]` à droite). `solution = {left_to_right}`, `measures = {pairs, fixed_points, crossings, min_area_ratio_gap_ppm}`, `search = {attempts, max_attempts: 2000}`. Les liens joignent l'ancre gauche de la rangée *i* à l'ancre droite de la rangée `left_to_right[i]`.

### Génération déterministe et recherche bornée

Tentative *a* (0 ≤ *a* < 2 000) : flux `DetRng` dérivé de (identifiant, graine, paramètres, *a*) ; tirage de N classes dans le réservoir, permutation mélangée, rejet de l'identité, de M5 et des liens concourants. Premier candidat valide renvoyé ; sinon `UNSATISFIABLE`, sans jamais relâcher un critère. Version `b3b3b3-match-v2-1.0`. Empreintes de référence figées dans les tests (3 combinaisons), identiques sous Python 3.11, 3.12 et 3.13 (vérifié à la main ; la CI ne teste que 3.11).

### Benchmark (1 000 graines par combinaison valide, générées **et** revérifiées)

13 combinaisons × 1 000 graines (0 à 999, identifiant `syn-bench`) = 13 000 activités : **0 échec**, pire cas 9 tentatives sur 2 000.

| pairs | relation | famille | moyenne | p95 | p99 | max | points fixes min/moy/max | écart M5 min (ppm) |
|---:|---|---|---:|---:|---:|---:|---|---:|
| 3 | twin | polygon | 1.57 | 3 | 5 | 7 | 0 / 0.49 / 1 | 8241 |
| 3 | twin | star | 1.52 | 3 | 5 | 9 | 0 / 0.52 / 1 | 8455 |
| 3 | twin | mixed | 1.51 | 4 | 5 | 7 | 0 / 0.52 / 1 | 8241 |
| 3 | count | polygon | 1.49 | 3 | 5 | 7 | 0 / 0.49 / 1 | 8241 |
| 4 | twin | polygon | 1.18 | 2 | 3 | 5 | 0 / 0.80 / 2 | 8241 |
| 4 | twin | mixed | 1.19 | 2 | 3 | 4 | 0 / 0.79 / 2 | 8241 |
| 4 | count | polygon | 1.22 | 2 | 3 | 4 | 0 / 0.79 / 2 | 8241 |
| 5 | twin | polygon | 1.38 | 3 | 4 | 5 | 0 / 1.06 / 3 | 8241 |
| 5 | twin | mixed | 1.44 | 3 | 4 | 6 | 0 / 1.03 / 3 | 8241 |
| 5 | count | polygon | 1.45 | 3 | 5 | 7 | 0 / 1.06 / 3 | 8241 |
| 6 | twin | polygon | 1.56 | 3 | 5 | 7 | 0 / 1.09 / 4 | 8241 |
| 6 | twin | mixed | 1.50 | 3 | 5 | 6 | 0 / 1.09 / 4 | 8241 |
| 6 | count | polygon | 1.52 | 3 | 5 | 7 | 0 / 1.01 / 4 | 8241 |

### Vérification indépendante

`verify_match_v2` ne dépend d'aucune fonction géométrique du générateur (seules les tables littérales et les constantes sont lues comme données) : signatures, orientation, simplicité, convexité, relation entre toutes les paires, unicité bilatérale, rapports aire/boîte en `Fraction`, boîtes réelles translatées, concours de tous les triplets de liens, mesures, empreinte. Égalité de types stricte (`True` ≠ 1, `1.0` ≠ 1), clés exactes. Tests : oracle séparé en `Fraction` comparé au vérificateur sur 3 000 enregistrements mutés et sur toutes les permutations de 3 à 6 rangées ; falsifications avec empreinte recalculée (l'empreinte ne prouve pas la validité) ; analyse des contours comparée à une référence sur 4 000 polygones aléatoires. Mutation (opérateurs de comparaison, booléens, arithmétique, constantes, négations ; 684 mutants des deux modules) : 654 tués, 30 survivants examinés un par un et tous équivalents (texte de message, comparaisons d'entiers distincts, égalités de bord inatteignables, bornes de boucle redondantes). La revue indépendante a de plus trouvé un `RecursionError` sur un champ publié imbriqué à 100 000 niveaux : le vérificateur renvoie désormais une erreur (testé sur sept champs). La première passe (130 survivants) a révélé un défaut réel, corrigé : les boîtes englobantes étaient mesurées à la position attendue et non à l'origine publiée.

### Limites propres à `match_v2`

* Aucune validation pédagogique humaine. L'hypothèse que `twin` est plus accessible que `count` (qui suppose de dénombrer jusqu'à 8) pour 4–5 ans n'est pas vérifiée ; avec 3 paires, une association tirée au hasard réussit une fois sur six (3! = 6 permutations), ou une fois sur cinq si l'enfant sait que l'identité est exclue : le minimum de 3 paires écarte le cas à une chance sur deux, pas le hasard.
* Pas de rendu : croisements de liens, lisibilité, épaisseur de trait relèvent de l'issue #15.
* Symboles abstraits sans sens narratif ; les pages réelles (p.27, p.46) ne sont pas couvertes.
* M5 est un indicateur faible (voir plus haut). `search.attempts` n'est pas rejoué indépendamment ; l'empreinte SHA-256 garantit l'intégrité, pas une provenance authentifiée.

## Sérialisation canonique (schéma `lafractale-mechanics-v2-activity-v1`)

UTF-8 ; JSON avec clés triées lexicographiquement à tous les niveaux, séparateurs `,` et `:` sans espace, `ensure_ascii=False` ; entiers,
chaînes, booléens, `null`, tableaux et objets uniquement (flottants, NaN, clés non textuelles refusés). Champs de premier niveau :
`activity_id`, `fingerprint`, `geometry`, `human_pedagogical_validation`, `kind`, `measures`, `mechanic`, `params`, `production_authorized`,
`schema`, `search`, `seed`, `solution`, `version`. `fingerprint` = SHA-256 hexadécimal minuscule des octets canoniques de l'enregistrement
**sans** la clé `fingerprint`. `loads_record` relit strictement (clés dupliquées refusées) et exige que les octets soient déjà canoniques.

Pour `maze_v2` : `geometry = {size, start, goal, open_edges}` (passages `[[x,y],[x,y]]`, plus petite cellule d'abord, triés), `solution = {path,
steps}`, `measures = {path_length, dead_ends, decisions, minimum_path_length, span}`, `search = {algorithm, attempts, max_attempts}`.
Les objets Python (`V2Activity`, `FrozenDict`) sont profondément immuables, y compris à la construction directe (les conteneurs sont gelés par `__post_init__`) ; `to_dict()` renvoie une copie indépendante. Limite connue de Python : `object.__setattr__` contourne tout objet gelé ; un enregistrement ainsi falsifié reste refusé par la vérification (empreinte).

## Limites

* Aucune validation pédagogique humaine : les niveaux mesurent la structure du labyrinthe, pas sa difficulté pour un enfant de 4–5 ans.
* Pas de rendu, pas de lisibilité graphique : les épaisseurs de murs, le masquage et l'occultation relèvent de l'issue #15 et de la QA du moteur.
* La recherche borne le coût (5 000 tentatives) ; le seul résultat négatif possible est l'échec explicite `UNSATISFIABLE`.
* Les pages réelles (p.14, p.43 pour le labyrinthe ; p.17 pour les points) ne sont pas branchées : leurs paramètres éditoriaux (départ, parcours, taille) restent à fixer par les humains.
