# Contradictions détectées et décisions humaines requises

## Contradictions / sources manquantes

1. **MAJOR-04 mentionne encore 47 paires dans B3-A.3.** Le plan actif comporte 46 consignes d’activité. Les 47 sont l’archive historique. B3-A.4 sépare donc strictement `46 actives` et `47 historiques`, sans fermer MAJOR-04.
2. **Ouvertures p.01–02 :** titres présents, copie bilingue lecteur absente.
3. **Corrigés p.49–54 :** cartographie 31 activités→6 pages présente ; solutions, libellés lecteurs et layouts définitifs absents.
4. **p.55 :** les 18 paires sont dans `book.yaml` et la maquette NON PRODUCTION, mais pas encore dans une source de production avec ordre/repères et copie lecteur figés.
5. **p.56 :** la maquette contient une copie candidate et des annotations techniques ; cette copie doit être séparée des annotations et validée humainement.
6. **Huit activités `HUMAN_REVIEW` :** p.17, 22, 37, 43, 44, 45, 46 et 48 manquent encore de données déterministes suffisantes (règle, objet, quantité, solution ou layout selon la page).
7. **B3-B :** la source de build historique et l’inventaire d’activités ne sont pas encore alignés sur le scénario B. Ceci est normal tant que B3-B n’a pas reçu de GO, mais bloque toute génération intégrale.

## Décisions à rendre — sans approbation implicite

1. Confirmer si la relecture humaine MAJOR-04 porte sur les 46 activités actives **plus** les unités textuelles applicables (ouvertures, 31 corrigés, 18 paires, p.56), l’archive de 47 restant consultable seulement.
2. Désigner les validateurs FR, EN/bilingue, pédagogie 4–5 ans, impression et l’arbitre final ; définir si les identités sont des noms professionnels ou des identifiants organisationnels stables.
3. Fournir/valider la copie active p.01–02, les solutions/renvois p.49–54, la copie production p.55 et p.56.
4. Approuver ou adapter le protocole d’épreuve, son échantillonnage et les seuils avant recrutement.
5. Décider si une option Drive privée sera utilisée ultérieurement ; si oui, fournir seulement le dossier cible et un GO de téléversement au moment voulu.
6. Décider séparément de la fusion de PR #10 après le nouveau commit B3-A.4, sa CI et sa revue indépendante. Aucune transition B3-B n’est autorisée par ce dossier.
