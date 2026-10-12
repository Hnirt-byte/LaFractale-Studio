# Contrat B3-A v1.0 — Architecture éditoriale Halloween 56 pages

## 1 · Base traçable
- Dépôt : `Hnirt-byte/LaFractale-Studio`.
- `main` de référence post B2-C4 : `397bc32c042dcd5533296ac7fe76b6a3ad749347`.
- Tree attendu : `72215ac28de46795338997be0bb38781274e80f4`.
- Source éditoriale initiale : `books/halloween_2026/page_plan.csv` dans l'archive historique B2-B, SHA-256 `6dcc6d9f2a23eddc320303e20f9cfb3f70ad9bb25f42b8b5672dc25ba07f6099`. **Ce n'est pas une preuve de conformité de ce fichier au HEAD B2-C4.**
- Vérification obligatoire : Hermes lit `books/halloween_2026/book.yaml`, `page_plan.csv`, `docs/EDITORIAL_BIBLE.md`, les contrats B2-C1 à C4 et la CI **dans le HEAD actuel**. Il établit un diff sémantique entre ce plan et la source actuelle, signale chaque divergence. En cas de conflit, il s'arrête avant mise à jour des données du livre.

## 2 · Périmètre autorisé
- Travail **éditorial documentaire uniquement** : proposition de chemin de fer détaillé sur 56 pages, progression, règles de conception, liste de décisions ouvertes, cartographie des solutions, inventaire des besoins d'illustration.
- Branche séparée docs-only `docs/b3-a-chemin-de-fer-halloween`, PR non fusionnée.
- Les documents B3-A doivent être ajoutés sous `docs/editorial/b3a/`, **sans écrire ni remplacer `books/halloween_2026/page_plan.csv`**, `book.yaml`, les fichiers Python, tests, oracles, workflows, assets et registres.
- Pas de PDF de production, pas de nouvel artwork, pas de build complet, pas de manipulation d'approbations ni d'autorisations externes.

## 3 · Contraintes de contenu non négociables
1. Toujours **56 pages intérieures**, couverture hors calcul et sans page supplémentaire implicite. Conserver les zones (01–02, 03–49, 50, 51–54, 55, 56) sauf décision humaine explicite.
2. Suivre la narration 5 chapitres : invitation → forêt → amis → bonbons → fête, pas d'univers inquiétant ou traumatisant.
3. Public de 4–5 ans, adulte lecteur potentiel : pas de présomption de lecture ou de calcul autonome. Suivre une montée graduelle de difficulté, maximum 8 points pour la lune pilote.
4. Présenter exactement les 18 mots canonique FR/EN du `book.yaml`. Ne pas ajouter d'expression au lexique évalué sans décision.
5. Au moins 8 mécaniques distinctes réparties ; aucune mécanique identique sur deux pages consécutives, hors séquences documentaires (ouverture/corrigés), sauf exception documentée.
6. La légende et le système de numéro d'une activité et son corrigé doivent rester cohérents. Chaque activité fermée doit posséder une solution non ambiguë.
7. Les trois pilotes p04 labyrinthe, p06 lune 1→8→1 et p20 chapeaux jumeaux restent des références approuvées **pour les démos** ; toute modification du contenu doit être distinguée comme proposition et motivée.
8. Utiliser uniquement les noms des poses Pip déjà approuvées comme **candidats narratifs** ; aucun moteur C1/C2 existant n'autorise pour autant le routage de Pip sur 47 nouvelles pages.
9. Garder `EDITORIAL=PENDING`, `KDP=FORBIDDEN`. Les éventuels statuts `approved` dans ce document sont interdits avant revue humaine.

## 4 · Modèle de fiche
Champs nécessaires : page, chapitre, titre historique et proposé, type historique et proposé, niveau, objectif, couple(s) de vocabulaire FR/EN, consignes provisoires FR/EN, rôle Pip, asset candidat (sans autorisation), nature de solution, illustration nécessaire, points de contrôle, statut de revue, provenance.

## 5 · Points bloquants du plan, pas du moteur
### 5.1 Corrigés sur quatre pages
Le chemin de fer contient 34 activités objectivement corrigeables. La cartographie 9/9/8/8 n'est qu'une option de pré-maquette. Il faut un exemple **à taille 100 % sur papier** prouvant que la lecture des numéros, tracés et réponses reste possible. Si non : proposer des alternatives de pagination 56 pages, chiffrées en activités sacrifiées ou regroupées ; demander arbitrage.
### 5.2 Lexique illustré
La page 55 prétend illustrer 18 entrées. Aucun ensemble de 18 pictogrammes n'est réputé approuvé. Proposer soit lexique typographique en deux colonnes, soit brief d'assets futurs soumis à validation explicite.
### 5.3 Fond perdu
Conserver la préférence **intérieur sans fond perdu**, à officialiser seulement après vérification de toutes les pages finales, marges recto/verso et Print Previewer.

## 6 · Matrice documentaire et contrôles
- Lignes 1..56, uniques et croissantes, colonnes requises remplies.
- Détection des répétitions de mécanique et du vocabulaire hors liste.
- 5 chapitres avec transitions et progression.
- Distinction correction « graphique », « chiffre », « libre », « modèle facultatif », « index », « aucun ».
- Exigence de résultat reproductible : tri et sérialisation canoniques des données B3-A + hash du CSV.
- Comparaison ligne à ligne avec page_plan.csv réellement présent au HEAD ; le résultat (changements proposés, tensions avec C4) est documenté et jamais appliqué automatiquement.
- Deux revues indépendantes de **la cohérence du plan** : revue A structure/traçabilité, revue B pédagogie bilingue/solutions/charge graphique. Les revues peuvent être documentaires et ne constituent pas une certification pour KDP.
- Ne pas masquer les désaccords humains ou forcer leur approbation par une règle technique.

## 7 · Sortie attendue de Hermes
1. `docs/editorial/b3a/` avec dossier complet et modifications documentaires traçables.
2. Rapport de différence entre plan historique, proposition et source `main` actuelle.
3. Inventaire des mécaniques déjà supportées, partiellement supportées et absentes du moteur, **sans implémentation**.
4. Proposition formalisée pour la densité des quatre pages de corrigés.
5. Statuts `B3A_PLAN=DRAFT_FOR_REVIEW`, `EDITORIAL=PENDING`, `KDP=FORBIDDEN`.
6. PR documents-only ouverte, non fusionnée ; aucun test historique supprimé ; si CI pertinente, succès sur le SHA exact.

## 8 · Gates et refus
- Modification d'un fichier moteur, asset, registre, book.yaml, page_plan.csv de production ou d'un oracle : **FAIL**, arrêter avant commit.
- Changement du HEAD stable non expliqué ou divergences éditoriales réelles non réconciliées : **STOP**, présenter le diff.
- Plan total autre que 56 pages, introduction de mots de lexique non approuvés, solution obligatoire omise : **FAIL**.
- Plan lisible mais densité corrigés non prouvée : **PASS DOCUMENTAIRE AVEC RÉSERVE**, aucune autorisation pour B3-B production tant que la décision n'est pas prise.
