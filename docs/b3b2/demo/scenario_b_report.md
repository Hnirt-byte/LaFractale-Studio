# B3-B.2 — Lecteur du scénario B : rapport de capacités et de blocages

> Analyse en lecture seule, `READ_ONLY_ANALYSIS_NON_PRODUCTION`. Aucun PDF, aucun asset, aucune approbation. Schéma `lafractale-scenario-b-report-v1`, lecteur `b3b2-reader-1.0`.

```text
MAJOR-03              = OPEN
MAJOR-04              = OPEN
EDITORIAL             = PENDING
KDP                   = FORBIDDEN
PRODUCTION_GENERATION = FORBIDDEN
ready_for_kdp         = false
```

## Autorité et provenance

- Pagination : `docs/editorial/b3a/b3a3/01_chemin_de_fer_scenario_B_56_pages.csv` (fait autorité).
- Consignes actives : `docs/editorial/b3a/b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv` ; grille B3-A.4 : `docs/editorial/b3a/b3a4/02_grille_relecture_humaine_complete.csv` ; corrigés : `docs/editorial/b3a/b3a3/02_controle_corriges_scenarios.csv`.
- Exclus du plan actif : `docs/editorial/b3a/b3a3/03_consignes_bilingues_historiques_47_propositions.csv`, `docs/editorial/b3a/b3a4/03_archive_historique_47_reference.csv`, `books/halloween_2026/page_plan.csv`.

| Source | Rôle | Octets | SHA-256 |
|---|---|---:|---|
| `docs/editorial/b3a/b3a3/02_controle_corriges_scenarios.csv` | ACTIVE_CANONICAL | 3161 | `c432d3a9324a304f36752216ced0eea451b7e2a1053da214aacfb3b70c5307fb` |
| `assets/illustrations/approvals.json` | ENGINE_CONFIGURATION | 2477 | `93c58e86a74e903af1be5cd4257d489c39bece8f5cd41d985586cbf775d45e61` |
| `docs/editorial/b3a/b3a3/03_consignes_bilingues_historiques_47_propositions.csv` | HISTORICAL_ARCHIVE_EXCLUDED_FROM_ACTIVE_PLAN | 18641 | `7683a1cc60c65fa7e7082973eb771c30641072ec595d8e808f7a041e0ae4032e` |
| `docs/editorial/b3a/b3a4/03_archive_historique_47_reference.csv` | HISTORICAL_ARCHIVE_EXCLUDED_FROM_ACTIVE_PLAN | 8750 | `b044b5328b848eae86a1115aaf2c7ba8720bd9c26a2befc9157a5d7b27f35038` |
| `books/halloween_2026/book.yaml` | ENGINE_CONFIGURATION | 1049 | `b1f0bafdc1097a384f281feb64b7f8cd7cae52cc3e837c4890a38c26da5a51d5` |
| `docs/editorial/b3a/b3a4/08_validation_evidence.json` | ACTIVE_SUPPORTING | 1090 | `b68f67477fe5b71564cc18b8555391e455895c4e4931ca6355497c4de331f143` |
| `docs/editorial/b3a/b3a4/02_grille_relecture_humaine_complete.csv` | ACTIVE_CANONICAL | 74405 | `45b12c7112a75289144d312c06229f663b1257b895edb2ae55efaa3cd1274f5d` |
| `docs/editorial/b3a/b3a3/03_consignes_bilingues_finales_46_pages_scenario_B.csv` | ACTIVE_CANONICAL | 20611 | `7be0080f8b7cd0159cd066afa1ef0b0197a0d869811a8ad5d40cb56ab6361ae2` |
| `books/halloween_2026/page_plan.csv` | LEGACY_NON_AUTHORITATIVE | 3166 | `6dcc6d9f2a23eddc320303e20f9cfb3f70ad9bb25f42b8b5672dc25ba07f6099` |
| `docs/editorial/b3a/b3a3/09_integrity_manifest.json` | INTEGRITY_REFERENCE | 3306 | `6a7da5acbeedee114a749c8bb8536bc23b2c676f1e2aabb90578e2015c7db486` |
| `docs/editorial/b3a/b3a4/09_integrity_manifest.json` | INTEGRITY_REFERENCE | 1532 | `400b9a4892b2163e65855198a8bebe06e820ae1d001b7aabba089edf6dec4587` |
| `docs/editorial/b3a/b3a3/01_chemin_de_fer_scenario_B_56_pages.csv` | ACTIVE_CANONICAL | 6427 | `2da1e37505ca7357ad77e31c1431dfcacc7e0fe4fc7254c4a72158f327b23d46` |

