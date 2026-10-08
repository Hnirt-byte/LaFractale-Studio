# Livraison V0.2-A — Découplage des compagnons

Source de base : tag v0.1.0, commit `4ce3db85ad34351d72bd18d45cb060cfd7668168`.
Version de travail (non taguée / non fusionnée) : `0.2.0a4`.

## Modifications clés
- Catalogue central `assets/companions/catalog.yaml` avec Pip autorisé uniquement pour Halloween, référence officielle SHA-256 verrouillée.
- Configurations `companion` par livre : Halloween = Pip ; Noël = `pending_selection`.
- Modèles, consignes, en-têtes PDF, registres, manifestes et QA sans dépendance globale à Pip.
- Rejet explicite des anciens champs `mascot`, des personnages hors livre autorisé et des références modifiées ou hors dossier.
- `build` refuse toujours tous les livres non finalisés et signale le compagnon manquant pour Noël.
- Aucune nouvelle illustration, aucun livre commercialisable, aucune publication Amazon KDP.

## Revue de sécurité Hermes (correctifs 0.2.0a2 + 0.2.0a3)
- Traversée `../` et échappement de namespace rejetés avant toute normalisation.
- Lecture du catalogue et des ressources approuvées sous Linux avec `openat` / `O_NOFOLLOW` sur chaque composant, liens symboliques de parents compris.
- Intégrité SHA-256 et état du catalogue revérifiés au moment du registre puis juste avant le manifeste.
- Tout texte éditorial utilisant un personnage non sélectionné est bloqué, même avec `pending_selection`, y compris scènes YAML et chemin de fer CSV.
- Le catalogue est lié à chaque livre par SHA-256 des octets + liste figée des identités réservées, même si `companion.status` vaut `pending_selection`. L'état est revérifié avant la production et immédiatement avant le manifeste.
- Contournement V0.2-A 0.2.0a2 confirmé par Hermes (suppression de Pip après `load_book` puis injection dans scène Noël) désormais bloqué avant PDF.
- Test de modification mid-build, symlink après chargement et injection pendant rendu inclus. Aucun changement graphique aux PDF.
- Plateforme d’exécution de ce garde-fou : Linux/POSIX avec `dir_fd` et `O_NOFOLLOW` (échec explicite si non disponible).

## Revue complémentaire 0.2.0a4
- Reproduction de la troisième attaque Hermes avant correction : `dataclasses.replace(book.companion, name="Pip")` autorisait réellement le rendu et son manifeste ; profil canonique obligatoire maintenant.
- Autre contournement découvert pendant l'audit : réutiliser le profil Halloween dans un objet Noël dont le `book_id` et la déclaration `companion` sont falsifiés en mémoire. Le chargement de source est désormais lié aux octets YAML et aux données exactes du plan, contrôlés à nouveau avant rendu et avant publication de la démo.
- Contrôle des noms réservés aussi dans les clés de tables éditoriales, pas seulement dans les valeurs.
- Les artefacts sont d'abord produits et vérifiés dans un répertoire temporaire privé ; une mutation pendant le rendu ne publie plus de PDF partiel dans `dist/`. Si une démo valide existait déjà, elle est préservée.
- Les objets Python internes ne sont **pas** des attestations de sécurité. Un code arbitraire exécuté avec les privilèges du processus pourrait toujours contourner les contrôles, d'où la recommandation d'un workspace isolé en lecture seule en environnement hostile.

## Validation locale
- Python 3.11+ visé, exécuté localement sous la version disponible du runtime.
- `python -m pip install --no-build-isolation -e ".[dev]"` : succès.
- `python -m pytest -q` : 85 passed (0 échec).
- `python -m lafractale validate` : Halloween et Noël OK.
- `python -m lafractale build-demo` puis `qa` : 2 scénarios OK.
- PDF : chacun 3 exercices / 3 corrigés. Noël sans « Pip » dans les textes PDF et JSON.
- `python -m lafractale build books/christmas_2026/book.yaml` : refus attendu (companion pending + plan manquant).
- Vérification visuelle : premières pages rendues, démos techniques non finalisées.

## Intégration Hermes
1. Sur le dépôt distant, vérifier que le SHA `main` est bien celui livré ou inspecter toute modification éventuelle.
2. Créer une branche `feat/studio-v0.2a-companions` depuis `main`, ne pas éditer `main` directement.
3. Si V0.2-A + les deux premiers hotfix sont déjà dans le working tree sans commit, appliquer **uniquement** `LaFractale-Studio-v0.2A-hotfix3.patch` après `git apply --check`. Si le working tree est propre sur v0.1.0, utiliser **uniquement** `LaFractale-Studio-v0.2A-v4-full.patch`. Ne jamais appliquer les deux. Le ZIP source complet est un secours, pas une invitation à remplacer le repo aveuglément.
4. Installer les dépendances dans un environnement isolé, lancer pytest, valider les 2 YAML, construire et auditer les 2 démos.
5. Vérifier `assets/characters/pip/pip_officiel_couleur.png` : SHA-256 `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`.
6. Vérifier par extraction texte et inspection que Pip n'apparaît dans aucune démo Noël.
7. Pousser une branche et ouvrir une PR **non fusionnée**, fournir le lien, SHA et logs CI.

Cette V0.2-A n'inclut ni moteur graphique V0.2-B ni compagnon Noël approuvé.

## Limitation du modèle de menace
Les contrôles détectent les modifications persistantes entre chargement, rendu et finalisation. Ils ne fournissent pas une transaction atomique contre des écritures concurrentes sous contrôle d'un adversaire, ni contre une modification suivie d'une restauration bit à bit entre deux vérifications. Pour une production hostile multi-utilisateurs, isoler le workspace en lecture seule avant traitement.
