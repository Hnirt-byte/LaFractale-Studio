# LaFractale Studio — Contrat de sécurité B2-C1 v1.1

**Statut : DÉCISIONS DE CONTRAT VALIDÉES POUR REPRISE DU DÉVELOPPEMENT ; IMPLÉMENTATION NON VALIDÉE.**
**Précédence :** ce document remplace entièrement `LaFractale_B2-C1_CONTRAT_TECHNIQUE.md` (v1.0). Ne pas fusionner les deux contrats en choisissant des dispositions contradictoires.
**Référence de code :** B2-B, `origin/main` à `d77e32327fecd0c4a983ef8298581525842c18fc` (vérifié par Hermes le 09/10/2026 ; à revérifier immédiatement avant la branche).
**Source documentaire vérifiée localement :** `LaFractale-Studio-source-B2B-Pip-v1.zip`, SHA-256 `3fb4c306302f3739d68f3dbaf6f2b339a2d448cf5097f2212c5fd92ea9d90895` (une archive n'est pas une preuve de l'arbre Git distant).
**Version source :** `0.2.0b2` ; suite locale B2-B annoncée : 382 tests.

## 1. Périmètre strict

Créer une option explicitement activée :

```sh
--illustration-routing halloween-pip-demo-v1 --approvals-sha256 PIN_EXTERNE
```

Elle réalise le **routage déterministe par activité** de Pip sur la démo Halloween de 3 fiches et 3 corrigés. Elle ne modifie ni les 56 pages du projet éditorial, ni les mécaniques, ni les réponses, ni les coordonnées du slot, ni les assets approuvés. Les modes historiques B2-B et la démo Noël restent inchangés. Pas d'accord de publication KDP.

Les trois modes sont **mutuellement exclusifs** :

1. `placeholder` : ni `--illustration-id`, ni `--illustration-routing`, ni `--approvals-sha256`. Sorties B2-B strictement identiques.
2. `legacy_illustration` : `--illustration-id ID --approvals-sha256 PIN`. Même illustration sur les 3 fiches et les 3 corrigés. Sorties B2-B strictement identiques.
3. `routed` : `--illustration-routing halloween-pip-demo-v1 --approvals-sha256 PIN`. Illustration spécifique liée à chaque activité de démo.

Le CLI `build-demo` et `qa` exigent le même mode explicite. `qa` **ne doit jamais inférer ou approuver** le mode routé depuis `manifest.json`. Toute combinaison partielle ou double, politique inconnue, PIN absent/faux ou routage Noël échoue fermé avant publication ; aucun fallback implicite.

## 2. Actifs protégés et frontières de confiance

- PNG officiel couleur `assets/characters/pip/pip_officiel_couleur.png` : SHA-256 `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`.
- Registre `assets/illustrations/approvals.json` : SHA-256 **externe** `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61`.
- Les six PNG dans `assets/illustrations/halloween_2026/pip/` et le registre doivent rester strictement inchangés octet par octet.
- Seules les API existantes `load_approved_artwork()` et `verify_approved_artwork()` authentifient un `VerifiedArtwork`, pour le **livre Halloween** et l'empreinte externe fournie séparément.
- Les YAML/CSV, manifestes, rapports, previews, PDF, tables de routage passées par l'appelant et SHA auto-déclarés sont des **données** et jamais une autorité d'approbation. Les sources éditoriales doivent être chargées puis revérifiées sous la politique du moteur.
- Le routage est défini uniquement **dans le code statique audité**, jamais dans un YAML, JSON, un manifeste, une option `--mapping` ou une structure acceptée librement depuis un utilisateur.
- `human_approved` valide uniquement l'usage technique de la variante dans la démo, pas les droits complets ni la publication. `publication_approved=false`, `ready_for_kdp=false`, `needs_visual_review`, blocage du `build` intégral et règles de sécurité de sortie restent inchangés.

## 3. Politique canonique immuable de C1

Le mode C1 est **strictement borné** aux trois activités vérifiées de la démo Halloween, **dans cet ordre de pages de PDF** :

| demo_index | activity_id attendu | source_page | activity_type | asset_id |
|---:|---|---:|---|---|
| 1 | `halloween_2026-p004` | 4 | `maze` | `pip-reflexion-v2` |
| 2 | `halloween_2026-p006` | 6 | `connect_dots` | `pip-indication-v1` |
| 3 | `halloween_2026-p020` | 20 | `match` | `pip-encouragement-v1` |

