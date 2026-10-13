# B3-B.3c.1 — Durcissement des vérificateurs v2 et suivi des dettes techniques B3-B.3b

```text
kind                  = SYNTHETIC_NON_PRODUCTION
base                  = main 2f5a55e7c1ec425ec889f644a7f1c102fe7dd460 (fusion de la PR #20)
production_authorized = false   MAJOR-03=OPEN  MAJOR-04=OPEN  EDITORIAL=PENDING
KDP=FORBIDDEN  PRODUCTION_GENERATION=FORBIDDEN  ready_for_kdp=false  (issue #15 ouverte)
```

Ce lot ne change ni règle géométrique, ni algorithme de génération, ni paramètre, ni sérialisation canonique, ni empreinte, ni
code d'erreur `V2Error`. Il ajoute une validation préalable de la **forme** des entrées et borne les messages d'erreur.

## 1. Contrat d'entrée

| Catégorie | Exemples | Garantie |
|---|---|---|
| **Entrées JSON/dict ordinaires** | résultat de `json.loads`, `V2Activity.to_dict()`, tout `dict` / `list` / `str` / `int` / `float` / `bool` / `None` imbriqués | `verify_v2`, `verify_maze_v2`, `verify_connect_dots_v2`, `verify_match_v2` renvoient **toujours** une liste de `str` ; elle est **non vide** pour tout enregistrement invalide ; aucune exception ; aucune acceptation à tort sur les mutations testées (§4) |
| **Arguments de `generate_v2`** | mécanique, identifiant, graine, paramètres | refus par `V2Error` à code stable (`UNKNOWN_MECHANIC`, `BAD_ACTIVITY_ID`, `BAD_SEED`, `BAD_PARAMS`, `UNKNOWN_PARAM`, `MISSING_PARAM`, `BAD_SIZE`, …), message borné ; jamais `ValueError`, `RecursionError` ni `TypeError` bruts |
| **Octets** | `loads_record` | `V2Error` (`BAD_JSON`, `NOT_CANONICAL`) — comportement déjà correct, désormais testé |
| **Objets Python arbitraires ou malveillants** | sous-classes d'`int`/`str`/`dict` aux méthodes spéciales hostiles, mappings personnalisés, `tuple`, `set`, `bytes`, références circulaires, objets quelconques | **Hors contrat.** Ceux qui sont détectables par leur type exact sont refusés sans être comparés, itérés ni rendus en texte ; pour les autres (par exemple un `Mapping` de premier niveau qui n'est ni `dict`, ni `FrozenDict`, ni `MappingProxyType`, ou un `V2Activity` dont les champs ont été falsifiés par `object.__setattr__`), aucune garantie n'est donnée |

## 2. Stratégie : refuser avant de calculer

1. **`core.hostile_shape(data)`** — parcours **itératif** (aucune récursion donc aucun `RecursionError`), appelé en premier par chacun des
   trois vérificateurs. Il refuse, en une seule ligne d'erreur explicite et sans autre travail :
   * plus de 8 niveaux d'imbrication (`MAX_RECORD_DEPTH`) — un enregistrement valide en compte 6 au plus (mesuré) ;
   * plus de 4 096 éléments visités (`MAX_RECORD_NODES`) — le plus grand enregistrement valide (labyrinthe 12×12) en compte 1 381 au plus sur 40 graines × 3 niveaux (mesuré en revue), soit une marge supérieure à 2,9 ; le test garantit un facteur 2 sur la graine 0 ; une référence partagée ou circulaire est comptée à chaque visite, donc elle ne boucle pas et ne se démultiplie pas ;
   * clé non textuelle ou de plus de 64 caractères ; chaîne de plus de 256 caractères ;
   * entier de plus de 4 096 bits (`MAX_RECORD_INT_BITS`, environ 1 230 chiffres, sous la limite de conversion entier↔texte de 4 300 chiffres de CPython) ;
   * tout type de feuille autre que `None`, `bool`, `int`, `float`, `str` exacts ; tout conteneur autre que `dict` / `list` exacts (le premier niveau peut aussi être un `FrozenDict` ou un `MappingProxyType`).
