# LaFractale Studio

**Évolution V0.2-A en préparation : compagnons propres à chaque livre (non publiée, branche dédiée).** La V0.1.0 reste le tag stable.

Moteur Python expérimental et réutilisable pour cahiers d'activités jeunesse bilingues. **V0.1 réelle, limitée à une démonstration technique de 3 fiches et 3 corrigés par scénario ; aucun livre commercialisé ou finalisé.**

## Démarrage rapide
```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m lafractale validate books/halloween_2026/book.yaml
python -m lafractale build-demo books/halloween_2026/book.yaml --out dist/halloween-demo
python -m lafractale qa dist/halloween-demo
```

Le compagnon est désormais défini par `companion` dans le YAML du livre et résolu depuis `assets/companions/catalog.yaml`. Pip appartient uniquement à Halloween. Noël reste en `pending_selection` : les démos sont neutres, sans Pip ni personnage inventé, et la construction intégrale reste bloquée. Voir `docs/COMPANIONS_V0.2A.md`.

Deux scénarios : `books/halloween_2026` (56 pages dans le chemin de fer initial), `books/christmas_2026` (80 pages **prévues**, seules trois fiches démo spécifiées). Les sorties comprennent `interior.pdf`, `answer_key.pdf`, `activities.json`, `quality_report.json` / `.md`, `manifest.json` et les PNG d'aperçu dans `previews/`. Toutes les pages produites sont marquées `needs_visual_review`.

`python -m lafractale build books/halloween_2026/book.yaml` **refuse** une génération intégrale tant que toutes les mécaniques éditoriales ne sont pas implémentées. Les originaux des compagnons approuvés ne doivent jamais être régénérés ni écrasés. **Aucune publication Amazon KDP.**

Lire `START_HERE_PROMPT.md`, `MASTER_PROMPT.md`, `docs/ARCHITECTURE.md`, `docs/EDITORIAL_BIBLE.md`, `docs/QUALITY_GATES.md`, `docs/KDP_PREPRESS.md` et `docs/IMPLEMENTATION_V0.1.md` pour les exigences et les limites.
