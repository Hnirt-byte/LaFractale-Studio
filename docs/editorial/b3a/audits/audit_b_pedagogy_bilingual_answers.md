# Audit B — Pédagogie, bilinguisme et corrigés du plan B3-A

**Date de l’audit :** 11 octobre 2026  
**Nature :** audit indépendant documentaire, sans modification du dépôt  
**Public visé par le plan :** enfants de 4–5 ans, avec lecture possible par un adulte  
**Statuts contractuels maintenus :** `B3A_PLAN=DRAFT_FOR_REVIEW`, `EDITORIAL=PENDING`, `KDP=FORBIDDEN`, `PRODUCTION_GENERATION=FORBIDDEN`

## 1. Identité et périmètre vérifiés

| Élément | Attendu | Observé | Résultat |
|---|---|---|---|
| Dépôt audité | `/opt/data/cache/scratch/lafractale-studio-github` | identique | PASS |
| Branche | `docs/b3-a-chemin-de-fer-halloween` | identique | PASS |
| HEAD | `397bc32c042dcd5533296ac7fe76b6a3ad749347` | identique | PASS |
| Tree | `72215ac28de46795338997be0bb38781274e80f4` | identique | PASS |
| Diff de fichiers suivis | aucun | aucun | PASS |
| Ajouts de travail | `docs/editorial/` | non suivi par Git | information |

L’identité Git requise est conforme. Les documents B3-A sont toutefois encore non suivis : le commit et le tree authentifient la base technique, pas encore le contenu B3-A lui-même. Le présent audit porte sur les fichiers B3-A présents dans cet arbre de travail, dont les empreintes internes ont été vérifiées séparément.

## 2. Éléments examinés

### Dossier B3-A consolidé

Les dix fichiers présents à la racine de `docs/editorial/b3a/` ont été examinés :

- `README.md`
- `01_reconciliation_report.md`
- `02_chemin_de_fer_consolide.csv`
- `02_chemin_de_fer_consolide.md`
- `03_mecanics_inventory.md`
- `04_faisabilite_corriges.md`
- `05_decisions_ouvertes.md`
- `06_gates_validation.md`
- `07_validation_evidence.json`
- `08_integrity_manifest.json`

### Pack source

Les treize fichiers de `docs/editorial/b3a/source_pack/` ont été examinés, y compris les deux CSV, le classeur XLSX et les manifestes :

- `00_LIRE_EN_PREMIER.md`
- `01_CONTRAT_B3A_v1.0.md`
- `02_CHEMIN_DE_FER_56_PAGES.csv`
- `02_CHEMIN_DE_FER_56_PAGES.xlsx`
- `03_CHEMIN_DE_FER_LISIBLE.md`
- `04_CARTOGRAPHIE_CORRIGES.csv`
- `05_BIBLE_ET_PROGRESSION.md`
- `06_GATES_RECETTE.md`
- `07_PROMPT_HERMES.md`
- `08_PROVENANCE_SOURCES.json`
- `09_REFERENCES_KDP.md`
- `10_CONTROLE_QUALITE_PACK.md`
- `11_MANIFEST_SHA256.json`

### Références techniques et éditoriales du dépôt

L’audit a également contrôlé notamment :

- `books/halloween_2026/book.yaml`
- `books/halloween_2026/page_plan.csv`
- `docs/EDITORIAL_BIBLE.md`
- `docs/QUALITY_GATES.md`
- `docs/B2C4_EDITORIAL.md`
- `src/lafractale/activities/engine.py`
- `src/lafractale/activities/models.py`
- `src/lafractale/story/plan.py`
- `src/lafractale/editorial.py`
- `tests/test_b2c4_editorial.py`

## 3. Contrôles effectivement exécutés

1. Vérification Git indépendante de la branche, du HEAD, du tree, du diff suivi et du statut de l’arbre de travail.
2. Recalcul SHA-256 :
   - 12/12 fichiers référencés par le manifeste du pack source conformes ;
   - 22/22 fichiers référencés par `08_integrity_manifest.json` conformes ;
   - empreintes de `book.yaml`, `page_plan.csv`, `EDITORIAL_BIBLE.md` et `QUALITY_GATES.md` conformes à la provenance déclarée.
