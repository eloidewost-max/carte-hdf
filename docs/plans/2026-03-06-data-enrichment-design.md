# Design: Enrichissement donnees data.gouv.fr

Date: 2026-03-06
Approche: C — Hybride (nouveau mode securite + enrichissement fiches + signaux prospection)

## Objectif

Integrer 5 nouveaux datasets data.gouv.fr pour enrichir la carte :
1. **Delinquance communale** (nouveau mode "securite")
2. **ZSP / QPV** (overlays + filtres prospection + fiches)
3. **Revenus / DGF** (fiches communes + signal prospection)
4. **Effectifs PM 2024** (mise a jour pipeline existant)

Principe directeur : **fiches communes ultra-riches** — le clic sur une commune affiche toutes les donnees disponibles quel que soit le mode actif.

---

## 1. Nouveau mode "Securite" (delinquance)

### Source
- Dataset: `621df2954fa5a3b5a023e23c` — Ministere de l'Interieur
- Fichier: base communale CSV (~34 MB compresse)
- Granularite: commune (code INSEE), par categorie de delit, par annee
- Derniere MAJ: janvier 2026 (donnees 2024)

### Categories de delits
Les categories presentes dans le dataset (a confirmer lors du processing) :
- Coups et blessures volontaires
- Vols avec violences
- Vols sans violence
- Cambriolages
- Vols de vehicules / dans vehicules
- Destructions et degradations
- Trafic de stupefiants
- Escroqueries
- Violences sexuelles

### Donnees generees : `delinquance.json`
```json
{
  "75056": {
    "total": 245000,
    "cats": {
      "vols_sv": 89000,
      "cambr": 12000,
      "coups": 34000,
      "destr": 28000,
      "stup": 15000,
      "escroc": 42000,
      "vols_av": 8000,
      "vols_veh": 11000,
      "viol_sex": 6000
    },
    "pop": 2161000,
    "r": 113.4,
    "year": "2024"
  }
}
```
Champs : `total` (nb delits total), `cats` (ventilation par categorie, cles courtes), `pop` (population), `r` (ratio total /10k hab), `year`.

### UI mode securite
- **Heatmap** : ratio total delits /10k habitants (echelle de couleurs 6 niveaux, bleu fonce > rouge)
- **Pills de categories** : comme les familles en mode politique — "Tous" par defaut, clic sur une categorie = heatmap filtre sur ce type
- **Sidebar** :
  - Section FILTRES : pills categories + slider ratio min
  - Section LEGENDE : echelle de couleurs avec seuils
  - Section STATS : tableau par famille politique (comme en surveillance) — ratio moyen de delinquance par bord politique
- **Bottom bar** : "X communes avec donnees | Ratio moyen : Y /10k | [categorie active]"
- **Hover tooltip** : "Ratio total: X /10k" ou "Ratio [categorie]: X /10k"

### Style function : `getStyleSecurite(feature)`
- Meme pattern que getStyleSurveillance
- Couleur fill = seuil sur le ratio (total ou par categorie selon filtre)
- `SECU_COLORS` : 6 niveaux (a definir, palette distincte des autres modes — ex: violet/magenta)
- Communes sans donnees : gris transparent ou invisible (filtre dataOnly)

### Mode color
`securite: '#c0392b'` (rouge brique, distinct des 3 autres)

---

## 2. Fiches communes enrichies (detail panel)

### Principe
Le detail panel affiche TOUTES les donnees disponibles pour la commune, **quel que soit le mode actif**. Les sections sont :

#### Section 1 — En-tete (existant, inchange)
- Nom (code INSEE), population
- Badge famille politique, nom du maire

#### Section 2 — Score prospection (existant, inchange en mode prospection)
- Score /100, top X%, decomposition signaux

#### Section 3 — NOUVEAU : Delinquance
- **Ratio total** en gros + comparaison moyenne nationale
- **Breakdown par categorie** : barres horizontales triees par volume
  - Chaque barre = nom categorie | barre proportionnelle | nombre | ratio /10k
- **Annee des donnees** (badge couleur fraicheur)
- Si pas de donnees : mention "Donnees indisponibles (commune < 5000 hab ou hors couverture)"

