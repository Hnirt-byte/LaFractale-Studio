# LaFractale Studio V0.2-B1 : composition graphique contrôlée

## Objet

Ce lot améliore **uniquement la démo technique de trois fiches par livre**. Il ne construit **ni livre complet, ni fichier KDP prêt à publier**. Le socle compagnon sécurisé `v0.2.0a4` est conservé sans modification fonctionnelle.

## Architecture

- `src/lafractale/layout/composition.py` : modèle immuable `Rect`, `TextBlock`, `PageComposition`, construction de zones et contrôle d'inclusion/non-chevauchement. Aucun dessin PDF dans ce module.
- `src/lafractale/layout/pdf.py` : rendu de la composition en primitives vectorielles monochromes ReportLab et trois mécaniques existantes, sans génération de nouveaux assets.
- `tests/test_layout.py` : tests de marges, non-chevauchement, textes trop longs, étiquettes de points, anti-divulgation Noël, absence d'illustration non approuvée et conservation d'une démo antérieure après échec de rendu.

## Décisions graphiques

- Prototype limité au format 8.5 x 11 pouces ou **supérieur** ; les petits formats sont explicitement refusés jusqu'à la prise en charge de gabarits spécifiques.
- Bords, titres, zones de consignes, espace de jeu et pagination composés de manière déterministe.
- Emplacement illustratif **réservé et identifié comme non validé**. Il n'est pas rempli avec Pip : sa référence couleur n'est pas une variante noir et blanc approuvée.
- Noël demeure `pending_selection`, aucun compagnon ajouté ou mentionné.
- Le jeu « points à relier » affiche les numéros, mais ne révèle plus automatiquement « Forme : lune / étoile / maison » en bas de la fiche. La scène du livre demeure celle du chemin de fer validé, même lorsqu'elle nomme la forme.
- Les mêmes données géométriques restent à la source des exercices et des corrigés. Les règles de validation précédentes restent obligatoires.
- Les textes trop longs entraînent un échec ; jamais de troncature silencieuse.

## Qualité et limites

Le validateur de composition contrôle les **rectangles logiques** et leur contenu mesuré. Les tests de PDF inspectent les blocs de texte et les pages rendues. Cette validation ne prouve pas automatiquement l'accessibilité 4–5 ans ni l'absence de toute collision au niveau des traits vectoriels. La revue humaine reste obligatoire.

Les marges sont provisoires et ne représentent pas une certification KDP. Absence volontaire de couverture, fond perdu, calcul de dos, export final, dessin du compagnon et variante monochrome de Pip. Ne pas retirer les refus de génération intégrale ni le statut `needs_visual_review`.

## Intégration

Base exacte : `v0.2.0a4`, commit `10657af751a24858e0978bb5a2e4274ec91b76d6`.

Branche suggérée : `feat/studio-v0.2b-layout`.

Commandes attendues (environnement disposant de Python >= 3.11 et DejaVu Sans TTF) :

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
python -m lafractale validate books/halloween_2026/book.yaml
python -m lafractale validate books/christmas_2026/book.yaml
SOURCE_DATE_EPOCH=1780000000 python -m lafractale build-demo books/halloween_2026/book.yaml --out dist/halloween
python -m lafractale qa dist/halloween --book books/halloween_2026/book.yaml
SOURCE_DATE_EPOCH=1780000000 python -m lafractale build-demo books/christmas_2026/book.yaml --out dist/christmas
python -m lafractale qa dist/christmas --book books/christmas_2026/book.yaml
```

Comparer visuellement **toutes** les fiches/corrigés, y compris les numéros autour des points à relier. Un résultat CI vert ne remplace pas la validation des visuels.
