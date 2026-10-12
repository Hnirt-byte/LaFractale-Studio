# B3-A — Recette éditoriale et audits indépendants

## Portes documentaires automatisables
- `A01` : 56 numéros consécutifs sans doublons.
- `A02` : structure de pages cohérente : ouverture 2, chapitres 48 (dont diplôme 1), corrigés 4, lexique 1, clôture 1.
- `A03` : les trois pilotes 04/06/20 clairement marqués ; le changement de leur contenu par rapport à C4 n'est pas silencieux.
- `A04` : chapitres et objectifs propres aux tranches 4–5 ans ; au moins 8 mécaniques distinctes dans les activités.
- `A05` : absence de répétition de même mécanique sur deux fiches d'activité consécutives, sauf justification.
- `A06` : vocabulaire compté sur les 18 entrées canoniques ; traductions manuelles restent à valider.
- `A07` : toute activité fermée possède un type de correction; 34 activités corrigibles cartographiées sur pages 51–54 de manière provisoire.
- `A08` : profils Pip indiqués comme intentions éditoriales non activables dans le moteur.
- `A09` : aucune pièce KDP déclarée approuvée, aucun PDF commercial.
- `A10` : comparaison source B2-B → main B2-C4 → proposition B3-A incluse et hashée.

## Validation humaine par fiche (checklist à renseigner)
- [ ] L'enfant comprend visuellement le geste demandé avec lecture par un adulte.
- [ ] Le temps et le niveau ne créent pas de frustration disproportionnée.
- [ ] Les quantités/nombres sont adaptés à l'âge annoncé.
- [ ] La réponse unique est démontrée pour les jeux fermés.
- [ ] Le français est clair ; l'anglais naturel et grammaticalement correct.
- [ ] Le visuel ne nécessite pas une couleur absente du N&B.
- [ ] Pip n'est pas un obstacle ni une distraction.
- [ ] Aucune illustration non approuvée ne passe en production.
- [ ] Les éléments graphiques sont distincts des pages voisines.
- [ ] La page est lisible et utilisable en impression réelle.

## Deux audits
**Audit A : structure et traçabilité.** Compare `page_plan.csv` historique et actuel, identifie les divergences, vérifie 56 numéros, les besoins de solutions, champs complets, provenance, statuts, no-change des fichiers protégés. Résultat `PASS` ou `FAIL`, findings reproductibles.

**Audit B : pédagogie et bilinguisme.** Contrôle la progression 4–5 ans, diversité, densité, clarté des consignes, fidélité FR/EN, cohérence histoire/vocabulaire, facilité des exercices et faisabilité de quatre pages de corrigés. Rend `PASS`, `PASS_WITH_OPEN_DECISIONS` ou `FAIL`; ne prétend pas qu'une QA automatisée constitue une vraie séance enfant.

## Règle spécifique corrigés
Les 34 jeux fermés représentent en moyenne 8,5 solutions par page de corrigé, auxquelles pourraient s'ajouter des modèles de tracé. Aucune maquette à l'échelle n'a encore démontré la lisibilité de 9 mini-solutions sur une page 8.5×11. **Il est interdit d'approuver B3-B sur la base du seul tableau 9/9/8/8.**

Si nécessaire, proposer 2 variantes sous 56 pages :
1. **Quatre pages**, avec réponses compactes seulement lorsque cela préserve l'identification des solutions et renvoi explicite aux pages sources ; imprimer 100 % pour essai.
2. **Six à huit pages**, avec réallocation documentée de 2–4 pages d'activités (ou autre réduction explicite). Ne pas réduire silencieusement le livre, le vocabulaire ni la densité des contenus.

## Statuts finaux
`B3A_PLAN=DRAFT_FOR_REVIEW` jusqu'à validation humaine du plan et de l'espace corrigés ; `KDP=FORBIDDEN`, `EDITORIAL=PENDING`. Une PR documentaire fusionnée ne vaut pas validation d'impression.