Empreinte agrégée : `c58b2fb132e1b476e745d0d47c818e82979f906a955ded06d5df95dcfcf708ed`

## Capacités réelles du moteur

- Générateurs : connect_dots, match, maze. Contrat de production : B3-B.1 : sources synthétiques uniquement, 12 fiches maximum, aucun asset ni livre réel.
- `maze` : grille 5×5 fixe, aucun paramètre de taille.
- `connect_dots` : house = 7 points, moon = 12 points, star = 10 points ; halloween-editorial-v1: croissant à 8 points (p.06 seulement).
- `match` : 4 paires, relation « jumeaux identiques (colonnes de mêmes symboles) » ; familles du registre ['shapes'], du générateur ['gifts', 'hats', 'shapes'].
- Profil éditorial `halloween-editorial-v1` : pages [4, 6, 20].

## Contrôles de structure

| Contrôle | Attendu | Observé | Résultat |
|---|---|---|---|
| Plan actif : 56 pages distinctes | 56 | 56 | PASS |
| Plan actif : aucune page dupliquée | [] | [] | PASS |
| Plan actif : aucune page hors 1..56 | [] | [] | PASS |
| Plan actif : scénario B uniquement | ['B'] | ['B'] | PASS |
| p.01-02 : titres d'ouverture (front_matter) | ['front_matter', 'front_matter'] | ['front_matter', 'front_matter'] | PASS |
| p.03-48 : 46 pages d'activité | 46 | 46 | PASS |
| p.49-54 : six pages de corrigés | ['answers', 'answers', 'answers', 'answers', 'answers', 'answers'] | ['answers', 'answers', 'answers', 'answers', 'answers', 'answers'] | PASS |
| p.55 : lexique | glossary typographique | glossary typographique | PASS |
| p.56 : diplôme et clôture | diploma + back_matter | diploma + back_matter | PASS |
| Respirations créatives p.42, p.45, p.47 | ['creative_color', 'creative_color', 'creative_color'] | ['creative_color', 'creative_color', 'creative_color'] | PASS |
| Respirations créatives : correction « libre » | [] | [] | PASS |
| Consignes actives : 46 pages p.03-48 | 46 | 46 | PASS |
| Sources historiques non confondues avec les sources actives (47 ≠ 46) | False | False | PASS |
| Titres identiques plan ↔ consignes | [] | [] | PASS |
| Types identiques plan ↔ consignes | [] | [] | PASS |
| Consignes FR et EN renseignées | [] | [] | PASS |
| Texte éditorial conforme à la politique Unicode du dépôt | [] | [] | PASS |
| p.06 : consigne identique au profil C4 du moteur | ['Relie les points de 1 à 8, puis reviens au 1.', 'Connect the dots from 1 to 8, then back to 1.'] | ['Relie les points de 1 à 8, puis reviens au 1.', 'Connect the dots from 1 to 8, then back to 1.'] | PASS |
| Corrigés : 31 unités | 31 | 31 | PASS |
| Corrigés : répartition 6/5/5/5/5/5 sur p.49-54 | [6, 5, 5, 5, 5, 5] | [6, 5, 5, 5, 5, 5] | PASS |
| Aucune activité libre dans les corrigés | [] | [] | PASS |
| Corrigés rattachés à des activités p.03-48 | [] | [] | PASS |
| Titres des corrigés = titres du plan | [] | [] | PASS |
| Page de corrigé identique consignes ↔ contrôle des corrigés | [] | [] | PASS |
| Grille B3-A.4 : 103 unités actives | 103 | 103 | PASS |
| Grille : 46 consignes + 31 corrigés + 18 paires + 2 ouvertures + 6 unités p.56 | {'activity_instruction': 46, 'answer_entry': 31, 'lexicon_pair': 18, 'opening_text': 2, 'closing_units': 6} | {'activity_instruction': 46, 'answer_entry': 31, 'lexicon_pair': 18, 'opening_text': 2, 'closing_units': 6} | PASS |
| Grille : aucune unité d'archive dans le périmètre actif | [] | [] | PASS |
| Entrées de corrigé de la grille = contrôle des corrigés | [] | [] | PASS |
| Pages de corrigé de la grille = contrôle des corrigés | [] | [] | PASS |
| Grille ↔ consignes actives (titre, type, FR, EN) | [] | [] | PASS |
| p.55 : 18 paires de lexique | 18 | 18 | PASS |
| p.55 : paires de la grille = vocabulaire de books/halloween_2026/book.yaml | ['araignée', 'balai', 'bonbon', 'chapeau', 'chat', 'chauve-souris', 'citrouille', 'fantôme', 'hibou', 'lune', 'maison', 'monstre', 'nuit', 'porte', 'sac', 'sorcière', "toile d'araignée", 'étoile'] | ['araignée', 'balai', 'bonbon', 'chapeau', 'chat', 'chauve-souris', 'citrouille', 'fantôme', 'hibou', 'lune', 'maison', 'monstre', 'nuit', 'porte', 'sac', 'sorcière', "toile d'araignée", 'étoile'] | PASS |
| book.yaml : 56 pages intérieures | 56 | 56 | PASS |
| p.56 : 6 unités | 6 | 6 | PASS |
| p.01-02 : 2 titres d'ouverture | 2 | 2 | PASS |
| Pages C4_LOCKED de la grille = pages couvertes par le profil du moteur | [4, 6, 20] | [4, 6, 20] | PASS |
| Types des pilotes C4 = types du moteur | [] | [] | PASS |
| Archive historique b3a3 : 47 propositions (exclues du plan actif) | 47 | 47 | PASS |
| Archive historique b3a4 : 47 propositions (exclues du plan actif) | 47 | 47 | PASS |
| Archive b3a4 : statut HISTORICAL_ONLY sur chaque ligne | [] | [] | PASS |
| Ancienne p.49 → p.48 finale (ancienne p.48 supprimée) | 49→48 | 49→48 | PASS |
| Statuts permanents des sources = constantes du lecteur | {'MAJOR-03': 'OPEN', 'MAJOR-04': 'OPEN', 'EDITORIAL': 'PENDING', 'KDP': 'FORBIDDEN', 'PRODUCTION_GENERATION': 'FORBIDDEN'} | {'MAJOR-03': 'OPEN', 'MAJOR-04': 'OPEN', 'EDITORIAL': 'PENDING', 'KDP': 'FORBIDDEN', 'PRODUCTION_GENERATION': 'FORBIDDEN'} | PASS |
| Validations humaines enregistrées (preuve) = lignes validées de la grille | 0 | 0 | PASS |
| Manifeste d'intégrité b3a3 : empreintes des fichiers | [] | [] | PASS |
| Manifeste d'intégrité b3a4 : empreintes des fichiers | [] | [] | PASS |
| Chiffres de la feuille de route B3-B (b3a4/05) recalculés | {'activities': 46, 'mechanisms': 16, 'c4_pilots': 3, 'existing_type_non_pilot': 7, 'unimplemented_activities': 36, 'unimplemented_mechanisms': 13} | {'activities': 46, 'mechanisms': 16, 'c4_pilots': 3, 'existing_type_non_pilot': 7, 'unimplemented_activities': 36, 'unimplemented_mechanisms': 13} | PASS |

