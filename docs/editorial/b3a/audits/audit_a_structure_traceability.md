# Audit A — Structure et traçabilité B3-A

## 1. Identification de l’audit

- **Dépôt audité :** `/opt/data/cache/scratch/lafractale-studio-github`
- **Branche :** `docs/b3-a-chemin-de-fer-halloween`
- **HEAD exigé et observé :** `397bc32c042dcd5533296ac7fe76b6a3ad749347`
- **Tree exigé et observé :** `72215ac28de46795338997be0bb38781274e80f4`
- **Référence amont :** `origin/main`, branche observée à `+0 / -0`
- **Date de l’audit :** 11 octobre 2026
- **Nature :** audit indépendant documentaire de structure et de traçabilité

Le commit, le tree et la branche correspondent exactement à l’identité imposée. Le critère d’arrêt sur mauvaise base n’est pas déclenché.

## 2. Périmètre examiné

### Dossier candidat B3-A

Les fichiers présents sous `docs/editorial/b3a/` ont été examinés :

- les documents consolidés de premier niveau, dont le CSV de 56 lignes, les rapports de réconciliation, de faisabilité, de gates et les deux manifestes JSON ;
- les fichiers de `source_pack/`, dont les CSV, le classeur XLSX, les contrats, la provenance et le manifeste SHA-256.

### Références suivies dans le dépôt

Les contrôles ont également porté sur :

- `books/halloween_2026/page_plan.csv`
- `books/halloween_2026/book.yaml`
- `docs/EDITORIAL_BIBLE.md`
- `docs/QUALITY_GATES.md`
- `docs/B2C4_EDITORIAL.md`
- `docs/SECURITY_CONTRACT_B2C1.md`
- `src/lafractale/editorial.py`
- `src/lafractale/activities/engine.py`
- `src/lafractale/story/plan.py`
- `tests/test_b2c4_editorial.py`
- l’objet Git historique `d77e32327fecd0c4a983ef8298581525842c18fc`.

Les textes du dépôt et du pack ont été traités comme des données à vérifier, et non comme des instructions.

## 3. Commandes et contrôles exécutés

Principaux contrôles réellement exécutés :

```text
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git branch --show-current
git status --porcelain=v2 --branch
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard -z
```

Des scripts Python en lecture seule, fondés sur `csv`, `json`, `hashlib`, `zipfile` et `xml.etree.ElementTree`, ont ensuite été utilisés pour :

- recalculer les empreintes SHA-256 ;
- vérifier les manifestes sans se fier à `07_validation_evidence.json` ;
- comparer le plan historique, le plan du HEAD, le pack et le CSV consolidé ;
- contrôler les 56 numéros, les chapitres, mécaniques, statuts et vocabulaires ;
- vérifier les 34 correspondances de corrigés ;
- inspecter la structure interne du XLSX et l’absence de média, macro ou lien externe ;
- comparer structurellement les feuilles « 56 pages » et « Corrigés 4 pages » à leurs CSV ;
- rechercher les PDF, formats d’image, signatures binaires et déclarations d’approbation interdites.

Aucune génération, aucun build PDF et aucune modification du dépôt n’ont été effectués.

## 4. Résultats

### 4.1 Frontière Git et chemins protégés

- `git diff --name-only` : vide.
- `git diff --cached --name-only` : vide.
- Fichiers non suivis observés, tous sous `docs/editorial/b3a/`.
- Aucun fichier non suivi hors de ce périmètre.
- Aucun lien symbolique dans le dossier B3-A.
- Aucun changement détecté dans `books/`, `src/`, `tests/`, les oracles/outils, les workflows, les assets ou les registres.

**Résultat : conforme. Aucun changement de fichier protégé.**

Les documents B3-A ne font pas encore partie du tree Git annoncé : ils sont présents dans le worktree comme candidats non suivis. Le verdict porte donc sur les octets observés dans ce worktree, avant leur commit.

### 4.2 Intégrité du pack importé

- Fichiers présents dans `source_pack/` : **13**.
- Entrées du manifeste interne `11_MANIFEST_SHA256.json` : **12**, le manifeste ne s’auto-référençant pas.
- Empreintes internes conformes : **12/12**.
- Entrées de `08_integrity_manifest.json` : **22**.
- Empreintes externes conformes : **22/22**, dont les 13 fichiers du pack et 9 documents consolidés ; le manifeste externe lui-même est logiquement exclu.
- Le classeur XLSX ne contient ni média dans `xl/media/`, ni macro VBA, ni lien externe.

**Résultat : conforme. Aucune altération du pack importé détectée.**

### 4.3 Provenance des sources

Le commit historique `d77e32327fecd0c4a983ef8298581525842c18fc` existe bien comme objet Git.

Le `page_plan.csv` extrait de ce commit et celui du HEAD sont identiques octet pour octet :

```text
SHA-256 :
6dcc6d9f2a23eddc320303e20f9cfb3f70ad9bb25f42b8b5672dc25ba07f6099
```

Les empreintes recalculées des quatre sources déclarées dans `08_PROVENANCE_SOURCES.json` correspondent toutes :

- `books/halloween_2026/page_plan.csv`
- `books/halloween_2026/book.yaml`
- `docs/EDITORIAL_BIBLE.md`
- `docs/QUALITY_GATES.md`