#### Section 4 — Surveillance (existant, enrichi)
- PM, ASVP, ratio /10k (existant)
- Sparkline tendance PM (existant)
- **NOUVEAU** : badge ZSP (oui/non)
- **NOUVEAU** : badge QPV (oui/non, + nb de QPV si > 1)

#### Section 5 — NOUVEAU : Contexte socio-economique
- **Revenu median** par UC (si dispo)
- **Taux de pauvrete** (si dispo)
- **DGF** : montant total + montant /habitant
- Barre comparative : position par rapport a la mediane nationale

#### Section 6 — Signaux prospection (existant, enrichi)
- stat_payant, videoverb, accidents (existant)
- **NOUVEAU** : ZSP/QPV mentionnes ici aussi comme signaux

#### Section 7 — Sources
- Tableau recapitulatif des sources de donnees avec annees (existant dans methodo, condense ici)

### Logique d'affichage
- Chaque section a un test de presence : si aucune donnee pour cette commune, la section est masquee (pas de "N/A" partout)
- Les donnees viennent de tous les JSON charges (maires, surv, prosp, delinquance, enrichment)

---

## 3. ZSP et QPV

### Sources
- **ZSP** : Dataset `562e326288ee38257812613d` — Shapefile des ~80 ZSP (Ministere Interieur)
- **QPV** : Dataset `5a561801c751df42d7fca9b6` — Perimetres des ~1500 QPV (ANCT, 2024)

### Approche de traitement
Les ZSP et QPV sont des **polygones** (pas indexes par commune). Le script Python doit :
1. Telecharger les shapefiles/geojson
2. Pour chaque commune du TopoJSON, tester l'intersection geometrique avec les ZSP/QPV
3. Generer un fichier `enrichment.json` avec les flags booleens par commune

### Donnees generees : integrees dans `enrichment.json`
```json
{
  "75056": {
    "zsp": true,
    "qpv": 3,
    "rev_med": 23450,
    "tx_pauvrete": 15.2,
    "dgf": 850000000,
    "dgf_hab": 393
  }
}
```

### Integration UI
- **Detail panel** : badges dans la section surveillance + contexte socio-eco
- **Mode prospection** : nouveaux filtres checkboxes "Commune en ZSP" / "Commune avec QPV"
- **Pas d'overlay cartographique** (trop lourd pour 1500 polygones QPV + complexifie la lecture)

---

## 4. Revenus et DGF

### Sources
- **Revenus** : Dataset `59faf660c751df1da4f5f5fc` — Filosofi/INSEE (donnees 2013, a verifier si plus recent disponible via INSEE direct)
- **DGF** : Dataset `5b2394c588ee383dd7faa86e` — DGCL (multi-annees)

### Donnees
Integrees dans `enrichment.json` (meme fichier que ZSP/QPV) :
- `rev_med` : revenu median par UC (euros)
- `tx_pauvrete` : taux de pauvrete (%)
- `dgf` : montant DGF total (euros)
- `dgf_hab` : DGF par habitant (euros)