## Constats et contradictions entre sources

- **CONTRADICTION** `PLAN_CORRECTION_STATUS_EMPTY` (pages 4, 5, 6, 7, 10, 11, 12, 14, 15, 16, 17, 20, 21, 22, 24, 25, 26, 27, 30, 31, 32, 34, 35, 36, 37) : Le plan actif ne renseigne correction_status que pour 9 pages ; 25 pages ont pourtant un corrigé dans le contrôle des corrigés. Le contrôle des corrigés fait foi pour le besoin de corrigé.
- **INFO** `ACTIVITY_WITHOUT_ANSWER_ENTRY` (pages 9, 19, 29, 38) : 4 activité(s) fermée(s) absente(s) du contrôle des corrigés (aucune solution requise ou oubli à confirmer) : p.09, p.19, p.29, p.38.
- **INFO** `LEGACY_PLAN_NOT_AUTHORITATIVE` (pages 42, 45, 48, 49, 50, 55, 56) : books/halloween_2026/page_plan.csv n'est pas utilisé comme référence (migration B3-A.3 non validée) ; 7 pages y portent un type différent du plan B actif.

## Synthèse chiffrée

- Compatibilité technique, 46 activités : SUPPORTED 3 · PARTIAL 7 · UNSUPPORTED 36 · UNKNOWN 0.
- Compatibilité technique, 56 pages : SUPPORTED 3 · PARTIAL 7 · UNSUPPORTED 46 · UNKNOWN 0 (les pages hors activité sont UNSUPPORTED : aucune composition spéciale).
- État éditorial des pages : BLOCKED_BY_SOURCE 9, HUMAN_REVIEW 8, NOT_VALIDATED 39.
- Corrigés requis : 31 — BLOCKED_BY_SOURCE 31.
- Pages à revue humaine de données : p.17, p.22, p.37, p.43, p.44, p.45, p.46, p.48.
- Validations humaines enregistrées : 0 / 103 unités.