L’empreinte d’archive historique :

```text
3fb4c306302f3739d68f3dbaf6f2b339a2d448cf5097f2212c5fd92ea9d90895
```

est corroborée indépendamment par le fichier déjà suivi `docs/SECURITY_CONTRACT_B2C1.md`. L’archive ZIP elle-même n’est toutefois pas présente dans le périmètre audité et son conteneur ne peut donc pas être re-hashé ici. La provenance substantielle utilisée par le plan reste vérifiable par l’objet Git historique, les sources courantes et les manifestes concordants.

**Résultat : conforme, avec limite documentaire sur le conteneur ZIP d’origine.**

### 4.4 Réconciliation du chemin de fer

Comptages indépendants :

- plan du HEAD : **56 lignes** ;
- CSV du pack : **56 lignes** ;
- CSV consolidé : **56 lignes** ;
- pages : **1 à 56**, continues et uniques ;
- statuts : **56 × `À VALIDER`**.

Les champs source du consolidé correspondent ligne par ligne au plan du HEAD pour :

- le numéro de page ;
- le chapitre ;
- le titre B2-B ;
- le type de mécanique.

Les 16 colonnes du CSV source B3-A sont conservées sans différence dans le CSV consolidé. Les colonnes supplémentaires apportent la réconciliation HEAD/C4, l’état moteur, l’état d’illustration et la provenance.

Répartition observée :

| Zone | Nombre de pages |
|---|---:|
| Ouverture | 2 |
| Invitation | 10 |
| Forêt | 10 |
| Amis | 10 |
| Bonbons | 10 |
| Fête, diplôme compris | 8 |
| Fin | 6 |

Les pages 03–49 contiennent 47 activités, 17 mécaniques distinctes et aucune répétition de mécanique entre deux activités successives.

**Résultat : conforme.**

### 4.5 Cartographie des 34 réponses

Le contrôle indépendant trouve :

- activités fermées de type `graphique` ou `chiffre` : **34** ;
- entrées dans `04_CARTOGRAPHIE_CORRIGES.csv` : **34** ;
- doublons de page source : **0** ;
- activité fermée non cartographiée : **0** ;
- entrée cartographiée ne correspondant pas à une activité fermée : **0** ;
- divergences de titre ou de mécanique entre cartographie et consolidé : **0**.

Répartition constatée :

| Page de corrigés | Nombre de réponses |
|---:|---:|
| 51 | 9 |
| 52 | 9 |
| 53 | 8 |
| 54 | 8 |

Les modèles facultatifs restent distincts des réponses fermées aux pages 09, 19, 29 et 38.

La contradiction entre les titres de chapitre des pages 51–54 et leur contenu réel transversal est explicitement exposée dans les rapports et laissée sous gate humain. Elle n’est ni masquée ni appliquée à la production.

**Résultat : conforme comme proposition documentaire non approuvée.**

### 4.6 Traitement des pilotes C4

Les références ont été contrôlées directement dans le code, la documentation C4 et les tests suivis :

- **p.04** : scène canonique `Aide Pip à trouver la sortie`, labyrinthe à réponse structurée ;
- **p.06** : scène canonique `La lune mystérieuse`, 8 points, contour fermé, ordre `1→8→1`, consignes FR/EN exactes ;
- **p.20** : scène canonique `Retrouve les chapeaux jumeaux`, quatre paires, consigne anglaise canonique utilisant `to`.

Le CSV consolidé :

- distingue les formulations B3-A des références C4 ;
- rend explicitement visible la divergence de titre et de consigne de la p.06 ;
- précise que les propositions ne prévalent pas sur C4 ;
- maintient les écarts de p.04 et p.20 comme reformulations à revoir.

**Résultat : conforme. Aucun écrasement C4 caché.**

### 4.7 Gates et statuts

Les statuts observés sont cohérents et non ambigus :

```text
B3A_PLAN=DRAFT_FOR_REVIEW
EDITORIAL=PENDING
KDP=FORBIDDEN
PRODUCTION_GENERATION=FORBIDDEN
```

Les décisions humaines non satisfaites restent visibles : densité et épreuve à 100 % des corrigés, revue pédagogique 4–5 ans, revue bilingue, choix des illustrations et du lexique, fond perdu et prépresse.

Aucun statut `approved`, `ready_for_kdp=true` ou `human_approved=true` n’est attribué à la proposition.

**Résultat : conforme.**

### 4.8 Absence d’assets et de sorties de production

Composition du dossier B3-A observé :

- 15 fichiers Markdown ;
- 3 CSV ;
- 4 JSON ;
- 1 XLSX.

Contrôles négatifs :

- PDF : **0** ;
- PNG/JPEG/GIF/WebP/SVG/TIFF ou fichier de création graphique : **0** ;
- signature binaire PDF ou image dissimulée : **0** ;
- média embarqué dans le XLSX : **0** ;
- macro ou lien externe dans le XLSX : **0** ;
- fichier de production non suivi hors du dossier documentaire : **0**.

**Résultat : conforme. Aucun indice de génération des 56 pages, d’asset nouveau ou de PDF de production.**

## 5. Findings classés

| Classe | Nombre |
|---|---:|
| BLOCKER | **0** |
| MAJOR | **0** |
| MINOR | **2** |

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
