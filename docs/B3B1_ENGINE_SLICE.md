# B3-B.1 — Tranche verticale du moteur (fixtures synthétiques uniquement)

```text
kind                  = SYNTHETIC_NON_PRODUCTION
ready_for_kdp         = false
MAJOR-03              = OPEN
MAJOR-04              = OPEN
EDITORIAL             = PENDING
KDP                   = FORBIDDEN
PRODUCTION_GENERATION = FORBIDDEN
```

Ces valeurs sont des **constantes du code** (`lafractale/engine/__init__.py`), jamais lues
depuis une source, et reprises telles quelles dans chaque rapport et manifeste.
Rien dans ce paquet ne valide, n'approuve ni ne lève une porte éditoriale.

## Ce que fait B3-B.1

Une chaîne complète, générique et testable, sur une fixture de 6 pages :

```text
source JSON stricte ─► activité (générateurs EXISTANTS) ─► solution vérifiée indépendamment
   ─► composition + PDF fiche / PDF corrigé (rendu EXISTANT) ─► QA ─► paquet traçable
```

Ce n'est **pas** un générateur de cahier : aucune donnée Halloween, aucun Pip, aucun asset,
aucune illustration, aucun livre. Les identifiants de livre réels et les noms de personnages
sont refusés par le contrat.

## Architecture

| Module | Rôle |
|---|---|
| `engine/__init__.py` | Constantes `KIND`, `GATES`, `READY_FOR_KDP` ; erreurs `EngineError`, `ContractError` |
| `engine/contracts.py` | Contrat JSON fermé, `SpecSet`/`PageSpec` immuables, JSON canonique, SHA-256 |
| `engine/registry.py` | Registre fermé des mécaniques : adaptateurs vers `activities/engine.py` + paramètres énumérés |
| `engine/solvers.py` | Vérification **indépendante** de la solution, à partir de la structure produite |
| `engine/render.py` | Noms de fichiers du paquet ; délègue à `layout.pdf.write_pdf` |
| `engine/qa.py` | Contrôles des deux PDF, du corrigé, des textes sources, de l'intégrité du paquet |
| `engine/pipeline.py` | Orchestration, staging, publication sans écrasement |
| `engine/main.py`, `__main__.py` | CLI `validate`, `run`, `audit` |

### Réutilisation (aucun fichier existant modifié)

| Existant | Utilisation |
|---|---|
| `activities.engine.generate`, `stable_seed` | Génération `maze`, `connect_dots`, `match`, inchangée |
| `quality.checks.validate_activity`, `validate_collection` | Couche de contrôle supplémentaire |
| `layout.pdf.write_pdf` (→ `compose_page`) | Composition, validation des zones, fichiers créés en exclusivité |
| `export.securefs` | `new_regular_file` (O_EXCL, O_NOFOLLOW), `audit_root_dirfd` |
| `security.strict_json`, `security.text` | JSON strict, politique Unicode, noms interdits |

## Contrat de source (`lafractale-engine-slice-v1`)

Clés **fermées** : toute clé inconnue ou dupliquée est refusée. Sont en plus explicitement
interdites `production`, `ready_for_kdp`, `companion`, `illustration(s)`, `asset(s)`, `book_id`,
`approved`, `editorial_profile`, etc.

* `kind` doit valoir `SYNTHETIC_TEST_FIXTURE` ; `spec_id` doit commencer par `synthetic_`.
* Format unique : 8,5 × 11 pouces. 1 à 12 fiches, numérotées 1..N ; `unit_id` uniques.
* Mécaniques et paramètres (énumérations fermées) :

| `mechanic` | `params` obligatoires |
|---|---|
| `maze` | aucun |
| `connect_dots` | `shape` ∈ `moon`, `house`, `star` |
| `match` | `family` = `shapes` (les familles saisonnières `hats`/`gifts` du générateur restent fermées) |

