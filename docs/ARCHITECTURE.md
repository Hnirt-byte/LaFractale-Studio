# Architecture cible du logiciel

- Python 3.11+ ; CLI V0.1 implémentée : `lafractale validate|build-demo|build|qa`.
- `src/lafractale/config/` : modèles et validation de schémas, erreurs explicites.
- `src/lafractale/activities/` : API `generate(spec, seed)->Activity` et `validate(activity)->ValidationResult`. Modèle contient `id`, `type`, `age_band`, `prompt_fr`, `prompt_en`, `scene`, `assets`, `geometry`, `answer`, `seed`.
- `src/lafractale/story/` : transitions, scènes et vérifications de progression sans répétition de scènes.
- `src/lafractale/assets/` : registres avec checksum, validité, résolution et approbation. Pas d'altération automatique des originaux.
- `src/lafractale/config/companions.py` + `assets/companions/catalog.yaml` : compagnons indépendants par livre, références SHA-256, exclusivité `allowed_book_ids`, statut `pending_selection` autorisé en démo neutre uniquement.
- `src/lafractale/layout/` : rendu typographique et graphiques vectoriels via ReportLab ou équivalent, conservation de marges.
- `src/lafractale/export/` : intérieur, corrigés, aperçus, manifest.
- `src/lafractale/quality/` : test de géométrie, unicité, vocabulaire, overflow, pagination, assets, contrôle humain à l'état `pending`.
- `tests/` : unitaires et intégration, fixtures reproductibles. GitHub Actions exécute pytest, validation, génération courte et QA en CI sans secrets.

## Principes
- Séparer strictement `ActivitySpec`, `ActivityData`, `SceneComposition` et `PageRender`. Une activité doit être testable sans créer une illustration.
- Éviter les heuristiques sur des nombres d'objets cachés dans une image IA : générer ou placer explicitement des objets comptables à partir d'une liste.
- Un changement de seed doit changer le jeu, mais la même seed avec la même version du moteur doit reproduire le même résultat.
- Les anti-doublons combinent règles du plan + hash des données + similarité graphique signalée pour revue (ne pas prétendre détecter toutes les ressemblances automatiquement).
- Assets requis absents = statut bloquant, jamais placeholder silencieux dans un livre final.

## Interfaces minimales attendues
`python -m lafractale validate books/halloween_2026/book.yaml`
`python -m lafractale build-demo books/halloween_2026/book.yaml --out dist/demo`
`python -m pytest -q`
Ces interfaces sont opérationnelles dans la V0.1 et restent prises en charge en V0.2-A.

## Git
Branches de fonctionnalité + PR ; aucun secret ; `.gitignore` pour outputs lourds, caches, `.env`; inclure quelques fixtures/aperçus de référence raisonnables. Versions et changelog.