2. **`core.bounded_repr`** remplace tous les `!r`, `str()` et `map(str, …)` appliqués à une valeur venant de l'entrée (vérificateurs, validateurs de paramètres, registre) : rendu total (ne lève jamais), 3 niveaux au plus, 80 caractères par chaîne, entiers de plus de 64 bits résumés (`<entier de N bits>`), autres objets réduits au nom de leur type tronqué.
3. **`core.cap_problems`** limite la liste à 100 problèmes plus une ligne de synthèse : une liste non vide reste non vide, et un enregistrement contenant des milliers d'éléments invalides ne produit pas des milliers de messages.
4. **Pas de capture générale.** `verify_match_v2` capturait `RecursionError`, `ValueError` et `OverflowError` autour de tout le vérificateur ; cette capture est **supprimée** et remplacée par la validation préalable. Un test d'analyse syntaxique interdit `except:`, `except Exception`, `RecursionError` et `OverflowError` dans les trois vérificateurs ; seules restent des captures étroites et antérieures (`V2Error`/`ValueError`/`TypeError` autour du calcul d'empreinte, `KeyError`/`TypeError` dans le diagnostic).
5. Un entier démesuré mais **inférieur à 4 096 bits** (par exemple 10⁴⁰⁰ en coordonnée) traverse la garde et reçoit toujours le diagnostic spécifique antérieur (« points et centre doivent rester dans … ») ; l'arithmétique en cause est bornée par ces contrôles de plage, effectués avant tout calcul.

Fichiers modifiés : `core.py` (garde, rendu borné, plafond, message de `check_params`), `maze_verify.py`, `connect_dots_verify.py`,
`match_verify.py` (garde en tête, rendu borné, plafond ; corps inchangé), `maze.py` / `connect_dots.py` / `match.py` (rendu borné dans les validateurs de paramètres),
`registry.py` (rendu borné). Les règles géométriques, générateurs, tables et constantes ne sont pas touchés.

## 3. Défauts de robustesse effectivement corrigés (contre-exemples reproduits sur `2f5a55e`, puis sur ce lot)

| # | Entrée hostile | Avant (`2f5a55e`) | Après |
|---|---|---|---|
| CE1 | `verify_v2(maze)` avec `schema = 10**5000` | **`ValueError`** (conversion entier→texte dans le message) | liste de 1 erreur |
| CE2 | `verify_v2(maze)` avec `kind` = liste imbriquée 100 000 fois | **`RecursionError`** | liste de 1 erreur |
| CE3 | `verify_v2(connect_dots)` avec `version` = chaîne de 100 000 caractères | liste de 2 erreurs, **100 107 caractères** | liste de 1 erreur, 57 caractères |
| CE4 | `verify_v2(connect_dots)` avec `schema = 10**5000` | **`ValueError`** | liste de 1 erreur |
| CE5 | `verify_v2(connect_dots)` avec `kind` = dictionnaires imbriqués | **`RecursionError`** | liste de 1 erreur |
| CE6 | `verify_v2(maze)` avec 1 300 passages invalides | **1 300 erreurs**, 79 490 caractères | 101 lignes, 6 030 caractères |
| CE7 | `verify_v2({"mechanic": "x" * 100000})` | 1 erreur de **100 037 caractères** | 1 erreur de 131 caractères |
| CE8 | `verify_v2(match)` avec `schema` de 100 000 caractères | 2 erreurs, **100 115 caractères** | 1 erreur, 57 caractères |
| CE9 | `verify_v2(maze)` avec une clé entière `10**5000` | **`ValueError`** (tri des clés par `str`) | liste de 1 erreur |
| CE10 | `generate_v2("maze_v2", …, {"size": 10**5000, …})` | **`ValueError`** brute | `V2Error` `BAD_SIZE`, 83 caractères |
| CE11 | `generate_v2` avec `size` = liste imbriquée 100 000 fois | **`RecursionError`** | `V2Error` `BAD_SIZE` |
| CE12 | `generate_v2` avec un paramètre inconnu dont le nom est `10**5000` | **`ValueError`** brute | `V2Error` `UNKNOWN_PARAM` |
| CE13 | `generate_v2` avec une mécanique de 100 000 caractères | `V2Error` de **100 103 caractères** | `V2Error` de 197 caractères |
| CE14 | `generate_v2("connect_dots_v2", …, shape = 100 000 caractères)` | `V2Error` de **100 052 caractères** | `V2Error` de 146 caractères |
| CE15 | `generate_v2("match_v2", …, relation = 10**5000)` | **`ValueError`** brute | `V2Error` `BAD_RELATION` |