## Les 56 pages

| Page | Titre | Type de contenu | Mécanique | Compat. technique | État des sources éditoriales | Validations manquantes | Actions nécessaires |
|---:|---|---|---|---|---|---|---|
| 01 | Mon Halloween bilingue avec Pip | ouverture | front_matter | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | ÉDIT: copie d'ouverture ; VALID: revue humaine ; DEV: dév. special_layouts |
| 02 | Bienvenue dans le monde de Pip | ouverture | front_matter | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | ÉDIT: copie d'ouverture ; VALID: revue humaine ; DEV: dév. special_layouts |
| 03 | Pip reçoit une invitation | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 04 | Aide Pip à trouver la sortie | activité | maze | SUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; ÉDIT: illustration de scène |
| 05 | Qui se cache dans le jardin ? | activité | find_count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 06 | La lune mystérieuse | activité | connect_dots | SUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; ÉDIT: illustration de scène |
| 07 | L’ombre de la citrouille | activité | shadow_match | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 08 | Décore l’invitation | création libre | creative_color | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 09 | Les chemins de Pip | activité | trace_paths | UNSUPPORTED | consigne FR/EN ✓ · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 10 | Compte les chauves-souris | activité | count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 11 | Les mots de Pip | activité | match_vocabulary | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.49) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.49 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 12 | L’indice caché | activité | spot_differences | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.50) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.50 ; VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 13 | La forêt douce de la nuit | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 14 | Le chemin des étoiles | activité | maze | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.50) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.50 ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 15 | Le hibou cherche les décorations | activité | find_count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.50) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.50 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 16 | La guirlande incomplète | activité | pattern | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.50) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.50 ; VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 17 | La maison au loin | activité | connect_dots | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.50) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.50 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 18 | Le chat au grand chapeau | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 19 | Les traces du balai | activité | trace_paths | UNSUPPORTED | consigne FR/EN ✓ · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 20 | Retrouve les chapeaux jumeaux | activité | match | SUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.51) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.51 ; VALID: revue humaine ; ÉDIT: illustration de scène |
| 21 | Combien d’araignées ? | activité | count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.51) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.51 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 22 | La toile mystérieuse | activité | path_logic | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.51) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.51 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 23 | La gentille sorcière | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 24 | Le balai disparu | activité | find_count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.51) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.51 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 25 | Pip rencontre un monstre gentil | activité | maze | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.51) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.51 ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 26 | La potion des étoiles | activité | pattern | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.52) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.52 ; VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 27 | Les chapeaux des amis | activité | match | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.52) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.52 ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 28 | Le monstre souriant | création libre | creative_color | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 29 | Les invitations des amis | activité | trace_paths | UNSUPPORTED | consigne FR/EN ✓ · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 30 | Combien d’amis ? | activité | count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.52) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.52 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 31 | Retrouve les objets identiques | activité | pair_matching | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.52) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.52 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 32 | Les mots des amis | activité | match_vocabulary | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.52) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.52 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 33 | Le sac magique de Pip | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 34 | Le chemin des bonbons | activité | maze | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.53) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.53 ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 35 | Les bonbons cachés | activité | find_count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.53) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.53 ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 36 | La guirlande de friandises | activité | pattern | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.53) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.53 ; VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 37 | Range les bonbons | activité | sort | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.53) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.53 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 38 | Pip rentre à la maison | activité | trace_paths | UNSUPPORTED | consigne FR/EN ✓ · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. trace_sequence_logic ; ÉDIT: illustration de scène |
| 39 | La porte décorée | création libre | coloring | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 40 | Un bonbon pour chacun | activité | one_to_one | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.53) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.53 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 41 | Les portes mystérieuses | activité | shadow_match | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.54) · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.54 ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 42 | Décore le sac de Pip | création libre | creative_color | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 43 | Les invités arrivent | activité | maze | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.54) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.54 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 44 | La grande chasse aux objets | activité | find_count | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.54) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.54 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. count_search ; ÉDIT: illustration de scène |
| 45 | Décore les étoiles de la fête | création libre | creative_color | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre | ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 46 | Qui apporte quoi ? | activité | match | PARTIAL | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.54) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.54 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. existing_primitives ; ÉDIT: illustration de scène |
| 47 | La fête de mes rêves | création libre | creative_color | UNSUPPORTED | consigne FR/EN ✓ · sans corrigé · illustr. non vérifiable · état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. free_drawing ; ÉDIT: illustration de scène |
| 48 | Je reconnais les mots | activité | match_vocabulary | UNSUPPORTED | consigne FR/EN ✓ · solution BLOCKED_BY_SOURCE (p.54) · illustr. non vérifiable · état HUMAN_REVIEW | FR, EN, équiv., 4-5 ans, arbitre, corrigé | ÉDIT: solution → p.54 ; ÉDIT: fixer les données de la page ; VALID: revue humaine ; DEV: dév. association_sort ; ÉDIT: illustration de scène |
| 49 | Corrigés 1 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 50 | Corrigés 2 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 51 | Corrigés 3 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 52 | Corrigés 4 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 53 | Corrigés 5 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 54 | Corrigés 6 | corrigés | answers | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | VALID: revue humaine ; DEV: dév. special_layouts |
| 55 | Mini-lexique français / anglais | lexique | glossary typographique | UNSUPPORTED | état NOT_VALIDATED | FR, EN, équiv., 4-5 ans, arbitre | ÉDIT: copie de production p.55 ; VALID: revue humaine ; DEV: dév. special_layouts |
| 56 | Bravo, à bientôt avec Pip ! | diplôme/clôture | diploma + back_matter | UNSUPPORTED | état BLOCKED_BY_SOURCE | FR, EN, équiv., 4-5 ans, arbitre | ÉDIT: copie de production p.56 ; VALID: revue humaine ; DEV: dév. special_layouts |

