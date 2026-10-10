# LaFractale Studio — Contrat technique et de sécurité B2-C2 v1.0

**Objet :** placement déterministe de Pip par activité, opt-in, sur la démo Halloween (3 fiches + 3 corrigés).
**Statut :** IMPLÉMENTATION EN COURS ; REVUE INDÉPENDANTE ET VALIDATION VISUELLE HUMAINE EN ATTENTE.
**Précédence :** s'ajoute à B2-B et à `docs/SECURITY_CONTRACT_B2C1.md`. N'annule aucune protection C1. En cas de contradiction, stopper et soumettre un amendement avant écriture de code.
**Provenance du présent document :** transcription fidèle de `LaFractale_B2-C2_CONTRAT_TECHNIQUE_v1.0.md` du pack de lancement B2-C2 v1.0 (SHA-256 `d95a8786f143b0d946c2bae4cca2a570c837046bfc25bf3a343d016539165e7f`). Le §0 a été exécuté avant toute écriture de code ; ses résultats sont consignés au §9. Les §§1 à 8 sont repris sans modification.
**Base Git vérifiée :** `origin/main` = `8a28fb824a2ef895f1cf22913bc231b3d1dd0826` (merge de la PR #6), tree `7f358dab86c479668bf0aeb8eb5604aee519c578`, CI post-fusion SUCCESS (run `38043339204`).

## 0. Préflight impératif : ancrer la base C1

Hermes doit effectuer les opérations de lecture suivantes AVANT de créer la branche :

1. `git fetch origin main` ; vérifier l'absence de travail en cours et récupérer le SHA **complet** de `origin/main`.
2. Vérifier que `git rev-parse origin/main^{tree}` vaut **exactement** `7f358dab86c479668bf0aeb8eb5604aee519c578` et que le commit est le merge B2-C1 rapporté sous l'abréviation `8a28fb8` (PR #6). Consigner le SHA complet dans les preuves. Un arbre différent, même avec une CI verte, requiert un arrêt et une clarification.
3. Confirmer le caractère MERGED de la PR #6 et les jobs post-fusion SUCCESS à partir des données GitHub, pas du seul message de statut.
4. Lire le contrat C1 réellement fusionné, les signatures effectives de `write_pdf`, `compose_page`, du chemin QA, de la CLI et de l'oracle. Confirmer la présence de `_routed_render_snapshot()` ou de son équivalent et le refus des activités non canoniques.
5. Confirmer les empreintes des assets protégés et l'absence de divergences avant toute création de branche.

**Si un point est impossible à établir : BLOCKED, pas de développement « supposé ».** Cette exigence n'est pas une autorisation de réécrire `main` ni de revenir à un état antérieur.

## 1. Périmètre et interface

Ajouter **un placement graphique explicitement activé**, sous la seule route C1 Halloween canonique :

```sh
build-demo books/halloween_2026/book.yaml \
  --illustration-routing halloween-pip-demo-v1 \
  --approvals-sha256 PIN_EXTERNE \
  --pip-placement halloween-pip-placement-v1
```

`qa` doit prendre **explicitement** le même `--pip-placement ...`, outre les arguments C1 habituels. Si l'API existante appelle cette option autrement, documenter une correspondance CLI/API stable et revoir le contrat avant un changement qui affecterait les modes précédents.

**Matrice des modes :**

| Mode demandé | `--pip-placement` | Résultat |
|---|---|---|
| B2-B `placeholder` | absent | Sortie historique **byte-identical** |
| B2-B `legacy_illustration` | absent | Sortie historique **byte-identical** |
| B2-C1 `routed` | absent | Sortie C1 fusionnée **byte-identical** |
| B2-C1 `routed` Halloween approuvé | `halloween-pip-placement-v1` | Nouveau rendu **C2 uniquement** |
| `placeholder`, `legacy_illustration`, Noël ou autre route | présent | **REJET** avant sortie |
| Politique inconnue / PIN absent ou faux / flags en conflit | présent | **REJET** avant sortie |

Aucun opt-in implicite, aucune inférence de politique à partir du `manifest.json`, d'un PDF ou d'un fichier de livre. **Le mode C1 non opt-in ne doit changer d'aucun octet.** Pas de nouvelle option `--x`, `--y`, `--width`, `--mapping` ni de coordonnées libres exposées par API.

## 2. Politique de placement V1 : trois zones déterministes

Réutiliser sans changement le routage d'illustrations C1, les trois `ActivitySpec` canoniques de `demo_specs(approved_book)`, et les trois poses approuvées :

| PDF, pages 1/2/3 | Activité | Pose (C1, INCHANGÉE) | Ancrage C2 |
|---:|---|---|---|
| 1 | `halloween_2026-p004` / `maze` | `pip-reflexion-v2` | `scene_right` : slot C1 actuel |
| 2 | `halloween_2026-p006` / `connect_dots` | `pip-indication-v1` | `lower_right` : bande libre entre plateau et pied de page |
| 3 | `halloween_2026-p020` / `match` | `pip-encouragement-v1` | `lower_left` : même bande, côté gauche |

La même association index/activité/pose/ancrage s'applique **au PDF des exercices et aux corrigés**. Le placement est une table **statique, figée dans le code audité** et liée à la route C1. Toute variation des identités, poses ou ancrages attendus : FAIL.

### Définition géométrique normative (unités : points PDF, origine bas-gauche)

Pour chaque activité canonique et chaque `answer_key`, calculer d'abord la composition **C1 de confiance** `L0` avec les mêmes polices et mesures de texte. Ne pas déduire la zone depuis des valeurs fournies par l'appelant, le manifeste ou le PDF.

- `scene_right` : `slot = L0.companion_slot`, sans aucun déplacement.
- `lower_left` / `lower_right` : calculer `gap_bottom = L0.footer.top`, `gap_top = L0.board.y`, `gap_height = gap_top - gap_bottom` ; `slot_width = L0.companion_slot.width` et `slot_height = L0.companion_slot.height`.
- Refuser si un nombre est non fini, si `gap_height < slot_height + 8.0 pt` ou si l'une des dimensions n'est pas positive.
- Définir `y = gap_bottom + (gap_height - slot_height)/2`.
- `lower_left` : `x = L0.board.x + 4.0 pt`.
- `lower_right` : `x = L0.board.right - slot_width - 4.0 pt`.
- `slot = Rect(x, y, slot_width, slot_height)` ; construire une nouvelle `PageComposition` immuable (pas de mutation de `L0`) remplaçant uniquement `companion_slot` pour le rendu C2.
- Vérifier que le nouveau slot est dans `L0.safe`, ne chevauche **aucune région nommée** (notamment `board`, `footer`, textes et en-tête), préserve **au moins 4 pt** de séparation verticale du plateau et du pied, ainsi que 4 pt de retrait latéral depuis le plateau. Exécuter `validate_composition()` et les vérifications d'impression existantes avant écriture.
- Les autres rectangles, textes, typographies, mécaniques, réponses, numéros, taille de page et marges restent **identiques** à `L0`.

La géométrie B2-B du format 8,5 × 11 pouces donne un espace vertical de **52 pt** entre `footer.top` et `board.y`, donc un slot de hauteur 41 pt avec **5,5 pt** libres de chaque côté. Cette faisabilité numérique issue de B2-B **n'est pas une validation de C1** : Hermes doit la refaire sur les six compositions du code fusionné ; si la structure diffère, STOP et soumettre un amendement plutôt qu'adapter silencieusement.

**Rendu de l'image :** appliquer exactement la formule d'échelle, la conservation des proportions, les marges internes et les contrôles DPI du renderer C1. Ne pas modifier, régénérer, recolorer, recadrer ni étirer les PNG. Le contenu et l'emplacement des exercices doivent rester inchangés. Aucun recouvrement par transparence « visuellement toléré » n'est autorisé.

## 3. Frontières de confiance et invariants

1. **Chaîne d'autorité :** `Book` chargé et vérifié → `demo_specs(book)` complets et ordonnés → génération validée → route C1 recalculée depuis politique statique + PIN externe → politique statique C2 → `PageComposition` déterministe. Ni route, ni placement, ni approbation ne sont autorisés par YAML/JSON/manifest/PDF ou par une donnée de l'appelant.
2. À la frontière de `write_pdf` en C2, copier et figer les données, **réappliquer** la vérification C1 complète des trois activités, du livre, de la route et du PIN, puis vérifier le placement C2 sans faire confiance à un objet de placement forgé. **Refuser avant ouverture/création du fichier PDF** pour tout appel direct partiel, réordonné, altéré ou avec placement non autorisé.
3. Ne pas ajouter de possibilité de passer à `write_pdf` une `Rect` ou des coordonnées arbitraires ; utiliser seulement l'identifiant strict de politique + contexte de confiance ou un plan immuable **entièrement recalculé**. Un plan fourni par l'appelant doit être revérifié par égalité stricte à un plan canonique.
4. À la QA, **recalculer indépendamment** le placement attendu à partir du choix CLI explicite, de `Book`, `demo_specs`, de la route C1 et d'une spécification de contrôle indépendante du renderer. Le manifeste est une donnée à comparer, jamais la source de vérité.
5. Protéger les sorties par les mécanismes déjà établis : contrôle d'inventaire ancré, anti-symlink, staging/publication atomique et restauration lors d'une erreur tardive. Ne jamais laisser une sortie partielle nouvelle ou écraser un résultat précédent sur FAIL.
6. Assets protégés **immuables** : 6 PNG Pip Halloween, `assets/illustrations/approvals.json`, PNG officiel couleur ; SHA couleur `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`, registre `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61`.
7. `publication_approved=false`, `ready_for_kdp=false`, `needs_visual_review`, assemblage 56 pages refusé, Noël inchangé, pas de certification prépresse/KDP et aucun changement d'autorisation de publication.

## 4. Sorties et audit des six pages

En C2, conserver **exactement l'inventaire C1 routé**, sans 7e image ni fichier additionnel dans le répertoire de build :

```
interior.pdf
answer_key.pdf
activities.json
quality_report.json
quality_report.md
manifest.json
previews/
  interior_page_01.png
  interior_page_02.png
  interior_page_03.png
  answer_key_page_01.png
  answer_key_page_02.png
  answer_key_page_03.png
```

Le manifeste C2 seul peut ajouter **une clé dédiée** `pip_placement` contenant le `policy_id` explicite et les 3 ancrages canoniques indexés par activité/page. Aucune clé C2 dans les trois modes non opt-in ; ne pas changer leur date/version/JSON/bytes. La QA compare le champ à un objet canonique recalculé. `activities.json` et la géométrie pédagogique restent identiques à C1 à seed fixé.

**Audit C2 obligatoire pour chacune des 6 pages PDF :**

- Identité index/activité/type/pose/ancrage conforme à la politique (fiches **et** corrigés).
- Exactement une image intégrée attendue par page, provenance approuvée, aucune image/masque supplémentaire ; SHA-256 des pixels décodés égale celui de la pose spécifique attendue. Ne pas accepter une pose approuvée mais sur la mauvaise page.
- Bbox PyMuPDF finie, ordonnée, entièrement contenue dans le **nouveau** slot prédit ; tolérance d'inclusion de **0,05 pt** et écart de chaque coordonnée à la formule de rendu attendue d'au plus **0,25 pt**, comme C1. Calculer le bbox attendu indépendamment du bbox du PDF.
- `dpi_x=72*pixel_width/(x1-x0)` et `dpi_y=72*pixel_height/(y1-y0)` : `min >= 299,99 DPI` ; contrôler étirement/ratio et limites de texte Unicode/polices existantes.
- Comparer le rendu des **6 PNG d'aperçu** aux 6 pages correspondantes avec `fitz.Matrix(1.4,1.4)`, `alpha=False` et pixels décodés ; comparer aussi le rejeu canonique complet, manifestes et sorties, à seed/environnement figés.
- Ne pas confondre contrôle du nouveau slot avec contrôle de collision : **les deux sont nécessaires**, y compris pour les objets dessinés dans le pied et le plateau.

Une falsification de pose, bbox, DPI, échelle, ancrage ou corrigé doit être refusée même avec des checksums et un manifeste recalculés.

## 5. Deux oracles de non-régression (obligatoires)

**Oracle B2-B existant :** maintenir son script, sa preuve par tree Git immuable et ses modes `placeholder` / `legacy_illustration`, byte-identical au commit `d77e32327fecd0c4a983ef8298581525842c18fc`.

**Nouvel oracle C1 :** à partir d'un checkout **isolé** du commit de fusion **complet** identifié au §0 et de son tree `7f358dab86c479668bf0aeb8eb5604aee519c578`, exécuter le mode routé **sans option de placement**. Comparer à l'exécution du code C2 candidat, **sans option de placement**, dans un second processus distinct, sous les mêmes polices/dépendances/seed 2026/`SOURCE_DATE_EPOCH=1780000000`/PIN externe. Contrôler **l'arborescence intégrale**, les octets de tous les fichiers et les QA historiques. Préserver les preuves identifiant exactement le Git tree candidat testé, et dans la CI vérifier `HEAD_TREE_MATCH` comme en B2-C1. Les comparaisons « candidat vs candidat » ne prouvent aucune non-régression.

La CI devra rejouer le nouvel oracle C1 **et** l'ancien B2-B. Si C1 a des difficultés d'isolation technique, STOP : ne pas remplacer par une comparaison au seul `manifest.json`.

## 6. Plan d'essais minimal

**Tests directs :** 3 activités × 2 PDF, politique/pose/ancrage exacts, appels directs de `write_pdf` avec 0/1/2/4 activités, ordre permuté, doublons, métadonnées falsifiées, route forgée, plan forgé, et flags C2 sur modes non autorisés. Chaque refus se produit avant création/modification du PDF.

**Tests géométriques :** bbox dans slot, slot dans marge de sécurité, écart attendu <=0,25 pt, contrôle >=299,99 DPI effectifs, tampon latéral/vertical >=4 pt, absence de collisions avec scène/titres/prompt/board/footer ; vérifier fiches et corrigés. Tests mutations : zone déplacée, chevauchement de 0,1 pt, ellipse d'échelle/étirement, image en dehors du slot, image surnuméraire, pose permutée seulement dans corrigé.

**Sorties/sécurité :** politique absente/incorrecte, PIN manquant/faux, source modifiée, fichier caché, symlink, FIFO, nouveau dossier vide, manifeste/checksum refabriqué, preview falsifié, échec tardif, publication atomique et conservation de l'ancienne sortie.

**Déterminisme :** deux builds C2 avec mêmes inputs donnent les mêmes octets ; aucun texte pédagogique ni coordonnées du plateau ne change ; B2-B et C1 sans opt-in restent byte-identical à leurs références externes.

**Tests historiques :** ne supprimer, désactiver ni marquer `xfail` aucun des 448 tests C1 annoncés ; comparer également la liste des tests (node IDs) pour éviter les suppressions masquées. Un total élevé ne suffit pas.

**Audit indépendant :** deux relectures distinctes, A « frontières de confiance/contournements », B « géométrie/rendu/régression », sur le **diff complet** de la base fusionnée au dernier commit candidat et sur son tree. Aucun MAJOR/BLOCKER résiduel.

## 7. Revue visuelle et publication

- Générer hors des répertoires de build audités une **planche comparative** C1/C2 par activité pour l'intérieur et le corrigé (12 vues, légendes distinctes), plus six previews C2 originales. Joindre un petit rapport des bbox et distances aux régions, des SHA et du statut de validation.
- Vérifier humainement netteté et lisibilité de Pip dans chaque placement, absence de collision, harmonie sans déséquilibrer l'activité, position identique intérieur/corrigé, sécurité pour l'impression N&B. Aucun déplacement libre n'est autorisé après cette revue sans nouvelle politique/version et nouveaux audits.
- Une validation visuelle de démo **n'implique PAS** validation de droits d'auteur, contenu complet de 56 pages, prépresse KDP ou publication.
- **B2-C2 doit s'arrêter à une PR non fusionnée** avec preuves et planche comparative. Aucune autorisation générale de fusion pour cette nouvelle phase ; l'utilisateur décide après revue des 12 vues. Pas d'auto-merge, pas de publication KDP, pas de développement B2-C3 en parallèle.

## 8. Condition de réussite

`PASS TECHNIQUE` : préflight ancré sur C1 fusionné, 2 oracles externes byte-identical, tests historiques+nouveaux, CI verte sur le tree exact, audits PDF indépendants, 2 revues PASS, aucun MAJOR/BLOCKER, assets intacts, PR non fusionnée avec preuves et planches.

`VALIDATION ÉDITORIALE` : distincte, nécessaire avant la fusion de B2-C2 ; relever explicitement « validation humaine en attente » même si les tests sont verts.

**Tout blocage technique sérieux est remonté avec reproduction, fichier/ligne et alternative argumentée ; jamais contourné en affaiblissant les gates.**

## 9. Hypothèses et faisabilité vérifiées sur le code C1 réellement fusionné

Cette section est propre à l'exécution Hermes ; elle documente les faits constatés avant toute écriture de moteur. Elle ne modifie aucune clause des §§1 à 8 (§0 point 5).

### 9.1 Ancrage Git

| Élément | Valeur observée (commandes exécutées le 10/10/2026) |
|---|---|
| `git rev-parse origin/main` | `8a28fb824a2ef895f1cf22913bc231b3d1dd0826` |
| `git rev-parse origin/main^{tree}` | `7f358dab86c479668bf0aeb8eb5604aee519c578` (identique à l'exigence du §0.2) |
| Parents du merge | `d77e32327fecd0c4a983ef8298581525842c18fc` (main B2-B) + `580d93efa2259fa5d543bf69517da895d69b15bb` (tête C1) |
| PR #6 | `state=MERGED`, `mergedAt=2026-10-10T09:59:37Z`, `mergeCommit.oid=8a28fb824a2ef895f1cf22913bc231b3d1dd0826` |
| CI post-fusion | run `38043339204` (`push`, head `8a28fb824a2ef895f1cf22913bc231b3d1dd0826`) → `conclusion=success` ; check-run `test` = `completed/success` |
| Branche C2 | `feat/studio-b2-c2-pip-placement`, créée depuis `8a28fb824a2ef895f1cf22913bc231b3d1dd0826`, tree initial `7f358dab86c479668bf0aeb8eb5604aee519c578` |

### 9.2 Surfaces C1 réellement présentes (vérifiées par lecture du checkout)

- CLI : `build-demo` et `qa` exposent `--illustration-routing` ; `build` ne l'expose pas. `qa` exige `--book`.
- `lafractale.illustrations.routing` : `ROUTING_HALLOWEEN_PIP_DEMO_V1`, `PageArtworkBinding`, `IllustrationRoute`, `resolve_illustration_mode()`, `build_illustration_route()`, `verify_illustration_route()`. Les deux classes sont des dataclasses gelées à tuple.
- `lafractale.layout.pdf.write_pdf(path, activities, book, *, answer_key, artwork=None, illustration_route=None, approved_book=None, trusted_approvals_sha256=None)` ; présence de `_routed_render_snapshot(activities, *, approved_book, illustration_route, trusted_approvals_sha256)` qui compare chaque activité à `generate(spec, activity.seed)` et refuse les séquences partielles/altérées.
- `lafractale.layout.composition` : `Rect`, `TextBlock`, `PageComposition` (gelées) et `compose_page(activity, book, *, index, count, answer_key, regular, bold, text_width) -> PageComposition`. `PageComposition.companion_slot` est le seul rectangle de placement.
- `lafractale.export.builder` : `build_demo(..., illustration_routing=None, trusted_approvals_sha256=None)`, `audit_output(...)`, `_audit_output_verified(...)`, `_exact_output_inventory(out, *, page_count, routed=False)`.
- Inventaire routé C1 : racine `interior.pdf`, `answer_key.pdf`, `activities.json`, `quality_report.json`, `quality_report.md`, `manifest.json`, `previews/` ; aperçus `interior_page_01..03.png` et `answer_key_page_01..03.png`.
- Oracle B2-B : `tools/verify_b2b_oracle.py` (tree immuable via index privé, worktree détaché, comparaison d'inventaire fermé et d'octets).

### 9.3 Faisabilité géométrique des trois ancrages (six compositions C1)

Composition mesurée sur le code fusionné, format 8,5 × 11 pouces (612 × 792 pt), polices DejaVu enregistrées, `_measure` de `layout.pdf` : `margin = 52.02 pt`, `board = (52.02, 143.02) 507.96 × 392.96`, `footer.top = 91.02 pt`, `companion_slot = (423.98, 616.98) 122 × 41`.

Bande basse demandée par le §2 : `gap_bottom = footer.top = 91.02`, `gap_top = board.y = 143.02` → **`gap_height = 52.00 pt`** (identique au chiffre annoncé par le contrat), `slot_height = 41 pt` → marge exigée `52 ≥ 41 + 8 = 49` **satisfaite**, `y = 96.52`.

| Page PDF | Activité / type | Ancrage C2 | Slot calculé `(x, y) w×h` | `right / top` | Jeu vertical (plateau / pied) | Retrait latéral (gauche / droit) | Dans `safe` | Collisions régions nommées | `validate_composition()` | Intérieur vs corrigé |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | `halloween_2026-p004` / `maze` | `scene_right` | (423.98, 616.98) 122×41 | 545.98 / 657.98 | -514.96 / 525.96 | 371.96 / 14.00 | oui | aucune | OK | identical |
| 2 | `halloween_2026-p006` / `connect_dots` | `lower_right` | (433.98, 96.52) 122×41 | 555.98 / 137.52 | 5.50 / 5.50 | 381.96 / 4.00 | oui | aucune | OK | identical |
| 3 | `halloween_2026-p020` / `match` | `lower_left` | (56.02, 96.52) 122×41 | 178.02 / 137.52 | 5.50 / 5.50 | 4.00 / 381.96 | oui | aucune | OK | identical |

- `scene_right` (page 1) est le slot C1 inchangé : aucun déplacement, jeu latéral droit de 14 pt vers `header.right`.
- Les deux ancrages de bande basse laissent **5,50 pt** de séparation verticale de chaque côté (exigence ≥ 4 pt) et **4,00 pt** de retrait latéral (exigence ≥ 4 pt).
- `validate_composition()` (zones finies, non vides, dans `safe`, sans chevauchement) passe sur les six compositions.
- Les slots sont **strictement identiques entre intérieur et corrigé** pour une même activité.
- Aucun problème bloquant relevé : la faisabilité du §2 est **confirmée** sur le code C1 fusionné, sans amendement.

### 9.4 Actifs protégés (invariants avant/après)

| Actif | SHA-256 |
|---|---|
| `assets/characters/pip/pip_officiel_couleur.png` | `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c` |
| `assets/illustrations/approvals.json` | `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61` |
| `pip-accueil-v1.png` | `72716b4193b6f15e5ffb55340f6d3ddfa428282e804b44ff410f01354bf52a09` |
| `pip-encouragement-v1.png` | `1bd15c92f77825160258e962f08b1bfcc593e9de99f229e73469d1c295051597` |
| `pip-felicitations-v2.png` | `74030cb477e121addd94bcb1d5d4dcb8193b7cb123695e7a546ef9a733dba098` |
| `pip-indication-v1.png` | `a3bec36fdec734d0791e5c76da99f1273eda43586310fdba795f6fc1a8089a81` |
| `pip-reference-nb-v1.png` | `8bf579336b405e2a9de0dc1fdbd7bbc281fd80dfa8d236d4108f8b1a6d9719b1` |
| `pip-reflexion-v2.png` | `37107eb5c2a7331232303a0c0ae0347e3766faacc00e0abc779c78409c47ba48` |

### 9.5 Tests historiques

Liste des node IDs collectée avant toute modification : **448 tests** (consignée hors dépôt dans `b2c2_baseline_nodeids.txt`). Aucune suppression, désactivation ni `xfail` n'est autorisée.
