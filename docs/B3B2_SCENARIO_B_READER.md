# B3-B.2 — Lecteur en lecture seule du scénario B

```text
kind                  = READ_ONLY_ANALYSIS_NON_PRODUCTION
ready_for_kdp         = false
MAJOR-03              = OPEN
MAJOR-04              = OPEN
EDITORIAL             = PENDING
KDP                   = FORBIDDEN
PRODUCTION_GENERATION = FORBIDDEN
```

Ces valeurs sont des **constantes du code** (`lafractale/scenario_b/__init__.py`). Elles ne sont jamais lues depuis une source : une
source qui les contredit produit un constat `GATES_CONSISTENT`, jamais un changement de statut.

## Rôle

Cartographier, page par page, ce qui sépare le moteur actuel du premier cahier complet : capacités techniques réelles, blocages
éditoriaux, validations humaines manquantes, contradictions entre documents. **Aucun PDF, aucune génération, aucun LLM, aucun appel
réseau, aucune écriture dans les sources.**

```bash
python -m lafractale.scenario_b analyze --root . --out-dir <répertoire hors sources> [--overwrite] [--strict]
python -m lafractale.scenario_b validate-report <scenario_b_report.json>
```

Sorties (noms fixes) : `scenario_b_report.json`, `scenario_b_report.md`, `scenario_b_synthesis.md`. La sortie est refusée dans
`docs/editorial`, `assets`, `books`, ou via un lien symbolique ; un rapport existant n'est remplacé qu'avec `--overwrite`.
Codes de sortie : `0` rapport écrit ; `1` (`--strict`) contradiction ou anomalie de structure détectée ; `2` analyse impossible.

## Sources et autorité

| Source | Rôle | Remarque |
|---|---|---|
| `b3a3/01_chemin_de_fer_scenario_B_56_pages.csv` | `ACTIVE_CANONICAL` | **fait autorité pour la pagination** |
| `b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv` | `ACTIVE_CANONICAL` | 46 consignes FR/EN p.03–48 |
| `b3a3/02_controle_corriges_scenarios.csv` | `ACTIVE_CANONICAL` | besoin de corrigé (31, lignes `B`) |
| `b3a4/02_grille_relecture_humaine_complete.csv` | `ACTIVE_CANONICAL` | 103 unités, états de validation réels |
| `b3a4/08_validation_evidence.json`, manifestes `09_integrity_manifest.json` | `ACTIVE_SUPPORTING` / `INTEGRITY_REFERENCE` | recoupements, empreintes |
| `b3a3/03_…historiques_47…`, `b3a4/03_archive_historique_47…` | `HISTORICAL_ARCHIVE_EXCLUDED_FROM_ACTIVE_PLAN` | comptées, jamais planifiées |
| `books/halloween_2026/page_plan.csv` | `LEGACY_NON_AUTHORITATIVE` | non utilisé (migration non validée) ; écart signalé en `INFO` |
| `books/halloween_2026/book.yaml`, `assets/illustrations/approvals.json` | `ENGINE_CONFIGURATION` | lexique, registre d'illustrations |

Chaque fichier est ouvert une fois via `engine.contracts.read_bounded` (pas de lien symbolique, fichier régulier, taille bornée),
haché en SHA-256 et listé dans `provenance`. Le décodage CSV est strict (UTF-8, en-tête et colonnes obligatoires, aucune ligne
irrégulière) ; le JSON passe par `security.strict_json` ; le texte des consignes par la politique Unicode `security.text`.

## Erreurs de structure vs blocages attendus

* **Fatal (code 2, aucun rapport)** : source obligatoire absente, lien symbolique, UTF-8 invalide, colonne obligatoire absente, ligne
  irrégulière, YAML/JSON illisible. L'analyse n'a alors aucun sens.
* **Constats (`findings`, le rapport est produit)** : `STRUCTURE` (page absente/dupliquée/hors plage, source optionnelle absente, Unicode),
  `CONTRADICTION` (désaccord entre sources), `INFO`. `analysis.structure_ok` vaut `false` s'il existe un constat `STRUCTURE`.
* **Blocages éditoriaux attendus** (copies d'ouverture absentes, 31 solutions, copies de production p.55/p.56, 8 pages `HUMAN_REVIEW`,
  validation humaine) : **jamais** des erreurs ; ils sont conservés tels quels dans `pages[].blockers` et `pages[].sources`.

## Compatibilité technique (indépendante de l'éditorial)

