# Contrat de sécurité V0.2-B1 : texte et génération

> Ce contrat définit les gardes-fous *avant* revue d'intégration. Les tests locaux ne
> remplacent ni une revue indépendante ni une certification de sécurité.

## Frontières de confiance

1. **Non fiables** : texte de tout YAML éditorial, clés et valeurs du catalogue,
   lignes du plan CSV, données d'activités (y compris produites/modifiées en
   mémoire), chemin de destination, contenu des artefacts à auditer.
2. **Vérifiés** : instantanés de sources et catalogue, appartenances des
   compagnons aux livres, somme SHA-256 du personnage approuvé, copie profonde
   figée des activités entre validation et rendu, sorties de génération.
3. **Hors périmètre** : exécution arbitraire de code Python hostile avec le même
   compte système, concurrence sur des répertoires modifiables par un autre
   processus du même UID, coupure système/absence de fsync, contenu malveillant
   exclusivement dessiné en pixels/vecteurs sans texte PDF extractible.
   Ces cas exigent un processus isolé, droits restreints et/ou d'autres outils.

## Politique Unicode (`NFKC-Latin-no-ignorable-v1`)

- **Une représentation unique :** contrôler NFKC et *rejeter* une chaîne qui
  change après normalisation. Ne pas normaliser silencieusement les données
  après leur approbation. Conserver les accents français précomposés.
- Refuser les caractères de format Unicode `Cf`, les surrogates `Cs`, les
  contrôles (sauf tab/retour/fin de ligne), et les principaux caractères
  `Default_Ignorable` d'autres catégories : CGJ U+034F, variations U+FE0F /
  U+E0100, fillers et points réservés.
- **La V0.2-B1 est strictement française/anglaise** : lettres limitées à une
  liste explicite de lettres latines européennes courantes ; les caractères
  cyrilliques, grecs, le `ı` sans point et les faux small caps sont rejetés.
  Avant d'ajouter une nouvelle langue, versionner et auditer cette liste.
- Chercher les identités non autorisées *après* canonicalisation, avec `casefold`
  et délimitation en mots. Le catalogue est la source d'autorité. Un livre
  `pending_selection` n'exempte aucun compagnon.
- Les sorties Noël ne doivent pas contenir « Pip » en clair. Le manifeste
  contient uniquement les **empreintes SHA-256 des noms réservés**, avec leur
  longueur en mots, afin que `audit_output()` puisse détecter ces noms dans
  le texte PDF et JSON sans réintroduire leur orthographe dans le manifeste.
  Ces empreintes ne sont pas des signatures cryptographiques de fichiers.

## Contrôles obligatoires par frontière

| Entrée/phase | Contrôle |
|---|---|
| Catalogue et asset | Chemin `openat/O_NOFOLLOW`, namespace, empreinte et métadonnées Unicode |
| YAML / plan CSV | Toutes les chaînes, clés incluses, NFKC/ignorable/lettres autorisées et compagnons réservés |
| Après `load_book` | Snapshot SHA-256 YAML/CSV/catalogue, profils canoniques et autorisations revérifiés |
| Activités générées | Copie indépendante et vérification de toutes les chaînes avant premier rendu |
| `write_pdf` | Snapshot de géométrie immuable, validation textuelle à l'entrée, sortie créée exclusivement |
| Après rendu et avant manifeste | Extraction PyMuPDF de tous les PDF, même garde-fou, vérification JSON et profil |
| `audit_output` | Vérification Unicode de manifest/report/activities JSON, rapport Markdown et texte extrait des PDF ; chemins symlinkés des JSON/MD rejetés |
| Publication | Staging privé, audit avant remplacement, rollback conservateur en cas de double échec |

## Matrice adversariale couverte

- `P\u200Bip`, `P\u200Cip`, `P\u200Dip`, `P\u00ADip`, `P\u2060ip`,
  `P\uFEFFip`, ainsi que U+034F, U+FE0F, U+E0100, U+061C, U+180F, U+3164.
- Fullwidth `Ｐｉｐ`, NFKC non canonique, espace insécable, caractères
  cyrilliques/grecs, i sans point et small caps.
- Variation dans YAML, CSV, catalogue, activité générée, entrée PDF directe,
  intervention lors du rendu, JSON modifié avec checksum recalculé, PDF final,
  rapport Markdown et symlink `activities.json`.
- Pour chaque mutation YAML du groupe invisible, le dernier manifeste/PDF
  valide est préservé octet par octet et continue à réussir `audit_output`.
- **Toutes les vulnérabilités B1 précédentes** : parents de sortie symlinkés,
  `write_pdf()` refus d'écraser, données de géométrie immuables, double échec
  de publication et restauration conservant le backup et ses fichiers.

## Critères de sortie avant toute PR

1. Le patch incrémental **et** le patch complet s'appliquent proprement sur
   leur base propre, puis produisent exactement les mêmes sources.