Un balayage de mutations (§4) trouvait avant correction, sur les trois mécaniques, 78 cas de `RecursionError`/`ValueError` dans les vérificateurs
(`maze_v2` : 37 ; `connect_dots_v2` : 41 ; `match_v2` les masquait par la capture générale), 146 messages non bornés, et 24 `ValueError`, 18 `RecursionError`
et 39 messages longs côté `generate_v2`. **Aucune acceptation à tort n'a été observée, ni avant ni après.**

## 4. Garanties démontrées par les tests (`tests/test_b3b3c1_verifier_hardening.py`)

* Pour chacune des trois mécaniques : une mutation à la fois de **chaque** champ de l'enregistrement (premier niveau, imbriqués, trois premiers éléments de chaque liste) par 29 valeurs hostiles (entiers de 5 000 chiffres et de 4 097 bits, listes et dictionnaires imbriqués 100 000 fois, 9 niveaux, NaN, ±∞, flottants, `None`, chaînes de 100 000 caractères, `bytes`, `set`, `tuple`, booléens, listes de 200 000 éléments, sous-classes d'`int`/`str`/`dict` dont `__eq__`, `__repr__` ou `items` lèvent, objets dont toutes les méthodes lèvent, liste circulaire, structure partagée à 2⁴⁰ visites, clés entières…) ; toutes refusées par `verify_v2` **et** par le vérificateur dédié : liste non vide de `str`, au plus 101 lignes, au plus 20 000 caractères en tout.
* Suppression de chaque clé, ajout d'une clé en trop à chaque niveau, valeurs hostiles dans tous les champs à la fois, valeurs hostiles en tête d'enregistrement : refus.
* `verify_v2` renvoie une liste pour toute entrée, y compris non mapping et mécanique hostile ; le nom hostile n'est jamais recopié.
* `generate_v2` : chaque argument hostile (mécanique, identifiant, graine, mapping de paramètres, chaque valeur de paramètre, nom de paramètre inconnu) provoque un `V2Error` à code non vide et message ≤ 400 caractères ; 13 codes d'erreur existants (14 cas) sont vérifiés inchangés ; `BAD_PARAMS`, `BAD_COMBINATION`, `UNSATISFIABLE` et `SELF_CHECK_FAILED` ne sont pas couverts par ce test.
* `loads_record` refuse les octets hostiles (imbrication 100 000, entier de 5 000 chiffres, UTF-8 invalide, NaN, clé dupliquée) par `V2Error`.
* **Non-régression** : 254 combinaisons (labyrinthes 3..12 × 3 niveaux × 3 graines, points 5..24 × 2 modes × 2 graines, associations 2..8 × 2 relations × 3 familles × 2 graines, y compris les refus) capturées sur `2f5a55e` : empreintes et codes de refus **identiques** (fixture `tests/fixtures/b3b3c1_reference_fingerprints.json`). Tous les enregistrements valides générés des tests sont acceptés par la garde, avec une marge d'un facteur 2 sur le plafond d'éléments.
* Discipline de code vérifiée par analyse syntaxique : aucune capture générale dans les vérificateurs, aucun rendu textuel non borné d'une valeur d'entrée, aucun couplage éditorial dans le socle.

