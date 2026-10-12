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
* association : les **symboles réellement dessinés** sont contrôlés ligne par ligne (voir ci-dessous), puis les liens du corrigé.

### Association : contrôle des symboles dessinés

Les lignes sont définies par les **points d'ancrage dessinés** (pas par le centre des symboles, qui
diffère de l'ancre pour un triangle ou une étoile). Chaque tracé de symbole (trait de 2,6 pt) est
rattaché à la ligne de son ancre, puis converti en **signature géométrique normalisée** (position et
taille supprimées) : cercle, carré (`re`), polygone à n sommets (sommets normalisés, ordre et sommet de
départ indifférents). La signature attendue de chaque symbole est dérivée de sa définition
(polygone régulier, étoile à rayon intérieur 0,47) et appliquée aux noms de l'activité, elle-même
régénérée depuis la source. Sont signalés : symbole **manquant** ou **supplémentaire** dans une ligne,
tracé hors de toute ligne, **tracé différent du symbole attendu** (colonne gauche ou droite), lien du corrigé
qui ne part pas des ancres, **liens différents des paires de l'activité**, lien joignant **deux signatures
différentes**. Une permutation simultanée des deux colonnes (cohérente dans le PDF) reste détectée car
les signatures sont comparées aux noms de l'activité régénérée, pas seulement entre elles. Les familles
sans signature connue (`hat_*`, `gift_*`) sont refusées (fail-closed).

L'audit d'un paquet publié recalcule tout depuis la source : inventaire fermé, manifeste, `activities.json`,
rapport, **date canonique des PDF** et **rejeu du rendu à l'octet**. Les PDF analysés sont exactement les
octets lus, hachés et comparés au rejeu. `audit --spec` utilise une source indépendante ;
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

Aucun horodatage d'exécution, aucun chemin absolu. Les fichiers sont créés en mode `0600`, les répertoires
créés par le moteur en `0700`.

### Reproductibilité des octets

ReportLab lit l'environnement du processus : `SOURCE_DATE_EPOCH` (dates `CreationDate`/`ModDate`, même avec
`invariant=1`) et les variables `RL_*` (par ex. `RL_ttfAsciiReadable`, `RL_pdfComments`, qui changent les
octets). L'environnement est un état **global** : un verrou local ne protège pas contre un autre composant
du processus. Le rendu s'exécute donc dans un **processus enfant** (`engine/_render_worker.py`) :

* son environnement est une **copie assainie** : `SOURCE_DATE_EPOCH=946684800` (date canonique
  **2000-01-01T00:00:00Z**, `D:20000101000000+00'00'`) et toutes les `RL_*` retirées ;
* le processus parent ne modifie **jamais** `os.environ` (succès comme exception) ; une modification
  concurrente de l'environnement par un autre thread ne peut pas altérer un rendu ;
* ReportLab exécute aussi `reportlab_settings` (via `sys.path`) et `~/.reportlab_settings` (via `HOME`) : l'enfant reçoit
  un `HOME` vide (répertoire temporaire) et un module `reportlab_settings` vide en `sys.modules` avant tout import ;
* le processus enfant refuse de s'exécuter sous un environnement non canonique ou si `~/.reportlab_settings` existe ;
* `python -P` : le répertoire courant n'est pas ajouté à `sys.path` ; `PYTHONPATH` est rendu absolu, la
  racine du paquet en cours d'exécution étant placée en tête (même code que le parent) ;
* la date canonique est tracée dans `manifest.json` et `quality_report.json` (`pdf_creation_epoch`), le mode
  d'isolation dans le manifeste ; l'audit vérifie les métadonnées de chaque PDF.