Ces identités correspondent aux données inspectées dans B2-B. Si le `book_id` effectif de la version Git diffère ou si une activité/page est déplacée, suspendre et demander une révision du contrat, au lieu de modifier automatiquement la politique. Ne pas associer les trois autres PNG simplement pour les « utiliser ».

**Construction interne obligatoire** :

- `Book` chargé et revérifié par `verify_book_snapshot()` et les contrôles compagnon/plan ; `demo_specs(book)` recalculé ; policy canonique du code ; **PIN externe** ; chargement/vérification de chaque PNG.
- Structure fermée de type `IllustrationRoute` composée d'un tuple ordonné de liaisons `PageArtworkBinding` avec, au minimum, `demo_index`, `activity_id`, `source_page`, `activity_type`, `asset_id` et `VerifiedArtwork` (ou identité et octets vérifiés équivalents).
- Les bindings et le conteneur sont réellement **immuables** (dataclasses gelées + tuple, sans dictionnaire mutable partagé) et leurs valeurs sont comparées intégralement à la route **recalculée indépendamment**.
- Refuser doublons, éléments supplémentaires, couverture partielle, ordre non canonique, activité altérée et substitutions entre poses *même si les deux poses sont individuellement approuvées*.
- Le moteur ne doit pas exposer un argument d'API permettant d'injecter directement une table activité → chemin/Pip arbitraire. Si une route interne transite jusqu'au rendu, celui-ci revalide/recalcule les liaisons contre le `Book`, `demo_specs`, la policy statique et le PIN externe **avant de produire les pages**. La QA recalcule à son tour la route depuis les mêmes sources d'autorité, **sans réutiliser la route ou le manifeste générés**.
- `write_pdf` conserve intégralement la compatibilité `artwork=` de B2-B ; tout nouveau paramètre est exclusif et ne peut contourner le chargement/vérification canonique.
- Les 2 PDF doivent utiliser les mêmes liaisons. Aucune mutation d'objet `Activity` lors du rendu. Revérifier les sources/PNG avant publication atomique.

## 4. Inventaires de sortie fermés, distincts et préalables à la lecture des fichiers

**L'inventaire racine est identique dans les trois modes** :

```
interior.pdf
answer_key.pdf
activities.json
quality_report.json
quality_report.md
manifest.json
previews/
```

**Inventaire `previews/` spécifique au mode, avec égalité exacte** (aucun fichier supplémentaire ou manquant, y compris caché, lien symbolique, sous-répertoire ou fichier spécial) :

- `placeholder` et `legacy_illustration` : uniquement `page_01.png`, `page_02.png`, `page_03.png` ; mêmes octets qu'à B2-B.
- `routed` : uniquement `interior_page_01.png`, `interior_page_02.png`, `interior_page_03.png`, `answer_key_page_01.png`, `answer_key_page_02.png`, `answer_key_page_03.png`.

Ne **pas** conserver en plus `page_XX.png` dans les sorties routées. Ne **pas** introduire les 6 nouveaux aperçus dans les sorties historiques. La sélection de la liste attendue vient **de l'argument CLI/mode autorisé et des spécifications de démonstration de confiance**, jamais du manifeste. L'inventaire doit être vérifié via les descripteurs de répertoire ancrés et `O_NOFOLLOW` comme B2-B, **avant** de faire confiance aux sorties. Maintenir les limites de décodage PNG et la comparaison de tous les pixels des aperçus au rendu de la page correspondante, des deux PDF en mode routé, avec exactement `fitz.Matrix(1.4, 1.4)` et `alpha=False`.

