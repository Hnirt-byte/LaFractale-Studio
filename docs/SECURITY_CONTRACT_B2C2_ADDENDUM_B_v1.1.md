# LaFractale Studio — B2-C2 — Addendum éditorial B v1.1 (politique de placement V2)

**Statut : décision éditoriale sur simulation, autorisation d'implémentation, pas d'autorisation de fusion.**

Ce document est le contrat versionné applicable à la **politique de placement V2**. Il est
consigné dans le dépôt **avant tout codage**, conformément à l'addendum éditorial B v1.1 fourni
par le décideur, et il précède toute modification du moteur, des tests ou de la politique.

## 0. Provenance et décision

- PR concernée : `https://github.com/Hnirt-byte/LaFractale-Studio/pull/7` — **ouverte, non fusionnée**.
- Base C1 stable : `8a28fb824a2ef895f1cf22913bc231b3d1dd0826`, tree `7f358dab86c479668bf0aeb8eb5604aee519c578`.
- Candidat C2 V1 (avant cet addendum) : `ad8281557757e1ce10e2eaaac47788c89881f556`,
  tree `95cdc6ea756b2bf86655ba9f82d787613c80961a`.
- Simulation de référence approuvée : `LaFractale_B2C2_VARIANTES_AB.zip`,
  SHA-256 `ef293e424d3f5b4f3e6a496dad566223113e8e8e574d46fabae6f8c2f7855033`.