3. Analyse CSV indépendante :
   - numérotation et unicité des pages ;
   - structure des sections ;
   - types de mécanique et adjacences ;
   - couverture du lexique ;
   - catégories de correction ;
   - égalité entre les 34 pages fermées déclarées et la cartographie des corrigés ;
   - répartition `9/9/8/8` ;
   - statuts moteur par page.
4. Comparaison des 16 colonnes du CSV source avec les colonnes correspondantes du CSV consolidé : aucune divergence.
5. Inspection interne du classeur XLSX comme archive Office Open XML : six onglets et 25 formules trouvés.
6. Exécution ciblée des tests C4 :

   `18 passed in 11.56s`

7. Interrogation directe du planificateur :
   - démo effective : p.04 `maze`, p.06 `connect_dots`, p.20 `match` ;
   - assemblage intégral toujours bloqué par les mécaniques et pages non implémentées.

Ces contrôles valident des propriétés documentaires et techniques. Ils ne remplacent ni une relecture par un spécialiste de la petite enfance, ni une séance avec enfants, ni une épreuve imprimée.

## 4. Résultats de cohérence documentaire

### 4.1 Structure des 56 pages

La structure calculée est cohérente :

| Zone | Pages | Nombre |
|---|---:|---:|
| Ouverture | 01–02 | 2 |
| Fiches d’activité | 03–49 | 47 |
| Diplôme | 50 | 1 |
| Corrigés | 51–54 | 4 |
| Lexique | 55 | 1 |
| Clôture | 56 | 1 |
| **Total** | **01–56** | **56** |

Les numéros sont uniques, continus et croissants.

Les cinq étapes narratives sont présentes :

- Invitation : p.03–12, 10 activités ;
- Forêt : p.13–22, 10 activités ;
- Amis : p.23–32, 10 activités ;
- Bonbons : p.33–42, 10 activités ;
- Fête : p.43–50, soit 7 activités et le diplôme p.50.

La narration suit bien le mouvement invitation → forêt → amis → bonbons → fête. Son ton est généralement doux et non effrayant.

### 4.2 Mécaniques

L’analyse relève :

- 47 pages d’activité, p.03–49 ;
- 17 libellés de mécanique distincts ;
- aucune répétition exacte d’un même libellé sur deux activités successives ;
- une distribution des labyrinthes, coloriages, tracés, comptages et associations entre les chapitres.

Cette diversité est documentaire. Elle ne prouve pas encore une diversité perceptible des plateaux, gestes, scènes ou compositions graphiques. Les rapprochements entre `match`, `pair_matching`, `match_vocabulary`, `find_count` et `count` devront notamment être contrôlés sur les maquettes.

### 4.3 Distinction exacte entre les 47 activités et C4

Le décompte correct est :

- **47** pages d’activité entre p.03 et p.49 ;
- **3** pilotes C4 : p.04, p.06 et p.20 ;
- **44** autres pages d’activité.

Parmi ces 44 autres pages :

- 8 utilisent un type que le générateur sait traiter génériquement, mais ne sont pas des identités de page implémentées par la démo : p.14, p.17, p.25, p.27, p.34, p.43, p.45 et p.46 ;
- 36 utilisent un type absent du moteur actuel.

Le code construit effectivement seulement les spécifications p.04, p.06 et p.20. Le support générique d’un type ne constitue pas l’implémentation éditoriale, graphique, pédagogique ou C4 de toutes les pages portant ce type.

### 4.4 Pilotes C4

| Page | Contrôle | Résultat |
|---:|---|---|
| 04 | scène C4 « Aide Pip à trouver la sortie », labyrinthe | référence correctement distinguée de la reformulation B3-A |
| 06 | scène « La lune mystérieuse », croissant fermé de 8 points, ordre `1→8→1` | divergence B3-A explicitement laissée ouverte |
| 20 | scène « Retrouve les chapeaux jumeaux », quatre paires | titre et intention alignés ; variation anglaise signalée |

