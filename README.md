# LaFractale Studio

**Évolution V0.2-A en préparation : compagnons propres à chaque livre (non publiée, branche dédiée).** La V0.1.0 reste le tag stable.

Moteur Python expérimental et réutilisable pour cahiers d'activités jeunesse bilingues. **V0.1 réelle, limitée à une démonstration technique de 3 fiches et 3 corrigés par scénario ; aucun livre commercialisé ou finalisé.**

## Démarrage rapide
```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m lafractale validate books/halloween_2026/book.yaml
python -m lafractale build-demo books/halloween_2026/book.yaml --out dist/halloween-demo
python -m lafractale qa dist/halloween-demo --book books/halloween_2026/book.yaml
```

Le compagnon est désormais défini par `companion` dans le YAML du livre et résolu depuis `assets/companions/catalog.yaml`. Pip appartient uniquement à Halloween. Noël reste en `pending_selection` : les démos sont neutres, sans Pip ni personnage inventé, et la construction intégrale reste bloquée. Voir `docs/COMPANIONS_V0.2A.md`.

Deux scénarios : `books/halloween_2026` (56 pages dans le chemin de fer initial), `books/christmas_2026` (80 pages **prévues**, seules trois fiches démo spécifiées). Les sorties comprennent `interior.pdf`, `answer_key.pdf`, `activities.json`, `quality_report.json` / `.md`, `manifest.json` et les PNG d'aperçu dans `previews/`. Toutes les pages produites sont marquées `needs_visual_review`.

`python -m lafractale build books/halloween_2026/book.yaml` **refuse** une génération intégrale tant que toutes les mécaniques éditoriales ne sont pas implémentées. Les originaux des compagnons approuvés ne doivent jamais être régénérés ni écrasés. **Aucune publication Amazon KDP.**

Lire `START_HERE_PROMPT.md`, `MASTER_PROMPT.md`, `docs/ARCHITECTURE.md`, `docs/EDITORIAL_BIBLE.md`, `docs/QUALITY_GATES.md`, `docs/KDP_PREPRESS.md` et `docs/IMPLEMENTATION_V0.1.md` pour les exigences et les limites.


## Aperçu du livre complet (56 pages)

```bash
python -m lafractale preview books/halloween_2026 --out dist/book_preview
```
Produit `book_preview.pdf` (56 pages, marqué « APERÇU — NON DESTINÉ À LA PUBLICATION »), `contact_sheet.png`, `pages/page_NNN.png` et `report.md`. Source : `books/halloween_2026/pages.csv` (scénario B, régénérable par `tools/import_scenario_b_pages.py` mais modifiable à la main). Les pages sans gabarit sont marquées « PAGE PROVISOIRE ». Un aperçu existant n'est jamais écrasé sans `--overwrite`. Feuille de route : `roadmap/audit_et_feuille_de_route_56p.md` (dossier projet).

## V0.2-B1 : composition graphique expérimentale

La composition contrôlée sépare les zones de page de leur rendu PDF vectoriel : en-tête, scène, consignes FR/EN, espace de jeu et emplacement **vide** d'illustration à valider. La démo conserve trois mécaniques et leurs corrigés, avec vérification anti-débords et tests de rendu. Les personnages ne sont pas dessinés automatiquement : l'illustration de Pip reste **référence seulement** pour Halloween, Noël demeure sans compagnon.

Voir `docs/GRAPHIC_LAYOUT_V0.2B.md`. Aucun PDF commercial ni certification KDP ne sont générés.

## Sécurité des exports B1

Sous Linux, la V0.2-B1 consolidée exige `openat` / `O_NOFOLLOW` pour parcourir les chemins de sortie sans suivre de symlinks. `write_pdf` crée exclusivement un nouveau fichier PDF et refuse d'écraser tout fichier existant. `build_demo` prépare des artefacts dans un dossier privé et ne publie qu'une démonstration auditée. Les activités sont transmises au moteur graphique par instantané en lecture seule; les noms de personnages réservés sont contrôlés avant le manifeste. Ces contrôles ne sont **pas** une isolation contre du code Python arbitraire exécuté avec les mêmes privilèges. Voir `docs/SECURITY_OUTPUT_B1.md`.

### V0.2-B2-A : illustrations optionnelles, aucune nouvelle mascotte approuvée

Le registre indépendant `assets/illustrations/approvals.json` est initialement vide. L'intérieur reste inchangé par défaut et affiche `VISUEL À VALIDER`. Un futur visuel monochrome pour le compagnon du livre ne pourra être inséré qu'avec son ID et le hash de la révision du registre validée **hors des artefacts**. Voir [`docs/GRAPHIC_ASSETS_B2A.md`](docs/GRAPHIC_ASSETS_B2A.md) et [`docs/SECURITY_CONTRACT_V0.2B2.md`](docs/SECURITY_CONTRACT_V0.2B2.md).
