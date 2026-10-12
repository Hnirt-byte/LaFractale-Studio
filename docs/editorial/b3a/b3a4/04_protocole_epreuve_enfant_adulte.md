# Protocole reproductible enfant–adulte (4–5 ans) — proposition B3-A.4

## Statut et trois niveaux de preuve

| Niveau | Support admis | Peut établir | Ne peut pas établir |
|---|---|---|---|
| Validation documentaire | CSV, matrices, hashes, sources | identité des pages, correspondance textes/corrigés, couverture des mécanismes | compréhension, motricité, fatigue, lisibilité réelle |
| Prototype non final | extraits Letter 100 % avec `NON PRODUCTION` | procédure, défauts grossiers, faisabilité logistique | clôture de MAJOR-03/04, difficulté finale, représentativité production |
| Épreuve représentative production | livre complet 56 p., impression, reliure, visuels et corrigés réellement prévus | observations formatives sur l’usage de l’artefact prévu | certification populationnelle ou clôture automatique de MAJOR |

Les résultats des prototypes NON PRODUCTION ne sont jamais agrégés à ceux d’une épreuve représentative.

## Prérequis matériels

- impression Letter 8,5 × 11 pouces à **100 %**, sans « ajuster » ;
- pour toute épreuve représentative : pagination 1–56, marge/gouttière/papier/reliure/illustrations/réponses représentatifs, SHA-256 du PDF et code de lot d’impression consignés ;
- p.04/p.06/p.20 identiques aux pilotes C4 ;
- aucune collecte de vrai prénom : p.56 utilise le jeton de test `PIP`.

## Échantillon des pages à observer

Chaque session couvre au minimum une activité par chapitre et par famille de mécanisme. L’échantillon total doit inclure :

- pilotes : p.04, p.06, p.20 ;
- respirations : p.42, p.45, p.47 ;
- séquence p.40–47 en ordre réel, pour la fatigue cumulative ;
- au moins un exemple de `coloring`, `find_count`, `shadow_match`, `trace_paths`, `count`, `match_vocabulary`, `spot_differences`, `pattern`, `path_logic`, `pair_matching`, `sort`, `one_to_one`, `maze`, `connect_dots`, `match`, `creative_color` ;
- les six corrigés p.49–54 ; le lexique p.55 ; le diplôme/clôture p.56.

La matrice détaillée de sélection est à arrêter par le responsable pédagogique avant recrutement ; aucune taille d’échantillon n’est approuvée par ce document.

## Déroulement contrôlé

1. L’adulte lit la consigne imprimée une fois, puis peut la répéter une fois sans reformulation.
2. Après 10 secondes sans initiation : prompt neutre « Montre-moi ce que tu penses qu’il faut faire. »
3. Pas de réponse, de modèle de réussite ni de correction pendant l’activité.
4. Arrêt immédiat à la demande de l’enfant ou en cas de détresse ; aucune incitation à terminer.
5. Durée, compréhension, geste, lisibilité, aide et transitions sont observés ; les activités libres ne sont pas notées pour leur qualité graphique.

## Variables observables

`page`, `chapter`, `mechanic`, `difficulty_band`, `first_action`, `latency_seconds`, `duration_seconds`, `instruction_repeat_count`, `assistance_max_0_4`, `completion_status`, `closed_answer_status`, `frustration_0_3`, `engagement_0_3`, `correction_lookup_seconds`, `correction_link_status`, `layout_issue_codes`, `transition_reaction`, `print_issue_codes`.

Échelle d’aide : 0 aucune ; 1 répétition verbatim ; 2 pointage ; 3 geste analogue sans réponse ; 4 abandon/reprise adulte.

## Cas spécifiques

- Corrigés p.49–54 : mesurer le repérage par l’adulte, la lisibilité du renvoi et toute confusion de mini-solution ; ne jamais les utiliser pour noter l’enfant.
- Lexique p.55 : lecture accompagnée de paires ; aucun décodage autonome demandé.
- p.56 : l’enfant écrit `PIP`, dessine dans le cercle, puis l’observateur relève toute collision fonctionnelle entre prénom, cercle, consigne, cadre et réserve d’illustration. La preuve ergonomique exige impression 100 %, diamètre imprimé et zone utile mesurés dans la fiche d’épreuve.

## Protection des données

Interdits dans GitHub et dans le dataset : noms, initiales, dates de naissance, coordonnées, école, photos/vidéos/audios, écriture enfantine scannée, diagnostic, citation identifiable, adresse IP ou identifiant stable inter-étude.

Utiliser seulement un `dyad_id` aléatoire à usage unique, une tranche d’âge (`48_59` ou `60_71` mois), langue de consigne, numéro de séance et codes d’observation. Consentement et table de recrutement restent hors dépôt et hors dataset. Toute PII accidentelle est supprimée avant archivage.

`MAJOR-03` reste `OPEN` : un prototype utilisant des illustrations absentes ou une mise en page non représentative ne peut pas le fermer.