Les tests techniques C4 passent. Cela ne vaut pas approbation éditoriale humaine des six pages fiche/corrigé.

### 4.5 Lexique canonique

Les 18 paires de `book.yaml` sont toutes présentes dans le plan, après normalisation typographique de l’apostrophe :

- fantôme / ghost ;
- citrouille / pumpkin ;
- chauve-souris / bat ;
- chat / cat ;
- lune / moon ;
- étoile / star ;
- chapeau / hat ;
- balai / broom ;
- araignée / spider ;
- toile d’araignée / spiderweb ;
- sorcière / witch ;
- monstre / monster ;
- hibou / owl ;
- maison / house ;
- bonbon / candy ;
- nuit / night ;
- porte / door ;
- sac / bag.

Les expressions `Accueil / welcome`, `Révision / review`, `Reprise / review` et `Bravo / well done` apparaissent aussi dans les champs de narration. Elles sont identifiées comme expressions libres ou fonctionnelles et ne sont pas présentées comme de nouvelles entrées du lexique évalué.

### 4.6 Corrigés

L’analyse confirme exactement :

- 31 lignes déclarées à correction graphique ;
- 3 lignes déclarées à correction chiffrée ;
- 34 lignes classées comme activités fermées ;
- 34 lignes distinctes dans la cartographie ;
- aucun doublon ni oubli entre les deux ensembles ;
- distribution p.51–54 : `9/9/8/8`.

Les quatre tracés p.09, p.19, p.29 et p.38 sont correctement exclus des 34 réponses fermées et classés comme modèles facultatifs.

La cohérence arithmétique de la cartographie est donc établie. La fermeture effective, l’unicité et la lisibilité des 31 activités hors pilotes C4 ne le sont pas encore.

## 5. Findings

### Synthèse par sévérité

| Sévérité | Nombre |
|---|---:|
| BLOCKER | 0 |
| MAJOR | 4 |
| MINOR | 3 |

### BLOCKER — 0

Aucun écart d’identité Git, de pagination, de statut contractuel ou de périmètre ne justifie un échec immédiat de la branche documentaire. Aucun document n’accorde une autorisation KDP ou de génération intégrale.

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

### MINOR-01 — Mention erronée de « quatre chapitres d’activités »

`01_reconciliation_report.md:38` mentionne « quatre chapitres d’activités 48 pages ». Le plan comporte cinq étapes narratives : Invitation, Forêt, Amis, Bonbons et Fête. Les données sont correctes ; la phrase doit être corrigée.

### MINOR-02 — Le pack source parle de « 47 nouvelles pages »

`source_pack/01_CONTRAT_B3A_v1.0.md:24` indique que C1/C2 n’autorise pas le routage de Pip « sur 47 nouvelles pages ».

Le décompte exact est :

- 47 pages d’activité au total ;
- 3 pilotes existants ;
- 44 autres pages d’activité.

La formulation devrait donc viser « les 44 autres pages d’activité » ou « l’ensemble des 47 pages, hors autorisation limitée aux trois pilotes ».

### MINOR-03 — Les résultats mis en cache du classeur ne corroborent pas le lexique

Le classeur contient 25 formules. Ses 18 formules de comptage du lexique ont toutes une valeur mise en cache égale à `0`, alors que l’analyse du CSV retrouve les 18 paires.

Aucune directive `calcPr` n’est présente dans le classeur pour imposer explicitement un recalcul à l’ouverture. La déclaration selon laquelle les formules ont été vérifiées ne suffit donc pas comme preuve autonome de couverture lexicale.

Cela n’invalide pas la couverture 18/18, confirmée indépendamment par le CSV, mais le classeur devrait être recalculé et sauvegardé avant d’être utilisé comme pièce de validation.

## 6. Décisions humaines explicitement ouvertes

Les décisions suivantes ne doivent pas être résolues par une CI, un statut Git ou le présent audit :

