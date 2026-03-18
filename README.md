# Carte Politique — Intelligence commerciale videoverbalisation

Carte interactive couvrant **34 844 communes** francaises, croisant donnees politiques, securitaires, socio-economiques et de police municipale pour identifier les opportunites commerciales en videoverbalisation.

Acces reserve aux collaborateurs Vizzia (`@vizzia.fr`) — authentification Clerk.

---

## Modes de visualisation

| Mode | Description | Donnees | Couleurs |
|------|-------------|---------|----------|
| **Prospection** | Score composite 0-100 du potentiel videoverbalisation | 6 signaux ponderes | Bleu → rouge (5 niveaux) |
| **Politique** | Couleur politique du maire (municipales 2020) | Nuances ministerielles | Par famille politique |
| **Surveillance** | Densite de police municipale (agents / 10k hab.) | Effectifs PM 2024 | Jaune → rouge (6 niveaux) |
| **Securite** | Taux de delinquance enregistree / 10k hab. | SSMSI 2024 | Violet → magenta (6 niveaux) |
| **Municipales 2026** | Donnees electorales municipales 2026 | Resultats T1 | Couleurs partis + effets lumineux |

---

## Datasets et sources

### Vue d'ensemble des fichiers de donnees

| Fichier | Source | Annee | Communes | Taille | Script |
|---------|--------|-------|----------|--------|--------|
| `maires.json` | Min. Interieur (RNE) | 2020 | 34 844 | 3,8 Mo | `process_maires.py` |
| `surveillance.json` | Min. Interieur | 2024 | 4 164 | 183 Ko | `process_surveillance.py` |
| `prospection.json` | Multi-sources | 2019-2025 | 16 747 | 1,3 Mo | `process_prospection.py` |
| `delinquance.json` | SSMSI | 2024 | ~9 400 | 1,2 Mo | `process_delinquance.py` |
| `enrichment.json` | DGFiP, INSEE, ANCT | 2021-2024 | ~35 000 | 3,2 Mo | `process_enrichment.py` |
| `insights.json` | Calcule | 2025 | ~9 500 | 5 Mo | `process_insights.py` |
| `municipales2026.json` | Min. Interieur | 2026 | variable | 8,5 Mo | `process_municipales2026.py` |
| `communes-topo.json` | IGN | 2022 | 34 844 | 13 Mo | — (pre-genere) |

### 1. Donnees politiques — `maires.json`

**Sources** : Nuances politiques (Min. Interieur, municipales 2020) + Repertoire National des Elus (data.gouv.fr)

| Champ | Description | Exemple |
|-------|-------------|---------|
| `n` | Nom de la commune | "Carcassonne" |
| `nu` | Code nuance politique | "LSOC" |
| `f` | Famille politique | "Gauche" |
| `cl` | Couleur hexadecimale | "#E2001A" |
| `lb` | Label lisible | "Socialiste" |
| `m` | Nom du maire | "Gerard Larrat" |

**6 familles** : Gauche, Droite, Centre, Extreme droite, Courants politiques divers, Non classe.

**Limite importante** : 92,3% des communes sont "Non classe" — le Ministere n'attribue des nuances qu'aux communes >1 000 hab. (scrutin de liste). Seules 2 693 communes ont une couleur politique.

### 2. Donnees de surveillance — `surveillance.json`

**Sources** : Effectifs police municipale (Min. Interieur 2024, ODS) + Population (INSEE 2021, XLSX)

| Champ | Description |
|-------|-------------|
| `pm` | Agents de police municipale |
| `asvp` | Agents de surveillance de voie publique |
| `pop` | Population INSEE 2021 |
| `r` | Ratio (PM+ASVP) / 10 000 hab. (plafonne a 50) |
| `r_raw` | Ratio brut avant plafonnement (si > 50) |

**Calcul** : `ratio = (pm + asvp) / population * 10 000`

**Plafonnement a 50** : sans plafonnement, quelques communes extremes (Lirac : 544, Riboux : 392) ecrasent l'echelle de couleur. Le plafond preserve la lisibilite.

**Couverture** : 4 164 communes sur 34 844 (12%). Les 30 680 restantes n'ont ni PM ni ASVP dans les donnees du Ministere.

**Jointure** : par nom normalise (NFD, majuscules, expansion "ST"→"SAINT") car le fichier source n'a pas de code INSEE. Taux de matching : 91%.

### 3. Donnees de prospection — `prospection.json`

