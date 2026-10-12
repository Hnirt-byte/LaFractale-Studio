# Étude — livraison vers un dossier Google Drive privé

## Décision présente

**Aucun export, aucune création de dossier, aucun partage et aucune autorisation OAuth Drive ne sont réalisés par B3-A.4.** Cette note décrit une option future contrôlée.

## Préconditions obligatoires

1. décision humaine explicite de livrer un artefact déterminé ;
2. dossier Drive privé désigné par son propriétaire, avec accès limité aux personnes nommées ;
3. OAuth restreint au périmètre Drive strictement nécessaire, sans élargissement implicite des scopes Gmail/Calendar existants ;
4. aucune clé, token, URL d’autorisation ou ID sensible dans Git, manifestes ou rapports ;
5. contenu local validé, hashé et approuvé avant toute téléversement ;
6. téléversement manuel déclenché par un GO distinct, puis lecture de métadonnées pour vérifier nom, hash local, parent et visibilité privée.

## Séquence future proposée

1. préparer localement un paquet immuable avec manifeste ;
2. demander le GO de téléversement, dossier cible et rôle de partage ;
3. téléverser sans partage public ni lien « anyone » ;
4. relire les métadonnées du fichier et du dossier ;
5. consigner uniquement l’ID de livraison si Kévin l’autorise, jamais des credentials ;
6. ne pas activer de synchronisation ou d’export automatique.

Cette option reste séparée de B3-B et de KDP. Elle ne prouve aucune préparation commerciale.