2. Le test adversarial exact d'Hermes est rejoué indépendamment du seul pytest.
3. `pytest`, validation YAML, build-demo, QA, revue PDF, déterminisme avec
   `SOURCE_DATE_EPOCH`, SHA de Pip et absence de Pip pour Noël sont verts.
4. La revue indépendante n'identifie aucune nouvelle vulnérabilité
   reproductible **dans le périmètre ci-dessus**.
5. Seulement alors : commit sur la branche de travail, push et PR sans fusion.

Attention : l'audit textuel des PDF dépend de la qualité de l'extraction
PyMuPDF. Un texte converti en chemin vectoriel ou en image n'est pas
contrôlable par simple extraction et nécessite une revue visuelle distincte.

## Audit indépendant des artefacts (durcissement post-B1)

`manifest.json`, les PDF, les JSON et les empreintes internes au manifeste
sont **non fiables** : ils ne peuvent pas définir la liste des noms réservés.
`audit_output(out, book=book)` exige un `Book` préalablement validé via
`load_book()` et réévalue son instantané YAML, son plan et son catalogue.
Sans contexte : **échec fermé**, même lorsque tous les checksums concordent.
La valeur `blocked_name_fingerprints` du manifeste est uniquement une
*assertion à comparer* aux empreintes recalculées depuis les sources approuvées,
jamais une source de politique. L'identité du livre, le compagnon et les
empreintes des sources doivent également correspondre aux données approuvées.

La commande CLI utilise désormais :
`python -m lafractale qa <répertoire> --book <YAML-source-de-confiance>`.
Le chemin `--book` doit être choisi indépendamment du manifeste et ne peut pas
être déduit du champ `source.book_config` du manifeste non fiable.

**Limite explicite :** les checksums non signés ne prouvent pas l'authenticité
d'un artefact intégralement réécrit. Cet audit vérifie la cohérence et les
interdictions éditoriales contre une source approuvée, pas une signature
cryptographique ni une attestation contre un adversaire modifiant la source.

## Addendum de sécurité : frontières lexicales et racine de QA (2026-10-09)

### Risque et règles vérifiables

- **Tous les textes en entrée et toutes les sorties auditées sont non fiables**,
  même si les checksums de leur manifeste sont cohérents. Les règles des noms
  interdits sont toujours recalculées depuis le livre et le catalogue approuvés.
- Les jetons de noms de compagnons sont formés **uniquement de lettres Unicode**
  acceptées par l'alphabet éditorial. Chiffres, `_`, séparateurs et ponctuation
  sont des frontières lexicales : `Pip_`, `_Pip`, `Pip2`, `Pip-2` et `(Pip)`
  déclenchent la même interdiction que `Pip` dans un livre sans ce compagnon.
  En revanche, un autre mot comme « pipette » ne devient pas artificiellement
  interdit. La tokenisation est identique pendant la génération et la QA.
- Les marques combinantes `Mn`, `Mc`, `Me` sont refusées **avant** la tokenisation,
  même lorsqu'elles sont compatibles avec NFKC : cela bloque `P\u0338ip` et
  `P\u0332ip`. Les accents français précomposés restent autorisés.
- Les API d'audit utilisent un **descripteur de répertoire racine** ouvert avec
  `openat` + `O_DIRECTORY` + `O_NOFOLLOW`, après vérification de tous les parents.
  Elles ne doivent **jamais appeler `Path(out).resolve()` sur un chemin fourni par
  l'appelant**. Le descripteur reste ouvert pendant le contrôle des artefacts ;
  les chemins lus sont ancrés via `/proc/self/fd/<fd>`.
- Les erreurs de racine absente, symlinkée ou traversant `..` font échouer
  `audit_output(out, book=book)` avec au moins une erreur et `qa` avec un retour
  non nul. L'audit normal d'un répertoire ordinaire doit continuer à réussir.

### Tests adversariaux exigés avant intégration

- Modifier `activities.json`, `quality_report.json`, `manifest.json` ou
  `quality_report.md` avec chaque attaque lexicale, et recalcuer les checksums
  des artefacts lorsqu'ils figurent dans `manifest.outputs`.
- Modifier **réellement un PDF** et recalculer son checksum dans le manifeste,
  puis vérifier que le texte extrait est interdit, y compris avec des marques
  combinantes (police Unicode embarquée dans le test).
- Injecter les mêmes chaînes dans le YAML source, vérifier le rejet dès
  `load_book` et la préservation bit-à-bit d'une précédente démo valide.
- Tester `audit_output` et la CLI `qa` avec un symlink de racine et un symlink
  de parent ; ne jamais résoudre ces chemins avant la validation.
- Tester les non-régressions : caractères français précomposés, texte ordinaire,
  albums Halloween avec Pip autorisé, sauvegarde rollback et données de rendu
  immuables.

**Limite :** le contrôle PDF textuel dépend de l'extraction PyMuPDF. Les glyphes
convertis en images ou dessins vectoriels nécessitent une inspection visuelle
spécifique. Le contrat ne prétend pas empêcher un code Python hostile exécuté
avec les mêmes droits d'écrire directement dans le système de fichiers.