**Manifeste** : modes B2-B inchangés *octet par octet*. En C1 exclusivement : une clé `illustration_routing` dont la valeur contient `policy_id` et un tuple/listing ordonné de `{demo_index, activity_id, source_page, activity_type, artwork}` (`artwork` = provenance dérivée d'un `VerifiedArtwork.manifest_entry()`). Pas de clé `illustration` héritée en plus. La QA compare l'objet complet à un manifeste régénéré de confiance, avec la même règle historique d'horodatage ISO UTC.

## 5. Audit indépendant des 6 pages PDF (obligatoire pour routed)

La QA calcule **elle-même** les identités attendues depuis `Book`/`demo_specs`/policy/PIN. Pour chacune des 3 pages de `interior.pdf` **et** des 3 pages de `answer_key.pdf`, elle doit :

1. Vérifier l'identité `(demo_index, activity_id, source_page, activity_type, asset_id)` attendue ; lier le PDF et la page à cette identité, sans dépendre d'un champ auto-déclaré du PDF ou du manifeste.
2. Exiger **une seule image raster intégrée** visible par page (xref PDF non nul), sans image supplémentaire ; contrôler ses dimensions, 1 canal gris, absence d'alpha/masque non autorisé et SHA-256 des **pixels décodés** contre le PNG validé attendu pour **cette page**. Ne pas se satisfaire d'une image faisant partie de la liste globale des six approuvées.
3. Déduire le rectangle attendu à partir du `companion_slot` produit par la composition stable et de la formule d'échelle B2-B, sans lire de bbox depuis le manifeste. Le PDF (PyMuPDF) expose un bbox en origine **haut-gauche** ; convertir le rectangle de `composition.py` depuis l'origine **bas-gauche** : `expected_slot=(slot.x, page_height-slot.top, slot.right, page_height-slot.y)`.
4. Vérifier que `bbox=(x0,y0,x1,y1)` contient **quatre valeurs finies**, `x1>x0`, `y1>y0`, que l'image reste **entièrement dans `expected_slot`**, tolérance numérique de `0.05 point` sur chaque bord ; et que chaque coordonnée de `bbox` diffère de la position/dimension **prédite par la formule du rendu B2-B** de **0.25 point maximum**. Ces tolérances valent aussi pour les corrigés ; elles ne permettent pas de déplacer le slot en C1.
5. Mesurer les **DPI effectifs depuis le bbox réellement incorporé** : `dpi_x = 72 * pixel_width / (x1-x0)` et `dpi_y = 72 * pixel_height / (y1-y0)`. Exiger `min(dpi_x,dpi_y) >= 299.99`, la marge de `0.01 DPI` ne servant qu'à absorber l'arrondi flottant autour de 300. Ne jamais inférer les DPI du seul PNG source ni d'un tag de métadonnées.
6. Vérifier la politique de texte/Unicode et les polices, sans réduction des contrôles historiques. Comparer ensuite **tous les fichiers régénérés canoniquement** au contenu livré, PDF et aperçus octet par octet, plus pixels des 6 aperçus contre leurs PDF respectifs.

**Indépendance requise** : cette vérification réside dans le chemin QA/audit, pas uniquement dans le renderer, et recalcule les associations depuis la politique fixe. Elle ne se contente ni des nombres d'images, ni de l'inventaire de registre, ni du seul re-render. Le rejeu canonique reste une **défense supplémentaire**, pas un remplacement des vérifications par page.

En cas de falsification d'une pose sur un seul PDF, d'un échange entre les poses p4/p6/p20, d'une bbox hors slot, d'une image redimensionnée sous 300 DPI ou d'un artefact manifestement truqué, échec fermé même si les checksums de sortie ont été recalculés dans `manifest.json`.

## 6. Oracle indépendant de non-régression B2-B

Le test de comparaison historique **doit faire intervenir deux codes réellement distincts** :

- **Oracle de référence** : checkout/worktree détaché **en lecture seule logique** au commit exact `d77e32327fecd0c4a983ef8298581525842c18fc` ; aucune importation Python depuis la branche C1. Ne pas utiliser l'archive seule comme oracle Git.
- **Candidat** : checkout/branche B2-C1, importation du code C1.

Exécuter chacun **dans un processus Python isolé** avec le même interpréteur, les mêmes versions de PyMuPDF, ReportLab, Pillow, PyYAML, les mêmes fontes (chemins + SHA-256 consignés), la même plateforme, les mêmes données Git du livre, le même `--seed 2026`, `SOURCE_DATE_EPOCH=1780000000` et le PIN externe inchangé pour le mode illustré. Éviter un `PYTHONPATH` contaminé par l'autre checkout ; tracer les versions/digests et vérifier qu'il s'agit bien de deux chemins source distincts.

Comparer **la liste fermée et les octets de chaque fichier** des deux sorties. Le `engine_version` historique, les métadonnées PDF et toutes les chaînes qui influencent les octets historiques doivent rester inchangés ; ne pas augmenter la version globale si cela modifie ces sorties. Toute version propre à C1 doit être confinée au nouveau mode. Comparer pour :

A. `build-demo books/halloween_2026/book.yaml` **sans visuel** ;
B. `build-demo books/halloween_2026/book.yaml --illustration-id pip-reflexion-v2 --approvals-sha256 93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61`.

Pour chaque cas, `qa` doit réussir sur le résultat provenant de l'**ancien moteur** avec l'ancienne CLI, ainsi que sur le résultat C1 avec la nouvelle CLI compatible, et les ensembles `manifest.json`, 2 PDF, `activities.json`, rapports JSON/MD et les **3 aperçus historiques** doivent être identiques octet par octet. Relever les SHA de chaque comparaison ; ne pas ignorer les différences de manifeste.

Une comparaison entre **deux builds C1** vérifie le déterminisme C1 mais **ne prouve pas** la non-régression. Si le checkout historique ne peut pas être obtenu, si l'environnement diverge ou si un byte-diff inexpliqué survient : **échec du gate, pas de PR présentée comme prête**. La CI doit pouvoir rejouer cette preuve ou conserver un artefact de preuve reproduisible (scripts, SHA, logs, détails d'environnement) et être revue indépendamment.

