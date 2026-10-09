# V0.1 implémentée, limites et mode opératoire

## Pré-requis
Python >=3.11, `pip install -e '.[dev]'`. Exports PDF via ReportLab et aperçus avec PyMuPDF. Police TTF DejaVu Sans à installer localement (défaut `/usr/share/fonts/truetype/dejavu/`), sinon définir `LAFRACTALE_FONT_PATH` et `LAFRACTALE_FONT_BOLD_PATH`. Aucune police n'est redistribuée.

## Exécution
```bash
python -m lafractale validate books/halloween_2026/book.yaml
python -m lafractale build-demo books/halloween_2026/book.yaml --out dist/halloween-demo --seed 2026
python -m lafractale qa dist/halloween-demo --book books/halloween_2026/book.yaml
python -m lafractale validate books/christmas_2026/book.yaml
python -m lafractale build-demo books/christmas_2026/book.yaml --out dist/christmas-demo
python -m lafractale qa dist/christmas-demo --book books/christmas_2026/book.yaml
python -m pytest -q
```

`build` bloque volontairement tous les cahiers intégraux tant que les types et mises en page éditoriales ne sont pas développés. Ni Halloween 56 pages ni Noël 80 pages ne sont créés artificiellement.

## Garantie logique
- Une seed d'activité repose sur SHA256(version + book_id + activity_id + seed utilisateur) : stabilité entre processus Python.
- Le labyrinthe est généré par parcours aléatoire couvrant les cellules, réponse calculée par BFS, validée par recomputation.
- L'association possède quatre symboles visuels distincts; ordre mélangé, clé bijective, validation de correspondance.
- Les points à relier utilisent des contours vectoriels fermés (lune canonique 12 points, étoile, maison), des coordonnées normalisées et un corrigé composé par le moteur. Test de numérotation, de fermeture, de surface, de concavité lunaire, de segments, de croisements.
- Contrôles collection : unicité IDs, numéros de pages, seeds, fingerprints, scènes et mécanique consécutive.
- `SOURCE_DATE_EPOCH` permet des métadonnées reproductibles; PDF ReportLab `invariant=1`.

## Provenance et graphisme
`assets/characters/pip/pip_officiel_couleur.png` reste **intact**, hashé au manifeste, état `APPROVED_REFERENCE`. Aucune nouvelle posture et aucun nouveau fantôme n'ont été inventés. Pip n'est **pas dessiné** sur les pages techniques : une variante B&W officielle doit encore être préparée, inspectée et approuvée. `rights: UNVERIFIED` implique une revue humaine avant commercialisation. Le jeu reste en vecteurs noirs sur blanc.

## Interdictions, limites et backlog
- **Aucune publication KDP.** Les PDF sont des maquettes de démonstration et non des intérieurs commercialisables.
- Pages non réalisées : couverture, scènes illustrées, coloriage, cherche-et-trouve, comptage, différences, diplômes, lexique, layouts spécifiques, cohérence narrative intégrale.
- Contrôles humains obligatoires : silhouette lunaire, numéros lisibles et non chevauchés, consignes adaptées aux 4–5 ans, relecture bilingue, fidélité au personnage, pagination KDP et épreuve.
- Contrôles de prépresse non encore implémentés : marges de reliure selon pagination réelle, fonds perdus, conformité noir et blanc, effective PPI pour illustrations, previewer KDP.
- La détection d'images quasi identiques est un **signalement futur** et non une validation logicielle acquise.
