# Livraison LaFractale Studio V0.1

- Date : 2026-10-08
- Dépôt distant : `Hnirt-byte/LaFractale-Studio`.
- Accès GitHub confirmé : compte `Hnirt-byte`, permission `ADMIN`, dépôt public avec branche par défaut `main` initialement vide.
- Initialisation distante : `main` contient le commit de bootstrap `chore: initialize repository`.
- Intégration V0.1 : sources de l'archive importées dans `feat/studio-v0.1`, sans métadonnées Git provenant du ZIP.
- Exécution vérifiée dans un environnement virtuel Python 3.13.5 : `python -m pip install -e '.[dev]'`, **38/38 tests OK**, validations CLI Halloween/Noël, générations de démo et QA OK.
- Déterminisme confirmé avec seed et `SOURCE_DATE_EPOCH` identiques ; PDF, JSON et manifestes byte-identiques.
- Démos conservées localement et ignorées par Git : `dist/halloween-demo/` et `dist/christmas-demo/` ; 3 fiches + 3 corrigés chacun. **Non publiables.**
- Assemblage intégral : volontairement refusé avec code de retour 2 ; aucun livre Halloween de 56 pages ni livre Noël de 80 pages n'est créé artificiellement.
- L'asset officiel de Pip est inchangé et son SHA-256 est vérifié.
- Pull request : à ouvrir de `feat/studio-v0.1` vers `main` après le push, avec `docs/PULL_REQUEST_DRAFT.md` comme description actualisée.

## Limites maintenues

- Aucune publication Amazon KDP.
- Aucun statut KDP-ready.
- Aucun Pip régénéré, modifié ou remplacé.
- Revue humaine obligatoire : lisibilité 4–5 ans, fidélité de Pip, droits des assets, règles KDP, aperçu KDP et épreuve papier.
