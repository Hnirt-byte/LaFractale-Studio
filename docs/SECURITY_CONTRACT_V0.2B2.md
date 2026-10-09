# LaFractale Studio V0.2-B2 — Contrat préalable de conception et de sécurité

**Statut : CONTRAT VALIDÉ / B2-A IMPLÉMENTÉ LOCALEMENT / REVUE INDÉPENDANTE EN ATTENTE**
**Base figée :** `v0.2.0b1`, commit `241d8189b3a450cf2d95acb25aad07b099e58952`
**Objet :** intégrer des illustrations approuvées aux fiches de démonstration, sans affaiblir les contrôles V0.2-A et V0.2-B1.

## 1. Périmètre fonctionnel et exclusions

- Introduire une bibliothèque d'**illustrations rattachées à un livre** et à une variante d'impression. Chaque image aura un identifiant, un rôle (compagnon, décor, pictogramme), un format d'usage, ses dimensions, son SHA-256 et un état de validation humaine.
- Préparer une API qui compose un visuel approuvé dans le `companion_slot` et, plus tard, dans des emplacements graphiques dédiés. Les rectangles et le contenu ne pourront pas être déformés ou faire sortir des objets des marges.
- Autoriser provisoirement uniquement les PNG raster décodés de manière stricte. SVG, PDF, fichiers distants, scripts, URL et formats convertis implicitement sont exclus du premier lot.
- Conserver sans modification les trois algorithmes d'activités, leurs solutions et le blocage de génération des livres complets.
- Maintenir les mentions `VISUEL À VALIDER`, `needs_visual_review` et `publication_approved=false` tant que tous les visuels et contrôles humains ne sont pas approuvés.
- **Aucune génération automatique de compagnon validé**. Pas d'invention du compagnon de Noël. Pip demeure exclusif à Halloween ; l'illustration couleur actuelle reste une **référence**, jamais une variante imprimable noir et blanc approuvée par défaut.

## 2. Frontières de confiance

| Entrée ou état | Niveau de confiance | Comportement exigé |
|---|---|---|
| YAML de livre, plan CSV, métadonnées graphiques | Non fiable | Validation complète du schéma, du texte, de l'identité et des limites quantitatives |
| Chemins de ressources, fichiers PNG | Non fiables tant qu'ils ne sont pas vérifiés | Chemins ancrés, sans `..` ni symlink ; lecture sans suivi de lien ; limites de taille et de pixels ; décodage contrôlé |
| Approbation et restrictions d'usage | Source éditoriale **distincte et approuvée** | Ne jamais déduire « approuvé » du livre ni du manifeste généré ; comparaison à la source de confiance |
| Registre du compagnon et source du livre | Vérifiés par les gardes-fous existants | Revalidation avant tout rendu et avant publication ; aucune substitution entre livres |
| Données d'activité et de composition | Non fiables si mutables | Instantané profond / structure immuable et revalidation géométrique du contenu remis au renderer |
| PDF, JSON, aperçu et manifestes générés | Non fiables pour l'audit | Relecture via le dossier ancré, politique obtenue depuis le livre approuvé, checksums recalculés et inspection des visuels |
| Code Python exécuté avec les mêmes droits | Hors périmètre | Pas de prétention de sandbox ; séparation de processus nécessaire pour ce scénario |

## 3. Règles obligatoires pour les images

1. **Fichier identifié par contenu** : empreinte SHA-256 de ses octets, rôle, livre autorisé et variante nommée. Rejeter une entrée avec empreinte absente, modifiée ou dont le rôle/livre diffère.
2. **Référence et variante distinctes** : `pip_officiel_couleur.png` reste protégé par son hash actuel `b54194f0cf3be821d38d08e2c7b9b177292b90175faa2180ccb34cdccd8e295c`. Une variante noir et blanc de Pip aura son propre fichier, sa propre empreinte et une approbation explicite.
3. **Un seul décodeur et format acceptés pour B2-A** : PNG local, format réellement vérifié (et non par extension), sans contenu réseau ou scripts. Refuser les images malformées, énormes, tronquées, formats inattendus ou multipages ; définir et tester des limites configurées mais bornées de taille, résolution et nombre de pixels.
4. **Lecture sécurisée et stabilité** : utiliser les primitives de fichiers déjà sécurisées ; ne pas rouvrir un chemin utilisateur après validation pour le rendre. Charger les octets vérifiés dans un instantané en mémoire, puis ne rendre qu'à partir de cet instantané.
5. **Gris/noir et blanc** : aucune insertion implicite de la référence couleur dans le PDF intérieur. La variante doit être approuvée et conforme au mode d'impression défini pour le livre ; aucune conversion silencieuse de palette.
6. **Aucun fallback trompeur** : si un visuel exigé manque, est refusé ou n'est pas approuvé, échec explicite ou maintien du placeholder technique, selon le mode demandé. Jamais remplacement automatique par un autre compagnon.
7. **Métadonnées non souveraines** : le nom du fichier, le YAML, les PNG, les JSON de sortie ou le manifeste ne peuvent pas modifier les autorisations éditoriales, les noms réservés ou l'état d'approbation.
8. **Rendus en image ou vecteur** : la QA textuelle PyMuPDF ne voit pas nécessairement les mots figurant en pixels. La garantie est donc fondée sur la provenance de visuels approuvés, des comparaisons d'empreintes et une revue visuelle, non sur une prétendue détection OCR exhaustive.

