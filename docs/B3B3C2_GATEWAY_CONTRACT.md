# B3-B.3c.2 — Contrat de passerelle entre le contrat de page (B3-B.3a) et les mécaniques v2 (B3-B.3b)

```text
kind                  = DESIGN_SPECIFICATION_NON_PRODUCTION
statut du document    = SPÉCIFICATION UNIQUEMENT — aucun code, aucun test exécutable, aucune donnée réelle
version du document   = b3b3c2-gateway-contract-0.1 (PROPOSITION, en attente des arbitrages du §12)
base                  = main 1a3a3e532f4c60dba83aaa8734bb235b05e8eb51 (fusion de la PR #21)
production_authorized = false   MAJOR-03=OPEN  MAJOR-04=OPEN  EDITORIAL=PENDING
KDP=FORBIDDEN  PRODUCTION_GENERATION=FORBIDDEN  ready_for_kdp=false  (issue #15 ouverte)
```

Ce document spécifie une passerelle **qui n'existe pas** et que ce lot n'implémente pas. Il ne crée aucune association entre une page
réelle et une activité, ne génère rien depuis les pages du livre, ne simule aucune validation humaine et ne débloque rien. Tous les
exemples sont **purement synthétiques** (§11 de ce document pour la règle de fabrication des exemples).

## 0. Constats techniques qui contraignent la conception

Ces faits sont lus dans le code de `main` (1a3a3e5) ; ils justifient plusieurs choix ci-dessous et plusieurs arbitrages du §12.

| # | Constat | Source | Conséquence |
|---|---|---|---|
| F1 | Une activité v2 exige un identifiant `syn-…` (minuscules, chiffres, tirets, 50 caractères au plus) ; un identifiant de page, un titre ou `P03-ACTIVITY` sont refusés (`BAD_ACTIVITY_ID`). | `mechanics_v2/core.py` (`ACTIVITY_ID`) | La passerelle ne peut pas passer un identifiant éditorial au générateur ; il faut un identifiant synthétique dérivé de la liaison (DEC-1). |
| F2 | Toute activité v2 porte `kind = SYNTHETIC_NON_PRODUCTION`, `production_authorized = false` (constantes du code) et `human_pedagogical_validation = "NONE"`. | `mechanics_v2/__init__.py`, `core.py` | Aucune sortie v2 ne peut, par construction, être « de production ». Ce contrat ne change pas cela. |
| F3 | Les vocabulaires v2 sont fermés et géométriques (polygones, étoiles, motifs de points) ; aucun pictogramme réel ni objet narratif n'existe. | `match.py`, B3-B.3b | Une activité générée est un **squelette structurel** (géométrie + solution), pas un contenu éditorial (DEC-2). |
| F4 | `PageRecord.readable` est dérivé de l'absence d'`Issue` bloquante ; `production_authorized` est une constante `False`. Les cinq revues d'une unité sont les copies littérales de la grille ; aucune n'est validée aujourd'hui (64 `NOT_VALIDATED`, 39 `BLOCKED_BY_SOURCE`, 0 validation humaine). | `scenario_b/pages.py`, `docs/B3B3A_PAGE_CONTRACT.md` | Sur les données réelles actuelles, aucune liaison ne peut dépasser le statut « technique seulement » (DEC-9). |
| F5 | `PageRecord` ne possède pas d'empreinte propre ; seules les sources ont un SHA-256 (`Provenance`). | `pages.py` | La passerelle calcule elle-même un condensé du `PageRecord` canonique sans modifier le contrat (§3.2). |
| F6 | `plan_correction_status` du plan est vide pour 25 pages qui ont pourtant un corrigé ; le contrôle des corrigés (p.49–54) fait foi (`answer_requirement`, `answer`, `answer_entries`). | `B3B3A_PAGE_CONTRACT.md` | `correction_status` n'est jamais une preuve (§7). |
| F7 | L'empreinte v2 est un SHA-256 de contenu : intégrité, pas provenance authentifiée ; `search.attempts` n'est pas rejoué ; la CI ne teste que Python 3.11. | dettes B3-B.3b | Les approbations ne peuvent pas reposer sur l'empreinte seule (§7.4, DEC-5). |
| F8 | Les vérificateurs v2 sont durcis (B3-B.3c.1) pour les entrées JSON/dict ordinaires ; les objets Python arbitraires sont hors contrat. | `B3B3C1_HARDENING_AND_DEBT.md` | La passerelle réutilise la même garde de forme sur tout fichier de liaison ou d'approbation (SEC-12). |

## 1. Objet, périmètre, non-objectifs

**Objet.** Définir comment une *unité éditoriale* (une `UnitRecord`/`PageRecord` du contrat B3-B.3a) peut, un jour, être **explicitement** reliée à
une mécanique v2 (`maze_v2`, `connect_dots_v2`, `match_v2`), comment les paramètres de génération sont proposés puis approuvés par des humains,
comment les validations restent des axes distincts, et comment les corrigés sont tracés — le tout *fail-closed*.

**Non-objectifs (interdits dans ce lot et dans toute PR qui implémenterait ce document sans GO).** Aucun code de passerelle ; aucune liaison réelle
page ↔ activité ; aucune génération depuis les pages du livre ; aucun rendu ; aucune validation humaine simulée ou inventée ; aucun déblocage
KDP ; aucune modification de `PageRecord`, des générateurs, des vérificateurs, des CSV, des livres, du moteur historique ou de la CI.

## 2. Séparation des responsabilités et schéma des flux

### 2.1 Qui possède quoi

| Composant | Possède | Peut consulter | Peut transformer | Peut transmettre | Ne peut jamais |
|---|---|---|---|---|---|
| **Contrat éditorial** (`scenario_b.pages`, B3-B.3a) | `PageRecord`, `UnitRecord`, statuts littéraux de la grille, provenance SHA-256, `Issue` | sources éditoriales actives (lecture seule) | rien hors de sa normalisation existante | `ScenarioBPages` immuable | connaître une mécanique v2, un paramètre, une approbation ; élever `production_authorized` |
| **Mécaniques v2** (`mechanics_v2`, B3-B.3b/c.1) | générateurs, vérificateurs, registre fermé, constantes `PRODUCTION_AUTHORIZED=False` | ses seuls arguments `(mechanic, activity_id, seed, params)` | arguments → `V2Activity` immuable | activité, solution, mesures, empreinte | lire un fichier, une variable d'environnement, un `PageRecord`, un CSV ; accepter un identifiant non `syn-` |
| **Passerelle** (future, non écrite) | `LinkRecord`, `ParamsRecord`, `GatewayResult`, table de compatibilité, moteur de décision | `ScenarioBPages` (valeurs, pas fichiers), registre `MECHANICS_V2` (liste et `PARAM_SPEC`), fichiers de liaison/approbation **écrits par des humains** | liaison + paramètres approuvés → arguments v2 par **projection pure** (aucun défaut, aucune déduction) | résultat technique étiqueté `TECHNICAL_ONLY`, refus avec code | écrire dans les sources, créer ou modifier une approbation, deviner un paramètre, choisir une mécanique, produire un remplacement, changer une constante |
| **Humains** (relecteurs, Kévin) | liaisons, approbations de paramètres, validations pédagogique/éditoriale, décisions de production/KDP | tout ce qui précède | — | — | être remplacés par un condensé SHA-256 ou par un automate |