| Source | Annee | Communes | Utilisation |
|--------|-------|----------|-------------|
| Effectifs PM multi-annees | 2019, 2021, 2024 | 4 964 | Signaux PM count + PM growth |
| Stationnement payant (GART/Cerema) | 2019 | 226 | Signal stat_payant |
| Videoverbalisation (video-verbalisation.fr) | 2025 | 586 | Filtre d'exclusion |
| Accidents routiers (ONISR BAAC) | 2023-2024 | 16 064 | Signal accidents |
| Population INSEE | 2021 | 4 145 | Signal pop_sweet |
| DGF par habitant (DGFiP) | 2022 | ~35 000 | Signal budget_capacity |

| Champ | Description |
|-------|-------------|
| `pm_trend` | Effectifs PM+ASVP par annee (ex: `[7, 12, 15]`) |
| `pm_trend_years` | Annees correspondantes (ex: `[2019, 2021, 2024]`) |
| `stat_payant` | Commune avec stationnement payant (`true`/`false`) |
| `videoverb` | Commune equipee en videoverbalisation |
| `accidents` | Accidents corporels cumules sur 2 ans |
| `pop`, `pm`, `asvp` | Population et effectifs actuels |

### 4. Donnees de delinquance — `delinquance.json`

**Source** : SSMSI (Min. Interieur), fichier Parquet ~14 Mo, annee 2024

| Champ | Description |
|-------|-------------|
| `total` | Nombre total de faits toutes categories |
| `cats` | 15 categories de delits (voir ci-dessous) |
| `pop` | Population |
| `r` | Ratio total / 10 000 hab. (non plafonne) |
| `year` | "2024" |

**15 categories** : cambriolages (`cambr`), destructions (`destr`), escroqueries (`escro`), trafic stupefiants (`traf_stup`), usage stupefiants (`usage_stup`, `usage_stup_afd`), violences physiques (`viol_phys`), violences intrafamiliales (`viol_intraf`), violences sexuelles (`viol_sex`), vols avec armes (`vols_armes`), vols accessoires vehicules (`vols_acc_veh`), vols dans vehicules (`vols_ds_veh`), vols de vehicule (`vols_veh`), vols sans violence (`vols_sv`), vols violents (`vols_viol`).