## 7. Tests supplémentaires et gates

- Maintenir **les 382 tests B2-B**, sans suppression/xfail/skip opportuniste, puis exécuter tous les nouveaux tests (un total supérieur ou égal à 382 ne suffit pas si des tests existants disparaissent).
- Tests positifs : chacune des 3 poses par page, même pose dans corrigé, 6 aperçus en mode routed, 3 dans chaque mode historique, manifeste C1 exact, deux rendus C1 déterministes avec inputs figés, audits par page réussis.
- Tests négatifs : PIN absent/faux, registre/PNG remplacés, illustration de Noël, route inconnue, flags en conflit, source de page/type/id modifiée, ordre changé, couverture partielle, duplication, substitution entre PNG approuvés, route falsifiée ou mutable, mauvaise pose sur un seul corrigé, aperçu d'un autre PDF, image supplémentaire, bbox décalée (> 0.05 pt hors slot), bbox incohérente (> 0.25 pt d'écart avec l'attendu), sous-résolution (< 299.99 DPI), overlay vectoriel, JSON à clés dupliquées, checksum et manifeste recalculés malicieusement, sortie supplémentaire cachée, symlink, échec tardif, restauration et intégrité de la précédente sortie publiée.
- Aucun nouveau format de rendu/export n'est demandé ; ne pas élargir C1 par commodité.
- Revalider les CLI Halloween / Noël ; `build` intégral reste refusé. La vérification C1 n'est pas une validation visuelle, prépresse ou KDP.

## 8. Workflow autorisé à Hermes

1. Confirmer `origin/main` et commit indiqué, SHA des assets protégés, statut Git propre ; vérifier le tag si présent, mais ne pas le substituer au **commit exact**.
2. Créer une branche `feat/studio-b2-c1-pip-routing` exclusivement depuis le commit de référence. Ne pas modifier `main`.
3. Poser ce contrat v1.1 dans `docs/SECURITY_CONTRACT_B2C1.md`, en gardant historique et justification des quatre corrections ; faire examiner **le contrat** indépendamment avant tout changement de moteur.
4. Mettre en place **l'oracle B2-B en premier**, avant implémentation, dans un worktree isolé avec script de comparaison et preuve reproductible.
5. Implémenter le mode C1 sans modifier les modes historiques ; adapter la QA pour les deux inventaires, la route canonique et l'audit graphique indépendant des 6 pages.
6. Tests positifs et adversariaux, CI et deux revues indépendantes (sécurité et stabilité) ; contrôler les SHAs des fichiers protégés avant et après.
7. Générer et joindre des aperçus **C1** pour la revue humaine ultérieure. La revue visuelle humaine et le prépresse restent **à faire**.
8. Ouvrir une **PR non fusionnée** uniquement après gates satisfaits, fournir les preuves et demander validation. En cas de nouvelle contradiction structurelle ou de vérification impossible, s'arrêter sans contournement et expliciter le blocage.

**Interdictions absolues** : aucun commit direct sur `main`, aucun merge automatique, aucune modification des sept assets protégés (6 PNG + référence couleur) ou de leur registre, aucun Pip Noël, aucune politique chargée depuis des données éditables, aucun bypass du PIN externe, aucune publication KDP, aucune déclaration `ready_for_kdp=true`.
