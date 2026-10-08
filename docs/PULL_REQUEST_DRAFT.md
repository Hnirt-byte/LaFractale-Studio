# Pull request — LaFractale Studio V0.1

**Base :** `main`
**Head :** `feat/studio-v0.1`
**Titre :** `feat: LaFractale Studio v0.1 - deterministic activity demo engine`

## Résumé
- Validation YAML des livres et chemin de fer Halloween à 56 pages prévues.
- Second scénario de configuration Noël à 80 pages prévues, sans création de pages factices.
- Trois exercices structurés et vérifiables : labyrinthe avec BFS, associations bijectives chapeaux/cadeaux, et points à relier avec lune fermée 1..12.
- PDF de démonstration par scénario : 3 fiches, 3 corrigés, aperçus PNG, rapport qualité et manifeste hashé.
- Asset officiel de Pip préservé et inventorié : aucun nouveau Pip, aucune variante N&B non approuvée.
- Refus explicite de l'assemblage intégral et de toute revendication de préparation KDP.
- Audit QA durci : manifeste limité aux artefacts de démonstration attendus, chemins traversants et symlinks rejetés, JSON malformé signalé proprement.
- Validation renforcée des scénarios de démonstration malformés, avec erreurs contrôlées.

## Vérifications exécutées le 8 octobre 2026
- Environnement isolé : Python 3.13.5, `python -m pip install -e '.[dev]'`.
- `python -m pytest -q` : **38 passed, 0 failed**.
- Validation YAML Halloween et Noël : OK.
- `build-demo` et `qa` pour les deux scénarios : OK.
- Déterminisme : deux builds Halloween avec la même seed et `SOURCE_DATE_EPOCH` ont produit des PDF, JSON et manifestes byte-identiques.
- Audit PDF : `interior.pdf` et `answer_key.pdf` pour Halloween et Noël sont lisibles, contiennent 3 pages, du texte et des fontes, et ne sont pas chiffrés.
- `build` intégral Halloween : refus attendu, code de retour 2 ; aucun PDF complet créé.
- Intégrité de l'asset officiel Pip : SHA-256 inchangé (`b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`).

## Points de revue manuelle
- Lisibilité 4–5 ans, rendu complet de la lune et des chapeaux.
- Graphisme narratif absent : Pip n'est pas dessiné dans les pages de démonstration.
- Autorisations des assets, règles KDP de production, aperçu KDP et épreuve papier.
- La CI GitHub Actions doit être revue avant toute fusion.

**Aucune publication Amazon KDP n'est effectuée. Ne pas fusionner automatiquement.**