1. **p.06 C4 :** conserver « La lune mystérieuse » et les consignes exactes C4, ou approuver formellement une variante sans perdre l’ordre `1→8→1`.
2. **Bilinguisme :** valider l’équivalence et la naturalité de toutes les consignes, particulièrement p.31, p.40 et p.50.
3. **Progression 4–5 ans :** définir la notion de tâche exigeante et arbitrer les longues séquences d’activités fermées.
4. **Réponses hors pilotes :** démontrer les solutions uniques des 31 activités fermées non couvertes par C4 après définition de leurs données et visuels.
5. **Quatre pages de corrigés :** accepter ou refuser `9/9/8/8` uniquement après maquette finale et impression à 100 %.
6. **Titres p.51–54 :** choisir entre des titres réellement conformes aux sources cartographiées et les titres neutres « Corrigés 1–4 ».
7. **Alternative de pagination :** décider explicitement quelles pages seraient regroupées ou retirées si six ou huit pages de solutions deviennent nécessaires.
8. **Lexique p.55 :** choisir entre une composition typographique en deux colonnes et 18 pictogrammes futurs approuvés.
9. **Scènes et illustrations :** valider séparément les scènes nouvelles, leurs droits et leur adéquation pédagogique.
10. **Pip hors démo :** définir une nouvelle politique de routage et de placement avant toute apparition sur les 44 autres pages d’activité.
11. **Fond perdu et prépresse :** confirmer les choix uniquement sur les pages finales et une épreuve physique.

## 7. Réserves sur les quatre pages de corrigés

La cartographie `9/9/8/8` est arithmétiquement exacte, mais sa faisabilité matérielle demeure non démontrée.

Une réponse peut nécessiter :

- un chemin de labyrinthe ;
- des points et segments numérotés ;
- plusieurs associations ;
- un inventaire d’objets ;
- un motif ou une suite ;
- des renvois lisibles vers la page source.

Une moyenne de 8,5 réponses par page ne suffit pas à conclure que ces éléments resteront identifiables pour un enfant de 4–5 ans ou un adulte accompagnant. Les pages p.51–54 doivent rester une hypothèse de pré-maquette.

L’option quatre pages est recevable uniquement si une impression à 100 % confirme :

- la lisibilité des numéros ;
- l’absence d’ambiguïté entre réponses ;
- la compréhension des renvois aux pages sources ;
- la lisibilité des chemins et tracés ;
- une taille exploitable sans loupe ni interprétation du maquettiste.

À défaut, une réallocation explicite vers six ou huit pages devra faire l’objet d’un arbitrage éditorial. Aucune activité ne doit disparaître silencieusement.

## 8. Limites de l’audit

Cet audit :

- n’a produit ni PDF ni illustration ;
- n’a pas examiné de maquette finale imprimée ;
- n’a pas observé d’enfant ou d’adulte utilisant les activités ;
- n’a pas certifié la durée, la difficulté réelle ou le plaisir de jeu ;
- n’a pas certifié les traductions par un lecteur bilingue professionnel ;
- n’a pas validé visuellement les solutions des 31 activités hors pilotes ;
- n’a pas effectué de contrôle prépresse, de Print Previewer ou de publication ;
- ne certifie ni Amazon KDP ni une quelconque disponibilité commerciale ;
- ne transforme aucun statut `À VALIDER` en approbation.

## 9. Conclusion

Le dossier est cohérent comme **plan documentaire de travail** : la pagination, les cinq étapes narratives, les 17 mécaniques déclarées, la couverture des 18 paires canoniques et la cartographie `9/9/8/8` sont reproductibles.

Il reste toutefois nécessaire de corriger les formulations qui assimilent le support générique d’une mécanique à l’implémentation d’une page, de remplacer l’affirmation de 34 réponses objectivement démontrées par une qualification documentaire, de revoir la charge successive des activités et de corriger les divergences FR/EN identifiées.

Le maintien explicite des statuts de brouillon, l’interdiction de production et l’ouverture honnête de la décision sur les quatre pages de corrigés permettent un passage documentaire avec décisions ouvertes, mais aucune progression vers B3-B, prépresse ou KDP ne peut être déduite de ce résultat.

**VERDICT: PASS_WITH_OPEN_DECISIONS**
