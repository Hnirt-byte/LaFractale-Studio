# V0.2-A — compagnons thématiques indépendants

## Statut
Prototype technique de migration sur la base source du tag `v0.1.0` (`4ce3db85ad34351d72bd18d45cb060cfd7668168`). **Ne constitue pas la V0.2 graphique finale ni une approbation KDP.**

## Principe
- LaFractale Édition est l'identité de collection ; le moteur Python n'est pas une licence de Pip.
- **Pip est réservé à `halloween_2026`**, avec sa référence officielle inchangée, hashée, et jamais dessinée automatiquement.
- Noël n'a pas encore de compagnon : `companion.status: pending_selection`. Son titre, son histoire et ses fiches de démonstration ne mentionnent pas Pip.
- Aucun nouveau compagnon n'est créé ou approuvé automatiquement. Un personnage de Noël sera choisi et validé ultérieurement.

## Configuration
Chaque livre déclare **obligatoirement** :

```yaml
# Halloween
companion:
  status: approved_reference
  id: pip
```

ou :

```yaml
# Noël, en attendant la décision éditoriale
companion:
  status: pending_selection
```

Les références approuvées sont stockées dans `assets/companions/catalog.yaml` : ID technique, nom, `allowed_book_ids`, chemin du fichier original sous `assets/characters/<id>/`, SHA-256, contraintes visuelles et `reference_only: true`. Une entrée de catalogue doit être créée et validée humainement avant de pouvoir être sélectionnée par un livre. Aucune modification du code Python n'est requise pour ajouter un nouveau personnage.

La syntaxe V0.1 `mascot` est intentionnellement refusée par les nouvelles configurations afin d'éviter l'attribution silencieuse de Pip à d'autres univers. La migration des anciens livres doit être explicite.

## Comportement garanti et limites
- La CLI `validate` vérifie le lien livre-personnage, l'existence et l'intégrité de l'asset approuvé.
- La CLI `build-demo` autorise un compagnon non choisi et utilise des consignes sans nom de personnage ; elle marque toujours les fiches comme `needs_visual_review`.
- La CLI `build` refuse l'assemblage intégral si aucun compagnon n'est approuvé, ainsi que pour les limitations existantes.
- Le titre de page, les consignes de labyrinthe, les données d'activités et les rapports de démo sont neutres en l'absence de compagnon.
- Aucun nouveau personnage, dessin ou pose n'est créé. Les droits des assets restent `UNVERIFIED`. Toutes les sorties restent **non publiables**.
- La vérification d'une référence approuvée ne vaut pas validation du rendu graphique final, d'une déclinaison N&B ou des droits commerciaux.

## Modèle de confiance du catalogue (correctif 0.2.0a3)
- Aucun segment `.` ou `..`, séparateur Windows ou échappement du répertoire `assets/characters/<id>/` n’est accepté pour une référence approuvée.
- La lecture du catalogue et des images est ancrée à la racine et refuse chaque composant symlink par `O_NOFOLLOW`, y compris les dossiers parents. Sur plateforme sans openat/O_NOFOLLOW, l’opération échoue explicitement, elle ne réduit pas sa sécurité silencieusement.
- Le hash et les informations approuvées sont revérifiés à chaque utilisation dans le registre ainsi qu’en fin de génération avant émission du manifeste.
- Chaque titre, histoire, scène de démonstration, vocabulaire et page du plan est contrôlé contre les noms des compagnons non autorisés. Un livre en `pending_selection` n’a droit à **aucun** nom du catalogue dans ses textes.
- Les tests sont des contrôles techniques : une révision humaine demeure requise pour les synonymes, surnoms et représentations visuelles non textuelles.

## Plan d'intégration pour Hermes
1. Depuis le dernier `main`, créer `feat/studio-v0.2a-companions`.
2. Appliquer exclusivement les différences V0.2-A du paquet livré. Ne pas remplacer le dépôt sans comparaison.
3. Exécuter les tests et les commandes CLI pour Halloween et Noël. Vérifier qu'aucun PDF de Noël ne mentionne Pip.
4. Vérifier que le checksum de la référence officielle Pip est inchangé.
5. Ouvrir une PR **non fusionnée** vers `main`, joindre les résultats ; aucune publication KDP.

## Canonical pending profile, V0.2-A v4

Do not trust `Book` or `CompanionProfile` objects solely because they are frozen dataclasses: `dataclasses.replace()` can forge their fields. Each use of `verify_companion_integrity` compares **all** fields with the canonical profile constructed from the pinned catalogue and book ID. For `pending_selection`, `id`, `name`, `reference`, and `sha256` must be `None`, while `visual_constraints` must be empty. The mutable YAML binding must exactly match that status.

Unselected profiles are not allowed to exempt catalogue names from text scanning, and their names must never reach activity generation or manifests. This is an integrity guard, not a general-purpose Python sandbox or a guarantee against concurrently changing files outside these checks.

## Vérification de provenance avant génération (0.2.0a4)

La validité d'un `CompanionProfile` **ne suffit pas** à autoriser sa réutilisation dans un autre `Book`. Le module `verify_book_snapshot()` compare les empreintes source et les structures chargées avec le YAML et le CSV originaux, relus au point d'usage. Ainsi, remplacer `book.data["book_id"]` puis `book.companion` ne suffit pas à autoriser Pip pour Noël, même si le nouveau profil est valide pour Halloween.

Les opérations `build_demo`, `demo_specs` et `registry` vérifient cette provenance. Une mutation survenant pendant l'export provoque une erreur et n'est pas publiée dans le dossier de sortie. Le remplacement de la démo est préparé dans un répertoire temporaire, puis effectué après QA.

**Limites :** ces garde-fous ne constituent pas une sandbox contre un module Python malveillant chargé dans le même interpréteur, une modification/restauration indétectable entre contrôles ni les changements concurrents sur les sorties. La prochaine frontière architecturale devra isoler les builds et employer des sources immuables. Ils ne prouvent pas non plus l'absence de toute faille inconnue.
