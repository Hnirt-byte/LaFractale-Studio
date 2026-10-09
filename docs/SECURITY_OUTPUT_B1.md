# Sécurité des écritures et du rendu V0.2-B1

## Périmètre de confiance

- Entrées non fiables : chemin de destination fourni au CLI, parents et feuilles symlinkés, structures d'activités mutables transmises au moteur PDF.
- Entrées contrôlées : code Python source, environnement et bibliothèques installées. Ce système ne permet pas l'exécution isolée de plugins Python non fiables.
- Déploiement testé : Linux. La sécurisation utilise `os.open(..., dir_fd=...)`, `O_NOFOLLOW` et `/proc/self/fd` ; Windows/macOS ne sont pas certifiés.

## Mesures techniques

1. Parcours parent du chemin de sortie depuis `/` au moyen de `O_DIRECTORY|O_NOFOLLOW`, avec descripteur ancré pour `mkdir` et `replace`. Un symlink dans n'importe quel parent provoque un refus avant l'export.
2. Fichier PDF bas niveau créé **uniquement s'il est absent** via `O_CREAT|O_EXCL|O_NOFOLLOW`, avec flux pré-ouvert transmis à ReportLab. Ne jamais utiliser cette API pour écraser un PDF existant. Nettoyage du PDF partiel en cas d'exception.
3. Répertoire de staging privé, audit des sorties et renommages ancrés au descripteur parent. La démo précédente passe temporairement en sauvegarde `.demo.previous-<nonce>` lors d'un remplacement. Si la publication échoue, le programme tente de restaurer la sauvegarde. **En cas de double échec publication + restauration, la sauvegarde n'est jamais effacée** : `PublicationRecoveryError.backup_path` donne son emplacement. Le chemin public `demo/` peut alors être absent, mais les PDF et le manifeste précédents demeurent dans la sauvegarde pour récupération manuelle.
4. Chaque activité est profondément copiée puis figée (`MappingProxyType`, tuples). `compose_page` et les fonctions de dessin n'ont plus accès à des conteneurs de géométrie mutables. La sérialisation `activities.json` part d'un instantané validé distinct de l'entrée du renderer.
5. En complément, les PDF sont relus pour rejeter les noms de compagnons interdits, avant écriture du manifeste de réussite.
6. `UnsafeOutputPath` ne signale que des défauts de chemin/symlink détectés pendant le parcours sécurisé. Les erreurs d'E/S produites **dans** le `with parent_dirfd(...)` sont propagées avec leur origine ; publication et restauration ont des erreurs spécifiques (`PublicationError` et `PublicationRecoveryError`).

## Vérifications

`PYTHONPATH=src python -m pytest -q tests/test_security_output_v02b.py` puis suite complète. Vérifier les quatre fichiers byte-identiques sur deux runs avec `SOURCE_DATE_EPOCH` identique. Vérifier que `PIP-INJECTED` ne peut apparaître dans les PDF, JSON et manifestes Noël.

Tests de reprise : `PYTHONPATH=src python -m pytest -q tests/test_publication_rollback_v02b.py`. Ils injectent indépendamment un échec de publication, un échec de restauration, puis les deux simultanément. En double échec, vérifier la présence de la sauvegarde valide, de `manifest.json`, l'absence de destruction de cette sauvegarde et l'exception explicite.

Récupération après double échec : **arrêter les builds sur cette destination**. Ne pas supprimer ni réutiliser la sauvegarde. Vérifier son `manifest.json` et son QA, puis restaurer **manuellement** sur un chemin contrôlé après résolution de la cause d'E/S ; refaire l'audit. Il n'existe pas de réparation automatique silencieuse.

## Limites explicites

- Un attaquant capable d'exécuter/modifier arbitrairement du code Python avec le **même UID** que le moteur peut manipuler les fonctions de rendu, descripteurs ou répertoires. Ce cas exige un processus isolé, droits minimaux, sources en lecture seule et éventuellement une sandbox dédiée.
- Un acteur ayant des droits d'écriture concurrents sur les mêmes répertoires ne doit pas être considéré comme un simple utilisateur de l'API. Empêcher toutes les courses entre processus sous le même UID requiert une politique d'accès OS et une architecture d'exécution contrôlée.
- Les renommages protègent contre les exceptions d'E/S simulées, pas contre une coupure d'alimentation ou une perte de persistance du système de fichiers. Une garantie de reprise après crash OS requiert une conception transactionnelle avec synchronisation durable (`fsync`) et journal de récupération.
- Un audit PDF automatisé (texte, fontes, hash) ne remplace pas une revue visuelle ni une certification KDP.
- Les noms interdits sont contrôlés dans le texte extrait; la recherche n'identifie pas un nom incorporé uniquement dans des pixels ou chemins vectoriels.

## Complément Unicode B1

Le contrat `docs/SECURITY_CONTRACT_V0.2B1.md` décrit maintenant les règles Unicode, leur application aux fichiers éditoriaux et PDF/JSON/Markdown, les tests adversariaux et les critères de revue.
