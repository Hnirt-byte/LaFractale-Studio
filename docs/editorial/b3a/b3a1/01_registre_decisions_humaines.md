# Registre de décisions humaines — B3-A.1

## Règle de statut

| Référence | État | Correction documentaire appliquée | Décision humaine encore requise |
|---|---|---|---|
| Audit B MAJOR-01 | **OUVERT** | oui : taxonomie moteur rectifiée dans le CSV consolidé | accepter la taxonomie et confirmer qu’aucune page hors C4 n’est présentée comme produite |
| Audit B MAJOR-02 | **OUVERT** | oui : vocabulaire de preuve rectifié | accepter la limite « besoins de corrigé cartographiés » ; l’unicité des 31 solutions reste future |
| Audit B MAJOR-03 | **OUVERT** | oui : gate A04 dégradé en attente de validation humaine | définir la charge et valider/réordonner les séquences |
| Audit B MAJOR-04 | **OUVERT** | propositions consignées dans la revue 47 | relecture bilingue humaine exhaustive |
| Audit A MINOR-01 | **CORRIGÉ DOCUMENTAIREMENT — ACCEPTATION À CONFIRMER** | oui | accepter la formulation « cinq chapitres narratifs » |
| Audit A MINOR-02 | **CORRIGÉ DOCUMENTAIREMENT — ACCEPTATION À CONFIRMER** | oui | accepter la donnée canonique ASCII et la règle typographique |

## Contenu intégral des findings d’origine

> Les six extraits suivants sont reproduits depuis les audits indépendants B3-A ; ils restent la référence du finding.

### MAJOR-01 — Huit pages hors C4 sont décrites comme « implémentées »

**Fichiers concernés :** `02_chemin_de_fer_consolide.csv`, indirectement les synthèses qui s’appuient sur sa colonne `engine_status`.

Onze lignes portent la formulation « Implémenté dans le moteur de démo » : les trois pilotes p.04, p.06, p.20, mais aussi p.14, p.17, p.25, p.27, p.34, p.43, p.45 et p.46.

Pour ces huit dernières pages, seul le **type générique** est supporté. Le planificateur ne crée que p.04, p.06 et p.20, et C4 est fermé à ces trois identités. Il n’existe pas de spécification de page, de contenu, de réponse, de routage Pip ou de contrôle C4 pour les huit autres.

**Correction requise :** remplacer, pour ces huit lignes, le statut par une formulation telle que :

> Mécanique générique supportée, mais page B3-A non implémentée, non routée et non validée.

Cette correction évitera que le lecteur assimile le support d’un type à l’existence de onze pages produites.

### MAJOR-02 — « 34 activités objectivement fermées » est une formulation trop forte

**Fichiers concernés :**

- `01_reconciliation_report.md:41`
- `04_faisabilite_corriges.md:5`
- `06_gates_validation.md:11`
- plusieurs synthèses du pack source

Le fait mécaniquement démontré est le suivant : **34 lignes sont classées comme devant recevoir une correction fermée et sont toutes cartographiées**.

Cela ne démontre pas encore que 34 activités concrètes possèdent une réponse unique :

- seules les trois pages pilotes disposent actuellement d’une activité structurée et techniquement contrôlée ;
- les 31 autres activités fermées sont des intentions documentaires ;
- 28 de ces 31 lignes indiquent explicitement « Solution unique à vérifier » ;
- p.10, p.21 et p.30 sont des comptages sans scène ni inventaire produits ;
- p.44, p.46 et p.49 ne fixent pas encore les objets ou mots précis ;
- p.48 ne définit pas encore ses deux mini-défis.

**Correction requise :** employer « 34 activités prévues comme fermées » ou « 34 besoins de corrigé cartographiés ». Réserver « réponse unique démontrée » aux activités dont les données, la solution et les contrôles existent réellement.

### MAJOR-03 — La progression ne démontre pas la règle de respiration pédagogique annoncée

`source_pack/05_BIBLE_ET_PROGRESSION.md` annonce :

> Pas plus de deux tâches exigeantes d’affilée.

Le terme « exigeante » n’est pas défini par un critère exploitable. En prenant les activités fermées comme indicateur conservateur de charge, les séquences suivantes dépassent deux pages :

