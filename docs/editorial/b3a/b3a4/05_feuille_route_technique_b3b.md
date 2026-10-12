# Feuille de route technique B3-B — sans implémentation

## État constaté

Le moteur actif ne couvre de bout en bout que les trois pilotes C4 : p.04 `maze`, p.06 `connect_dots`, p.20 `match`. Les types supportés sont limitées à `{maze, connect_dots, match}` ; les 43 autres identités du scénario B ne deviennent pas productibles parce qu’elles partagent un nom de type.

Pour le scénario B :

- 46 activités, 16 mécanismes actifs ;
- 3 pilotes canoniques complets ;
- 7 activités de types existants, mais nécessitant données, géométrie, scènes, réponses et routage nouveaux ;
- 36 activités relevant de 13 mécanismes non implémentés.

Cette constatation ne modifie aucun code et ne vaut pas autorisation B3-B.

## Phases proposées

1. **Contrat documentaire gelé** — désigner le scénario B et sa grille B3-A.4 comme source de build après décision humaine, sans écraser les historiques.
2. **Schéma de page** — représenter type, payload, réponse, statut de corrigé, FR/EN, assets, approbations, page source/finale et contraintes de composition.
3. **Primitives existantes** — généraliser `maze`, `connect_dots`, `match` sans altérer les identités C4 ; prouver les sept nouvelles pages de mêmes types par tests de sémantique.
4. **Nouvelles mécaniques** — développer avec invariants et solutions uniques : dessin libre/coloriage/tracé ; comptage/recherche ; associations/tri ; séquences/différences/logique.
5. **Assets et droits** — registre multi-rôles, provenance, SHA-256, droits, approbation humaine externe, routage et placement par page. Les assets C4 ne deviennent pas réutilisables par défaut.
6. **Layouts spéciaux** — ouverture, 46 activités, six corrigés condensés, lexique 18 paires, diplôme/clôture ; pagination stricte 1–56.
7. **Export fermé** — intérieur, couverture séparée après gel KDP, aperçus, sources figées, rapport qualité, manifeste complet et inventaire de sortie versionné.
8. **Gates humaines et prépresse** — relecture exhaustive, épreuve représentative 100 %, revue graphique, test enfant–adulte, préflight et aperçu KDP, seulement après autorisations explicites.

## Invariants de production à prévoir

- pages 1..56 exactement une fois ; 46 activités p.03–48 ; 31 entrées de corrigé p.49–54 selon `6/5/5/5/5/5` ; aucune activité libre dans les corrigés ;
- chaque solution fermée est unique, visible et renvoie à sa page source ;
- p.55 maintient les 18 paires sans pictogramme non approuvé ;
- p.56 protège la zone prénom/cercle/consigne à l’impression 100 % ;
- sources, seed, versions outil, assets, approbations et sorties sont hashés dans un manifeste ;
- le LLM est optionnel et hors chemin déterministe : toute suggestion créative est versionnée, traçable et requiert approbation humaine avant entrée dans les sources ;
- aucune approbation humaine ne se déduit d’un manifest ou d’un export.

## Architecture d’export cible

```text
delivery/
  interior.pdf                 # 56 pages
  cover.pdf                    # après gel papier/page count/paramètres KDP
  previews/interior/page_001.png … page_056.png
  previews/cover.png
  sources/scenario_B.csv
  sources/bilingual_review.csv
  sources/correction_map.csv
  sources/page_specs.json
  sources/asset_bindings.json
  quality/quality_report.json
  quality/preflight.json
  quality/human_approvals.json
  manifest.json
```

La migration doit adapter l’inventaire fermé des sorties et ses tests ; elle ne doit pas accepter des fichiers supplémentaires implicitement.

## Risques à traiter avant B3-B

- le `books/halloween_2026/page_plan.csv` est une source de build historique qui ne reflète pas encore B3-A.3 ;
- les solutions concrètes des 31 corrigés, les textes d’ouverture et les copies de production p.55/p.56 sont absents ou seulement documentaires ;
- les scènes/objets hors pilotes ne sont pas dans le catalogue approuvé ;
- la couverture dépend du nombre final de pages, du papier et des paramètres KDP gelés ;
- `MAJOR-03`, `MAJOR-04`, `EDITORIAL=PENDING`, `KDP=FORBIDDEN` et `PRODUCTION_GENERATION=FORBIDDEN` restent des gates bloquantes.