## 4. Contrôles graphiques et pédagogiques

- Vérifier l'inclusion dans les zones autorisées, les proportions conservées, la résolution réelle d'impression, l'absence de rognage et les collisions avec textes/consignes, numéros et jeux.
- Conserver les caractères et contrastes compatibles avec des enfants de 4–5 ans ; contrôler les légendes bilingues (français et anglais) et les instructions sans dévoiler les solutions.
- Tester l'insertion du même visuel approuvé dans les PDF fiche/corrigé, ainsi que les compositions sans compagnon pour Noël `pending_selection`.
- Contrôler les PDF à la fois par extraction structurée et par rendu de **chaque page** aux dimensions cibles, puis imposer une revue humaine formelle.
- Conserver l'interdiction d'export KDP complet et l'approbation visuelle manuelle.

## 5. Scénarios adversariaux prévus **avant développement**

1. Image PNG remplacée après chargement, symlink sur sa feuille ou un parent, chemin contenant `..`, fichier spécial ou chemin extérieur au namespace.
2. Faux PNG par extension, PNG tronqué, charge d'image démesurée, image incompatible, métadonnées malformées, saturation mémoire/CPU.
3. Variante couleur Pip utilisée comme noir et blanc sans validation ; variant `approved` forgé dans le YAML ou le manifeste ; ressource Pip reliée à Noël.
4. Companion Noël `pending_selection` avec identifiant, nom, placement ou asset Pip falsifié dans le livre et dans la composition.
5. Mutation de l'objet activité, du rectangle, des métadonnées d'illustration ou des pixels après validation mais avant le rendu.
6. PDF/JSON/manifeste/aperçu falsifiés après génération, checksums recalculés, sortie auditée par symlink ; audit refusant tout contexte non approuvé.
7. Échec de lecture/de décodage/rendu au milieu du build : aucune publication de nouveau PDF partiel, ancienne démo conservée. Publication et restauration échouant : sauvegarde récupérable conservée.
8. Deux générations avec seed, sources et versions identiques : PDF, manifestes, JSON et aperçus identiques octet par octet.
9. Aucun ajout, suppression ou affaiblissement des tests adversariaux 247/247 de B1.

## 6. Critères d'acceptation

- [x] Contrat revu et validé avant tout code par le responsable du projet.
- [ ] Inventaire d'images et droits d'usage explicitement approuvés pour chaque livre.
- [ ] Tests unitaires, intégration, QA/CLI, matrice adversariale et déterminisme réussis.
- [ ] SHA Pip officiel inchangé et aucune présence de Pip dans les sorties Noël.
- [ ] Comparaison avec le code exact du tag `v0.2.0b1` ; zéro régression des 247 tests.
- [ ] Toutes les nouvelles fonctions de chargement, composition et rendu ont été examinées pour les traversées de chemins, TOCTOU, sources de confiance et rollback.
- [ ] Revue indépendante après tests locaux, avec scénarios de reproduction détaillés en cas d'échec.
- [ ] Revue humaine de chaque page PDF et de chaque visuel ; marquage « technique » conservé jusqu'à validation.
- [ ] PR uniquement après validation ; pas de fusion automatique, pas de publication KDP.

## 7. Découpage proposé

**B2-A — infrastructure de visuels approuvés** : registre, schéma, vérification et chargement d'octets, intégration au layout avec placeholders par défaut, tests de sécurité ; aucun personnage nouveau créé.