* Les consignes FR/EN et la scène viennent **de la source** ; le générateur ne les impose pas.
* Les noms `Pip`, `Halloween`, `Christmas`, `Noël`, `Noel` sont refusés dans tout texte (liste de jetons exacts : un garde-fou, pas une preuve d'absence de contenu réel).
* Alternance de mécaniques et scènes distinctes (règles de `validate_collection`).

La fixture est `tests/fixtures/b3b1/synthetic_slice_v1.json`.

## Vérification indépendante des solutions

`solvers.py` ne croit pas les métadonnées du générateur :

* **Labyrinthe** : les passages réels sont relus ; un graphe connexe de n² cellules avec
  exactement n²−1 passages est un arbre couvrant, donc le chemin départ → arrivée est
  **unique**. Un cycle, une cellule inaccessible, une arête hors grille/non adjacente/doublon,
  un chemin ou un nombre de pas erroné sont refusés. (Le validateur historique
  `validate_activity` ne contrôle pas l'unicité ; il n'est pas modifié.)
* **Points** : numérotation 1..N, nombre de points attendu pour la forme, absence de
  croisement ou de contact entre segments non adjacents, segments non trop courts, corrigé 1..N puis retour à 1.
* **Association** : symboles distincts, mêmes symboles des deux côtés, colonnes non
  identiques, corrigé bijectif et égal aux paires recalculées.

## QA (`qa.py`)

Pour la fiche **et** le corrigé, après relecture des PDF avec PyMuPDF :
nombre de pages, format 612 × 792 pt, absence d'image, **scène, consigne FR, consigne EN
et libellé « FICHE nn » présents dans le texte du PDF**, mention de maquette, titre
fiche/corrigé cohérent, texte et tracés à ≥ 36 pt du bord, police DejaVu intégrée, politique de texte.

Cohérence activité ↔ solution **mesurée sur la géométrie dessinée** :

* la fiche ne contient aucun tracé absent du corrigé ; le corrigé ne s'en distingue que par le tracé de solution ;
* labyrinthe : murs dessinés = passages de l'activité (origine et taille ajustées sur le tracé), tracé de solution = chemin de l'activité, sans traverser de mur ;
* points : positions dessinées = coordonnées de l'activité (ajustement affine), contour passant par les points dans l'ordre 1..N puis retour au 1, numéros affichés = 1..N ;
* association : liens du corrigé = paires de l'activité.

L'audit d'un paquet publié recalcule tout depuis la source : inventaire fermé, manifeste, `activities.json`,
rapport, et **rejeu du rendu à l'octet**. `audit --spec` utilise une source indépendante ;
sans `--spec`, `sources/spec.json` du paquet est utilisé (cohérence interne, pas authenticité).

## Sorties (inventaire fermé)

```text
<out>/
  interior_SYNTHETIC_NON_PRODUCTION.pdf
  answer_key_SYNTHETIC_NON_PRODUCTION.pdf
  activities.json
  quality_report.json
  manifest.json            # chemins relatifs POSIX + SHA-256 des autres fichiers
  sources/spec.json        # copie octet pour octet de la source
```

Aucun horodatage, aucun chemin absolu : deux générations de la même source, dans deux
répertoires différents, sont identiques à l'octet (avec la même police DejaVu et les
mêmes versions des bibliothèques). Les fichiers sont créés en mode `0600`, les répertoires créés par le moteur en `0700`.

Publication : paquet construit et audité en staging privé, puis écrit avec création exclusive
(jamais d'écrasement ; destination absente ou répertoire vide ; lien symbolique refusé), puis
re-audité. En cas d'échec, les fichiers créés sont retirés.

## Utilisation

```bash
python -m lafractale.engine validate tests/fixtures/b3b1/synthetic_slice_v1.json
python -m lafractale.engine run tests/fixtures/b3b1/synthetic_slice_v1.json --out dist/b3b1-synthetic
python -m lafractale.engine audit --out dist/b3b1-synthetic --spec tests/fixtures/b3b1/synthetic_slice_v1.json
python -m pytest -q tests/test_b3b1_contracts.py tests/test_b3b1_solvers.py \
    tests/test_b3b1_pipeline.py tests/test_b3b1_qa_tamper.py
```

Codes de sortie : `0` succès, `2` refus (message explicite sur `stderr`).

## Limites connues

* Avertissement `pdf.fonts.base14_helvetica_reference` : le rendu historique référence Helvetica
  sans l'intégrer (corrigé seulement par le chemin C4). Signalé en `WARN`, non corrigé ici.
* La QA repère les points par le rayon de 4,1 pt du rendu historique (cases `8,2 pt`) et les murs par leur épaisseur de 3 pt : si le rendu change, elle échoue (fail-closed) au lieu de passer à tort.
* Pas de contrôle prépresse/KDP, pas de fonds perdus, pas de couverture, pas d'épreuve papier.
* Un contrôle automatique n'est ni une relecture bilingue humaine (MAJOR-04), ni un essai
  enfant–adulte (MAJOR-03), ni une validation éditoriale.
* L'audit ne protège pas contre un processus ayant les mêmes privilèges (TOCTOU hors périmètre,
  comme pour `export/builder.py`).
* Le contrôle d'unicité du labyrinthe n'est pas ajouté à `quality/checks.py` et
  `books/halloween_2026/page_plan.csv` n'est pas migré : incréments distincts.
