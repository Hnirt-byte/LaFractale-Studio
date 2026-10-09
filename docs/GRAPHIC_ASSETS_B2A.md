# V0.2-B2-A : bibliothèque graphique et provenance

**Statut : développement en revue, non publiable.** Aucun compagnon ni visuel imprimable n'a été créé ou approuvé par ce lot.

## Règle de confiance

Le YAML d'un livre n'accorde aucun droit d'utilisation graphique. Un catalogue distinct `assets/illustrations/approvals.json`, suivi en Git et approuvé par un humain, répertorie les variantes. Le moteur exige **en plus** le SHA-256 exact de ce catalogue fourni par un opérateur de confiance, indépendamment du YAML et des artefacts. Le SHA n'est pas lu dans le manifeste pour autoriser quoi que ce soit.

La source officielle couleur de Pip reste inchangée, hors du namespace des variantes imprimables. Le catalogue B2-A est vide ; il n'autorise donc **aucun visuel réel**.

## Format du registre (futur, illustratif uniquement)

L'enregistrement suivant est une *description de schéma*, pas une approbation :

```json
{
  "schema_version": 1,
  "illustrations": [
    {
      "id": "exemple-futur",
      "book_id": "halloween_2026",
      "companion_id": "pip",
      "role": "companion",
      "variant": "monochrome",
      "path": "assets/illustrations/halloween_2026/pip/exemple-futur.png",
      "sha256": "<SHA-256 DE 64 CHIFFRES HEXADÉCIMAUX>",
      "width": 660,
      "height": 220,
      "human_approved": true
    }
  ]
}
```

Les approbations visuelles et les preuves de droits devront être archivées humainement avant de fournir le digest externe correspondant au registre. La simple modification d'un champ `human_approved` dans JSON ne vaut pas autorisation.

## Commandes réservées aux futurs visuels validés

```bash
python -m lafractale build-demo books/halloween_2026/book.yaml \
  --out dist/halloween_2026 \
  --illustration-id <identifiant-validé> \
  --approvals-sha256 <empreinte-validée-hors-manifeste>

python -m lafractale qa dist/halloween_2026 \
  --book books/halloween_2026/book.yaml \
  --illustration-id <identifiant-validé> \
  --approvals-sha256 <empreinte-validée-hors-manifeste>
```

Sans ces paramètres, le moteur **n'insère aucune image** et conserve `VISUEL À VALIDER` dans toutes les fiches. Toute commande avec seulement l'un de ces paramètres échoue.

## Limites et vérifications

Les PNG doivent être locaux, gris 8 bits, CRC valides, sans métadonnées, ≤ 8 Mo, ≤ 8 Mpx, et délivrer au moins 300 DPI à l'échelle imprimée. Aucune conversion implicite couleur → gris, aucun PNG de la référence officielle Pip.

Le slot préexistant est utilisé, sans rognage ni déformation ; l'intégration est reproduite à l'identique dans les fiches et les corrigés. Le manifeste de démo rapporte la provenance. L'audit exige le livre validé et, si une illustration est présente, son identité et le registre approuvé hors sortie. Le PDF est audité pixel par pixel pour le visuel, les aperçus sont comparés au rendu du PDF. `ready_for_kdp` et `publication_approved` restent à `false`.

Pour tester l'infrastructure sans créer de faux visuel officiel, les tests utilisent des PNG gris **strictement temporaires** de validation technique. Aucun n'est livré dans les assets de production.

**Contrôle indépendant renforcé (B2-A)** : pour toute démo comportant une illustration approuvée, la QA régénère également les deux PDF à partir du livre et du registre source approuvés. Elle compare leurs octets aux PDF audités. Une altération vectorielle ou un remplacement de pixels, même accompagné d'un manifeste et d'aperçus recalculés, est rejeté. Ce contrôle nécessite les mêmes polices et le même environnement de rendu déterministe ; il n'est pas une signature cryptographique des artefacts.


**Correctif de la revue B2-A :** la comparaison par régénération est désormais **systématique**, y compris pour les démos sans image. Elle couvre PDF intérieurs et corrigés, activités JSON, rapport qualité JSON, Markdown, manifeste strict et aperçus PNG. Le manifeste ne peut pas justifier les fichiers en fournissant ses propres checksums. Seul le champ `generated_at_utc` est traité comme métadonnée déclarative UTC validée, et non comme preuve cryptographique du temps de création.