- Choix éditorial : **variante B (rangée d'introduction, ancre `intro_right`)** sur les fiches
  `halloween_2026-p004`, `halloween_2026-p006`, `halloween_2026-p020` **et leurs corrigés**.
- Variante A (bande basse) et variante B′ (dans le plateau) : **non retenues**.
- Statut commercial : maquette technique, `publication_approved=false`, aucune publication KDP.

## 1. Priorité et portée (clause de non-affaiblissement)

1. Le présent addendum prévaut sur les §2 et §3 du contrat B2-C2 v1.0 **uniquement pour la
   géométrie normative de la politique de placement V2** (`halloween-pip-placement-v2`) et pour
   les invariants de politique explicitement listés au §2 du présent document.
2. Il **n'affaiblit aucun contrôle général** du contrat B2-C2 v1.0 : frontières de confiance,
   PIN externe obligatoire, réapplication du Book / de la route C1 / des spécifications,
   immutabilité, revalidation obligatoire aux frontières renderer **et** QA, autorité du
   manifeste (comparaison à un objet recalculé), inventaire de sortie fermé, vérification des
   actifs protégés, refus avant écriture, oracles B2-B et B2-C1.
3. Toute règle du contrat B2-C2 v1.0 non listée au §2 reste applicable sans changement.
4. Aucune API de coordonnées, de rectangle, d'offset ou de mappage d'appelant n'est introduite.
   L'appelant ne nomme qu'une politique ; la géométrie est recalculée depuis des sources de
   confiance (voir §4).

## 2. Règles V1 explicitement remplacées (traçabilité)

| Règle V1 (contrat B2-C2 v1.0) | Statut sous V2 | Motif |
| --- | --- | --- |
| §2 tableau : `scene_right` pour p004, `lower_right` pour p006, `lower_left` pour p020 | **remplacée** : l'ancre unique `intro_right` s'applique aux trois activités | décision éditoriale B sur simulation |
| §2 définition géométrique : bande basse `gap_bottom = footer.top`, `gap_top = board.y`, `y = gap_bottom + (gap_height - slot_height)/2`, ancrages `lower_left` / `lower_right` | **hors politique** : plus aucun plan actif n'émet ces ancrages | la bande basse plafonne la mascotte à 38 pt (constat éditorial) |
| §2 : `scene_right` réutilise `L0.companion_slot` sans déplacement | **hors politique** : la V2 dérive un nouveau slot de la rangée d'introduction | idem |
| §3 : « Politique de placement duplique un ancrage » (unicité des ancrages) | **abrogée comme invariant de politique** | les trois activités partagent désormais l'ancre `intro_right` ; l'unicité de l'`demo_index`, la complétude, l'ordre et l'égalité stricte avec la table figée restent exigés |
| §2 chiffres `5,5 pt` de jeu vertical et `41 pt` de slot | **sans objet sous V2** | la géométrie V2 est celle du §4 ci-dessous |
| identifiant de politique `halloween-pip-placement-v1` | **refusé explicitement** (erreur dédiée) | politique unique active V2 ; C2 n'ayant jamais été fusionnée, aucune sortie publiée n'utilise V1 |

Aucune autre règle n'est modifiée. Les ancrages hérités `scene_right`, `lower_left` et
`lower_right` restent **implémentés et couverts par les tests unitaires de géométrie** (aucune
suppression de cas de test), mais ne sont **atteignables par aucune politique active** : le seul
plan constructible est celui du §4, et `anchor_for()` refuse tout ancrage absent du plan vérifié.

## 3. Politique V2 figée

- Identifiant unique : `halloween-pip-placement-v2`.
- Table statique figée dans le code audité (jamais lue depuis YAML, JSON, manifeste, PDF, variable
  d'environnement ou mappage d'appelant) :

| Index PDF | Activité | Pose C1 conservée | Ancrage V2 |
| ---: | --- | --- | --- |
| 1 | `halloween_2026-p004` / `maze` | `pip-reflexion-v2` | `intro_right` |
| 2 | `halloween_2026-p006` / `connect_dots` | `pip-indication-v1` | `intro_right` |
| 3 | `halloween_2026-p020` / `match` | `pip-encouragement-v1` | `intro_right` |

- Les trois corrigés ont **exactement** le même placement que les fiches intérieures.
- `policy_id` et `bindings` (index, identité, page source, type, ancrage) forment le manifeste
  `pip_placement`, comparé à un objet **recalculé** ; le manifeste n'est jamais source de vérité.
- Le mode résolu `none` (aucune option) est inchangé : aucun des trois modes historiques
  (`placeholder`, `legacy_illustration`, routé C1 sans placement) ne reçoit de clé C2.

## 4. Géométrie normative V2 (`intro_right`)

Unités : points PDF, origine en bas à gauche. Ces nombres sont des **résultats de référence**, pas
une API : le code les **recalcule** depuis les régions canoniques de `compose_page()` (voir §5).

- Taille de l'image Pip visible : `48.00 pt` (16,93 mm) — carrée, ratio conservé.
- Bord droit de l'image : `L0.header.right - 16.00 pt`.
- Bord supérieur de l'image : `L0.header.y - 4.00 pt`.
- **Image visible** : `Rect(x = 495.98, y = 615.98, width = 48.00, height = 48.00)`.
- **Slot technique** : insets C1 inversés (4 pt horizontaux, 3 pt verticaux de chaque côté) →
  `Rect(x = 491.98, y = 612.98, width = 56.00, height = 54.00)`.
- Bbox PDF attendue via PyMuPDF (origine en haut à gauche) :
  `(495.98, 128.02, 543.98, 176.02)`, tolérance contractuelle **0,25 pt**.
- Le slot est reconstruit comme `replace(L0, companion_slot = <slot>)` ; `L0` n'est jamais muté.

### 4.1 Jeux à contrôler, visuel et slot distincts

| Mesure | Exigence V2 | Valeur de référence |
| --- | --- | --- |
| Image ↔ bandeau d'en-tête | ≥ 4,00 pt | 4,00 pt |
| Image ↔ zone de consigne (`prompt_fr`) | ≥ 4,00 pt | 4,00 pt |
| Slot ↔ bandeau d'en-tête | documenté, non contractuel | 1,00 pt |
| Slot ↔ zone de consigne | documenté, non contractuel | 1,00 pt |
| Image ↔ mot le plus proche | > 0 | 37,25 pt (badge « FICHE xx ») |
| Image ↔ tracé le plus proche | > 0 | 4,00 pt (bandeau d'en-tête) |
| Image ↔ plateau | > 0 | 80,00 pt |
| Image ↔ filet du pied de page | > 0 | 38,00 pt |
| Résolution effective | ≥ 299,99 dpi | 1 881 dpi (1254 px sur 48 pt) |
| Collisions texte / tracés | aucune | 0 / 0 |

Le contrôle de collision porte sur le **slot** et sur l'image ; les deux sont nécessaires et aucun
des deux n'est désactivé. Le §4.2 précise la seule tolérance locale admise.

### 4.2 Tolérance locale de la bande `scene` (strictement locale à `intro_right`)

Le rectangle de l'image dépasse la bande verticale de la région `scene` (y de 616,98 à 657,98) :
**1,00 pt en bas et 6,00 pt en haut**. Cette tolérance est :

- **strictement locale** à l'ancrage `intro_right` et à la politique V2 ;
- sans effet sur les contrôles de collision, qui restent actifs : le rectangle de l'image comme le
  slot technique **ne chevauchent aucune région nommée** (vérifié : les abscisses de `scene` et de
  la colonne d'introduction sont disjointes, et le slot garde 1 pt avec l'en-tête et la consigne) ;
- bornée par les deux exigences du §4.1 : l'image reste dans la bande libre comprise entre la
  consigne (`L0.prompt_fr.region.top + 4 pt`) et l'en-tête (`L0.header.y - 4 pt`).

Aucun contrôle de collision n'est désactivé globalement, ni pour un autre ancrage, ni pour un
autre livre.

## 5. Recalcul obligatoire (aucune géométrie acceptée sur déclaration)

`write_pdf` et la QA doivent recalculer, avant toute écriture : le Book vérifié, `demo_specs`,
les trois activités canoniques (seed du manifeste), la route C1 (PIN externe), le plan V2
(égalité stricte avec la table figée), puis le slot `intro_right` depuis `L0` selon §4. Un plan
forgé, incomplet, réordonné, substitué ou altéré est refusé **avant** création ou modification de
tout fichier.

## 6. Invariants et preuves minimales

1. Aucun changement des 8 actifs protégés (six PNG N&B, original couleur, registre d'approbations)
   ni de leur PIN externe.
2. Aucune mutation du livre, de la séquence canonique, des consignes, du plateau, des solutions,
   du format et des marges.
3. Rendu **sans** `--pip-placement` strictement byte-identique aux trois modes historiques ;
   oracles indépendants B2-B et B2-C1 rejoués sur leurs commits de référence.
4. Six pages validées (3 intérieurs, 3 corrigés) : identité des actifs, bbox attendu et inclusion
   dans le slot (0,05 pt), écart à la formule de rendu ≤ 0,25 pt, pixels gris / 1 canal / alpha 0,
   DPI ≥ 299,99, marge de sécurité, absence de collision avec textes, tracés et régions nommées.
5. Reproduction des six vues B approuvées par le **moteur de production** V2, à conditions de rendu
   identiques (mêmes polices, seed, résolution, moteur), avec comparaison pixel à pixel et
   explication de toute différence autre que des métadonnées PDF ; mots et tracés identiques à la
   référence C2.
6. Non-suppression de tests : les 519 cas existants sont conservés ; seules les attentes de
   politique rendues obsolètes par la décision versionnée sont adaptées (liste au §7) ; des tests
   adversariaux V2 sont ajoutés, dont le refus explicite de V1.
7. Aucune fusion, aucun B2-C3, aucune publication KDP ; PR #7 reste ouverte ; double revue
   indépendante et CI sur le **nouveau** commit/tree.

## 7. Adaptations de tests autorisées (aucune suppression)

1. `CANONICAL_ANCHORS` : les trois ancrages deviennent `intro_right`.
2. Attentes de politique V1 (`scene_right`, `lower_left`, `lower_right`, jeux 5,5 pt, slot 122 × 41)
   remplacées par les valeurs du §4.
3. `halloween-pip-placement-v1` passe de la liste des politiques valides à celle des politiques
   **refusées** ; `halloween-pip-placement-v2` suit le trajet inverse.
4. L'invariant d'unicité des ancrages est retiré (§2) ; l'unicité des `demo_index`, la complétude,
   l'ordre et l'égalité stricte restent exigés.
5. Ajouts obligatoires : rectangles forgés et débordements sur l'en-tête / la consigne, bbox
   déplacée, sous-ensemble et réordonnancement d'activités, altérations du manifeste et du PDF,
   vérification sur les **deux** `answer_key`, absence de création ou de modification de fichier en
   cas de refus, et refus explicite de la politique V1.

## 8. Traçabilité de la simulation

Le ZIP de référence a été vérifié par SHA-256, décompression sans erreur et inspection des PDF.
Ses PDF sont des documents **à trois pages** ; les rendus classés dans `fiche06` / `fiche20` ont
été lus respectivement en **page 2 et page 3**, jamais en page 1. Les six PNG 300 dpi de la
variante B correspondent pixel par pixel à la bonne page PDF simulée, et leurs textes
(`get_text("words")`) et tracés (`get_drawings()`) sont égaux à ceux des pages C2 de référence.

La reproductibilité depuis les **scripts réellement archivés** est vérifiée dans un répertoire de
travail neuf, avec comparaison aux livrables du ZIP. L'avertissement d'écrasement d'un script de
simulation sous `/opt/data/cache/scratch` n'implique aucune mutation du dépôt : le dépôt est suivi
par Git et son `git status` est vide au moment de l'ancrage.
