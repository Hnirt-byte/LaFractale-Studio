# Prompt à envoyer à Hermes — B3-A

**Mission : architecture éditoriale du cahier Halloween 56 pages. Ne pas générer le livre.**

Tu reçois le ZIP `LaFractale_B3-A_PACK_LANCEMENT_v1.0.zip`. Lis tous les documents, et commence par les sources, le contrat et les deux fichiers de chemin de fer.

## Ancrage Git et garde-fous
- Repo : `Hnirt-byte/LaFractale-Studio`.
- `main` attendu : `397bc32c042dcd5533296ac7fe76b6a3ad749347` (tree `72215ac28de46795338997be0bb38781274e80f4`).
- Attention : notre `page_plan.csv` de travail vient d'une **archive historique B2-B**. Ne présume pas qu'il correspond au `page_plan.csv` actuel du dépôt. Vérifie avant toute écriture la version exacte du `book.yaml`, du chemin de fer et de la bible éditoriale sur `main`.
- Si `main` diffère ou si C4 a changé des spécifications canoniques, établis le diff des divergences ; n'écrase jamais les fichiers `books/` ni les politiques C1/C2/C4.

## Étape 1 : revue de contrat, sans code
1. Vérifie que le dossier respecte les contrats B2-A à B2-C4 et la nouvelle structure éditoriale.
2. Compare le `page_plan.csv` original du dépôt à notre proposition B3-A, page par page.
3. Vérifie les titres, consignes et mécaniques des pilotes C4 pages 04, 06 et 20 sur l'état réel de `main`. Une suggestion B3-A n'annule pas automatiquement un contenu C4 fusionné.
4. Fais un inventaire **documentaire seulement** des mécaniques déjà implémentées / partiellement implémentées / non implémentées dans le moteur.
5. Signale toute contradiction matérielle avant de créer une branche.

## Étape 2 : consolidation documentaire
Si aucune contradiction bloquante n'est constatée : crée `docs/b3-a-chemin-de-fer-halloween` depuis le commit stable. Copie dans `docs/editorial/b3a/` les fichiers éditoriaux de ce pack ; conserve leurs statuts de propositions. Ajoute un rapport de réconciliation contre HEAD et les hypothèses ouvertes.

Priorités : 56 pages sans ajout ni omission, 5 chapitres, 18 mots, jeux variés, progression pour 4–5 ans, cohérence FR/EN, rôles Pip comme intentions éditoriales, 34 jeux corrigeables et risque majeur de densité des corrigés. Aucune création d'asset.

Ne modifie **aucun** fichier de production, aucune source Python, tests, oracles, workflow, illustrations, registre, ni `books/halloween_2026/book.yaml` ou `page_plan.csv` original. Ne convertis pas une proposition en statut `approved`.

## Étape 3 : audits et présentation
1. Vérifie les invariants documentaires et la traçabilité du diff.
2. Obtiens deux revues indépendantes : A (structure/traçabilité/effet Git), B (pédagogie/bilingue/corrigés).
3. Propose un vrai arbitrage sur les quatre pages de solutions : présenter lisibilité et alternatives 4 vs 6–8 pages, mais sans réécrire la pagination sans accord.
4. Fais constater l'absence de changement dans les fichiers sensibles, et la CI applicable au commit.
5. Ouvre une PR **docs-only non fusionnée**, avec fichiers ajoutés et rapport d'audit. Aucun merge automatique.

## Rapport attendu
- Commit et tree du HEAD initial, branche documentaire et PR.
- Tableau des divergences source historique / HEAD / proposition.
- Compte exact des 56 pages, types, mots, besoins d'illustration, activités à corrigé.
- Faisabilité des corrigés avec recommandation.
- Deux verdicts d'audit indépendants et findings.
- Liste des décisions éditoriales ouvertes, notamment les 4 pages de corrigés.
- `B3A_PLAN=DRAFT_FOR_REVIEW`, `EDITORIAL=PENDING`, `KDP=FORBIDDEN`.

Ne commence pas B3-B, ne produis pas les 56 PDF, ne publie rien sur KDP. Si les validations sont incomplètes, arrête l'intégration et fournis le problème précis.