| Statut | Règle appliquée |
|---|---|
| `SUPPORTED` | mécanique présente **et** page couverte de bout en bout (pilote C4 : p.04 `maze`, p.06 `connect_dots`, p.20 `match`, profil `halloween-editorial-v1`) |
| `PARTIAL` | générateur présent, mais page non couverte : contrat B3-B.1 limité aux fixtures synthétiques, `maze` 5×5 fixe sans paramètre, `connect_dots` à nombre de points non spécifié, `match` limité à 4 jumeaux identiques et à la famille `shapes` du registre |
| `UNSUPPORTED` | mécanique absente du moteur (36 activités, 13 mécaniques) ou page sans composition (ouverture, corrigés, lexique, diplôme) |
| `UNKNOWN` | type de plan inconnu du lecteur, ou page absente du plan : exigences non évaluables |

Les faits moteur sont **mesurés** (`engine_capabilities`) en générant en mémoire des activités de sonde avec les générateurs existants,
pas recopiés. Passer une grille entière à `VALIDATED` ne change aucun statut technique (testé).

## Schéma du rapport (`lafractale-scenario-b-report-v1`)

Clés racine (fermées) : `schema`, `kind`, `reader_version`, `gates`, `ready_for_kdp`, `authority`, `provenance`, `engine_capabilities`,
`illustration_registry`, `analysis`, `findings`, `pages`, `summary`, `synthesis`. Aucune horloge ni chemin absolu : le rapport est
**octet-à-octet déterministe** (JSON trié, UTF-8) et indépendant de l'emplacement du dépôt.

Chaque entrée de `pages[]` (56, numérotées 1..56) :

| Clé | Contenu |
|---|---|
| `page`, `title`, `plan_present`, `plan_type`, `content_kind`, `mechanic`, `plan` | identité issue du plan B3-A.3 |
| `technical` | `status` ∈ SUPPORTED/PARTIAL/UNSUPPORTED/UNKNOWN, `family`, `reasons`, `missing_capabilities`, `open_questions` |
| `sources.instruction` | `PRESENT`/`ABSENT`/`NOT_APPLICABLE`, textes FR/EN, classification B3-A.3, `c4_locked` |
| `sources.solution` | `required`, `kind`, `answer_page`, `status` (état réel de la grille : `BLOCKED_BY_SOURCE`, …, `NOT_REQUIRED`, ou `NOT_LISTED_IN_ANSWER_CONTROL` pour une activité fermée absente du contrôle des corrigés — p.09/19/29/38 — signalée en `INFO`) |
| `sources.illustration` | `scene_art` (`NOT_VERIFIABLE_NO_PAGE_BINDING`), `companion_art` (liaison C1 approuvée ou `NONE_BOUND`) |
| `sources.units` | unités de la grille avec leur complétude, statut et revue humaine réels |
| `editorial` | `state` (`BLOCKED_BY_SOURCE`, `HUMAN_REVIEW`, `NOT_VALIDATED`, `VALIDATED`, `NO_SOURCE`), `missing_validations` |
| `blockers`, `dependencies`, `actions` | codes, catégories (`DEV`, `EDITORIAL_CONTENT`, `HUMAN_VALIDATION`, `DOC_CONSISTENCY`) |

`VALIDATED` n'est restitué que si la grille porte à la fois une identité de validateur et une référence de preuve ; sinon le constat
`VALIDATION_WITHOUT_EVIDENCE` est émis et l'unité reste non validée. Rien n'est jamais approuvé par déduction. La validité du rapport
est vérifiée par `lafractale.scenario_b.schema.validate_report` (aussi exposée par la sous-commande `validate-report`).

## Architecture

| Module | Rôle |
|---|---|
| `scenario_b/sources.py` | chargement borné, SHA-256, CSV/JSON stricts |
| `scenario_b/capabilities.py` | faits du moteur mesurés, règles de compatibilité par page |
| `scenario_b/analyzer.py` | contrôles de structure, recoupements, diagnostics par page, synthèse |
| `scenario_b/synthesis.py` | catalogue de composants, dépendances, ordre d'implémentation |
| `scenario_b/render.py` | Markdown (pur, déterministe) |
| `scenario_b/schema.py` | schéma testable du rapport |
| `scenario_b/__main__.py` | CLI |

Réutilisé sans modification : `engine.contracts.read_bounded`, `security.strict_json`, `security.text`, `activities.engine`
(`generate`, `SHAPES`), `engine.registry.MECHANICS`, `editorial` (profil C4), `illustrations.routing` (liaisons C1, lecture seule).
Aucun module existant n'importe `scenario_b` (testé) : le lecteur est isolé du moteur de production.

## Rapport de démonstration

`docs/b3b2/demo/` contient le rapport produit sur les sources réellement présentes dans ce dépôt
(`python -m lafractale.scenario_b analyze --root . --out-dir docs/b3b2/demo`). Il n'est **pas** un document éditorial : il ne valide rien.