- p.04–07 : 4 ;
- p.10–12 : 3 ;
- p.14–17 : 4 ;
- p.20–22 : 3 ;
- p.24–27 : 4 ;
- p.30–32 : 3 ;
- p.34–37 : 4 ;
- p.40–46 : 7.

La séquence p.40–46 est particulièrement dense avant l’activité libre p.47. Les niveaux D3 p.44 et p.48 sont bien déclarés facultatifs, mais aucune preuve enfant/adulte ne démontre encore que la charge globale convient aux 4–5 ans.

**Décision requise :**

1. définir ce qu’est une tâche exigeante ;
2. faire une revue humaine page par page ;
3. soit justifier les séquences, soit insérer des respirations par réordonnancement explicite ;
4. ne pas présenter `A04` comme une validation pédagogique acquise.

### MAJOR-04 — Plusieurs couples FR/EN ne demandent pas exactement la même action

La plupart des consignes sont courtes et compréhensibles avec lecture adulte. Plusieurs divergences doivent néanmoins être corrigées ou validées explicitement :

| Page | Observation |
|---:|---|
| 06 | Les propositions FR et EN omettent le retour au point 1 exigé par C4. Cette divergence est déjà ouverte et correctement signalée. |
| 31 | « Entoure les objets identiques » / « Circle the matching objects » ne précise ni les quatre paires ni la façon de marquer une paire ; la consigne reste ambiguë au regard de la réponse fermée. |
| 40 | Le français demande de relier ; l’anglais demande de donner un bonbon. Le geste graphique attendu n’est pas équivalent. |
| 50 | Le français demande de dessiner un sourire et d’écrire le prénom avec un adulte ; l’anglais se limite à « Well done! You did it! ». Les deux versions ne portent pas la même activité. |

Des écarts plus faibles existent également p.02, p.13 et p.33 : simplification sémantique, ajout de « friendly » ou emploi de `candy` là où plusieurs bonbons semblent prévus.

**Correction requise :** relecture bilingue humaine des 47 activités et des pages fonctionnelles, avec contrôle séparé de la naturalité linguistique et de l’équivalence du geste demandé.

### MINOR-01 — Nombre de chapitres mal libellé dans le rapport de réconciliation

`01_reconciliation_report.md` indique :

> « quatre chapitres d'activités 48 pages »

Le plan contient en réalité **cinq** chapitres narratifs : Invitation, Forêt, Amis, Bonbons et Fête. Les 48 pages et la position du diplôme sont correctement comptées ; l’erreur porte sur le libellé du nombre de chapitres.

**Correction recommandée :** remplacer « quatre chapitres » par « cinq chapitres ».

### MINOR-02 — Apostrophe non canonique dans une paire du lexique

Le `book.yaml` contient :

```text
toile d'araignée: spiderweb
```

Le chemin de fer emploie :

```text
toile d’araignée / spiderweb
```

La différence est limitée à l’apostrophe ASCII U+0027 contre l’apostrophe typographique U+2019. La paire est sémantiquement présente et aucun mot supplémentaire n’est introduit, mais une comparaison exacte sans normalisation ne produit que 17 correspondances littérales sur 18.

**Correction recommandée :** reprendre l’orthographe exacte du `book.yaml` dans le CSV, ou documenter explicitement la normalisation Unicode utilisée par les contrôles.

## 6. Réserves et limites

- Le dossier candidat est encore non suivi par Git ; aucun tree final de PR contenant ces fichiers n’a donc été audité. Toute modification des 23 fichiers observés doit invalider ou renouveler ce contrôle.
- L’archive ZIP historique n’est pas présente dans le dépôt audité. Son empreinte est corroborée par un document antérieur suivi, mais le conteneur ZIP ne peut pas être recalculé.
- Les feuilles XLSX ont été comparées structurellement à leurs CSV ; les formules n’ont pas été recalculées par un tableur graphique.
- Cet audit ne valide pas la lisibilité réelle des quatre pages de corrigés, les solutions graphiques futures, les traductions, l’adéquation pédagogique à des enfants de 4–5 ans, les droits d’illustration, le prépresse ou KDP.
- Aucun PDF, asset ou livre de 56 pages n’a été généré dans le cadre de cet audit.
- Le présent rapport n’est ni un audit B de pédagogie/bilinguisme, ni une certification éditoriale humaine, ni une étude enfant, ni une autorisation de production ou de publication.

