# Changelog

## [0.2.0a4] — Profils canoniques et provenance de source (non fusionné)
- Vérification de **tous** les champs du profil `pending_selection`, même après `dataclasses.replace()` ; aucune exemption de nom ni rendu quand aucun compagnon n'est choisi.
- Liaison entre objet `Book` et contenu YAML/plan original, avec empreintes et comparaison directe des données rechargées, pour bloquer le transfert croisé de profils entre livres.
- Démonstration générée dans un répertoire de préparation temporaire ; seul un ensemble d'artefacts vérifié est transféré vers le dossier de sortie.
- Tests adversariaux : falsification des champs du profil, des statuts, du livre et de ses empreintes en mémoire, YAML modifié, injection pendant le rendu et protection de la dernière démo valide.


## [0.2.0a3] — Catalogue figé pour tous les statuts
- Empreinte SHA-256 brute et noms réservés capturés au chargement, y compris `pending_selection`.
- Contrôles d'intégrité avant rendu, registre et manifeste ; toute modification ultérieure du catalogue entraîne un refus.
- Tests adversariaux pour suppression post-chargement de Pip, édition cosmétique du catalogue, modification en cours de génération et effet sur les livres approuvés.

## [0.2.0a2] — Correctif de sécurité sur la V0.2-A
- Résolution stricte des chemins du catalogue/compagnons (namespace, symlinks parent).
- Contrôle d’intégrité au moment de l’utilisation et contrôle des noms de personnages dans toutes les données éditoriales.
- Tests adversariaux ajoutés suite à la revue indépendante Hermes.

## [0.2.0a1] - Développement local non fusionné
- Compagnons propres à chaque livre, catalogue SHA-256 et restriction par `allowed_book_ids`.
- Pip réservé à Halloween, Noël sans compagnon en attendant validation éditoriale.
- Consignes et en-têtes de démo sans Pip codé en dur ; manifeste et QA indiquent le statut du compagnon.
- Suite de tests renforcée : contrôle des affectations croisées et intégrité des assets.
- Aucun livre final ni illustration nouvelle.


## 0.1.0 - 2026-10-08
- Première démo reproductible avec validation YAML, maze/match/connect_dots vérifiables, PDF et corrigés, rapport de qualité, manifest, aperçus et tests automatisés.
- Échafaudage Christmas 80 pages, sans fabrication de fausses pages.
- Aucune version finale KDP ; uniquement des aperçus de démonstration.