### Integration prospection (signal optionnel)
Nouveau signal `budget_capacity` (poids defaut: 0%, activable par l'utilisateur) :
- `min(dgf_hab / 500, 1)` — normalise entre 0 et 1, sature a 500 EUR/hab
- Ajoute comme 6eme slider dans les parametres prospection
- Poids 0% par defaut pour ne pas casser le scoring existant

---

## 5. Mise a jour PM 2024

### Action
- Mettre a jour `process_surveillance.py` pour telecharger le fichier PM 2024 (resource ID `081e94fe-b257-4ae7-bc31-bf1f2eb6c968`)
- Verifier que le format ODS n'a pas change
- Regenerer `surveillance.json`

---

## 6. Nouveau script : `process_delinquance.py`

### Pipeline
1. Telecharger le CSV compresse depuis data.gouv.fr (dataset `621df2954fa5a3b5a023e23c`)
2. Parser les colonnes : code commune, categorie de delit, nombre de faits
3. Agreger par commune : total + ventilation par categorie
4. Joindre la population depuis surveillance.json
5. Calculer le ratio /10k
6. Exporter `delinquance.json`

### Mapping categories
Les libelles longs du CSV → cles courtes :
- "Coups et blessures volontaires" → `coups`
- "Vols avec violences" → `vols_av`
- "Vols sans violence contre des personnes" → `vols_sv`
- "Cambriolages de logement" → `cambr`
- "Vols de vehicules" → `vols_veh`
- "Destructions et degradations volontaires" → `destr`
- "Trafic de stupefiants" → `stup`
- "Escroqueries" → `escroc`
- "Violences sexuelles" → `viol_sex`
(mapping exact a confirmer lors de l'exploration du CSV)

---

## 7. Nouveau script : `process_enrichment.py`

### Pipeline
1. Telecharger QPV GeoJSON depuis ANCT
2. Telecharger ZSP Shapefile depuis Ministere Interieur → convertir en GeoJSON (avec geopandas/fiona)
3. Telecharger revenus CSV depuis Geoptis/INSEE
4. Telecharger DGF depuis DGCL
5. Pour ZSP/QPV : intersection spatiale avec les communes (necessitite geopandas + communes GeoJSON)
6. Merger toutes les donnees par code INSEE
7. Exporter `enrichment.json`

### Dependances Python supplementaires
- `geopandas` (pour intersections spatiales ZSP/QPV)
- `shapely` (dependance de geopandas)
- `fiona` ou `pyogrio` (lecture shapefile)
- `requests` (deja utilise)

---

## 8. Chargement frontend

### Nouveau fetch
```javascript
var results = await Promise.all([
  fetchJSON('maires.json'),
  fetchJSON('surveillance.json'),
  fetchJSON('prospection.json'),
  fetchJSON('communes-topo.json'),
  fetchJSON('delinquance.json'),    // NOUVEAU
  fetchJSON('enrichment.json')       // NOUVEAU
]);
```

### Taille estimee des nouveaux fichiers
- `delinquance.json` : ~2-4 MB (35k communes x 10 champs)
- `enrichment.json` : ~500 KB (donnees partielles, pas toutes les communes)
- Total charge supplementaire : ~3-5 MB

### Performance
- Meme pattern que les autres : objets en memoire, acces O(1) par code INSEE
- Pas de traitement lourd cote client pour les nouvelles donnees (sauf scoring prospection qui reste identique + 1 signal optionnel)

---

## 9. Architecture des couleurs par mode

| Mode | Couleur mode | Palette heatmap | Donnee coloree |
|------|-------------|-----------------|----------------|
| Politique | `#4a90d9` | Couleurs familles | Famille politique |
| Surveillance | `#e8913a` | Jaune > rouge (6 niv) | Ratio PM /10k |
| **Securite** | `#c0392b` | **Violet > magenta (6 niv)** | **Ratio delits /10k** |
| Prospection | `#4ecdc4` | Bleu fonce > rouge (5 niv) | Score composite |

Palette securite (proposition) : `['#2c1654', '#5b2a86', '#8e3a9e', '#c94c8a', '#e8665c', '#f5a623']`

---

## 10. Methodologie drawer

Ajouter dans la section methodologie :
- Description du mode securite (source, annee, categories)
- Ajout des nouvelles sources dans le tableau (delinquance, ZSP, QPV, revenus, DGF)
- Mention des biais connus : seuil de population pour le dataset delinquance (~5000 hab), anciennete des revenus (2013)

---

## Resume des fichiers a creer/modifier

### Nouveaux fichiers
- `process_delinquance.py` — genere `delinquance.json`
- `process_enrichment.py` — genere `enrichment.json`
- `delinquance.json` — donnees delinquance par commune
- `enrichment.json` — ZSP, QPV, revenus, DGF par commune

### Fichiers modifies
- `index.html` — nouveau mode securite + fiches enrichies + filtres prospection
- `process_surveillance.py` — MAJ source PM 2024 (si necessaire)

### Ordre d'implementation
1. Scripts Python (data pipeline) — peuvent etre testes independamment
2. Frontend : chargement des nouveaux JSON
3. Frontend : fiches communes enrichies (detail panel)
4. Frontend : nouveau mode securite
5. Frontend : filtres prospection ZSP/QPV + signal budget_capacity
6. Frontend : methodologie MAJ
7. Tests et polish