**Couverture** : ~9 400 communes (27%). Les petites communes sont masquees par le seuil de diffusion SSMSI (protection de l'anonymat).

### 5. Donnees d'enrichissement — `enrichment.json`

| Champ | Source | Annee | Description |
|-------|--------|-------|-------------|
| `qpv` | ANCT | 2024 | Nombre de Quartiers Prioritaires (843 communes) |
| `dgf_hab` | DGFiP | 2022 | Dotation Globale de Fonctionnement / hab. (EUR) |
| `dette_hab` | DGFiP | 2022 | Dette / hab. (EUR) |
| `cafn_hab` | DGFiP | 2022 | Capacite d'autofinancement nette / hab. (EUR) |
| `perso_hab` | DGFiP | 2022 | Charges de personnel / hab. (EUR) |
| `rev_med` | Filosofi/INSEE | 2021 | Revenu median par UC (EUR) |
| `tx_pauv` | Filosofi/INSEE | 2021 | Taux de pauvrete (%) — ~4 350 communes |

### 6. Insights — `insights.json`

Peer groups et benchmarks calcules par `process_insights.py` (~2 min).

**Algorithme de distance** : distance euclidienne ponderee sur 4 dimensions normalisees (z-score) :
- `log(population)` — poids 0.4
- `revenu median` — poids 0.25
- `taux de pauvrete` — poids 0.25
- `famille politique` — bonus de proximite -0.3 si meme famille

| Champ | Description |
|-------|-------------|
| `peers` | Top 5 codes INSEE des communes similaires |
| `peer_names` | Noms affichables |
| `bench` | Benchmarks par indicateur (`val`/`med`/`pct`) |
| `flags` | Flags narratifs pour l'argumentaire commercial |

**Flags narratifs** : `crime_above_peers`, `no_pm_peers_have`, `no_vv_peers_have`, `pm_growing`, `high_accident_rate`, `budget_capacity`, `high_poverty`.

---

## Score de prospection — formule

Le score (0-100) est la moyenne ponderee de 6 signaux, chacun normalise entre 0 et 1 :

### Signal 1 : Stationnement payant (30%)

```
signal = 1 si stationnement payant, 0 sinon
```

Source : GART/Cerema 2019. **226 communes** seulement (~800+ en realite).

### Signal 2 : Effectif police municipale (20%)

```
signal = min((pm + asvp) / pop * 10 000 / 50, 1)
```

### Signal 3 : Croissance des effectifs PM (10%)

```
taux = max((effectif_2024 - effectif_2019) / effectif_2019, 0)
signal = min(taux * sqrt(effectif_2024) / 5, 1)
```

La ponderation par `sqrt(volume)` evite que les petites variations dominent (passer de 0 a 1 agent ≠ passer de 10 a 20).

### Signal 4 : Accidents routiers (15%)

```
signal = min(accidents_2ans / pop * 10 000 / 30, 1)
```

Source : ONISR BAAC 2023-2024 (~109 000 accidents corporels).

### Signal 5 : Taille de la commune (25%)

```
signal = exp(-0.5 * ((ln(pop) - ln(30 000)) / 1.2)^2)
```

Gaussienne centree sur 30 000 hab. : les communes 5 000–100 000 hab. sont la cible ideale.

| Population | Signal |
|-----------|--------|
| 5 000 | 0.36 |
| 10 000 | 0.64 |
| 30 000 | 1.00 |
| 100 000 | 0.64 |
| 500 000 | 0.08 |

### Signal 6 : Capacite budgetaire (0% par defaut)

```
signal = min(dgf_hab / 500, 1)
```

Desactive par defaut, activable via slider.

### Score final

```
score = arrondi((sum(signal_i * poids_i) / sum(poids_i)) * 100)
```

**Distribution** : 79% des communes < 10/100. **239 communes** depassent 50/100.

### Filtres de prospection

| Filtre | Effet |
|--------|-------|
| Stat. payant uniquement | 226 communes avec stationnement payant |
| Sans videoverbalisation | Exclut les 586 communes deja equipees |
| Population min. | Slider seuil de population |
| Communes avec QPV | 843 communes avec Quartier Prioritaire |

---

## Fraicheur des donnees

*Au 1er mars 2026*

| Donnee | Annee | Age | Statut |
|--------|-------|-----|--------|
| Municipales 2026 (T1) | 2026 | actuel | vert |
| Videoverbalisation | 2025 | ~1 an | vert |
| Effectifs PM | 2024 | ~2 ans | vert |
| Delinquance | 2024 | ~2 ans | vert |
| QPV | 2024 | ~2 ans | vert |
| Accidents routiers | 2023-2024 | ~2 ans | vert |
| Comptes communes (DGFiP) | 2022 | ~4 ans | jaune |
| Population INSEE | 2021 | ~5 ans | jaune |
| Revenus medians (Filosofi) | 2021 | ~5 ans | jaune |
| Nuances politiques | 2020 | ~6 ans | orange |
| Stationnement payant (GART) | 2019 | ~7 ans | rouge |

L'interface affiche des badges de fraicheur colores : vert (< 3 ans), jaune (3-5 ans), orange (5-7 ans), rouge (> 7 ans).

---

## Limites connues

### Couverture des donnees

| Donnee | Couverture | Cause |
|--------|-----------|-------|
| Nuances politiques | 7,7% | Seules les communes > 1 000 hab. |
| Stationnement payant | 226 communes | Enquete GART 2019 incomplete |
| Surveillance | 12% | Communes sans PM/ASVP absentes |
| Delinquance | ~27% | Seuil de diffusion SSMSI |
| Taux de pauvrete | ~4 350 communes | Secret statistique Filosofi |

### Biais du scoring

1. **Biais "communes moyennes"** : le signal `pop_sweet` (25%) favorise mecaniquement les communes ~30 000 hab.
2. **Sous-representation stationnement payant** : 226 communes sur 800+ reelles → contribution moyenne de 0,4 pts/100
3. **Accidents corporels uniquement** : exclut les accidents materiels et infractions sans accident
4. **Population permanente** : les communes touristiques ont des ratios surevalues (PM et delinquance)

### Donnees absentes

- Police intercommunale (mutualisations depuis 2019)
- Radars et PV automatises (pas de dataset open data communal)
- Budget "securite" detaille (DGFiP sans decoupage fonctionnel)

---

## Architecture technique

### Frontend

Application monopage dans `index.html` (~3 400 lignes). Pas de framework, pas de build system.

| Composant | Technologie |
|-----------|-------------|
| Cartographie | Leaflet.js 1.9.4 |
| Geometries | TopoJSON → GeoJSON (topojson-client 3.1.0) |
| Fond de carte | CartoDB Dark No Labels |
| Authentification client | Clerk JS (CDN) |
| Style | CSS inline, theme sombre |

### Backend / Hosting

| Composant | Technologie |
|-----------|-------------|
| Hebergement | Vercel (site statique) |
| Auth middleware | Vercel Edge Middleware (`middleware.js`) |
| Verification JWT | `jose` (Web Crypto, compatible Edge) |
| Provider auth | Clerk (restriction domaine `@vizzia.fr`) |
| Cache email | Map en memoire (cap 500 entrees) |

**Flux d'authentification** :
1. L'utilisateur accede a l'URL → le middleware intercepte
2. Pas de cookie `__session` → redirection vers `/sign-in`
3. Connexion via Clerk → cookie de session pose
4. Le middleware verifie le JWT contre le JWKS Clerk
5. Verification du domaine email (`@vizzia.fr`) via API Clerk (resultat cache)
6. Acces autorise → les fichiers statiques sont servis

### Data pipeline

```
Sources externes (data.gouv.fr, INSEE, ONISR, DGFiP)
        │
        ▼
Scripts Python (process_*.py)
        │
        ▼
Fichiers JSON (maires.json, surveillance.json, ...)
        │
        ▼
Frontend (index.html charge les JSON au demarrage)
```

### Performance

- **35 000 polygones** rendus via Leaflet Canvas
- **Style pre-alloues** : 6 objets `STYLE_*` partages pour eviter 35k allocations par restyle
- **Cache scores** : `prospScoreCache` evite de recalculer 35k scores a chaque interaction
- **Debounce** : sliders (50ms) et recherche (80ms)
- **Normalisation pre-calculee** : noms de communes normalises une fois au chargement pour la recherche

### Deep linking

URL : `?mode=X&commune=XXXXX&filter=Y`

- `mode` : prospection (defaut, omis), politique, surveillance, securite, municipales2026
- `commune` : code INSEE 5 chiffres
- `filter` : famille politique active

---

## Developpement

### Prerequis

- Python 3.8+ avec `pandas`, `openpyxl`, `odf`, `pyarrow`
- Un navigateur web (pas de serveur de dev necessaire)
- Node.js + npm (uniquement pour le deploiement Vercel)

### Lancer en local

```bash
# Ouvrir directement dans le navigateur
open index.html
# L'auth Clerk est bypassee en local (le middleware ne tourne que sur Vercel)
```

### Regenerer les donnees

```bash
python3 process_maires.py           # necessite nuances-communes.csv + elus-maires.csv dans /tmp
python3 process_surveillance.py     # telecharge depuis data.gouv.fr
python3 process_prospection.py      # construit les donnees de scoring
python3 process_delinquance.py      # telecharge le parquet (~14 Mo)
python3 process_enrichment.py       # telecharge QPV, DGFiP, Filosofi
python3 process_insights.py         # calcule peer groups + benchmarks (~2 min)
python3 process_municipales2026.py  # donnees municipales 2026
```

Les URLs des sources sont en dur dans les scripts. Si une URL change sur data.gouv.fr, le script echouera.

### Deployer

Le deploiement est automatique via Vercel :

1. Push sur `main` → Vercel deploie
2. Variables d'environnement (`CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`) configurees dans le dashboard Vercel
3. La cle publishable est aussi dans `sign-in.html` et `index.html` (publique par design)

---

## Structure du repo

```
index.html              ← Application complete (HTML + CSS + JS)
sign-in.html            ← Page de connexion Clerk
middleware.js           ← Vercel Edge Middleware (auth)
vercel.json             ← Configuration Vercel
package.json            ← Dependance jose
communes-topo.json      ← Geometries des communes (TopoJSON, 13 Mo)
maires.json             ← Donnees politiques
surveillance.json       ← Effectifs police municipale
prospection.json        ← Signaux de prospection
delinquance.json        ← Statistiques de delinquance
enrichment.json         ← Donnees socio-economiques
insights.json           ← Peer groups et benchmarks
municipales2026.json    ← Donnees municipales 2026
process_*.py            ← Scripts de generation des donnees
METHODOLOGIE.md         ← Documentation detaillee des calculs et biais
CLAUDE.md               ← Instructions pour Claude Code
```

---

## Licence

Usage interne Vizzia.
