# Fiche de validation visuelle : Pip N&B (B2-B)

**Projet :** LaFractale Édition, *Mon Halloween bilingue avec Pip* (4-5 ans).
**Date de consignation :** 9 octobre 2026. **Base technique :** `v0.2.0b2`. **Kit :** B2-B final V2.
**Décision exprimée en conversation :** référence N&B V1, accueil/encouragement/indication V1 et réflexion/félicitations V2 validées visuellement.
**Décompte correct :** 1 référence N&B + 5 poses (accueil, encouragement, indication, réflexion V2 avec nuage pensif, félicitations V2 plus expressives) = **6 dessins**.

## Références et périmètre

- Pip couleur canonique : `assets/characters/pip/pip_officiel_couleur.png`, SHA-256 `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`. **Ne jamais remplacer ce fichier.**
- Pip est réservé au **livre Halloween**. Aucune utilisation dans Noël ni dans les autres thèmes.
- Les poses réflexion V1 et félicitations V1 ont été **remplacées par les V2 validées**. Les versions V1 de ces deux poses ne figurent pas dans ce kit final.
- Les six images sources RGB, approuvées pour leur **apparence**, sont archivées ici sans modification.
- Les six PNG gris 8 bits fournis sont des **copies techniques dérivées** (sans recadrage ni redessin, 1254 × 1254 px). Leurs rendus et le lot final V2 ont été acceptés pour l’intégration technique B2-B. Le registre actif a été consigné séparément, avec contrôle des empreintes ; l’approbation ne porte ni sur les pages finales ni sur KDP.
- Cette fiche constate une validation éditoriale en conversation. Elle **ne constitue ni signature cryptographique ni autorisation commerciale/KDP**.

## Inventaire

| Dessin | Identifiant moteur | Usage dans le cahier |
|---|---|---|
| Référence N&B | `pip-reference-nb-v1` | Étalon graphique ; gabarit de fidélité et pages de présentation |
| Accueil | `pip-accueil-v1` | Ouverture des activités, présentation de consigne |
| Encouragement | `pip-encouragement-v1` | Incitation à poursuivre et à essayer |
| Indication | `pip-indication-v1` | Signalement de la zone de jeu ou de consigne |
| Réflexion V2 | `pip-reflexion-v2` | Observation, déduction, labyrinthes et association |
| Félicitations V2 | `pip-felicitations-v2` | Fin de page, réussite et encouragement final |

## Contrôle d’intégrité de chaque copie technique

| Identifiant | SHA-256 du PNG gris |
|---|---|
| `pip-reference-nb-v1` | `8bf579336b405e2a9de0dc1fdbd7bbc281fd80dfa8d236d4108f8b1a6d9719b1` |
| `pip-accueil-v1` | `72716b4193b6f15e5ffb55340f6d3ddfa428282e804b44ff410f01354bf52a09` |
| `pip-encouragement-v1` | `1bd15c92f77825160258e962f08b1bfcc593e9de99f229e73469d1c295051597` |
| `pip-indication-v1` | `a3bec36fdec734d0791e5c76da99f1273eda43586310fdba795f6fc1a8089a81` |
| `pip-reflexion-v2` | `37107eb5c2a7331232303a0c0ae0347e3766faacc00e0abc779c78409c47ba48` |
| `pip-felicitations-v2` | `74030cb477e121addd94bcb1d5d4dcb8193b7cb123695e7a546ef9a733dba098` |

## Conditions d’intégration non négociables

1. Vérifier les 6 octets sources RGB et les 6 PNG gris via les SHA de `INVENTAIRE_SHA256.json`.
2. Conserver la traçabilité de la validation en conversation du lot final V2 ; `human_approved: true` dans le registre B2-B décrit uniquement une autorisation technique des six copies identifiées par leurs empreintes.
3. Importer exclusivement les PNG gris dans `assets/illustrations/halloween_2026/pip/`. Ne pas placer les originaux RGB dans le namespace du moteur.
4. Le registre candidat de l’ancien ZIP (`candidat_REGISTRE_NON_ACTIF/*`) reste un document historique **non activable**. La source actuelle de production est exclusivement `assets/illustrations/approvals.json` déjà présente sur la branche B2-B et épinglée par son hash externe. Ne pas la réécrire.
5. Les six entrées existantes du registre B2-B sont approuvées pour les essais techniques. SHA-256 du registre : `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61`. L’empreinte doit rester fournie par l’opérateur **hors YAML, manifestes et sorties** ; ce document ne constitue pas en lui-même une source de confiance pour `audit_output()`.
6. Le moteur B2-A ne choisit **qu’un seul `illustration_id` pour l’ensemble de la démo** ; l’attribution de poses différentes selon les pages nécessitera une évolution distincte, conçue/testée par GPT-6.
7. Faire passer les 379 tests historiques B2-A, le test de registre vide isolé et les trois tests B2-B, puis la revue indépendante Hermes. Vérifier la résolution 300 DPI à la taille imprimée ; le moteur n’attribue aucun statut KDP.
8. Aucun KDP, aucune approbation de couverture ou d’intérieur global ; `publication_approved` reste `false`.

## Suivi de validation technique (non commercial)

- [x] Référence couleur officielle confirmée.
- [x] Sources visuelles noir et blanc conservées en conversation.
- [x] Lot final V2, incluant les copies techniques présentées, accepté pour intégration B2-B.
- [x] Six entrées existantes du registre B2-B renseignées avec `human_approved: true` (état local Hermes, non modifié par ce correctif).
- [x] SHA-256 du registre local vérifié et consigné : `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61`.
- [ ] Trois tests B2-B, générations illustrées et QA indépendante validés dans le clone Hermes après application du correctif.
- [ ] Placement par page (B2-C) défini et vérifié ultérieurement.

## Limites et périmètre de l'approbation B2-B

- Les six dessins N&B, dont réflexion V2 et félicitations V2, sont autorisés **uniquement pour les démonstrations techniques Halloween** et pour les contrôles de mise en page.
- Le registre conservé sur la branche B2-B a une empreinte externe fixée ci-dessus ; ni ce document ni `INVENTAIRE_SHA256.json` ne peuvent remplacer cette empreinte fournie par l'opérateur au moteur.
- Les épreuves imprimées, la lisibilité à taille réelle, les corrigés finaux, l'intérieur complet de 56 pages et la couverture restent **à valider**.
- Les fichiers PNG, le personnage Pip couleur et le moteur Python sont immuables dans ce lot documentaire/tests.
