# B3-B.3a — Contrat canonique des 56 pages (scénario B)

```text
kind                  = READ_ONLY_PAGE_CONTRACT_NON_PRODUCTION
production_authorized = false   (constante du code)
ready_for_kdp         = false
MAJOR-03              = OPEN
MAJOR-04              = OPEN
EDITORIAL             = PENDING
KDP                   = FORBIDDEN
PRODUCTION_GENERATION = FORBIDDEN
```

Module : `src/lafractale/scenario_b/pages.py` — `load_pages(root) -> ScenarioBPages`.
Aucune CLI, aucun argument, aucune variable d'environnement : la fonction ne prend que la racine des sources.

## Rôle

Représenter chacune des 56 pages du cahier Halloween (scénario B) par un `PageRecord` **immuable** et **traçable**, construit à partir des
sources éditoriales actives, en lecture seule. Ce contrat est la fondation des fonctionnalités suivantes du moteur ; il **n'autorise
rien** : ni rendu, ni génération, ni adaptation vers le contrat synthétique B3-B.1 (aucun `SpecSet` n'est produit, aucun adaptateur n'existe).

## Sources et réutilisation

Chargement unique par `scenario_b.sources.load_sources` (B3-B.2 : fichier régulier, pas de lien symbolique, taille bornée, SHA-256,
CSV strict). Les règles de pagination (56 pages, p.03–48, p.49–54, répartition 6/5/5/5/5/5, 18 paires, 6 unités p.56, 103 unités,
respirations p.42/45/47) sont **importées** de `scenario_b.analyzer`, jamais recopiées. Pas de second parseur CSV/JSON.

| Source | Usage |
|---|---|
| `b3a3/01_chemin_de_fer_scenario_B_56_pages.csv` | identité de page : titre, type, statut du plan, niveau de demande |
| `b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv` | consignes FR/EN p.03–48 |
| `b3a3/02_controle_corriges_scenarios.csv` (lignes `B`) | besoin de corrigé : page source → page de destination |
| `b3a4/02_grille_relecture_humaine_complete.csv` | 103 unités et statuts éditoriaux réels |

`books/halloween_2026/page_plan.csv` (migration non validée) est lu comme octets par `load_sources` mais **jamais parsé ni utilisé** ;
les archives de 47 propositions, les preuves, les manifestes et le registre d'illustrations ne sont pas utilisés non plus.

## Modèle

Tous les objets sont des `dataclass(frozen=True, slots=True)` ne contenant que `str`, `int`, `bool`, `None`, tuples et autres objets gelés
(aucun `dict`/`list`/`set`). `to_dict()` renvoie une copie neuve : la modifier n'atteint jamais le contrat.

* `PageRecord` : `page`, `title`, `nature` (`opening`/`activity`/`creative`/`answers`/`lexicon`/`closing`/`unknown`), `content_type`
  (type du plan), `mechanic` (= type du plan pour les activités, `None` sinon), `plan_status`, `demand_level`, `plan_correction_status`,
  `c4_locked`, `instruction_fr/en`, `answer_requirement` (`REQUIRED` / `NOT_LISTED_IN_ANSWER_CONTROL` / `NOT_APPLICABLE`), `answer`
  (page source → page de corrigé, type, unité de grille), `answer_entries` (pages 49–54 : entrées reliées), `units`, `provenance`, `issues`.
* `UnitRecord` : une unité de la grille ; **tous les statuts sont la copie littérale** de la grille (`final_status`, cinq revues,
  `validator_identity`, `evidence_reference`), plus `evidence_complete` (identité **et** preuve renseignées).
* `Provenance` : fichier, SHA-256, colonnes concernées et **ligne physique uniquement lorsqu'elle est fiable** (fichier à un enregistrement
  par ligne ; sinon `None`).
* `Issue` : `code`, `severity` (`BLOCKING` / `NON_BLOCKING`), message, pages, sources.

## Deux niveaux qui ne fusionnent pas

* **`readable`** (`readability = READABLE | NOT_READABLE`) est *dérivé* : c'est l'absence de toute `Issue` bloquante. Ce n'est pas un champ,
  il ne peut pas être passé au constructeur ni affecté. Il dit que la page est lisible et structurellement non ambiguë — pas qu'elle est validée.
* **`production_authorized`** est une propriété qui renvoie la constante `False` du module. Ce n'est ni un champ, ni un argument de
  constructeur, ni une colonne lue : une colonne CSV nommée `production_authorized` est ignorée et signalée (`AUTHORIZATION_COLUMN_IGNORED`) ;
  une variable d'environnement ou un YAML n'est jamais consulté. Même une unité `VALIDATED` avec preuve complète laisse la page à `False`.
  (Limite connue de Python : `object.__setattr__` contourne tout objet gelé ; le contrat protège contre l'usage normal et la falsification
  par les données, pas contre du code hostile dans le même processus.)

## Cohérence : bloquant ou documenté

Erreurs de structure (source absente, lien symbolique, CSV mal formé, UTF-8 invalide, colonne absente) : `ReaderError`, aucun contrat partiel.

**Bloquant** — la page concernée n'est pas `READABLE` : page dupliquée/absente du plan ; consigne absente, vide ou dupliquée ; titre/type
plan ≠ consignes ; grille ≠ consignes ; Unicode non canonique (politique `security.text`) ; unité dupliquée, orpheline, hors périmètre actif
ou rattachée à une page de nature incompatible ; nombre d'unités attendu non respecté (p.01, 02, 55, 56, une consigne par activité) ;
corrigé dupliqué, page de corrigé invalide ou différente entre contrôle et consignes, entrée de grille absente/orpheline/mal placée, corrigé
sur une page libre (coloriage, création), plan « libre » avec corrigé, plan annonçant un corrigé non listé, répartition ≠ 31 / 6-5-5-5-5-5 ;
statut hors vocabulaire B3-A.4 ; `VALIDATED` sans identité de validateur **et** preuve (revendication non reconnue) ; `final_status=VALIDATED`
sans les cinq revues `VALIDATED`. Une anomalie sans page identifiable (p. ex. page hors 1..56, unité orpheline) est portée par
`ScenarioBPages.issues` et retire `all_readable`.

**Non bloquant** — documenté seulement : `correction_status` du plan vide pour 25 pages qui ont un corrigé (le contrôle des corrigés fait
foi) ; colonne d'autorisation ignorée.

## Sérialisation

`ScenarioBPages.to_canonical_json()` : JSON à clés triées, séparateurs fixes, sans horodatage ni chemin absolu — identique d'une machine et
d'un répertoire à l'autre. Le schéma est `lafractale-scenario-b-pages-v1` ; `gates` reprend les constantes du lecteur B3-B.2.

## Résultat sur les sources actuelles

56 pages, 56 `READABLE`, 103 unités (46 consignes, 31 corrigés, 18 paires, 2 ouvertures, 6 unités p.56), 31 corrigés reliés (6/5/5/5/5/5),
statuts littéraux inchangés (64 `NOT_VALIDATED`, 39 `BLOCKED_BY_SOURCE`, 0 validation humaine), `production_authorized=False` partout.
« Lisible » ne signifie pas « prêt » : l'état éditorial reste `PENDING`.

## Hors périmètre

Rendu, génération, `SpecSet`, mécaniques v2 (B3-B.3b), levée de MAJOR-03/04, validation éditoriale, KDP. Rien n'importe `pages.py` en dehors des tests.