## 7. Conclusion

La base Git est exacte, la frontière documentaire est respectée, les fichiers protégés sont inchangés, les manifestes sont cohérents, la provenance substantielle est recoupée, les 56 lignes sont réconciliées avec le plan historique et le HEAD, les 34 réponses sont toutes cartographiées, les écarts C4 sont visibles et aucun actif ou PDF de production n’est présent.

Les deux findings mineurs sont des corrections de précision documentaire. Ils ne masquent aucune décision, ne modifient aucun contrat de production et ne justifient pas un échec de l’Audit A.

**VERDICT: PASS**

## Décisions proposées, impact et condition de clôture

### MAJOR-01 — Statut réel des mécaniques

**Décision proposée :**

- p.04, p.06, p.20 : `Pilote C4 implémenté et routé pour la démo technique uniquement ; aucune autorisation de production intégrale.`
- p.14, p.17, p.25, p.27, p.34, p.43, p.45, p.46 : `Type générique présent dans le moteur ; page B3-A non implémentée, non routée et non validée.`
- toutes les autres pages : `Mécanique ou composant absent du moteur ; ligne documentaire uniquement.`

**Impact :** supprime l’amalgame entre type générique et page réellement implémentée ; aucun changement C1–C4 ni moteur.

**Décision requise :** accepter cette taxonomie sur la PR #10.

**Clôture :** seulement après acceptation humaine et contrôle qu’aucune synthèse ne présente les huit pages comme produites.

### MAJOR-02 — Niveau de preuve des 34 corrigés

**Décision proposée :** employer `34 activités prévues comme fermées et 34 besoins de corrigé cartographiés`. Réserver `réponse unique démontrée` à une activité ayant données, solution calculée, visuel et contrôle d’ambiguïté.

**Impact :** le compte de 34 ne change pas ; les 31 solutions hors C4 ne deviennent pas validées par cette correction.

**Décision requise :** accepter cette limite de preuve et exiger une validation individuelle avant B3-B.

**Clôture :** terminologie seulement ; le gate des 31 solutions reste ouvert.

### MAJOR-03 — Charge et respiration 4–5 ans

**Décision proposée :** traiter provisoirement toute activité obligatoire `graphique` ou `chiffre` comme potentiellement exigeante ; convertir A04 en preuve de diversité documentaire seulement ; exiger une revue humaine page par page puis une séance enfant/adulte.

**Impact :** aucune conséquence moteur ; un réordonnancement ou une simplification future reste possible.

**Décision requise :** définir « tâche exigeante », nommer le responsable de revue et choisir pour chaque séquence longue : justification, simplification ou réordonnancement.

**Clôture :** grille approuvée + revue des 47 activités + validation des séquences finales.

### MAJOR-04 — FR/EN et médiation adulte

**Décision proposée :** retenir les 47 propositions de `03_revue_consignes_fr_en_47_activites.csv` comme base de relecture. Les pages C4 04, 06 et 20 sont verrouillées. Pour les activités de vocabulaire, l’adulte lit et l’enfant écoute, pointe ou relie ; aucune lecture autonome n’est présumée.

**Impact :** les textes B3-A initiaux sont conservés comme provenance ; les propositions B3-A.1 ne deviennent pas la copie finale sans relecture bilingue.

**Décision requise :** validation explicite par un relecteur bilingue, notamment p.06, p.31, p.40 et le diplôme/clôture.

**Clôture :** relecture exhaustive et intégration des formulations humaines approuvées.

### MINOR-01 — Cinq chapitres

**Décision proposée :** utiliser `cinq chapitres narratifs d’activités p.03–49, puis le diplôme p.50`.

**Impact :** documentation seulement.

**Décision requise :** confirmer la formulation.

**Clôture :** recherche globale sans occurrence de « quatre chapitres d’activités ».

### MINOR-02 — Apostrophe canonique

**Décision proposée :** conserver dans la donnée et les comparaisons la chaîne `toile d'araignée / spiderweb`; toute apostrophe typographique est une transformation de rendu explicitement documentée, jamais une donnée de référence.

**Impact :** correspondance littérale 18/18 sans normalisation implicite.

**Décision requise :** confirmer la règle données ASCII / typographie de rendu éventuelle.

**Clôture :** CSV consolidé et contrôles alignés.