## Blocages et dépendances par page

### p.01 — Mon Halloween bilingue avec Pip

- Blocage `BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : 1 unité(s) (P01-OPENING-TITLE) : BLOCKED_BY_SOURCE.
- Blocage `OPENING_COPY_ABSENT` (EDITORIAL_CONTENT) : 1 unité(s) (P01-OPENING-TITLE) : SOURCE_PARTIAL_TITLE_ONLY.

### p.02 — Bienvenue dans le monde de Pip

- Blocage `BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : 1 unité(s) (P02-OPENING-TITLE) : BLOCKED_BY_SOURCE.
- Blocage `OPENING_COPY_ABSENT` (EDITORIAL_CONTENT) : 1 unité(s) (P02-OPENING-TITLE) : SOURCE_PARTIAL_TITLE_ONLY.

### p.04 — Aide Pip à trouver la sortie

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)
- Dépend de : profil éditorial C4 (texte canonique non modifiable)

### p.05 — Qui se cache dans le jardin ?

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)

### p.06 — La lune mystérieuse

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)
- Dépend de : profil éditorial C4 (texte canonique non modifiable)

### p.07 — L’ombre de la citrouille

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)

### p.10 — Compte les chauves-souris

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)

### p.11 — Les mots de Pip

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.49).
- Dépend de : p.49 (mise en page du corrigé)
- Dépend de : p.55 (lexique 18 paires) et pictogrammes approuvés

### p.12 — L’indice caché

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.50).
- Dépend de : p.50 (mise en page du corrigé)

### p.14 — Le chemin des étoiles

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.50).
- Dépend de : p.50 (mise en page du corrigé)

### p.15 — Le hibou cherche les décorations

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.50).
- Dépend de : p.50 (mise en page du corrigé)

### p.16 — La guirlande incomplète

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.50).
- Dépend de : p.50 (mise en page du corrigé)

### p.17 — La maison au loin

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.50).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : L’ordre numérique, le nombre de points et la fermeture éventuelle peuvent être difficiles ou ambigus.
- Dépend de : p.50 (mise en page du corrigé)

### p.20 — Retrouve les chapeaux jumeaux

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.51).
- Dépend de : p.51 (mise en page du corrigé)
- Dépend de : profil éditorial C4 (texte canonique non modifiable)

### p.21 — Combien d’araignées ?

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.51).
- Dépend de : p.51 (mise en page du corrigé)

### p.22 — La toile mystérieuse

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.51).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : La notion de chemins qui se croisent peut être abstraite à 4 ans.
- Dépend de : p.51 (mise en page du corrigé)

### p.24 — Le balai disparu

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.51).
- Dépend de : p.51 (mise en page du corrigé)

### p.25 — Pip rencontre un monstre gentil

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.51).
- Dépend de : p.51 (mise en page du corrigé)

### p.26 — La potion des étoiles

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.52).
- Dépend de : p.52 (mise en page du corrigé)