Règle de dépendance : `passerelle → (contrat éditorial, mécaniques v2)`. **Aucun import dans l'autre sens.** `scenario_b` n'importe pas `mechanics_v2` ni
la passerelle ; `mechanics_v2` n'importe ni `scenario_b` ni la passerelle ; le moteur historique n'importe rien de ces trois (test d'isolation par analyse de code, §10).

### 2.2 Schéma des flux

```text
 SOURCES ÉDITORIALES (lecture seule, CSV actifs)                         FICHIERS HUMAINS (versionnés, revus)
        │  load_sources + SHA-256                                          ├── liens.json      (LinkRecord)
        ▼                                                                  ├── params.json     (ParamsRecord : proposés)
 ┌───────────────────┐                                                     └── approbations.json (ApprovalRecord)
 │ CONTRAT ÉDITORIAL │  ScenarioBPages (PageRecord, UnitRecord, Issue)               │
 │  scenario_b.pages │──────────────────────────────┐                                │ garde de forme (SEC-12)
 └───────────────────┘                              ▼                                ▼
                                          ┌─────────────────────────────────────────────────────┐
                                          │                    PASSERELLE                       │
                                          │ 1 résolution    (unité unique ? lien déclaré ?)     │
                                          │ 2 compatibilité (table fermée, jamais l'origine)    │
                                          │ 3 condensés     (page, sources, versions) = frais ? │
                                          │ 4 paramètres    (approuvés ? bornes de PARAM_SPEC ?)│
                                          │ 5 projection pure → arguments techniques            │
                                          └───────────────┬─────────────────────────────────────┘
                                                          │ (mechanic, syn-id, seed, params) — rien d'autre
                                                          ▼
                                          ┌───────────────────────────────┐
                                          │ MÉCANIQUES v2 (generate_v2,   │
                                          │ verify_v2 ; indépendantes)    │
                                          └───────────────┬───────────────┘
                                                          │ V2Activity (SYNTHETIC_NON_PRODUCTION)
                                                          ▼
                                          ┌─────────────────────────────────────────────┐
                                          │ 6 contrôle des axes de validation (§6)      │
                                          │ 7 liaison de corrigé (§7)                   │
                                          │ 8 verdict : REFUSED(code) | TECHNICAL_ONLY  │
                                          └─────────────────────────────────────────────┘
        Aucune flèche ne sort vers : sources éditoriales, approbations, rendu, export, KDP.
        Aucun état « AUTORISÉ » n'existe dans ce contrat (production_authorized reste la constante False).
```

## 3. Structure de liaison versionnée

### 3.1 `LinkRecord` (schéma `lafractale-gateway-link-v1`)

Fichier écrit **à la main par des humains**, jamais produit par un outil à partir des sources. Chaque liaison associe **une** unité à **une** mécanique.

| Champ | Type | Règle |
|---|---|---|
| `link_id` | chaîne `lnk-` + `[a-z0-9-]{1,40}` | unique dans le fichier ; **identifiant opaque** : ne dérive pas du titre, de la page ni d'un CSV |
| `schema` | chaîne | exactement `lafractale-gateway-link-v1` |
| `source_ref.book` | chaîne | identifiant du livre/racine de sources chargé (le contrat de page opère par racine de livre ; deux livres existent dans le dépôt) ; absent ou différent du livre chargé → `BOOK_MISMATCH` |
| `source_ref.unit_id` | chaîne | l'identifiant d'unité exact de `UnitRecord.unit_id` ; comparaison **octet à octet** après la normalisation canonique du contrat (`security.text`) |
| `source_ref.page` | entier | recoupement obligatoire avec `UnitRecord.final_page` ; incohérence → refus (jamais utilisé comme clé de recherche) |
| `source_ref.page_digest` | SHA-256 hex | condensé du `PageRecord` canonique (§3.2) au moment de la liaison |
| `source_ref.sources_sha256` | dictionnaire fixe `{plan, instructions, answers, grid}` | SHA-256 des quatre sources utilisées (valeurs de `Provenance`) |
| `mechanic` | chaîne | l'une des clés de `MECHANICS_V2` ; sinon `UNKNOWN_MECHANIC` |
| `mechanic_version` | chaîne | la version attendue (`MechanicV2.version`) ; divergence → refus |
| `gateway_contract` | chaîne | version de ce contrat (`b3b3c2-gateway-contract-…`) |
| `declared_by` | `{id, role}` | identité humaine déclarée (non authentifiée, §7.4) |
| `declared_at` | chaîne | informatif seulement, jamais une base de décision |

**Règles.**

* **Aucune déduction.** Ni le titre, ni le numéro de page, ni `PageRecord.mechanic`, ni une colonne CSV ne créent ni ne complètent une liaison. Une unité sans `LinkRecord` n'a **aucune** mécanique (état `UNLINKED`) : ce n'est pas une erreur, c'est l'état par défaut ; il n'émet aucun résultat et ne déclenche aucun repli (§6.1).
* **Compatibilité = condition nécessaire, jamais origine.** Une table fermée et versionnée `COMPATIBILITY` (proposition en DEC-7) indique quelles valeurs de `PageRecord.mechanic` peuvent être liées à quelle mécanique v2. La passerelle **vérifie** que la liaison déclarée est permise ; elle ne la **choisit** pas.
* **Unité sans mécanique compatible** (`PageRecord.mechanic` absent de la table, ou nature non-activité) : `REFUSED(NO_COMPATIBLE_MECHANIC)`. Aucune mécanique « la plus proche ».
* **Doublons.** Deux `LinkRecord` de même `link_id` ; deux liaisons pour la même `unit_id` ; une même `unit_id` rattachée à deux mécaniques → `REFUSED(AMBIGUOUS_LINK)` pour **toutes** les liaisons concernées (pas de « première gagne »). Même règle pour les paramètres et les approbations (§7.2 bis).
* **Références ambiguës ou introuvables.** `unit_id` absent de `ScenarioBPages`, présent plusieurs fois, ou dont `final_page` diffère de `source_ref.page` → `REFUSED(BOOK_MISMATCH | UNIT_NOT_FOUND | UNIT_AMBIGUOUS | PAGE_MISMATCH)`.
* **Identifiants.** Comparaison exacte ; pas de normalisation de casse, d'espaces ni de Unicode au-delà de la forme canonique du contrat ; les identifiants à homoglyphes ou caractères invisibles sont refusés par la politique `security.text` existante.
* **Lien périmé** : `page_digest`, `sources_sha256`, `mechanic_version` ou `gateway_contract` différents des valeurs courantes → `STALE_LINK` (refus ; renouvellement humain explicite).

### 3.2 Condensé de la page (sans modifier `PageRecord`)

`page_digest = SHA-256( canonical_json( PageRecord.to_dict() ) )`, calculé par la passerelle avec la même sérialisation canonique que le contrat
(clés triées, séparateurs fixes, UTF-8). Il inclut les statuts littéraux des unités : toute modification d'un statut, d'une consigne ou d'une
provenance change le condensé et périme liaison et approbations (§7.5). C'est un contrôle d'intégrité, **pas** une authentification.

*Conséquence assumée de ce choix* : `PageRecord.to_dict()` contient `Provenance` (SHA-256 du **fichier source entier** et numéros de ligne). Toute modification de l'une des quatre sources, **même sur une autre page**, change le condensé de **toutes** les pages du livre et périme donc toutes les liaisons et approbations (péremption maximale, voir DEC-8). C'est volontaire dans cette proposition (fail-closed, preuve simple) ; un condensé restreint à la page serait possible mais devrait être arbitré. La stabilité du condensé d'une machine à l'autre repose sur la sérialisation canonique du contrat de page (chemins relatifs, clés triées) et **devra être démontrée par un test d'octets identiques** avant d'invoquer SEC-15.

### 3.3 Exemple synthétique

Les identifiants et numéros ci-dessous sont fictifs (la page `901` n'existe pas : le cahier a les pages 1 à 56).

```json
{
  "schema": "lafractale-gateway-link-v1",
  "link_id": "lnk-fixture-0001",
  "source_ref": {
    "unit_id": "syn-unit-0001",
    "page": 901,
    "page_digest": "<64 hex synthétiques>",
    "sources_sha256": {"plan": "<hex>", "instructions": "<hex>", "answers": "<hex>", "grid": "<hex>"}
  },
  "mechanic": "maze_v2",
  "mechanic_version": "b3b3b1-maze-v2-1.0",
  "gateway_contract": "b3b3c2-gateway-contract-0.1",
  "declared_by": {"id": "syn-human-1", "role": "SYNTHETIC_FIXTURE"},
  "declared_at": "2000-01-01T00:00:00Z"
}
```

## 4. Paramètres : proposés, approuvés, techniques

Trois objets distincts, à trois niveaux de confiance, **non fusionnables**. Aucun paramètre n'est lu ni déduit des données éditoriales existantes.

| Niveau | Objet | Auteur | Contenu | Peut être transmis à un générateur ? |
|---|---|---|---|---|
| **Proposé** | `ParamsRecord.proposed` | un humain, ou un outil/assistant **marqué** `proposer_kind = TOOL` | valeurs candidates + justification libre | **Non**, jamais |
| **Approuvé** | `ApprovalRecord` (`kind = PARAMS`) | une identité humaine déclarée, non vide | un *sujet* = condensé de `(link_id, mechanic, version, params, seed, page_digest)` | **Non** directement : il n'est qu'une preuve |
| **Technique** | arguments `(mechanic, activity_id, seed, params)` | la **projection pure** de la passerelle | exactement les clés de `PARAM_SPEC` + graine + identifiant `syn-…` | **Oui**, à un seul endroit : `generate_v2` |

### 4.1 Procédure

1. **Proposition.** Un `ParamsRecord` référence un `link_id` et contient `params` (ensemble **fermé** : exactement les clés de `PARAM_SPEC` de la mécanique ; une clé en trop → `UNKNOWN_PARAM`, une clé absente → `MISSING_PARAM`, comme `check_params`), `seed` (entier explicite, DEC-6), `proposer`, `rationale`.
2. **Validation technique des bornes** par la passerelle en appelant les validateurs publics v2 (`PARAM_SPEC`) — sans générer. Une valeur hors borne n'est pas corrigée, elle est refusée.
3. **Approbation humaine.** Un `ApprovalRecord` de `kind = PARAMS` désigne le `ParamsRecord` par son condensé. L'approbateur est une identité humaine **déclarée** ; **l'auteur de la proposition peut être l'approbateur seulement si DEC-4 l'autorise** (recommandation : approbateur ≠ proposant lorsque le proposant est un outil).
4. **Projection.** La passerelle construit les arguments techniques par copie des valeurs approuvées ; l'identifiant `syn-…` est dérivé de `link_id` (DEC-1) par une fonction publique déterministe et documentée ; **aucune valeur par défaut, aucune graine implicite, aucune variable d'environnement**.
5. **Génération.** `generate_v2(...)` (qui régénère puis revérifie) ; toute `V2Error` est un refus avec son code d'origine, sans repli.

### 4.1 bis Sujet approuvé et drapeau `allow_pending_source`

`subject_digest = SHA-256( canonical_json({link_id, mechanic, mechanic_version, params, seed, allow_pending_source, page_digest, gateway_contract}) )`. `allow_pending_source` est un booléen **explicite, faux par défaut (valeur obligatoire dans le fichier, jamais supposée)** ; il n'a qu'un effet : lever le refus R13 pour une unité `NOT_VALIDATED`, **sans** jamais lever R09 (`BLOCKED_BY_SOURCE`), R07, R14 ni R15. Il est inclus dans le condensé (donc approuvé par un humain, périmé si modifié), figure dans `GatewayResult.labels` sous la forme `SOURCE_NOT_VALIDATED` lorsqu'il a été utilisé, et ne confère aucune validation (V3, V4, V5 et V6 inchangés). Il est **proposé** (DEC-9) et ne devient réel que si cette décision l'adopte.

### 4.2 Exemples synthétiques

```json
{ "schema": "lafractale-gateway-params-v1", "link_id": "lnk-fixture-0001",
  "proposer": {"id": "syn-human-1", "kind": "HUMAN"},
  "proposed": {"params": {"size": 5, "difficulty": "medium"}, "seed": 7, "allow_pending_source": false},
  "rationale": "exemple synthétique, aucune valeur éditoriale" }
```

```json
{ "schema": "lafractale-gateway-approval-v1", "approval_id": "apr-fixture-0001", "kind": "PARAMS",
  "decision": "APPROVED",
  "subject": {"link_id": "lnk-fixture-0001", "subject_digest": "<hex>", "allow_pending_source": false},
  "approver": {"id": "syn-human-2", "role": "SYNTHETIC_FIXTURE", "authentication": "UNAUTHENTICATED"},
  "evidence_reference": "syn-evidence-0001",
  "contract_versions": {"gateway": "b3b3c2-gateway-contract-0.1", "mechanic": "b3b3b1-maze-v2-1.0", "page_contract": "b3b3a-pages-1.0"},
  "recorded_at": "2000-01-01T00:00:00Z" }
```

## 5. Contrats d'entrée / sortie proposés

| Contrat | Schéma | Rôle | Écrit par |
|---|---|---|---|
| `LinkRecord` | `lafractale-gateway-link-v1` | associe une unité à une mécanique | humain |
| `ParamsRecord` | `lafractale-gateway-params-v1` | paramètres **proposés** | humain ou outil marqué |
| `ApprovalRecord` | `lafractale-gateway-approval-v1` | décision humaine liée à un condensé | humain uniquement |
| `GatewayResult` | `lafractale-gateway-result-v1` | verdict + preuves + étiquettes | passerelle (jamais persisté dans les sources) |

### 5.1 `GatewayResult`

| Champ | Contenu |
|---|---|
| `verdict` | `REFUSED` ou `TECHNICAL_ONLY` — **il n'existe pas d'autre valeur dans ce contrat** |
| `refusal` | `{code, message_borné, étape}` si `REFUSED`, sinon `null` |
| `link_id`, `unit_id` | références opaques |
| `technical` | si `TECHNICAL_ONLY` : `mechanic`, `version`, `activity_fingerprint`, `solution_digest`, `verify_v2 == []` |
| `axes` | le vecteur des six axes du §6, avec les domaines de valeurs du §6 (V1/V2 `PASS\|FAIL\|UNKNOWN`, V3/V4 `NOT_EVALUATED\|ATTESTED_UNAUTHENTICATED\|CONTRADICTORY`, V5/V6 `CONSTANT_FALSE`) ; absent (`null`) si le refus survient avant leur calcul |
| `answer_binding` | `BOUND \| MISSING \| INCONSISTENT \| NOT_REQUIRED` (§7) |
| `labels` | **toujours, y compris pour un refus** : `["SYNTHETIC_NON_PRODUCTION", "production_authorized=false", "ready_for_kdp=false"]` ; non supprimables |
| `fingerprints` | `page_digest`, `params_digest`, `activity_fingerprint`, `result_digest` |

Le résultat ne contient **ni** chemin absolu, **ni** horodatage décisionnel, **ni** texte éditorial ; sérialisation canonique identique à celle de B3-B.3b.

### 5.2 Exemples de sortie (synthétiques)

```json
{ "schema": "lafractale-gateway-result-v1", "verdict": "TECHNICAL_ONLY", "refusal": null,
  "link_id": "lnk-fixture-0001", "unit_id": "syn-unit-0001",
  "technical": {"mechanic": "maze_v2", "version": "b3b3b1-maze-v2-1.0", "activity_fingerprint": "<hex>", "solution_digest": "<hex>", "verify_v2": []},
  "axes": {"V1_page_readable": "PASS", "V2_geometry": "PASS", "V3_pedagogy_human": "NOT_EVALUATED",
           "V4_editorial": "NOT_EVALUATED", "V5_production": "CONSTANT_FALSE", "V6_kdp": "CONSTANT_FALSE"},
  "answer_binding": "NOT_REQUIRED",
  "labels": ["SYNTHETIC_NON_PRODUCTION", "production_authorized=false", "ready_for_kdp=false"] }
```

```json
{ "schema": "lafractale-gateway-result-v1", "verdict": "REFUSED",
  "refusal": {"code": "STALE_APPROVAL", "message": "page_digest divergent depuis l'approbation apr-fixture-0001", "step": "3-digests"},
  "link_id": "lnk-fixture-0001", "unit_id": "syn-unit-0001", "technical": null, "axes": null, "answer_binding": null,
  "labels": ["SYNTHETIC_NON_PRODUCTION", "production_authorized=false", "ready_for_kdp=false"],
  "fingerprints": {"page_digest": "<hex>", "result_digest": "<hex>"} }
```

## 6. Contrôle des validations : six axes indépendants

Les six axes ne se déduisent **jamais** les uns des autres. Chacun a une source de vérité, un décideur et une valeur courante.

| Axe | Question | Source de vérité | Décideur | Valeur sur `main` |
|---|---|---|---|---|
| **V1** Lisibilité technique de la page | la page est-elle lisible et structurellement non ambiguë ? | `PageRecord.readable` (aucune `Issue` bloquante) | machine (B3-B.3a) | calculable, ne signifie pas « prête » |
| **V2** Validité géométrique de l'activité | l'activité générée satisfait-elle tous ses critères exacts ? | `verify_v2(activity) == []` + `generate_v2` (auto-vérification) | machine (B3-B.3b/c.1) | calculable |
| **V3** Validation pédagogique humaine | un humain a-t-il validé l'adéquation 4–5 ans **de cette activité** ? | **uniquement** un `ApprovalRecord(kind=PEDAGOGY)` lié à `activity_fingerprint` ; les statuts de revue de l'unité (`human_review_status`, `age_4_5_mediation_status`) ne portent que sur le **texte de la consigne** et ne sont jamais une source de V3 | humain | `NOT_EVALUATED` (0 validation) |
| **V4** Validation éditoriale | l'unité, l'activité et son corrigé sont-ils validés éditorialement ? | `UnitRecord.final_status = VALIDATED` (cinq revues `VALIDATED`, identité **et** preuve) + `ApprovalRecord(kind=EDITORIAL_*)` | humain | `NOT_EVALUATED` (`EDITORIAL=PENDING`) |
| **V5** Autorisation de production | la production est-elle autorisée ? | constante `False` du code (`pages.PRODUCTION_AUTHORIZED`, `mechanics_v2.PRODUCTION_AUTHORIZED`) | humain, **par modification de code revue** — jamais par donnée | `False` |
| **V6** Autorisation KDP | la sortie KDP est-elle autorisée ? | constante `pages.READY_FOR_KDP = False`, statut `KDP FORBIDDEN` | humain, hors passerelle | `False` |

**Domaine des valeurs.** V1 et V2 : `PASS`, `FAIL`, `UNKNOWN`. V3 et V4 : `NOT_EVALUATED`, `ATTESTED_UNAUTHENTICATED` (une approbation fraîche, complète et cohérente existe ; son identité n'est que déclarée, §7.4), `CONTRADICTORY`. **V3 et V4 ne valent jamais `PASS`** dans ce contrat : la passerelle ne *constate* pas une validation humaine, elle consigne qu'une attestation déclarée existe. V5 et V6 : `CONSTANT_FALSE` uniquement.

**Nuance de l'axe V3.** La grille actuelle valide (ou validera) le **texte de la consigne**, pas une activité générée. Une activité générée par la passerelle est un *objet nouveau* : une validation pédagogique de la consigne ne vaut donc **jamais** validation de l'activité (la validation de l'activité est un `ApprovalRecord` distinct, lié à `activity_fingerprint`).

### 6.1 Table ordonnée de décision (première règle applicable gagne ; une seule table, complète)

L'ordre est celui du diagramme du §9. Une même entrée donne donc toujours le même code de refus.

| Rang | Étape | Condition | Verdict | Code de refus |
|---|---|---|---|---|
| R01 | garde | un fichier ou un champ échoue la garde de forme (SEC-12, SEC-13) | `REFUSED` | `HOSTILE_INPUT` |
| R02 | garde | tout champ, colonne, argument, variable d'environnement ou approbation affirmant `production_authorized`, `ready_for_kdp` ou une autorisation PRODUCTION/KDP | `REFUSED` | `AUTHORIZATION_CLAIM_REJECTED` |
| R03 | résolution | `LinkRecord` de même `link_id` en double, plusieurs liaisons pour une unité, une unité reliée à deux mécaniques | `REFUSED` (toutes les liaisons concernées) | `AMBIGUOUS_LINK` |
| R04 | résolution | livre/racine absent ou différent de celui chargé ; `unit_id` introuvable ; `unit_id` présent plusieurs fois ; `source_ref.page` ≠ `final_page` | `REFUSED` | `BOOK_MISMATCH` / `UNIT_NOT_FOUND` / `UNIT_AMBIGUOUS` / `PAGE_MISMATCH` |
| R05 | mécanique | mécanique absente de `MECHANICS_V2` ; type de page sans entrée dans `COMPATIBILITY` ; nature non-activité | `REFUSED` | `UNKNOWN_MECHANIC` / `NO_COMPATIBLE_MECHANIC` |
| R06 | fraîcheur | `page_digest`, `sources_sha256`, `mechanic_version` ou `gateway_contract` du lien différents des valeurs courantes | `REFUSED` | `STALE_LINK` |
| R07 | page | V1 ≠ PASS : la page porte une `Issue` bloquante — **y compris** un statut inconnu, une validation sans preuve ou incohérente, que le contrat de page convertit déjà en `Issue` bloquante (`UNIT_STATUS_UNKNOWN`, `VALIDATION_WITHOUT_EVIDENCE`, `VALIDATION_INCONSISTENT`) | `REFUSED` | `PAGE_NOT_READABLE` |
| R08 | statuts | statut hors vocabulaire ou absent **dans un fichier de la passerelle** (liaison, paramètres, approbation) ; statuts contradictoires entre approbations (p. ex. `EDITORIAL_*` sans `PEDAGOGY` correspondante ; `APPROVED` et `REJECTED` pour un même sujet) | `REFUSED` | `UNKNOWN_STATUS` / `CONTRADICTORY_STATUS` / `AMBIGUOUS_APPROVAL` |
| R09 | statuts | unité `BLOCKED_BY_SOURCE` | `REFUSED` | `EDITORIAL_STATUS_BLOCKING` |
| R10 | paramètres | `ParamsRecord` en double pour un `link_id`, clé inconnue/absente, valeur hors borne (validateurs publics de `PARAM_SPEC`) | `REFUSED` | `AMBIGUOUS_PARAMS` / `UNKNOWN_PARAM` / `MISSING_PARAM` / `BAD_*` (codes v2 conservés) |
| R11 | approbation | pas d'`ApprovalRecord` `PARAMS` `APPROVED` pour le condensé courant, ou identité déclarée absente/vide, ou preuve vide | `REFUSED` | `PARAMS_NOT_APPROVED` |
| R12 | approbation | approbation dont un condensé ou une version diverge (§7.5) | `REFUSED` | `STALE_APPROVAL` |
| R13 | source | unité `NOT_VALIDATED` sans `allow_pending_source = true` dans le sujet approuvé (DEC-9) | `REFUSED` | `EDITORIAL_STATUS_PENDING` |
| R14 | génération | `generate_v2` lève une `V2Error`, ou `verify_v2(activity)` non vide (V2 ≠ PASS) | `REFUSED` | `ACTIVITY_INVALID` (+ code `V2Error` d'origine) |
| R15 | corrigé | corrigé requis et `answer_binding ∈ {MISSING, INCONSISTENT}` | `REFUSED` | `ANSWER_UNBOUND` |
| R16 | sortie | tout ce qui précède est passé | `TECHNICAL_ONLY` | — |

**Unité non reliée.** Une unité sans `LinkRecord` n'a pas de ligne dans cette table : elle n'est pas évaluée et la passerelle ne rend **aucun** `GatewayResult` pour elle (état `UNLINKED`, ni erreur ni repli). Ce n'est un refus que lorsqu'un *appelant* demande explicitement le résultat d'une unité précise : la réponse est alors `REFUSED(UNLINKED)`.

**Pré-conditions réservées.** Le code `HUMAN_VALIDATION_MISSING` est réservé à un futur consommateur qui exigerait V3 ou V4 ; aucun traitement du présent contrat ne les exige.

Conséquences **exprimées sous forme de règles négatives** :

* V1 = PASS **n'implique pas** V2, V3, V4, V5, V6.
* V2 = PASS **n'implique pas** V3 ni V4.
* V3 = PASS **n'implique pas** V4 ; V4 = PASS **n'implique pas** V5 ; V5 n'est pas représentable par donnée ; V6 est hors passerelle.
* Aucun chemin de la table ne produit une valeur autre que `REFUSED` ou `TECHNICAL_ONLY`.
* Le tableau est le seul endroit où un code de refus est défini ; le §8.2 et le §10 y renvoient.

### 6.2 Machine à états d'une liaison

```text
 ABSENTE ──(humain écrit LinkRecord)──► DÉCLARÉE ──(schéma + garde OK)──► DÉCLARÉE_VALIDE
 DÉCLARÉE_VALIDE ──(résolution unique + compatibilité + condensés frais)──► LIÉE
 LIÉE ──(ParamsRecord valide aux bornes)──► PARAMÈTRES_PROPOSÉS
 PARAMÈTRES_PROPOSÉS ──(ApprovalRecord PARAMS valide, frais)──► PARAMÈTRES_APPROUVÉS
 PARAMÈTRES_APPROUVÉS ──(generate_v2 puis verify_v2 == [])──► RÉSULTAT_TECHNIQUE  (terminal : TECHNICAL_ONLY)
 tout état ──(échec d'une règle R01..R15)──► REFUSÉE(code)          (aucune sortie, aucun repli)
 tout état ≥ LIÉE ──(divergence d'un condensé ou d'une version)──► PÉRIMÉE ──(nouvelle décision humaine seulement)──► DÉCLARÉE
```

Il n'existe **aucun état** « autorisée », « validée pour production » ni « prête KDP » : les axes V3/V4 sont des *attestations déclarées* (jamais `PASS`) consignées dans
`GatewayResult.axes`, pas des états de la liaison, et aucun ne fait avancer la liaison au-delà de `RÉSULTAT_TECHNIQUE`.

## 7. Corrigés et traçabilité

### 7.1 Chaîne de relation

```text
 unité source (UnitRecord, p.03–48)
   └── AnswerLink (page source → page de corrigé, p.49–54)           ← contrôle des corrigés = foi pour l'EXIGENCE et la PLACE du corrigé
        └── answer_entry unit (UnitRecord de la page de corrigé)      ← texte éditorial du corrigé (humain), statut littéral de la grille
   └── LinkRecord → activité v2 (activity_fingerprint)
        └── solution technique (V2Activity.solution)                   ← proposition TECHNIQUE, jamais du texte éditorial
 AnswerBinding = { link_id, source_unit_id, answer_page, answer_entry_unit_id, activity_fingerprint, solution_digest, answer_page_digest }
```

### 7.2 Règles

* **Exigence de corrigé.** Elle provient exclusivement de `PageRecord.answer_requirement` et de `PageRecord.answer` / `answer_entries` (contrôle des corrigés). **`plan_correction_status` (le champ `correction_status` du plan) n'est jamais lu pour décider** : il peut être vide alors qu'un corrigé existe (dette F6) et pourrait être renseigné sans qu'un corrigé n'existe. Ce champ n'est ni preuve de présence, ni de validité, ni d'approbation.
* **Statuts de `answer_requirement`.** `REQUIRED` → `answer_binding` doit valoir `BOUND` (sinon R15). `NOT_APPLICABLE` → `NOT_REQUIRED`. `NOT_LISTED_IN_ANSWER_CONTROL` → contradiction à arbitrer par un humain : `INCONSISTENT` (refus), jamais « pas de corrigé ».
* **`BOUND`** exige : l'unité d'entrée de corrigé existe, est unique, est sur la page de corrigé annoncée, et son `answer_page_digest` est frais.
* **Contenu.** La solution v2 (chemin, ordre, permutation) est une **donnée technique**. La passerelle ne rédige, ne traduit ni ne complète aucun libellé de corrigé. Un corrigé éditorial est un texte humain, lié à `solution_digest` par un `ApprovalRecord(kind=EDITORIAL_ANSWER)` : l'humain atteste « ce texte décrit cette solution ».
* **Incohérence.** `solution_digest` d'une approbation ≠ solution courante, page de corrigé divergente entre contrôle et grille, ou deux corrigés pour une même unité → `INCONSISTENT`.

### 7.2 bis Approbations : types, doublons, conflits, révocation

* **Types (`kind`) fermés** : `PARAMS` (paramètres et graine), `PEDAGOGY` (adéquation de l'**activité** générée, liée à `activity_fingerprint`), `EDITORIAL_ACTIVITY` (activité retenue éditorialement), `EDITORIAL_ANSWER` (le texte du corrigé décrit bien `solution_digest`). Tout autre `kind` → `UNKNOWN_STATUS`. Dans cette version du contrat, seuls les `kind` `PARAMS` conditionnent un résultat ; les trois autres sont **consignés** dans `axes` (V3/V4) et ne débloquent rien.
* **Doublons et conflits.** Deux approbations de même sujet et de même `kind` (même `APPROVED` répété), ou un `APPROVED` et un `REJECTED` pour un même sujet, → `AMBIGUOUS_APPROVAL` (refus, comme pour les liaisons). Aucun ordre temporel ne départage : `recorded_at` est informatif. Même règle pour deux `ParamsRecord` d'un même `link_id` (`AMBIGUOUS_PARAMS`).
* **Révocation.** Elle consiste à *retirer* le fichier d'approbation par un changement revu (historique du dépôt) ou à y ajouter un `REJECTED` — ce qui, d'après la règle précédente, produit un refus `AMBIGUOUS_APPROVAL` jusqu'à ce qu'un humain retire la ligne obsolète. Il n'existe pas de « révocation implicite ».
* **Exemple synthétique (`PEDAGOGY`).** `{"schema":"lafractale-gateway-approval-v1","approval_id":"apr-fixture-0002","kind":"PEDAGOGY","decision":"APPROVED","subject":{"link_id":"lnk-fixture-0001","activity_fingerprint":"<hex>"},"approver":{"id":"syn-human-3","role":"SYNTHETIC_FIXTURE","authentication":"UNAUTHENTICATED"},"evidence_reference":"syn-evidence-0002","contract_versions":{"gateway":"b3b3c2-gateway-contract-0.1","mechanic":"b3b3b1-maze-v2-1.0","page_contract":"b3b3a-pages-1.0"},"recorded_at":"2000-01-01T00:00:00Z"}`. Une approbation `PEDAGOGY` ne fait pas passer V3 à `PASS` : elle le fait passer à `ATTESTED_UNAUTHENTICATED`.
* **Définitions des condensés.** `solution_digest = SHA-256(canonical_json(V2Activity.solution))` ; `answer_page_digest = SHA-256(canonical_json(PageRecord.to_dict() de la page de corrigé))`. `activity_fingerprint` est l'empreinte v2 existante (`V2Activity.fingerprint`) ; elle dépend de l'identifiant `syn-…`, donc de la dérivation depuis `link_id` : changer le `link_id` ou la fonction de dérivation change l'empreinte et périme les approbations.

### 7.3 Preuves attendues pour une approbation

`approver.id` non vide (identité humaine **déclarée** ; la passerelle ne peut pas distinguer un humain d'un outil qui se déclare humain, §7.4) ; `evidence_reference` non vide ; `decision` explicite ; `subject_digest` ; `contract_versions` complètes ; pas de champ d'autorisation. Une approbation sans identité **et** preuve est une revendication non reconnue (même règle que la grille B3-B.3a).

### 7.4 Ce que l'empreinte SHA-256 n'est pas

Un SHA-256 prouve que le contenu est **inchangé**, pas **qui** l'a approuvé. Dans ce contrat : l'empreinte *lie* une approbation à un contenu précis ; elle ne l'*authentifie* pas. Toute approbation porte donc `authentication = UNAUTHENTICATED` tant qu'un mécanisme d'authentification humain n'est pas arbitré (DEC-5). Elle ne peut jamais, seule, élever un statut.

### 7.5 Invalidation d'une approbation

Une approbation devient `STALE` (refus, jamais renouvelée automatiquement) dès que **l'un** des éléments suivants change : `page_digest` (donc toute source, consigne, statut ou provenance du livre chargé), `sources_sha256`, `link_id` ou fonction de dérivation de l'identifiant `syn-…`, `allow_pending_source`, `answer_page_digest`, version de la mécanique, version du contrat de page, version de ce contrat, paramètres, graine, `activity_fingerprint`, `solution_digest`, identité de l'unité, ou passage de l'unité à un statut bloquant. Une approbation `REJECTED` n'est jamais réinterprétée comme `APPROVED`. Aucune approbation n'est héritée d'une version précédente.

## 8. Sécurité : invariants et politique fail-closed

### 8.1 Invariants

| ID | Invariant |
|---|---|
| SEC-01 | `production_authorized` et `ready_for_kdp` sont des constantes du code ; aucune donnée (liaison, paramètre, approbation, CSV, variable d'environnement, argument) ne peut les modifier ; toute affirmation en ce sens est refusée (R02). |
| SEC-02 | Aucune validation technique (V1, V2) ne crée une validation pédagogique, éditoriale, de production ou KDP (table §6.1). |
| SEC-03 | Aucune association n'est déduite d'un titre, d'un numéro de page, d'un CSV ou de `PageRecord.mechanic` : seule une `LinkRecord` humaine associe. |
| SEC-04 | Aucun paramètre n'est deviné, complété par défaut, tiré d'une donnée éditoriale ou d'un environnement ; ensemble de clés fermé. |
| SEC-05 | Aucun fallback : en cas d'échec, pas d'activité de remplacement, pas de mécanique voisine, pas d'autre graine, pas de relâchement de borne. Un remplacement exige une **nouvelle décision humaine** consignée. |
| SEC-06 | La passerelle n'écrit jamais dans les sources, les approbations, les liaisons ni les livres ; elle ne produit qu'un `GatewayResult` en mémoire. |
| SEC-07 | Aucun import de la passerelle par le contrat éditorial, les mécaniques v2 ou le moteur historique ; aucun import du contrat éditorial par les mécaniques. |
| SEC-08 | Les générateurs ne reçoivent que `(mechanic, activity_id, seed, params)` ; identifiant `syn-…` ; jamais de texte éditorial. |
| SEC-09 | Toute divergence de condensé ou de version périme liaison, paramètres et approbations (§7.5). |
| SEC-10 | Un statut inconnu, absent, contradictoire ou insuffisamment justifié est un refus explicite, jamais une valeur par défaut. |
| SEC-11 | Une approbation nécessite une identité humaine **déclarée** et une preuve (référence) non vides ; un SHA-256 seul n'authentifie rien, et l'identité déclarée n'est pas une authentification (DEC-5). |
| SEC-12 | Tout fichier d'entrée (liaison, paramètres, approbation) passe par une garde de forme bornée avant toute lecture (profondeur, nombre d'éléments, types exacts, entiers/chaînes bornés), réutilisant la discipline de B3-B.3c.1 ; objets Python arbitraires hors contrat. |
| SEC-13 | Fichiers lus : fichier régulier, pas de lien symbolique, taille bornée, UTF-8 strict, clés dupliquées refusées, JSON canonique (mêmes exigences que `scenario_b.sources` / `loads_strict`). |
| SEC-14 | Les messages de refus sont bornés et n'incluent jamais une valeur d'entrée brute (`bounded_repr`). |
| SEC-15 | Déterminisme : mêmes entrées, mêmes octets de sortie ; aucune horloge, aucun réseau, aucune variable d'environnement dans une décision. |
| SEC-16 | Chaque `GatewayResult` porte des étiquettes non supprimables `SYNTHETIC_NON_PRODUCTION`, `production_authorized=false`, `ready_for_kdp=false`. |
| SEC-17 | La passerelle n'élargit aucun vocabulaire v2 (familles saisonnières, pictogrammes réels) : ils restent fermés. |
| SEC-18 | `plan_correction_status` n'est jamais une preuve ; l'exigence de corrigé vient du contrôle des corrigés uniquement (§7.2). |

### 8.2 Comportements attendus en cas d'échec (tous *fail-closed*)

| Cas | Verdict | Code | Comportement |
|---|---|---|---|
| Référence d'unité introuvable ou ambiguë | `REFUSED` | `UNIT_NOT_FOUND` / `UNIT_AMBIGUOUS` | aucune recherche approchée (titre, page) |
| Mécanique inconnue | `REFUSED` | `UNKNOWN_MECHANIC` | pas de mécanique voisine ; message borné |
| Paramètres incompatibles ou hors borne | `REFUSED` | `UNKNOWN_PARAM`, `MISSING_PARAM`, `BAD_*` (codes v2 conservés, R10, avant toute génération) | aucune correction automatique |
| Activité techniquement invalide | `REFUSED` | `ACTIVITY_INVALID` + code v2 (`UNSATISFIABLE`, `SELF_CHECK_FAILED`…) | aucune autre graine tentée |
| Corrigé absent ou incohérent | `REFUSED` | `ANSWER_UNBOUND` | aucun corrigé fabriqué |
| Validation humaine manquante (V3/V4) | le résultat technique n'en dépend pas : l'axe reste `NOT_EVALUATED` et **aucun statut supérieur n'est affiché** ; paramètres sans approbation humaine : refus | `PARAMS_NOT_APPROVED` (R11) ; `HUMAN_VALIDATION_MISSING` est réservé à un futur consommateur exigeant V3/V4 | pas de remplacement par une validation « présumée » |
| Empreinte ou version divergente | `REFUSED` | `STALE_LINK` (R06) / `STALE_APPROVAL` (R12) | renouvellement humain explicite uniquement |
| Statut éditorial bloquant | `REFUSED` | `EDITORIAL_STATUS_BLOCKING` | pas de contournement, y compris en environnement de test |

## 9. Diagramme de décision condensé (même ordre que la table R01–R16 du §6.1)

```text
 entrée ─► R01 garde de forme ─ échec ─► REFUSED(HOSTILE_INPUT)
        ─► R02 revendication d'autorisation ? ─ oui ─► REFUSED(AUTHORIZATION_CLAIM_REJECTED)
        ─► R03 liaison unique ? ─ non ─► REFUSED(AMBIGUOUS_LINK)            (unité sans liaison : UNLINKED, pas de résultat)
        ─► R04 livre + unité uniques, page cohérente ? ─ non ─► REFUSED(BOOK_MISMATCH/UNIT_*/PAGE_MISMATCH)
        ─► R05 mécanique connue et compatible ? ─ non ─► REFUSED(UNKNOWN_MECHANIC/NO_COMPATIBLE_MECHANIC)
        ─► R06 condensés et versions du lien frais ? ─ non ─► REFUSED(STALE_LINK)
        ─► R07 page lisible (V1) ? ─ non ─► REFUSED(PAGE_NOT_READABLE)
        ─► R08 statuts des fichiers de la passerelle connus et cohérents ? ─ non ─► REFUSED(UNKNOWN/CONTRADICTORY/AMBIGUOUS_*)
        ─► R09 unité BLOCKED_BY_SOURCE ? ─ oui ─► REFUSED(EDITORIAL_STATUS_BLOCKING)
        ─► R10 paramètres uniques, clés exactes, aux bornes ? ─ non ─► REFUSED(AMBIGUOUS_PARAMS/UNKNOWN_PARAM/MISSING_PARAM/BAD_*)
        ─► R11 paramètres approuvés (identité déclarée + preuve) ? ─ non ─► REFUSED(PARAMS_NOT_APPROVED)
        ─► R12 approbation fraîche ? ─ non ─► REFUSED(STALE_APPROVAL)
        ─► R13 unité NOT_VALIDATED sans allow_pending_source ? ─ oui ─► REFUSED(EDITORIAL_STATUS_PENDING)
        ─► R14 generate_v2 ok et verify_v2 == [] (V2) ? ─ non ─► REFUSED(ACTIVITY_INVALID)
        ─► R15 corrigé requis ⇒ BOUND ? ─ non ─► REFUSED(ANSWER_UNBOUND)
        ─► R16 TECHNICAL_ONLY  (jamais plus)
```

## 10. Tests futurs et critères d'acceptation (aucun test écrit ici)

### 10.1 Critères d'acceptation de la future implémentation

CA-1 la table §6.1 (R01–R16) est entièrement couverte, chaque ligne par au moins un cas positif et un négatif ; CA-2 aucun cas ne produit un verdict autre que `REFUSED` ou `TECHNICAL_ONLY` ; CA-3 aucune tentative de contournement (§10.3) n'aboutit ; CA-4 le contrat de page, les générateurs, les vérificateurs, le moteur historique, les CSV, les livres, les workflows et les 254 empreintes de référence B3-B.3c.1 sont octet-identiques ; CA-5 test d'isolation par analyse de code (SEC-07) ; CA-6 suite complète, quatre oracles et CI verts ; CA-7 revue indépendante ciblée sans anomalie bloquante ; CA-8 `production_authorized` et `ready_for_kdp` restent constants ; CA-9 aucune donnée éditoriale réelle dans les tests ni dans les exemples.

### 10.2 Matrice de tests

| Groupe | Objet | Cas positifs (synthétiques) | Cas négatifs |
|---|---|---|---|
| G1 Schéma et garde | `LinkRecord`, `ParamsRecord`, `ApprovalRecord` | enregistrement valide ; clés triées ; JSON canonique | clé inconnue/manquante ; type inattendu ; imbrication 100 000 ; entier de 5 000 chiffres ; chaîne géante ; clé dupliquée ; sous-classe hostile ; lien symbolique ; UTF-8 invalide |
| G2 Résolution | liaison ↔ unité | `unit_id` unique et `page` cohérente | `unit_id` absent ; dupliqué ; `page` ≠ `final_page` ; identifiant à homoglyphe ; casse différente ; liaison par titre seul ; liaison par numéro de page seul |
| G3 Duplication et ambiguïté | unicité (liaisons, paramètres, approbations) | N liaisons distinctes | deux liens de même `link_id` ; deux `ParamsRecord` d'un `link_id` ; deux approbations identiques ou `APPROVED` + `REJECTED` d'un même sujet ; unité sans liaison (aucun résultat) ; même `unit_id` dans deux livres ; deux mécaniques pour une unité ; deux liens vers la même unité ; ordre des fichiers inversé donne le **même** refus |
| G4 Compatibilité | table fermée | mécanique compatible | mécanique inconnue ; `PageRecord.mechanic` sans entrée ; nature non-activité ; mécanique « voisine » non déclarée |
| G5 Paramètres | proposé/approuvé/technique | projection pure exacte | clé en trop ; clé manquante ; valeur hors borne ; graine absente ; valeur par défaut implicite ; paramètre lu d'une variable d'environnement ; paramètre non approuvé ; proposition d'outil sans approbation humaine |
| G6 Approbations | identité, preuve, fraîcheur | approbation complète fraîche | `approver.id` vide ; preuve vide ; `authentication` omise ; `decision` absente ; condensé divergent ; approbation d'une autre liaison ; approbation d'un autre `kind` ; approbation `REJECTED` relue comme `APPROVED` |
| G7 Péremption | §7.5 | — | changement d'un statut de la grille ; d'une consigne ; d'une source ; de la version de mécanique ; du contrat de page ; de la graine ; de l'activité ; chacun périme toutes les approbations dépendantes |
| G8 Axes | table §6.1 | V1+V2 PASS donne `TECHNICAL_ONLY` | V2 PASS sans V3 ; V3 `ATTESTED_UNAUTHENTICATED` sans V4 ; V4 attesté affiché comme production ; ordre des règles : une entrée violant R04 et R12 rend toujours R04 ; `VALIDATED` sans preuve ; cinq revues incomplètes ; statut inconnu ; statut `BLOCKED_BY_SOURCE` |
| G9 Corrigés | §7 | `BOUND` ; `NOT_REQUIRED` | `correction_status` vide + corrigé existant ; `correction_status` renseigné + corrigé absent ; page de corrigé divergente ; solution divergente de l'approbation ; deux corrigés pour une unité ; `NOT_LISTED_IN_ANSWER_CONTROL` |
| G10 Fail-closed | §8.2 | — | chaque cas du tableau §8.2, vérifiant l'absence de repli, de seconde graine et de mécanique de remplacement |
| G11 Isolation | SEC-07 | — | import interdit dans chaque sens (analyse de code) ; absence d'écriture disque ; absence de lecture d'environnement ; `PageRecord` inchangé |
| G12 Non-régression | CA-4 | 254 empreintes B3-B.3c.1 identiques | toute dérive d'empreinte, de message de code d'erreur ou d'octet des sorties historiques |

### 10.3 Tentatives de contournement à tester (négatifs obligatoires)

1. Liaison contenant `"production_authorized": true` ou `"ready_for_kdp": true` ; colonne ou champ « authorized » ; variable d'environnement `PRODUCTION=1`.
2. Approbation « du système » ou d'un outil (`approver.kind = TOOL`), ou sans `approver.id`.
3. Approbation pédagogique réutilisée après changement de graine ou de mécanique.
4. Réutilisation d'une approbation d'une liaison pour une autre unité (même condensé de paramètres).
5. Unité `VALIDATED` sans identité de validateur, ou avec preuve sans identité.
6. Relecture d'une grille où `correction_status` est vide « donc pas de corrigé », ou renseigné « donc corrigé validé ».
7. Passer le titre ou le numéro de page à la place de `unit_id`.
8. Fournir `syn-…` construit à la main pour une page réelle afin de contourner la dérivation d'identifiant (DEC-1).
9. Ajouter une clé de paramètre « bonus » ou « force » ; omettre la graine pour obtenir un défaut ; fournir une graine par variable d'environnement.
10. Après échec de génération, relancer silencieusement avec une autre graine ou une autre taille ; basculer `match_v2` ↔ `connect_dots_v2`.
11. Modifier une source éditoriale après approbation et s'attendre à ce que l'approbation reste valide.
12. Fichiers hostiles : symlink vers un fichier hors dépôt ; JSON profondément imbriqué ; entiers de 5 000 chiffres ; clés dupliquées ; surrogates Unicode.
13. Se servir d'un `GatewayResult` `TECHNICAL_ONLY` comme preuve d'une validation (champ `axes` falsifié dans un fichier relu : le résultat n'est jamais une entrée de la passerelle).
14. Remplacer la constante `PRODUCTION_AUTHORIZED` ou `READY_FOR_KDP` par `True` dans le code (cas de revue) : un test d'invariant par analyse de code doit **échouer**, afin que le changement ne passe pas inaperçu.

### 10.4 Exemples synthétiques négatifs (illustrations)

```json
{"id": "NEG-03", "input": "LinkRecord avec source_ref.unit_id absent et page=901 seulement", "expected": {"verdict": "REFUSED", "code": "UNIT_NOT_FOUND"}}
{"id": "NEG-07", "input": "ApprovalRecord APPROVED, approver.id = \"\", subject_digest valide", "expected": {"verdict": "REFUSED", "code": "PARAMS_NOT_APPROVED"}}
{"id": "NEG-11", "input": "source modifiée après approbation, la page restant lisible (consigne d'une autre page changée)", "expected": {"verdict": "REFUSED", "code": "STALE_LINK"}}
{"id": "NEG-12", "input": "unité passée à VALIDATED sans identité ni preuve dans la source (le contrat de page signale VALIDATION_WITHOUT_EVIDENCE)", "expected": {"verdict": "REFUSED", "code": "STALE_LINK (le condensé a changé, R06 précède R07)"}}
{"id": "NEG-14", "input": "LinkRecord avec \"production_authorized\": true", "expected": {"verdict": "REFUSED", "code": "AUTHORIZATION_CLAIM_REJECTED"}}
```

## 11. Règle de fabrication des exemples et des fixtures futures

Identifiants préfixés `syn-`, `lnk-fixture-`, `apr-fixture-` ; pages fictives hors 1..56 (901 et suivantes) ; aucune consigne, aucun titre, aucun libellé,
aucun nom de personnage ni de livre réel ; aucun fichier du dépôt éditorial ne sert de fixture ; les approbateurs sont des identifiants fictifs
(`syn-human-N`) marqués `SYNTHETIC_FIXTURE`. **Mode fixture.** Les tests construisent des `PageRecord`/`ScenarioBPages` synthétiques en mémoire (hors des pages 1..56, donc non résolubles par `load_pages`) ; la passerelle reçoit alors un objet `ScenarioBPages` en argument (injection explicite, pas de variable d'environnement) et refuse tout rôle `SYNTHETIC_FIXTURE` lorsque le livre chargé est un livre réel (`BOOK_MISMATCH` ou `UNKNOWN_STATUS`). La distinction fixture/réel est donc portée par les **données** (identifiant de livre et rôle), jamais par un interrupteur d'environnement (SEC-15).

## 12. Décisions architecturales à trancher avant tout codage

La recommandation est donnée en premier pour chaque décision.

| ID | Question | Options | Recommandation et raison |
|---|---|---|---|
| **DEC-1** | Identifiant d'activité (F1 : v2 exige `syn-…`) | (a) la passerelle dérive `syn-` + condensé court de `link_id` (fonction publique, déterministe) ; (b) créer une nouvelle version v3 acceptant des identifiants éditoriaux ; (c) assouplir `ACTIVITY_ID` | **(a)** : aucun générateur ni vérificateur modifié, la séparation est conservée ; (b) et (c) touchent les mécaniques et élargissent la surface de risque. |
| **DEC-2** | Que représente une « activité liée » (F3) ? | (a) **squelette structurel** : géométrie + solution, sans contenu éditorial ; (b) activité habillée de contenu éditorial | **(a)** tant que le vocabulaire (pictogrammes, objets) et le registre d'assets ne sont pas décidés (dépendance humaine n°1). (b) exige un contrat distinct. |
| **DEC-3** | Emplacement des liaisons et approbations | (a) dossier versionné dédié (p. ex. `books/<livre>/gateway/`) hors des sources actives, revu par PR ; (b) colonne dans un CSV éditorial ; (c) fichier généré | **(a)** ; (b) viole « aucune association déduite d'un CSV » et modifie des sources ; (c) fait de l'outil l'auteur de la décision. |
| **DEC-4** | Qui propose, qui approuve | (a) proposition par un humain **ou un outil marqué** ; approbation par une identité humaine déclarée, ≠ proposant si le proposant est un outil (limite : un outil se déclarant humain n'est pas détectable, d'où DEC-5) ; (b) proposition humaine uniquement ; (c) auto-approbation permise | **(a)** : l'assistant peut aider à préparer des valeurs mais ne décide jamais ; (c) refusé. |
| **DEC-5** | Authentification des approbations humaines (F7) | (a) étiquette `UNAUTHENTICATED` + exigence que le fichier d'approbation soit introduit par PR revue avec propriétaires de code (CODEOWNERS) ; (b) commits signés ; (c) signature détachée par clé de l'approbateur ; (d) accepter l'identité déclarée sans étiquette | **(a) dans un premier temps**, avec (b) ou (c) comme jalon ultérieur ; **(d) refusé** : il présenterait une déclaration comme une preuve. |
| **DEC-6** | Graine | (a) explicitement proposée puis approuvée avec les paramètres ; (b) dérivée du `link_id` | **(a)** : cohérent avec « aucun paramètre deviné » ; (b) est déterministe mais constitue un choix implicite non approuvé. |
| **DEC-7** | Table de compatibilité initiale | (a) fermée : `maze → maze_v2`, `connect_dots → connect_dots_v2`, `match → match_v2` ; autres types (`pair_matching`, `one_to_one`, `shadow_match`, `match_vocabulary`, `sort`, …) **sans mécanique compatible** tant qu'un humain ne les admet pas ; (b) plus large | **(a)** : les symboles v2 sont géométriques synthétiques (F3) ; admettre `one_to_one`, par exemple, exige une décision éditoriale. |
| **DEC-8** | Granularité de l'invalidation | (a) stricte : tout changement de condensé ou de version périme tout ; (b) partielle par axe | **(a)** : plus simple à prouver et fail-closed ; (b) pourra être étudiée avec des preuves de non-impact. |
| **DEC-9** | Unités `NOT_VALIDATED` (cas de toutes les données réelles actuelles, F4) | (a) autoriser `TECHNICAL_ONLY` étiqueté, avec le drapeau explicite `allow_pending_source` défini au §4.1 bis (obligatoire, faux par défaut, inclus dans le condensé approuvé) ; (b) refuser tant que l'unité n'est pas `VALIDATED` ; (c) deux modes (fixtures / réel) | **(a)** : permet de valider techniquement la chaîne sans prétendre à rien d'éditorial ; les unités `BLOCKED_BY_SOURCE` restent refusées (R09) ; (b) bloquerait tout progrès tant que 0 unité n'est validée. |
| **DEC-10** | Emplacement du code et dépendances | (a) nouveau paquet `src/lafractale/gateway/` important `scenario_b.pages` et `mechanics_v2.registry`, importé par rien d'autre, avec test AST ; (b) dans `scenario_b` ; (c) dans `mechanics_v2` | **(a)** : préserve l'indépendance dans les deux sens. |
| **DEC-11** | Découpage de l'implémentation | (a) trois incréments, chacun une PR : **B3-B.3c.3** schémas + garde + lecture de fichiers (pur, sans génération) ; **B3-B.3c.4** résolution, compatibilité, condensés, moteur de décision ; **B3-B.3c.5** projection et exécution à blanc sur fixtures synthétiques ; (b) une seule PR | **(a)** : revue plus simple, risque isolé, comme B3-B.3b. |
| **DEC-12** | Faut-il un `AnswerBinding` persistant ou calculé à chaque exécution ? | (a) calculé, jamais persisté, vérifié à chaque exécution contre le contrôle des corrigés ; (b) persisté dans un fichier | **(a)** : une copie persistée pourrait dériver silencieusement ; seules les approbations humaines sont persistées. |

## 13. Dette et limites connues de cette spécification

* Aucune des garanties ci-dessus n'est démontrée : c'est une **spécification**, sans code ni test exécutable. Les tests du §10 sont des exigences, pas des résultats.
* Les dettes B3-B.3b (`search.attempts` non rejoué, provenance SHA-256 non authentifiée, CI limitée à Python 3.11) subsistent et sont **utilisées comme contraintes** (F7), non résolues ici.
* La dette `correction_status` (F6) est traitée **en l'ignorant** comme preuve ; sa correction dans le plan relève de la source éditoriale et n'est pas entreprise.
* L'authentification forte des approbations humaines (DEC-5) n'est pas conçue ici au-delà de l'étiquette et du processus de revue.
* Le rendu, la composition de pages, le registre d'assets, la fermeture de MAJOR-03/04, la validation éditoriale et la décision KDP sont hors périmètre.

MAJOR-03 et MAJOR-04 restent OPEN ; EDITORIAL PENDING ; KDP FORBIDDEN ; PRODUCTION_GENERATION FORBIDDEN ; `ready_for_kdp=false` ; issue #15 ouverte.
