## V0.2-B1 Unicode hardening (prérequis à la PR)

- Contrat de sécurité versionné, une seule politique Unicode appliquée à la lecture,
  aux plans et données générées, aux PDF extraits, aux JSON et à la QA Markdown.
- Rejet NFKC non canonique, caractères invisibles/de format et homoglyphes hors
  alphabet éditorial FR/EN. Empreintes des noms réservés dans le manifeste
  sans divulguer le nom Pip dans les sorties Noël.
- Nouvelle matrice de tests adversariaux : YAML, CSV, catalogue, générateur,
  rendu, JSON altéré et conservation des générations précédentes.
- Aucun changement de mécanique d'activité ou d'illustration officielle.

# Changelog

## [B3-B.2] - Lecteur en lecture seule du scénario B
- Nouveau paquet isolé `lafractale.scenario_b` : analyse des sources B3-A.3/B3-A.4 actives, capacités réelles du moteur, blocages éditoriaux, rapport JSON/Markdown déterministe et synthèse des développements (voir `docs/B3B2_SCENARIO_B_READER.md`).
- Aucun fichier éditorial, asset, générateur ou moteur de production modifié ; aucune génération PDF ; statuts permanents inchangés.

## [0.2.0b1, hotfix rollback pré-PR] - Préservation des sauvegardes sur double échec
- Le dernier export valide n'est plus effacé lorsque publication et restauration échouent toutes deux : sauvegarde `.demo.previous-*` conservée et accessible via `PublicationRecoveryError.backup_path`.
- Suppression de la sauvegarde uniquement après publication confirmée. Une restauration réussie replace l'ancienne démo sans destruction.
- `parent_dirfd` ne transforme plus les erreurs d'E/S de la fonction appelante en erreurs de chemin : `UnsafeOutputPath` est réservé à la validation des composants.
- Six tests adversariaux supplémentaires avec injection de défaillances `os.replace`, dont un double échec exact ; documentation de récupération et limites de crash OS.

## [0.2.0b1, hardening pré-PR] - Fermeture des trois contournements B1
- Sortie sécurisée sur Linux : traversée des parents via descripteurs `openat`, `O_DIRECTORY|O_NOFOLLOW`, staging créé sous un parent ancré et remplacement avec `dir_fd`.
- `write_pdf()` n'ouvre plus une chaîne de chemin ReportLab en écriture : fichier régulier créé exclusivement (`O_CREAT|O_EXCL|O_NOFOLLOW`) via un flux pré-ouvert, supprimé en cas d'échec.
- Composition et dessin reçoivent des copies profondes figées des activités; vérification des sources et exclusion des noms de compagnons interdits avant publication du manifeste.
- Tests indépendants des symlinks parents/feuilles, de l'écrasement de cible externe, de la mutation après composition et de l'injection directe de texte dans le PDF.
- Ne constitue pas un bac à sable contre un programme Python malveillant ayant le même UID. Voir `docs/SECURITY_OUTPUT_B1.md`.

## [0.2.0b1] - Prototype de composition graphique V0.2-B1, non publiable
- `PageComposition` immuable et rectangles de contenu validés avant rendu.
- PDF monochrome à zones lisibles, dessins des trois jeux conservés en vectoriel.
- Slot compagnon volontairement vide; aucune variante non approuvée de Pip.
- Suppression du libellé automatique « Forme : ... » des points à relier.
- 14 tests de rendu, sécurité des marges et atomicité d'export ajoutés.


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

## V0.2-B1, hotfix lexical/QA-root (non intégré)

- Délimitation de noms compagnons sur les seules lettres de l'alphabet éditorial,
  indépendamment des chiffres et underscores (fini le bypass via `\\w+`).
- Rejet explicite des marques combinantes Unicode `Mn`, `Mc`, `Me`.
- Audit via FD de racine et `O_NOFOLLOW` : refus des symlinks du chemin d'audit,
  y compris la racine et les parents, sans résoudre le chemin non fiable.
- Matrice adversariale ajoutée : YAML, JSON, Markdown, manifeste, PDF réels,
  checksums recalculés, tests CLI et conservation des démos valides.
- Statut : maquette technique, non publiable sur Amazon KDP.


### Correctif B2-A : frontière JSON stricte (pré-PR)
- Parsing partagé qui refuse les clés dupliquées récursivement pour le
  manifeste, les activités, les rapports qualité et le registre d'approbation.
- Rejet des clés échappées équivalentes, des nombres non finis, des chaînes
  Unicode invalides et des documents trop profondément imbriqués.
- Aucun changement aux visuels ni à la logique des jeux ; QA sans confiance
  dans les checksums internes des sorties.
