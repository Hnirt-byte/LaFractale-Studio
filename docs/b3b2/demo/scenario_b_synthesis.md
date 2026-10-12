# B3-B.2 — Synthèse des développements restants

> Dérivée du rapport JSON (même source de vérité). Statuts permanents inchangés : MAJOR-03=OPEN, MAJOR-04=OPEN, EDITORIAL=PENDING, KDP=FORBIDDEN, PRODUCTION_GENERATION=FORBIDDEN, ready_for_kdp=false.

## 1. Développement technique nécessaire (par composant)

### C1 — Contrat de page de production et chargeur du scénario B

Dépend de : —. Réutilise : lafractale.scenario_b.sources (B3-B.2); engine.contracts (JSON strict, JSON canonique, SHA-256); security.text (politique Unicode).
- schéma fermé de page (type, payload, réponse, FR/EN, assets, approbations, page source/finale)
- chargeur du scénario B actif en remplacement de books/halloween_2026/page_plan.csv, sans l'écraser
- levée contrôlée de la restriction « fixtures synthétiques » pour des sources réelles, sans génération de production

### C2 — Généralisation de maze, connect_dots et match

Pages concernées : p.14, p.17, p.25, p.27, p.34, p.43, p.46.
Dépend de : C1. Réutilise : activities.engine (générateurs); engine.solvers (vérification indépendante); profil éditorial C4.
- `connect_dots` (PARTIAL) pages p.17 — liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; ligne de corrigé condensé p.49-54 ; silhouette et nombre de points propres à la page non spécifiés
- `match` (PARTIAL) pages p.27, p.46 — association hétérogène invité→objet avec indices narratifs (le vérificateur exige des colonnes identiques) ; famille de symboles 'hats' non ouverte dans le registre (seule 'shapes' l'est) ; liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; ligne de corrigé condensé p.49-54
- `maze` (PARTIAL) pages p.14, p.25, p.34, p.43 — liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; ligne de corrigé condensé p.49-54 ; paramètre de taille/difficulté absent (grille 5x5 fixe) ; scène/habillage et routage d'illustration propres à la page
- maze : paramètre de taille/difficulté (p.43 exigence élevée), scènes par page
- connect_dots : silhouette maison à nombre de points déclaré (p.17), croissant C4 inchangé
- match : famille 'hats' ouverte au registre, association hétérogène invité→objet (p.46), 4 paires fixes à confirmer

### C3 — Registre d'assets multi-rôles (scènes, objets, pictogrammes)

Dépend de : C1. Réutilise : illustrations.registry (SHA-256, approbation séparée); assets/illustrations/approvals.json.
- rôles scène/objet/pictogramme/trait de coloriage avec provenance, droits et SHA-256
- routage et placement par page ; les assets C4 ne deviennent pas réutilisables par défaut

### C4 — Corrigés condensés p.49-54 (31 entrées, 6/5/5/5/5/5)

Pages concernées : p.49, p.50, p.51, p.52, p.53, p.54.
Dépend de : C1, C2. Réutilise : fiche/corrigé du moteur; layout.composition.
- `answers` (UNSUPPORTED) pages p.49, p.50, p.51, p.52, p.53, p.54 — composition de page spéciale (hors fiche d'activité)
- mise en page condensée avec renvoi à la page source
- rendu de solution par mécanique (incrémental)
- aucune activité libre dans les corrigés

### C5 — Famille associations et tri

Pages concernées : p.07, p.11, p.31, p.32, p.37, p.40, p.41, p.48.
Dépend de : C2, C3. Réutilise : vérification de bijection de match; registre de pictogrammes.
- `match_vocabulary` (UNSUPPORTED) pages p.11, p.32, p.48 — lien explicite avec le lexique p.55 ; paires mot/image lues par un adulte ; pictogrammes approuvés (p.55 sans pictogramme non approuvé)
- `one_to_one` (UNSUPPORTED) pages p.40 — correspondance terme à terme 1-5 (hétérogène) ; vérificateur de bijection
- `pair_matching` (UNSUPPORTED) pages p.31 — détection de paires identiques dans une grille d'objets ; unicité des paires
- `shadow_match` (UNSUPPORTED) pages p.07, p.41 — paires silhouette/objet avec ombres distinctes ; vérificateur de bijection non triviale
- `sort` (UNSUPPORTED) pages p.37 — critère de tri explicite sans couleur (noir et blanc) ; vérificateur de classification unique
- paires silhouette/objet, mot/image, objets identiques, 1:1 et tri sans couleur
- vérificateurs de solution unique
- lien avec le lexique p.55

### C6 — Famille comptage et recherche

Pages concernées : p.05, p.10, p.15, p.21, p.24, p.30, p.35, p.44.
Dépend de : C1, C3. Réutilise : placement déterministe de scène; réponse chiffrée.
- `count` (UNSUPPORTED) pages p.10, p.21, p.30 — corrigé de type chiffre ; générateur d'ensembles dénombrables ; réponse chiffrée vérifiée
- `find_count` (UNSUPPORTED) pages p.05, p.15, p.24, p.35, p.44 — corrigé avec repérage des cibles ; placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles
- placement d'objets cibles et leurres sans chevauchement
- vérification des comptes
- corrigé chiffré ou repéré

### C7 — Famille tracés, séquences et logique

Pages concernées : p.09, p.12, p.16, p.19, p.22, p.26, p.29, p.36, p.38.
Dépend de : C2, C3. Réutilise : graphe de labyrinthe de maze; vérificateur de croisements de connect_dots.
- `path_logic` (UNSUPPORTED) pages p.22 — graphe de chemins avec croisements maîtrisés ; vérificateur de chemin unique non croisé
- `pattern` (UNSUPPORTED) pages p.16, p.26, p.36 — générateur de suites avec élément manquant ; vérificateur de solution unique
- `spot_differences` (UNSUPPORTED) pages p.12 — deux scènes dérivées avec différences contrôlées ; vérificateur du nombre de différences
- `trace_paths` (UNSUPPORTED) pages p.09, p.19, p.29, p.38 — corrigé graphique du tracé ; générateur de tracés (guides) et vérificateur de non-croisement/continuité
- tracés guidés et chemins sans croisement
- suites avec élément manquant
- scènes à différences contrôlées

### C8 — Famille dessin libre et coloriage

Pages concernées : p.03, p.08, p.13, p.18, p.23, p.28, p.33, p.39, p.42, p.45, p.47.
Dépend de : C3. Réutilise : composition de fiche.
- `coloring` (UNSUPPORTED) pages p.03, p.13, p.18, p.23, p.33, p.39 — gabarit de coloriage (grandes zones) sur illustration au trait approuvée
- `creative_color` (UNSUPPORTED) pages p.08, p.28, p.42, p.45, p.47 — gabarit de page libre (zone de création, aucune réponse attendue)
- gabarits à grandes zones et zones de création libre
- aucune réponse ni corrigé

### C9 — Layouts spéciaux (ouverture, lexique 18 paires, diplôme/clôture)

Pages concernées : p.01, p.02, p.55, p.56.
Dépend de : C1. Réutilise : layout.composition; politique de texte.
- `diploma + back_matter` (UNSUPPORTED) pages p.56 — composition de page spéciale (hors fiche d'activité)
- `front_matter` (UNSUPPORTED) pages p.01, p.02 — composition de page spéciale (hors fiche d'activité)
- `glossary typographique` (UNSUPPORTED) pages p.55 — composition de page spéciale (hors fiche d'activité)
- p.01-02 ouverture
- p.55 lexique 18 paires sans pictogramme non approuvé
- p.56 diplôme protégeant la zone prénom/cercle/consigne à 100 %

### C10 — Export fermé, manifeste et préflight

Dépend de : C4, C5, C6, C7, C8, C9. Réutilise : export.builder; inventaire fermé des sorties; tools/preflight_b2c3.py.
- intérieur 56 pages, aperçus, manifeste complet, inventaire de sortie versionné

## 2. Contenu éditorial à compléter

- `BLOCKED_BY_SOURCE` : 3 page(s) — p.01, p.02, p.56
- `LEXICON_PRODUCTION_COPY_ABSENT` : 1 page(s) — p.55
- `OPENING_COPY_ABSENT` : 2 page(s) — p.01, p.02
- `PRODUCTION_COPY_NOT_FINAL` : 1 page(s) — p.56
- `SOLUTION_BLOCKED_BY_SOURCE` : 31 page(s) — p.04, p.05, p.06, p.07, p.10, p.11, p.12, p.14, p.15, p.16, p.17, p.20, p.21, p.22, p.24, p.25, p.26, p.27, p.30, p.31, p.32, p.34, p.35, p.36, p.37, p.40, p.41, p.43, p.44, p.46, p.48

## 3. Validation humaine requise

- 103 unités sur 103 sans validation humaine ; aucune proposition générée n'est considérée comme approuvée.
- Pages à revue de données (HUMAN_REVIEW) : p.17, p.22, p.37, p.43, p.44, p.45, p.46, p.48.
- Rôles : réviseur FR ; réviseur EN ; relecteur bilingue ; pédagogie 4-5 ans ; impression 100 % ; arbitre éditorial.

## 4. Problèmes de cohérence documentaire

- **CONTRADICTION** `PLAN_CORRECTION_STATUS_EMPTY` : Le plan actif ne renseigne correction_status que pour 9 pages ; 25 pages ont pourtant un corrigé dans le contrôle des corrigés. Le contrôle des corrigés fait foi pour le besoin de corrigé.

## 5. Ordre d'implémentation proposé (dépendances réelles)

| Rang | Composant | Pages | Dépend de | Justification |
|---:|---|---:|---|---|
| 1 | C1 — Contrat de page de production et chargeur du scénario B | 0 | — | Tous les autres composants lisent ce schéma ; aucune page réelle n'est productible tant que le contrat refuse les sources non synthétiques. |
| 2 | C2 — Généralisation de maze, connect_dots et match | 7 | C1 | Débloque 7 pages avec le code déjà vérifié ; fournit la bijection et le graphe de labyrinthe réutilisés ensuite. |
| 3 | C3 — Registre d'assets multi-rôles (scènes, objets, pictogrammes) | 0 | C1 | Quatre familles sur cinq dépendent d'illustrations approuvées ; l'approbation humaine est le chemin le plus long, à lancer tôt. |
| 4 | C4 — Corrigés condensés p.49-54 (31 entrées, 6/5/5/5/5/5) | 6 | C1, C2 | Se construit avec les solutions de chaque famille ; le cadre peut être posé dès que C2 fournit trois rendus de solution. |
| 5 | C5 — Famille associations et tri | 8 | C2, C3 | Famille la plus proche de match : réutilise directement la bijection et son vérificateur (C2). |
| 6 | C6 — Famille comptage et recherche | 8 | C1, C3 | Aucune mécanique voisine à réutiliser ; dépend des objets approuvés de C3. |
| 7 | C7 — Famille tracés, séquences et logique | 9 | C2, C3 | Réutilise le graphe de maze et la géométrie de connect_dots ; p.22 reste soumise à revue humaine des données. |
| 8 | C8 — Famille dessin libre et coloriage | 11 | C3 | Techniquement simple mais entièrement conditionné par les traits approuvés de C3 ; p.42, p.45 et p.47 sont des respirations sans corrigé. |
| 9 | C9 — Layouts spéciaux (ouverture, lexique 18 paires, diplôme/clôture) | 4 | C1 | Indépendant des mécaniques mais bloqué par les copies de production absentes (blocage éditorial, pas technique). |
| 10 | C10 — Export fermé, manifeste et préflight | 0 | C4, C5, C6, C7, C8, C9 | Dernier maillon ; reste interdit tant que les statuts permanents n'ont pas été levés par décision humaine. |