**B2-B — variantes et visuels réels** : proposer et faire approuver **visuellement** une version noir et blanc de Pip distincte de la référence couleur, produire des petits décors et pictogrammes pédagogiques, puis enregistrer leurs empreintes et approbations.

**B2-C — placement, pré-presse technique et revue** : vérification de résolution, placement, lisibilité, séquence d'activités et impressions d'essai. Aucune déclaration « prêt KDP » avant les étapes finales.

**Décision requise avant codage** : validation du présent contrat et du mode d'impression noir et blanc/échelle de gris pour le premier cahier Halloween.

## 8. Addendum d'implémentation B2-A

- Aucun visuel publiable n'est livré dans le registre initial ; `assets/illustrations/approvals.json` contient `illustrations: []`.
- L'appel explicite exige `illustration_id` et un **SHA-256 externe de registre** transmis par l'opérateur qui a approuvé la révision de ce registre. Un hash recalculé depuis la sortie, le YAML ou le registre lui-même ne prouve pas l'approbation.
- Sous-ensemble PNG admissible : 8 bits en niveaux de gris, chunks `IHDR`/`IDAT`/`IEND` uniquement, CRC vérifiés, aucune métadonnée, palette, transparence, couleur, trame animée ni données après IEND, max. 8 Mo et 8 millions de pixels, chaque côté ≤ 4096 px. Le rendu se fait depuis des **octets validés et capturés**, jamais en rouvrant le chemin.
- Le rôle implémenté dans le slot est uniquement `companion`. Les futurs décors/pictogrammes exigent une nouvelle revue de sécurité et de placement.
- L'audit avec image exige le même contexte externe que le build ; il compare les pixels décompressés de chaque image PDF au PNG approuvé, contrôle son emplacement, puis compare les pixels de chaque aperçu à un nouveau rendu des PDF.
- La sortie sans visuel conserve le placeholder technique. Les audits sans contexte refusent une sortie contenant un visuel, même si le manifeste fournit des empreintes.
- Les champs `human_approved` et les SHA locaux ne constituent **pas** à eux seuls une preuve d'approbation humaine ou de droits de reproduction : gouvernance de la PR, vérification de la licence et remise séparée du digest attendu restent nécessaires.
- Hors périmètre : sandbox de code Python hostile de même UID, autorité cryptographique contre un opérateur qui pourrait remplacer la valeur du hash externe, garanties de persistance après coupure électrique, détection OCR de texte dessiné en pixels.

- **B2-A, anti-falsification des PDF :** lorsqu'une illustration est activée, l'audit reconstruit les PDF avec le livre et le catalogue approuvé pour les comparer octet par octet. Les aperçus PNG sont eux-mêmes comparés pixel par pixel à la page PDF recalculée. Cette régénération ne remplace pas la revue visuelle ni le contrôle des droits.

## 9. B2-A : rectification après revue indépendante (audit par rejeu canonique)

- **Package installable :** la version PEP 440 est `0.2.0b2` ; `B2-A1` est le nom du lot fonctionnel, pas un suffixe de version Python. L'installation éditable fait partie des critères bloquants.
- **Sources de confiance :** le `Book` chargé et revérifié, son catalogue compagnon et, le cas échéant, le registre de variantes épinglé via le SHA-256 transmis hors artefacts. Ni le manifeste, ni les JSON, ni un aperçu ne définissent l'autorité.
- **Audit universel :** `audit_output()` régénère depuis ces sources **les deux PDF même en mode placeholder**, `activities.json`, `quality_report.json`, `quality_report.md` et toutes les pages d'aperçu. Chaque fichier est comparé octet par octet à la version régénérée ; la liste des aperçus doit aussi correspondre. Les essais d'altération avec checksums recalculés sont obligatoires.
- **Schéma manifeste :** le dictionnaire complet du manifeste est comparé à celui généré par les sources vérifiées. Les propriétés inconnues, les faux statuts, seeds incohérents, assets et champs sémantiques falsifiés échouent. L'horodatage doit être ISO 8601 UTC canonique.
- **Limites explicites :** sans attestation externe, un horodatage UTC *syntaxiquement valide* reste déclaratif et le seed demandé est celui annoncé par le manifeste ; l'audit vérifie la conformité des fichiers à ce seed, pas l'authenticité de la demande initiale. Cette QA ne constitue ni signature, ni preuve de droits. Une certification d'un build exact nécessiterait de pinner le seed/temps en dehors des sorties.
- **Tests d'injection :** mutations indépendantes des JSON d'activités, champs graphiques/humains du rapport qualité, Markdown, overlays vectoriels dans chacun des deux PDF, aperçus modifiés et manifestes falsifiés ; tests illustrés et sans illustration. L'ancienne génération doit survivre aux échecs de build.
- **Principe de revue :** un audit par rejeu utilise le renderer de confiance, non un hook de faute temporairement substitué dans un test. Après vérification d'un rollback, restaurer ce renderer avant de vérifier le dossier préexistant.


