# Design : Couche surveillance sur la carte politique

## Contexte

La carte politique affiche ~35 000 communes colorées par famille politique du maire. On ajoute une couche fusionnée de données de surveillance (vidéoprotection + police municipale) sans remplacer la vue politique.

## Sources de données

| Dataset | Granularité | Fraîcheur | Format source |
|---|---|---|---|
| Police municipale effectifs par commune (data.gouv) | Commune | 2024 | XLS/XLSX |
| Villes sous vidéosurveillance (data.gouv) | Commune | 2012 | CSV |

## Fichier produit : `surveillance.json`

Dict indexé par code INSEE :
```json
{ "01001": { "pm": 3, "asvp": 1, "vs": true } }
```
- `pm` : policiers municipaux
- `asvp` : agents de surveillance de la voie publique
- `vs` : commune équipée en vidéosurveillance (booléen)

## Rendu visuel

- **Couleur de fond** : inchangée (famille politique)
- **Bordure** : épaisseur 0.3 à 4px proportionnelle à `pm + asvp`, couleur blanche si `vs === true`, sinon gris foncé
- **Info panel (hover)** : section supplémentaire "Surveillance" avec effectifs et vidéoprotection oui/non

## Légende

Nouvelle section "Surveillance" sous la légende politique existante :
- Dégradé d'épaisseur de trait (effectif police municipale)
- Bordure blanche = vidéoprotection
- Dates de fraîcheur par source

## Script de traitement

`process_surveillance.py` :
1. Télécharge les deux datasets depuis data.gouv.fr
2. Parse le XLS police municipale (dernière année disponible)
3. Parse le CSV villes sous vidéosurveillance
4. Croise par code INSEE
5. Produit `surveillance.json`
