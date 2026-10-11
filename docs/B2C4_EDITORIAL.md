# B2-C4 — Profil éditorial `halloween-editorial-v1`

Correctif éditorial opt-in des trois fiches pilotes, appliqué **strictement en
aval** de la revalidation C1 et du placement C2 V2. Il ne modifie aucun mode
historique (placeholder B2-B, legacy B2-B, routage C1, placement C2 V2).

## Architecture

- `src/lafractale/editorial.py` — profil fermé, source-backed :
  - `resolve_editorial_profile` / `editorial_spec` (opt-in, profil inconnu refusé) ;
  - `transform_editorial(activity, book, profile)` — transformation statique et
    déterministe, appliquée **après** `validate_collection` historique et la
    revalidation C1 (`_routed_render_snapshot`) ;
  - `validate_editorial_activity` — délègue à `validate_activity(..., moon_len=8)`.
- `src/lafractale/quality/checks.py` — `validate_activity`/`validate_collection`
  gagnent un paramètre `moon_len` (défaut **12**, inchangé) : le croissant C4 à
  8 points passe les **mêmes** règles géométriques que la lune historique.
- `src/lafractale/layout/composition.py` — `compose_page` accepte un `editorial`
  optionnel (taille de la consigne EN 12 pt) ; sans profil, sortie historique.
- `src/lafractale/layout/pdf.py` — `write_pdf` accepte `editorial_profile` :
  transformation après revalidation C1, rendu typographique (libellé 12 pt,
  légendes 11 pt), fonds blancs, et `initialFontName` pour retirer Helvetica.

## Transformations

| Fiche | Type | Changement |
| --- | --- | --- |
| 04 | labyrinthe | scène → « Aide Pip à trouver la sortie » |
| 06 | points | lune 12 pts → croissant 8 pts (1→8, retour 1) ; consignes FR/EN explicites |
| 20 | chapeaux | scène → « Retrouve les chapeaux jumeaux » |

## Garde-fous

- Le profil exige la route C1 et le placement C2 V2 (refus sinon).
- Aucune géométrie, taille, texte ou nombre de points n'est lu depuis YAML,
  JSON, manifeste ou l'environnement ; tout est statique dans le code.
- Le moteur historique reste intact : `generate` produit toujours la lune à
  12 points, et `validate_collection` (défaut) la refuse toujours à 8 points.

## Oracles

- B2-B, B2-C1, B2-C2 : `PASS` — identité octet par octet des modes historiques.
  L'oracle B2-C2 est passé de l'identité de **source** à l'identité de **sortie**
  (le moteur évolue légitimement derrière le profil opt-in) ; la preuve de
  non-régression reste une reconstruction indépendante depuis l'arbre de
  référence, jamais depuis le moteur candidat.
- B2-C4 (`tools/verify_b2c4_oracle.py`) : démonstration de **déterminisme**,
  **isolation** et **traçabilité** sur l'arbre candidat exact. Aucune référence
  canonique C4 n'est épinglée avant validation éditoriale humaine.

## Statuts

- `B2-C4 TOOL` : en attente de fusion (PR) — jamais de fusion sans validation.
- `PREPRESS` : `WARN` conservés (les défauts restent honnêtement rapportés).
- `EDITORIAL` : `PENDING` — la validation éditoriale des 6 pages reste humaine.
- `KDP` : `FORBIDDEN` — aucune publication.