**Méthode de vérification** : générer la fixture sous plusieurs environnements (variable absente, `1`,
`1780000000`, `42` avec `RL_ttfAsciiReadable=0` et `RL_pdfComments=1`) et plusieurs versions de Python
(3.11, 3.13), puis comparer les SHA-256 de tous les fichiers : ils doivent être identiques. Les octets
dépendent encore de la version de ReportLab (y compris son éventuel `reportlab/local_rl_settings.py`, qui fait
partie de l'installation) et des polices DejaVu : ces éléments ne sont pas épinglés.

**Empreintes de référence** (`tests/fixtures/b3b1/reference_hashes.json`, ReportLab 4.5.1, PyMuPDF 1.28.2,
DejaVu des paquets Ubuntu du CI) pour `synthetic_slice_v1.json` :

| Fichier | SHA-256 |
|---|---|
| `activities.json` | `6fe8a13429390b9d8bd2909b6e55a2552f85cf805ff225258a6114cf93390e39` |
| `sources/spec.json` | `88e98de2eb9e3d33568ca394d37c9096bb59fbfaea2acbd6e47aa02f26b4c415` |
| `interior_SYNTHETIC_NON_PRODUCTION.pdf` | `c9f614d810cbd7d164c761be84d7a5aa167546d9ae604774c439732e0776987d` |
| `answer_key_SYNTHETIC_NON_PRODUCTION.pdf` | `640d7864593f3a910a22d48d3f22315c26def6055303983074b1dd90cf72461e` |
| `quality_report.json` | `b009f3a5f3f9b86c3aa7d3382a8f01f9684881d3c213355651bf319b83e6a834` |
| `manifest.json` | `161cb853b263715f4ce593ae94548771aae3025caa269bd2ab7ba069f7d51e7d` |

Les deux premières sont toujours comparées par le test ; les quatre autres seulement si l'empreinte de
l'environnement (versions ReportLab/PyMuPDF + SHA-256 des polices) correspond, sinon le test est ignoré avec
une raison explicite. Pour régénérer après un changement légitime de bibliothèque ou de police : relancer la
comparaison multi-environnements ci-dessus, vérifier l'identité, puis mettre à jour le fichier.

### Lectures bornées

Chaque fichier lu par l'audit ou par le CLI l'est avec `read_bounded` : ouverture unique en
`O_NOFOLLOW | O_NONBLOCK` (lien symbolique refusé, tube sans blocage), `fstat` sur **ce même descripteur**
(fichier régulier, taille), lecture de `limite + 1` octets au plus (un fichier qui grossit après le contrôle
est refusé). Plafonds : PDF 12 000 000 octets (plus grand plafond historique, aperçus), JSON du paquet
4 000 000 (plafond historique d'`activities.json`), source 200 000.

Publication : paquet construit et audité en staging privé, puis écrit avec création exclusive
(jamais d'écrasement ; destination absente ou répertoire vide ; lien symbolique refusé), puis
re-audité. En cas d'échec, les fichiers créés sont retirés.

## Utilisation

```bash
python -m lafractale.engine validate tests/fixtures/b3b1/synthetic_slice_v1.json
python -m lafractale.engine run tests/fixtures/b3b1/synthetic_slice_v1.json --out dist/b3b1-synthetic
python -m lafractale.engine audit --out dist/b3b1-synthetic --spec tests/fixtures/b3b1/synthetic_slice_v1.json
python -m pytest -q tests/test_b3b1_*.py
```

Codes de sortie : `0` succès, `2` refus (message explicite sur `stderr`).

## Limites connues

* Avertissement `pdf.fonts.base14_helvetica_reference` : le rendu historique référence Helvetica
  sans l'intégrer (corrigé seulement par le chemin C4). Signalé en `WARN`, non corrigé ici.
* La QA repère les points par le rayon de 4,1 pt du rendu historique (cases `8,2 pt`), les murs par leur épaisseur de 3 pt et les symboles d'association par leur trait de 2,6 pt et leurs ancres de 6,8 pt : si le rendu change, elle échoue (fail-closed) au lieu de passer à tort.
* Chaque rendu démarre un processus Python (≈ 0,5 s) ; une génération en lance trois (construction, audit du staging, audit après publication).
* Les octets dépendent des versions de ReportLab et des polices DejaVu (voir les empreintes de référence).
* Pas de contrôle prépresse/KDP, pas de fonds perdus, pas de couverture, pas d'épreuve papier.
* Un contrôle automatique n'est ni une relecture bilingue humaine (MAJOR-04), ni un essai
  enfant–adulte (MAJOR-03), ni une validation éditoriale.
* L'audit ne protège pas contre un processus ayant les mêmes privilèges (TOCTOU hors périmètre,
  comme pour `export/builder.py`).
* Le contrôle d'unicité du labyrinthe n'est pas ajouté à `quality/checks.py` et
  `books/halloween_2026/page_plan.csv` n'est pas migré : incréments distincts.