### p.27 — Les chapeaux des amis

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.52).
- Dépend de : p.52 (mise en page du corrigé)

### p.30 — Combien d’amis ?

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.52).
- Dépend de : p.52 (mise en page du corrigé)

### p.31 — Retrouve les objets identiques

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.52).
- Dépend de : p.52 (mise en page du corrigé)

### p.32 — Les mots des amis

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.52).
- Dépend de : p.52 (mise en page du corrigé)
- Dépend de : p.55 (lexique 18 paires) et pictogrammes approuvés

### p.34 — Le chemin des bonbons

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.53).
- Dépend de : p.53 (mise en page du corrigé)

### p.35 — Les bonbons cachés

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.53).
- Dépend de : p.53 (mise en page du corrigé)

### p.36 — La guirlande de friandises

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.53).
- Dépend de : p.53 (mise en page du corrigé)

### p.37 — Range les bonbons

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.53).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Un critère de tri implicite ou fondé sur la couleur serait inaccessible en noir et blanc.
- Dépend de : p.53 (mise en page du corrigé)

### p.40 — Un bonbon pour chacun

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.53).
- Dépend de : p.53 (mise en page du corrigé)

### p.41 — Les portes mystérieuses

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.54).
- Dépend de : p.54 (mise en page du corrigé)

### p.43 — Les invités arrivent

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.54).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Plusieurs invités peuvent suggérer plusieurs départs ou parcours, ce qui n’est pas défini.
- Dépend de : p.54 (mise en page du corrigé)

### p.44 — La grande chasse aux objets

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.54).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Six cibles issues de plusieurs thèmes constituent une charge visuelle élevée pour 4 ans.
- Dépend de : p.54 (mise en page du corrigé)

### p.45 — Décore les étoiles de la fête

- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Éviter un modèle obligatoire ou un nombre d’étoiles imposé ; l’adulte peut nommer étoile / star.

### p.46 — Qui apporte quoi ?

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.54).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Des indices narratifs subtils peuvent rendre les quatre associations arbitraires.
- Dépend de : p.54 (mise en page du corrigé)

### p.48 — Je reconnais les mots

