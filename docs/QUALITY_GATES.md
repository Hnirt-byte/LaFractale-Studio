# Portes de qualité

## Bloquants automatiques
- Nombre de pages exact; pages uniques; identifiants et chemins d'assets existants.
- Traductions référencées dans le lexique, consignes sans placeholder et sans texte tronqué.
- Labyrinthes : départ, arrivée, frontières, traversabilité confirmée par recherche de chemin, difficulté mesurée.
- Points à relier : numérotation bijective 1..N, contours suffisamment significatifs et silhouette entière; vérification des segments, collisions, fermeture selon modèle de forme. **Une lune dessinée par seulement un demi-cercle est rejetée.** La qualité de silhouette demande aussi une revue visuelle.
- Association : appariement bijectif et correction unique ; bonne distribution spatiale.
- Cherche-et-trouve : inventaire exact des objets visibles, placements non masqués, consigne conforme.
- Trouve les différences : changements décrits par objet et position, nombre exact validé par composition contrôlée (pas par comparaison approximative de deux images IA).
- Doublons : unicité ID, des seeds et des données ; mêmes types interdits deux pages consécutives, sauf exception enregistrée.
- Rendu : aucune sortie de zone sûre, fontes intégrées, résolution effective suffisante, transparences et fonds perdus contrôlés.

## Obligatoires humains (non automatisables parfaitement)
- Pip réellement fidèle au portrait officiel; noeud papillon visible sur vues de face.
- Compréhension enfant 4–5 ans, lisibilité, simplicité de la consigne.
- Activité plaisante, forme connect-the-dots satisfaisante, durée adaptée, difficulté graduée.
- Orthographe, traductions et pertinence de l'histoire.
- Couleur du livre final, KDP Previewer et épreuve papier.

## Statuts de page
`draft`, `generated`, `auto_pass`, `needs_visual_review`, `approved`, `rejected`.
Publication impossible tant qu'une page est `rejected` ou `needs_visual_review` et tant que l'épreuve finale n'est pas approuvée.

## Tests de non-régression obligatoires
Fixture de lune complète 1..12; labyrinthe atteignable; labyrinthe bloqué rejeté; association correcte; association incohérente rejetée; double page ID rejetée; asset manquant rejeté; reprise d'une seed identique.
