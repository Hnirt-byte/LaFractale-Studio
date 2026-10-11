# LaFractale Studio — B3-A · Dossier de conception éditoriale

**Statut : PROPOSITION POUR REVUE, PAS APPROBATION.** Réalisé le 11 octobre 2026.

## Décision de méthode

La phase B2-C4 a été fusionnée sur `main` (commit `397bc32c042dcd5533296ac7fe76b6a3ad749347`, tree `72215ac28de46795338997be0bb38781274e80f4`), selon le rapport post-fusion. Ce pack n'est **pas** une copie du dépôt courant : il consolide les intentions du `page_plan.csv` et du `book.yaml` historiques **B2-B** pour préparer la réconciliation sur le HEAD réel.

Nous **ne générons pas** 56 pages ni ne modifions `books/` pendant B3-A. Nous validons un plan éditorial, puis seulement les étapes suivantes porteront sur moteur, nouveaux visuels, génération et prépresse.

## Contenu du pack

- `01_CONTRAT_B3A_v1.0.md` : périmètre, invariants, interfaces et critères d'acceptation.
- `02_CHEMIN_DE_FER_56_PAGES.csv` : les 56 pages, champs exploitables.
- `02_CHEMIN_DE_FER_56_PAGES.xlsx` : classeur modifiable et tableaux de contrôle.
- `03_CHEMIN_DE_FER_LISIBLE.md` : version lisible, consignes FR/EN proposées.
- `04_CARTOGRAPHIE_CORRIGES.csv` : proposition 9/9/8/8 pour 34 corrigés objectifs, **non validée**.
- `05_BIBLE_ET_PROGRESSION.md` : 5 chapitres, 18 mots, règles pédagogiques et poses Pip.
- `06_GATES_RECETTE.md` : contrôle automatisable et décisions humaines.
- `07_PROMPT_HERMES.md` : mission docs-only et audit indépendant.
- `08_PROVENANCE_SOURCES.json` : empreintes des sources historiques et référence de `main`.
- `09_REFERENCES_KDP.md` : exigences d'impression sourcées, sans statut prêt à publier.

## Synthèse chiffrée

- **56 pages intérieures**, dont **2 pages d'ouverture (01–02)**, **47 pages d'activités (03–49)**, **1 diplôme (50)**, **4 pages de corrigés (51–54)**, **1 lexique (55)** et **1 clôture (56)**.
- Cinq chapitres : Invitation 10 p., Forêt 10 p., Amis 10 p., Bonbons 10 p., Fête 8 p. diplôme inclus.
- **34 pages nécessitant des corrigés objectifs**, plus 4 pages de tracé avec modèle facultatif. Ce ratio rend les pages 51–54 **à risque de surcharge**.
- Les 18 paires FR/EN canoniques de `book.yaml` sont conservées.
- Les pages 04, 06 et 20 sont des pilotes B2-C4. Leur formulation proposée doit être contrôlée contre le commit fusionné, pas seulement contre l'archive B2-B.

## Décision éditoriale à rendre avant B3-B

1. **Corrigés :** confirmer 4 pages après une épreuve à taille réelle, ou réallouer la pagination dans une V2 soumise à approbation.
2. **Titre et consignes :** validation française et anglaise des 47 exercices, particulièrement pour la lecture accompagnée 4–5 ans.
3. **Images non approuvées :** les nouveaux décors, 18 éventuels pictogrammes du lexique et nouvelles scènes ne sont pas des assets autorisés. Aucun usage automatique.
4. **Intérieur sans fond perdu :** direction privilégiée, à confirmer sur les 56 pages finales et dans le fichier book.yaml à l'étape adéquate.

**Publication KDP : FORBIDDEN.** La validation de B3-A n'est pas une autorisation de création finale ou de commercialisation.
