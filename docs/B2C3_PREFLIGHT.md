# B2-C3 — Préflight prépresse read-only et dossier de revue éditoriale

Outil de **diagnostic opt-in en lecture seule** (`tools/preflight_b2c3.py`) sur les
six pages de la démonstration Halloween C2 V2 (3 fiches + 3 corrigés, politique
`halloween-pip-placement-v2`, pose `intro_right`). Il ne modifie jamais les PDF,
les textes, les activités, les assets Pip, `book.yaml`, `page_plan.csv`, le
registre d'approbation ni les sorties C2. La QA C2 historique s'exécute d'abord ;
un échec QA est un BLOCKER et interrompt l'analyse.

## Statuts de décision (distincts)

- `PASS_DIAGNOSTIC_TECHNIQUE` / `FAIL_DIAGNOSTIC_TECHNIQUE` : qualité de l'outil.
- `PREPRESS_PASS` / `WARN` / `FAIL` / `NOT_EVALUABLE` : état des pages, par contrôle.
- `APPROBATION_EDITORIALE = PENDING` : validation humaine de la grille 6 pages.
- `KDP_READY = FORBIDDEN` : la démo (3 pages) n'est pas un manuscrit soumissible.

## Faits KDP (recroisés le 2026-10-10, sources officielles)

- Trim 8,5 × 11 po = 612 × 792 pt ; avec fond perdu 621 × 810 pt (+0,125/+0,25 po).
- Marge gouttière 24–150 pages ≥ 0,375 po = 27 pt ; marge extérieure ≥ 0,25 po
  (18 pt) sans fond perdu, ≥ 0,375 po (27 pt) avec.
- Images ≥ 300 DPI ; polices ≥ 7 pt et intégrées ; traits ≥ 0,75 pt (recommandé) ;
  fonds gris ≥ 10 % d'encre (recommandé).
- Sources :
  - https://kdp.amazon.com/fr_FR/help/topic/GVBQ3CMEQW3W2VL6
  - https://kdp.amazon.com/fr_FR/help/topic/G201857950
  - https://kdp.amazon.com/fr_FR/help/topic/G201834180

Le fond perdu (`bleed: to_be_confirmed`) n'est **pas** tranché : l'analyseur
déclare la compatibilité du PDF avec les deux enveloppes, sans choisir.

## Invariants

- Le moteur `src/lafractale` est **inchangé** ; l'oracle C2 V2 le vérifie et
  atteste la sortie placée V2 byte-identique à la référence `e9b8036…`.
- Aucun test historique supprimé ou mis en `skip` ; les nouveaux cas s'ajoutent.
- `publication_approved`, `ready_for_kdp`, homologation Amazon : interdits.