## 10. Addendum B2-A : décodage strict des JSON non fiables

- **Menace** : les sorties de génération (`manifest.json`, `activities.json`,
  `quality_report.json`) et le registre d'illustrations sont des fichiers JSON
  qui peuvent être modifiés indépendamment. Une paire de clés identiques dans
  le même objet peut être lue différemment par des logiciels `first-key-wins`
  ou `last-key-wins`, même quand les autres checksums ont été recalculés.
- **Frontière** : tout décodage de ces entrées doit passer par
  `lafractale.security.strict_json.loads_strict`, y compris les manifestes
  canoniques relus lors de la régénération de confiance. Ne pas employer
  `json.loads()` / `json.load()` directement pour un artefact ou un registre.
- **Règle** : rejeter les noms de clés dupliqués à **chaque niveau** des objets
  JSON, y compris sous des objets imbriqués ou des éléments de tableaux et
  après décodage des séquences `\uXXXX` ; rejeter les constantes non standard
  `NaN`, `Infinity`, les flottants non finis et les chaînes Unicode malformées.
  Une profondeur de document excessive est également rejetée.
- **Autorité** : une empreinte SHA-256 externe du registre ne rend pas
  acceptable un registre JSON ambigu ; les checksums déclarés dans un
  manifeste ne rendent pas acceptable un artefact ambigu. La comparaison avec
  les artefacts régénérés reste obligatoire, **après** le parsing strict.
- **QA** : en cas de JSON ambigu, `audit_output()` doit retourner au moins une
  erreur et `python -m lafractale qa` un code non nul. Aucun statut de
  publication ne peut être déclaré approuvé sur cette base.
- **Limites** : ces règles règlent l'ambiguïté JSON, pas l'authenticité
  cryptographique d'un manifeste non signé ni l'exécution de code hostile
  dans le même processus.

## 11. Addendum B2-A : inventaire fermé des sorties auditées

- **Menace** : un attaquant ayant accès au répertoire de livraison peut ajouter
  une fausse approbation (`ready_for_kdp.txt`), un PDF supplémentaire, une entrée
  cachée, un sous-répertoire ou un aperçu factice sans toucher aux empreintes
  attendues du manifeste. Une QA « verte » ne doit jamais accompagner des
  fichiers qui n'ont pas été régénérés et vérifiés.
- **Règle** : `audit_output()` impose l'égalité exacte de l'inventaire racine
  avec `interior.pdf`, `answer_key.pdf`, `activities.json`, `quality_report.json`,
  `quality_report.md`, `manifest.json`, `previews/`. Aucun autre nom, y compris
  fichier caché ou sous-répertoire, n'est autorisé. Les six fichiers doivent
  être des fichiers réguliers et `previews/` un vrai répertoire, jamais des
  symlinks, pipes ou objets spéciaux.
- **Aperçus** : `previews/` ne peut contenir que les fichiers
  `page_01.png` ... `page_NN.png`, où le nombre de pages provient du plan
  approuvé, et non du manifeste. Aucun fichier supplémentaire, dossier,
  symlink ou aperçu manquant n'est admis.
- **Frontière** : l'inventaire est lu à travers la racine auditée ancrée par
  un descripteur ; l'ouverture du sous-répertoire `previews` emploie
  `O_DIRECTORY|O_NOFOLLOW`. Les checksums du manifeste ne peuvent jamais
  élargir la liste des sorties autorisées.
- **Échec** : le contrôle de l'inventaire précède la lecture du manifeste et
  le rejeu des PDF ; toute différence rend la QA non conforme. Lors d'une
  reconstruction rejetée, le répertoire publié précédent reste intact.
- **Limites** : le contrat couvre un dossier stable pendant l'audit, pas un
  adversaire pouvant manipuler les entrées simultanément au sein du même UID.
  Aucun « QA TECHNIQUE OK » ne certifie une approbation graphique, humaine
  ou une publication KDP.
