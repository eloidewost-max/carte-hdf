# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive map visualizing French municipal mayors' political affiliations, local surveillance data, crime statistics, and socio-economic indicators across ~35,000 communes. Four modes: **politique** (political family colors), **surveillance** (heatmap of police agents per capita), **securite** (crime rate heatmap by category), and **prospection** (composite score for video-enforcement potential).

## Architecture

**Single-file frontend** — all HTML, CSS, and JavaScript live in `index.html` (~2600 lines). No build system, no package manager, no framework beyond Leaflet.

### Frontend Stack
- **Leaflet.js** (v1.9.4) for map rendering, loaded from CDN
- **topojson-client** (v3.1.0) for converting TopoJSON → GeoJSON, loaded from CDN
- **CartoDB Dark No Labels** basemap
- Vanilla JavaScript (ES5-compatible), inline CSS

### Data Pipeline
Python scripts generate JSON data files from external sources (data.gouv.fr, INSEE, ONISR, DGFiP):

```
process_maires.py       → maires.json        (mayors + political family, ~3.8 MB)
process_surveillance.py → surveillance.json  (police counts + ratio, ~183 KB)
process_prospection.py  → prospection.json   (prospection signals + scoring data, ~1.3 MB)
process_delinquance.py  → delinquance.json   (crime stats by commune, ~1.2 MB)
process_enrichment.py   → enrichment.json    (QPV, DGFiP finances, revenus, ~3.2 MB)
```

Python dependencies: `pandas`, `openpyxl`, `odf`, `pyarrow` (for parquet)

### Key Data Files
- `communes-topo.json` — TopoJSON commune boundaries (13 MB, object key: `a_com2022`)
- `maires.json` — keyed by INSEE code, fields: `n` (name), `nu` (nuance), `f` (famille), `cl` (color), `lb` (label), `m` (maire)
- `surveillance.json` — keyed by INSEE code, fields: `pm` (police municipale), `asvp` (ASVP agents), `pop` (population), `r` (ratio per 10k, capped at 50), `r_raw` (uncapped ratio, only if capped)
- `prospection.json` — keyed by INSEE code, fields: `stat_payant`, `videoverb`, `pm`, `asvp`, `pop`, `pm_trend` (array), `pm_trend_years` (array), `accidents` (count 2023-2024), `accidents_years`
- `delinquance.json` — keyed by INSEE code, fields: `total` (total crimes), `cats` (object with 15 short keys), `pop` (population), `r` (ratio per 10k), `year`
- `enrichment.json` — keyed by INSEE code, fields: `qpv` (QPV count), `dgf_hab` (DGF per capita), `dette_hab`, `cafn_hab`, `perso_hab`, `rev_med` (median income), `tx_pauv` (poverty rate)

### Crime Categories (delinquance.json `cats` keys)
`cambr` (cambriolages), `destr` (destructions), `escro` (escroqueries), `traf_stup` (trafic stupefiants), `usage_stup`, `usage_stup_afd`, `viol_phys` (violences physiques), `viol_intraf` (violences intrafamiliales), `viol_sex` (violences sexuelles), `vols_armes`, `vols_acc_veh`, `vols_ds_veh`, `vols_veh`, `vols_sv` (vols sans violence), `vols_viol`

### Prospection Scoring
Composite score from 6 weighted signals (no_videoverb moved to filter-only):
- `stat_payant` (30%) — commune has paid parking (GART 2019)
- `pm_count` (20%) — police agents per 10k pop, capped at 1
- `pm_growth` (10%) — growth rate weighted by sqrt(volume) to avoid small-number noise
- `accidents` (15%) — road accidents per 10k pop (ONISR 2023-2024)
- `pop_sweet` (25%) — gaussian on log(pop) centered at 30k
- `budget_capacity` (0% default) — DGF per capita normalized (DGFiP 2022), user-activatable

### State Management
Global JS variables: `activeFilter` (selected political family), `currentMode` ('politique'|'surveillance'|'securite'|'prospection'), `survFilters` (ratio slider + checkbox), `prospWeights` (signal weights for scoring), `prospFilters` (prospection mode filters including `qpvOnly`), `secuFilter` (selected crime category or null), `secuFilters` (ratioMin slider + dataOnly checkbox), `delinq` (delinquance data object), `enrich` (enrichment data object).

### Core Flow
1. Fetch 5 JSON data files on load (maires, surveillance, prospection, delinquance, enrichment)
2. Convert TopoJSON → GeoJSON via `topojson.feature()`
3. Style communes via `getStylePolitique()`, `getStyleSurveillance()`, `getStyleSecurite()`, or `getStyleProspection()` based on mode
4. Hover shows info panel, click zooms, filters restyle the layer
5. Search bar with autocomplete indexes commune names from `maires.json`, uses `layerByCode` lookup to zoom to selected commune
6. Detail panel shows all available data for a commune regardless of active mode (delinquance breakdown, finances, QPV badge, freshness badges)

### Mode Colors
| Mode | Color | Palette |
|------|-------|---------|
| Politique | `#4a90d9` | Political family colors |
| Surveillance | `#e8913a` | Yellow → red (6 levels) |
| Securite | `#c0392b` | Violet → magenta (6 levels, `SECU_COLORS`) |
| Prospection | `#4ecdc4` | Blue → red (5 levels) |

## Commands

### Regenerate data files
```bash
python3 process_maires.py           # requires nuances-communes.csv + elus-maires.csv in /tmp
python3 process_surveillance.py     # downloads from data.gouv.fr APIs
python3 process_prospection.py      # builds prospection scoring data
python3 process_delinquance.py      # downloads parquet from data.gouv.fr (~14 MB)
python3 process_enrichment.py       # downloads QPV CSV, DGFiP JSON, Filosofi 2021 CSV
```

### Development
Open `index.html` directly in a browser — no dev server needed.

## Conventions

- **Commits:** `type: message` format (feat, fix, style, docs, chore)
- **JS naming:** camelCase variables, kebab-case DOM IDs and CSS classes
- **Data keys:** short abbreviations to minimize JSON size (see data files section above)
- **Language:** UI text is in French
