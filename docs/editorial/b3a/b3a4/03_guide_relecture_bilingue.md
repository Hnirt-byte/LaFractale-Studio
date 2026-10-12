# Guide de relecture humaine bilingue — B3-A.4

## Portée exacte

La grille `02_grille_relecture_humaine_complete.csv` contient :

- 46 unités d’activité actives p.03–48, provenant du scénario B ;
- 2 titres d’ouverture p.01–02, **bloqués** faute de copie bilingue active ;
- 31 unités de corrigé p.49–54, **bloquées** faute de solutions et libellés actifs ;
- 18 paires du lexique p.55 ;
- 6 unités textuelles candidates p.56, explicitement extraites d’une maquette `NON PRODUCTION`.

Les 47 propositions historiques sont séparées dans `03_archive_historique_47_reference.csv`. Elles ne participent jamais au total actif, aux pourcentages de revue ni à une décision de pagination.

## Rôles humains requis

Chaque unité applicable doit conserver l’identité, le rôle et la date ISO du validateur :

1. réviseur FR : oralité, syntaxe, référents, quantités et vocabulaire 4–5 ans ;
2. réviseur EN compétent : idiomaticité et action réellement équivalente ;
3. relecteur bilingue : même geste, même objet, même quantité, même ordre et même médiation ;
4. relecteur pédagogie 4–5 ans : lecture portée par l’adulte, charge visuelle/motrice/orale, fatigue et réponse unique ;
5. relecteur impression : lisibilité réelle à 100 %, notamment corrigés, p.55 et p.56 ;
6. arbitre éditorial : accepte/refuse la correction avec justification.

Une analyse LLM peut être versée en `evidence_reference` comme signal, **jamais** comme `VALIDATED`.

## Règles de décision

- `C4_LOCKED` protège le texte des p.04, p.06 et p.20 contre tout changement silencieux ; ce n’est pas une validation linguistique ou enfant.
- `VALIDATED_HUMAN` demande le nom/identifiant professionnel, rôle, date, preuve référencée et absence de finding bloquant.
- `BLOCKED_BY_SOURCE` est obligatoire tant que les ouvertures, corrigés ou copie de production p.56 n’existent pas sous une source autoritaire.
- Le français et l’anglais peuvent être naturels sans être mot-à-mot ; ils doivent toutefois imposer la même action et aucune aide supplémentaire dans une seule langue.
- Toute activité de vocabulaire reste médiée oralement ; aucun enfant 4–5 ans ne doit devoir lire pour agir.

`MAJOR-04` reste `OPEN` jusqu’à la revue humaine exhaustive de toutes les unités applicables et à une décision humaine explicitement documentée.
