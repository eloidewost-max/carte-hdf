# Design : Fiche Prospect Intelligente

**Date :** 2026-03-09
**Contexte :** Outil interne marketing/commerciaux pour cibler les communes à potentiel vidéoprotection/vidéoverbalisation.
**Usages principaux :** Exploration libre de la carte + préparation de RDV.

## Problème

Le commercial ouvre une fiche commune, voit des chiffres bruts éparpillés, et doit mentalement construire l'argumentaire et chercher des comparaisons. Les données 2019 minent la crédibilité.

**Besoins identifiés :**
- Contexte narratif : résumé argumentaire auto-généré
- Comparaisons multi-critères : benchmark vs communes similaires
- Fraîcheur des données : sources les plus récentes possibles

## Architecture retenue : pré-calcul Python (Approche A)

Nouveau script `process_insights.py` qui pré-calcule peer groups, benchmarks et flags narratifs. Le frontend consomme un `insights.json` et génère le texte côté client.

**Raison du choix :** calculs lourds (peer matching sur 35k communes) faits une seule fois en Python, frontend reste léger, facilement testable.

## 1. Pipeline `process_insights.py`

### Entrées
- maires.json (famille politique)
- surveillance.json (PM, ASVP, ratio)
- prospection.json (stat_payant, videoverb, accidents, pm_trend)
- delinquance.json (criminalité par catégorie, ratio)
- enrichment.json (QPV, DGF, revenus, pauvreté)

### Sortie : `insights.json` (~2-3 MB)

```json
{
  "11069": {
    "peers": ["34032", "81004", "65440", "11262", "66136"],
    "peer_names": ["Beziers", "Albi", "Tarbes", "Narbonne", "Perpignan"],
    "bench": {
      "crime_r":    { "val": 423, "med": 289, "pct": 78 },
      "pm_r":       { "val": 6.2, "med": 4.1, "pct": 62 },
      "accidents_r":{ "val": 8.3, "med": 5.7, "pct": 71 },
      "rev_med":    { "val": 19200, "med": 21500, "pct": 34 },
      "tx_pauv":    { "val": 22.1, "med": 17.3, "pct": 72 }
    },
    "flags": {
      "crime_above_peers": true,
      "no_pm_peers_have": false,
      "no_vv_peers_have": false,
      "pm_growing": true,
      "high_accident_rate": true,
      "budget_capacity": true,
      "high_poverty": true,
      "peers_have_stat_payant_pct": 85
    }
  }
}
```

### Peer group : algorithme

Distance euclidienne normalisée sur 4 dimensions :
- `log(population)` — poids 0.4
- `rev_med` normalisé (z-score) — poids 0.25
- `tx_pauv` normalisé (z-score) — poids 0.25
- `famille politique` — bonus -0.2 si même famille (rapproche dans l'espace)

Top 20 peers retenus par commune. Filtre : communes avec au moins 3 dimensions disponibles.

### Benchmarks

Pour chaque commune, calculer le percentile parmi ses 20 peers sur :
- Ratio criminalité /10k (`crime_r`)
- Ratio PM /10k (`pm_r`)
- Accidents /10k (`accidents_r`)
- Revenu médian (`rev_med`)
- Taux de pauvreté (`tx_pauv`)

### Flags narratifs (booléens)

| Flag | Condition |
|------|-----------|
| `crime_above_peers` | Percentile criminalité > 75 |
| `no_pm_peers_have` | Commune sans PM ET >50% des peers en ont |
| `no_vv_peers_have` | Commune sans VV ET >30% des peers en ont |
| `pm_growing` | Tendance PM en hausse (dernier > premier dans pm_trend) |
| `high_accident_rate` | Percentile accidents > 50 |
| `budget_capacity` | DGF/hab > médiane des peers |
| `high_poverty` | Percentile pauvreté > 60 |

Champ supplémentaire : `peers_have_stat_payant_pct` (% des peers avec stat payant).

## 2. Frontend : section "Argumentaire" dans le detail panel

### Résumé narratif

Nouveau bloc entre le score prospection et les données brutes. Texte généré côté JS à partir des flags :

> *"Carcassonne (48 800 hab.) présente un potentiel élevé. La délinquance enregistrée est supérieure à 78% des communes comparables. 85% des communes de profil similaire disposent déjà d'une police municipale. Le taux d'accidents corporels est au-dessus de la médiane. La capacité budgétaire (DGF 104 EUR/hab) permet d'envisager un investissement."*

Chaque phrase correspond à un flag. Seules les phrases dont le flag est `true` apparaissent.

### Tableau de comparaison

| Indicateur | Commune | Peer group (med.) | Rang |
|---|---|---|---|
| Criminalite /10k | 423 | 289 | 78e pct |
| PM /10k | 6.2 | 4.1 | 62e pct |
| Accidents /10k | 8.3 | 5.7 | 71e pct |

Barres visuelles horizontales colorées (vert < 50e pct, orange 50-75, rouge > 75).

### Top 5 peers nommés

"Communes comparables : Beziers, Albi, Tarbes, Narbonne, Perpignan" — cliquables pour naviguer vers leur fiche.

## 3. Deep linking

Encoder l'état dans l'URL via `history.pushState` :

```
?mode=prospection&commune=11069
```

Paramètres supportés :
- `mode` : prospection|politique|surveillance|securite
- `commune` : code INSEE (ouvre le detail panel au chargement)
- `filter` : famille politique active (optionnel)

Au chargement, parser `URLSearchParams` et restaurer l'état.

## 4. Rafraichissement données

| Source | Action | Effort |
|---|---|---|
| Stat. payant (2019) | Rechercher source Cerema/GART plus recente ou scraper annuaires | Moyen |
| Population (2021) | Passer au recensement 2024 quand disponible | Faible |
| Filosofi (2021) | Surveiller publication 2022 par INSEE | Faible |
| Nuances (2020) | Attendre municipales 2026 | Bloque |

## Sequence de developpement

1. `process_insights.py` — pipeline Python (peer groups + benchmarks + flags)
2. Section argumentaire — nouveau bloc dans le detail panel
3. Deep linking — URL state avec pushState
4. Refresh donnees — sources plus fraiches en parallele