- Blocage `SOLUTION_BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : Solution et libellé de corrigé absents (p.54).
- Blocage `HUMAN_REVIEW_DATA_INSUFFICIENT` (HUMAN_VALIDATION) : Cinq ou six mots à traiter ensemble peuvent surcharger l’attention et la mémoire.
- Dépend de : p.54 (mise en page du corrigé)
- Dépend de : p.55 (lexique 18 paires) et pictogrammes approuvés

### p.49 — Corrigés 1

- Dépend de : activités sources : p.04, p.05, p.06, p.07, p.10, p.11

### p.50 — Corrigés 2

- Dépend de : activités sources : p.12, p.14, p.15, p.16, p.17

### p.51 — Corrigés 3

- Dépend de : activités sources : p.20, p.21, p.22, p.24, p.25

### p.52 — Corrigés 4

- Dépend de : activités sources : p.26, p.27, p.30, p.31, p.32

### p.53 — Corrigés 5

- Dépend de : activités sources : p.34, p.35, p.36, p.37, p.40

### p.54 — Corrigés 6

- Dépend de : activités sources : p.41, p.43, p.44, p.46, p.48

### p.55 — Mini-lexique français / anglais

- Blocage `LEXICON_PRODUCTION_COPY_ABSENT` (EDITORIAL_CONTENT) : 18 unité(s) (P55-LEX-01…P55-LEX-18) : SOURCE_COMPLETE_PAIR_MOCK_LAYOUT_ONLY.

### p.56 — Bravo, à bientôt avec Pip !

- Blocage `BLOCKED_BY_SOURCE` (EDITORIAL_CONTENT) : 6 unité(s) (P56-CONGRATULATIONS…P56-THANKS) : BLOCKED_BY_SOURCE.
- Blocage `PRODUCTION_COPY_NOT_FINAL` (EDITORIAL_CONTENT) : 6 unité(s) (P56-CONGRATULATIONS…P56-THANKS) : SOURCE_CANDIDATE_COPY_NON_PRODUCTION.

## Diagnostic technique détaillé (pages d'activité)

- **p.03 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.04 maze** — SUPPORTED : Pilote C4 couvert de bout en bout par le profil halloween-editorial-v1 (génération, vérification indépendante de la solution, rendu, corrigé).
- **p.05 find_count** — UNSUPPORTED : Mécanique 'find_count' absente du moteur (générateurs : connect_dots, match, maze). Manque : placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles ; corrigé avec repérage des cibles.
- **p.06 connect_dots** — SUPPORTED : Pilote C4 couvert de bout en bout par le profil halloween-editorial-v1 (génération, vérification indépendante de la solution, rendu, corrigé).
- **p.07 shadow_match** — UNSUPPORTED : Mécanique 'shadow_match' absente du moteur (générateurs : connect_dots, match, maze). Manque : paires silhouette/objet avec ombres distinctes ; vérificateur de bijection non triviale.
- **p.08 creative_color** — UNSUPPORTED : Mécanique 'creative_color' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de page libre (zone de création, aucune réponse attendue).
- **p.09 trace_paths** — UNSUPPORTED : Mécanique 'trace_paths' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de tracés (guides) et vérificateur de non-croisement/continuité ; corrigé graphique du tracé.
- **p.10 count** — UNSUPPORTED : Mécanique 'count' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur d'ensembles dénombrables ; réponse chiffrée vérifiée ; corrigé de type chiffre.
- **p.11 match_vocabulary** — UNSUPPORTED : Mécanique 'match_vocabulary' absente du moteur (générateurs : connect_dots, match, maze). Manque : paires mot/image lues par un adulte ; pictogrammes approuvés (p.55 sans pictogramme non approuvé) ; lien explicite avec le lexique p.55.
- **p.12 spot_differences** — UNSUPPORTED : Mécanique 'spot_differences' absente du moteur (générateurs : connect_dots, match, maze). Manque : deux scènes dérivées avec différences contrôlées ; vérificateur du nombre de différences.
- **p.13 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.14 maze** — PARTIAL : Générateur 'maze' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; scène/habillage et routage d'illustration propres à la page ; paramètre de taille/difficulté absent (grille 5x5 fixe) ; ligne de corrigé condensé p.49-54.
- **p.15 find_count** — UNSUPPORTED : Mécanique 'find_count' absente du moteur (générateurs : connect_dots, match, maze). Manque : placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles ; corrigé avec repérage des cibles.
- **p.16 pattern** — UNSUPPORTED : Mécanique 'pattern' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de suites avec élément manquant ; vérificateur de solution unique.
- **p.17 connect_dots** — PARTIAL : Générateur 'connect_dots' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Formes disponibles : house (7 pts), moon (12 pts), star (10 pts) ; le nombre de points exigé par la page n'est pas spécifié. Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; silhouette et nombre de points propres à la page non spécifiés ; ligne de corrigé condensé p.49-54. Questions : Nombre de points et silhouette attendus pour cette page ?
- **p.18 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.19 trace_paths** — UNSUPPORTED : Mécanique 'trace_paths' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de tracés (guides) et vérificateur de non-croisement/continuité ; corrigé graphique du tracé.
- **p.20 match** — SUPPORTED : Pilote C4 couvert de bout en bout par le profil halloween-editorial-v1 (génération, vérification indépendante de la solution, rendu, corrigé).
- **p.21 count** — UNSUPPORTED : Mécanique 'count' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur d'ensembles dénombrables ; réponse chiffrée vérifiée ; corrigé de type chiffre.
- **p.22 path_logic** — UNSUPPORTED : Mécanique 'path_logic' absente du moteur (générateurs : connect_dots, match, maze). Manque : graphe de chemins avec croisements maîtrisés ; vérificateur de chemin unique non croisé.
- **p.23 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.24 find_count** — UNSUPPORTED : Mécanique 'find_count' absente du moteur (générateurs : connect_dots, match, maze). Manque : placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles ; corrigé avec repérage des cibles.
- **p.25 maze** — PARTIAL : Générateur 'maze' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; scène/habillage et routage d'illustration propres à la page ; paramètre de taille/difficulté absent (grille 5x5 fixe) ; ligne de corrigé condensé p.49-54.
- **p.26 pattern** — UNSUPPORTED : Mécanique 'pattern' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de suites avec élément manquant ; vérificateur de solution unique.
- **p.27 match** — PARTIAL : Générateur 'match' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Le moteur associe des jumeaux identiques (4 paires fixes) ; la famille 'hats' n'est pas ouverte dans le registre B3-B.1. Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; ligne de corrigé condensé p.49-54 ; famille de symboles 'hats' non ouverte dans le registre (seule 'shapes' l'est).
- **p.28 creative_color** — UNSUPPORTED : Mécanique 'creative_color' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de page libre (zone de création, aucune réponse attendue).
- **p.29 trace_paths** — UNSUPPORTED : Mécanique 'trace_paths' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de tracés (guides) et vérificateur de non-croisement/continuité ; corrigé graphique du tracé.
- **p.30 count** — UNSUPPORTED : Mécanique 'count' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur d'ensembles dénombrables ; réponse chiffrée vérifiée ; corrigé de type chiffre.
- **p.31 pair_matching** — UNSUPPORTED : Mécanique 'pair_matching' absente du moteur (générateurs : connect_dots, match, maze). Manque : détection de paires identiques dans une grille d'objets ; unicité des paires.
- **p.32 match_vocabulary** — UNSUPPORTED : Mécanique 'match_vocabulary' absente du moteur (générateurs : connect_dots, match, maze). Manque : paires mot/image lues par un adulte ; pictogrammes approuvés (p.55 sans pictogramme non approuvé) ; lien explicite avec le lexique p.55.
- **p.33 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.34 maze** — PARTIAL : Générateur 'maze' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; scène/habillage et routage d'illustration propres à la page ; paramètre de taille/difficulté absent (grille 5x5 fixe) ; ligne de corrigé condensé p.49-54.
- **p.35 find_count** — UNSUPPORTED : Mécanique 'find_count' absente du moteur (générateurs : connect_dots, match, maze). Manque : placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles ; corrigé avec repérage des cibles.
- **p.36 pattern** — UNSUPPORTED : Mécanique 'pattern' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de suites avec élément manquant ; vérificateur de solution unique.
- **p.37 sort** — UNSUPPORTED : Mécanique 'sort' absente du moteur (générateurs : connect_dots, match, maze). Manque : critère de tri explicite sans couleur (noir et blanc) ; vérificateur de classification unique.
- **p.38 trace_paths** — UNSUPPORTED : Mécanique 'trace_paths' absente du moteur (générateurs : connect_dots, match, maze). Manque : générateur de tracés (guides) et vérificateur de non-croisement/continuité ; corrigé graphique du tracé.
- **p.39 coloring** — UNSUPPORTED : Mécanique 'coloring' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de coloriage (grandes zones) sur illustration au trait approuvée.
- **p.40 one_to_one** — UNSUPPORTED : Mécanique 'one_to_one' absente du moteur (générateurs : connect_dots, match, maze). Manque : correspondance terme à terme 1-5 (hétérogène) ; vérificateur de bijection.
- **p.41 shadow_match** — UNSUPPORTED : Mécanique 'shadow_match' absente du moteur (générateurs : connect_dots, match, maze). Manque : paires silhouette/objet avec ombres distinctes ; vérificateur de bijection non triviale.
- **p.42 creative_color** — UNSUPPORTED : Mécanique 'creative_color' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de page libre (zone de création, aucune réponse attendue).
- **p.43 maze** — PARTIAL : Générateur 'maze' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Exigence élevée (labyrinthe final) : aucun paramètre de taille/difficulté, grille 5x5 fixe. Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; scène/habillage et routage d'illustration propres à la page ; paramètre de taille/difficulté absent (grille 5x5 fixe) ; ligne de corrigé condensé p.49-54.
- **p.44 find_count** — UNSUPPORTED : Mécanique 'find_count' absente du moteur (générateurs : connect_dots, match, maze). Manque : placement déterministe d'objets cibles/leurres dans une scène ; vérificateur de comptage/unicité des cibles ; corrigé avec repérage des cibles.
- **p.45 creative_color** — UNSUPPORTED : Mécanique 'creative_color' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de page libre (zone de création, aucune réponse attendue).
- **p.46 match** — PARTIAL : Générateur 'match' disponible, mais la page n'est pas couverte de bout en bout (profil éditorial limité aux pages [4, 6, 20]). Le moteur associe des jumeaux identiques (4 paires fixes), non des éléments hétérogènes. Manque : liaison page de production refusée par le contrat B3-B.1 (fixtures synthétiques seulement) ; ligne de corrigé condensé p.49-54 ; association hétérogène invité→objet avec indices narratifs (le vérificateur exige des colonnes identiques).
- **p.47 creative_color** — UNSUPPORTED : Mécanique 'creative_color' absente du moteur (générateurs : connect_dots, match, maze). Manque : gabarit de page libre (zone de création, aucune réponse attendue).
- **p.48 match_vocabulary** — UNSUPPORTED : Mécanique 'match_vocabulary' absente du moteur (générateurs : connect_dots, match, maze). Manque : paires mot/image lues par un adulte ; pictogrammes approuvés (p.55 sans pictogramme non approuvé) ; lien explicite avec le lexique p.55.
