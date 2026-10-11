# Chemin de fer consolidé — 56 pages

`02_chemin_de_fer_consolide.csv` est la version tabulaire de référence pour la revue B3-A. Il conserve les 56 propositions du pack et ajoute la provenance, l'état moteur réel et la réconciliation C4, sans modifier le `page_plan.csv` de production.

## Synthèse

- Pages : 56, numéros 01–56 continus.
- Chapitres : Ouverture 2, Invitation 10, Forêt 10, Amis 10, Bonbons 10, Fête 8, Fin 6.
- Activités : 17 mécaniques distinctes ; aucune répétition adjacente parmi les activités.
- Vocabulaire : 18/18 paires de `book.yaml` couvertes.
- Corrigés fermés : 34, cartographiés provisoirement p.51–54 en `9/9/8/8`.
- Pip : rôles et assets sont des candidats narratifs ; aucune extension de routage C1/C2/C4 n'est autorisée.

## Règles de lecture

- `type_source` et `titre_source_B2B` décrivent la source historique, identique au `main` ancré.
- `type_propose`, titres et consignes sont des propositions B3-A, pas des données de production.
- La colonne `c4_reference` prime pour les pages 04, 06 et 20.
- `engine_status` décrit l'état présent ; il ne constitue pas un mandat d'implémentation.
- Toute ligne conserve le statut `À VALIDER` jusqu'à une revue humaine explicite.

Le CSV est volontairement sérialisé de manière stable (UTF-8, ordre de lignes 1..56, ordre de colonnes fixé) et son empreinte est publiée dans `08_integrity_manifest.json`.