## 5. Garanties non démontrées

* L'absence d'exception est démontrée **par balayage de mutations et par construction** (la garde précède tout calcul), pas par une preuve formelle : un champ imbriqué ou une combinaison de deux champs hostiles non couverts par le balayage n'est pas exclu. Le balayage est à une mutation par champ ; des combinaisons de deux mutations ne sont testées que pour « tous les champs à la fois ».
* Pas de borne de **temps** mesurée en environnement contraint : le coût est borné par construction (4 096 éléments, tailles de grille et nombre de points plafonnés), mais aucun test de durée limite n'existe.
* Les objets Python arbitraires (§1) : aucune garantie au-delà du refus par type exact.
* La limite d'entier de 4 096 bits suppose la limite de conversion par défaut de CPython (4 300 chiffres) : un hôte qui l'augmente ou la désactive (`sys.set_int_max_str_digits`) ne rend pas le code incorrect (la garde borne déjà les entiers), mais la justification de ce seuil ne vaut plus.
* Python : la suite pytest a été exécutée sous 3.13 seulement ; la CI ne teste que 3.11 (voir dette n°4). Les scripts de balayage et de contre-exemples de la revue ont de plus été rejoués sous 3.11 et 3.12 sans anomalie (hors suite pytest, non conservés dans le dépôt).

## 6. Limites toujours présentes

* Comportement changé et assumé : un enregistrement dont le premier niveau est une **sous-classe** de `dict` (par exemple `OrderedDict`) ou un autre `Mapping` personnalisé est désormais refusé (« type non pris en charge ») alors que les vérificateurs l'acceptaient s'il se comportait comme un `dict`. Les enregistrements issus de `json.loads`, de `V2Activity.to_dict()`, de `FrozenDict` et de `MappingProxyType` sont inchangés. Les valeurs imbriquées de type `tuple` étaient déjà refusées par l'égalité stricte.
* Une chaîne de plus de 256 caractères ou une clé de plus de 64 caractères dans un enregistrement est désormais refusée d'emblée, même si le champ concerné aurait de toute façon été refusé ensuite (les enregistrements valides n'en contiennent pas).
* Les messages d'erreur sont du texte libre en français : ils peuvent évoluer ; seuls les codes `V2Error` sont stables.
* Le rendu de `keys_summary` (12 clés) et de `bounded_repr(measures)` (320 caractères) perd du détail par rapport à l'ancien rendu complet ; seul le texte change.
* Le plafond de 100 problèmes masque les suivants (compte indiqué) ; un enregistrement invalide reste refusé quel que soit le plafond.

## 7. Dettes techniques B3-B.3b — suivi

| # | Dette | Statut |
|---|---|---|
| 1 | Audit de robustesse aux entrées hostiles de `maze_v2` et `connect_dots_v2` | **Soldée par ce lot** dans le périmètre du §1 (entrées JSON/dict ordinaires et arguments de `generate_v2`) ; restent les limites des §5 et §6 |
| 2 | `search.attempts` non rejoué indépendamment pour les trois mécaniques | **Conservée, non traitée** (hors périmètre de ce lot) |
| 3 | L'empreinte SHA-256 garantit l'intégrité, pas une provenance authentifiée | **Conservée, non traitée** |
| 4 | CI testant Python 3.11 seulement ; égalité des empreintes sous 3.12 et 3.13 vérifiée à la main | **Conservée, non traitée** ; aucun workflow modifié |

Les statuts MAJOR-03 et MAJOR-04 (OPEN), EDITORIAL (PENDING), KDP (FORBIDDEN), PRODUCTION_GENERATION (FORBIDDEN), `ready_for_kdp=false` et l'issue #15 (ouverte) ne sont pas modifiés. B3-B.3c.2 (contrat de passerelle), le rendu et toute intégration éditoriale ne sont pas commencés.
