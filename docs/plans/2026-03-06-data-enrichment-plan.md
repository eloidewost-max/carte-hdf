# Data Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate 4 new data.gouv.fr datasets into the interactive commune map: delinquance communale (new mode), QPV, comptes communes (DGF/dette/CAF), revenus — with ultra-rich detail panels showing all data on commune click.

**Architecture:** Two new Python scripts generate `delinquance.json` and `enrichment.json`. Frontend gets a 4th mode "securite" + enriched detail panels showing all available data regardless of active mode. QPV comes from a simple CSV (insee_com column), no spatial intersection needed.

**Tech Stack:** Python (pandas, openpyxl, requests), vanilla JS/Leaflet (existing), data.gouv.fr APIs

---

## Phase 1: Data Pipeline

### Task 1: Create `process_delinquance.py`

**Files:**
- Create: `process_delinquance.py`
- Output: `delinquance.json`

**Step 1: Write the script skeleton**

```python
#!/usr/bin/env python3
"""Generate delinquance.json from Ministere de l'Interieur communal crime data."""

import gzip
import io
import json
import os
import sys

import pandas as pd
import requests

# Parquet file from data.gouv.fr (communal, geographie 2025, data 2024)
PARQUET_URL = "https://static.data.gouv.fr/resources/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales/20250710-144903/donnee-comm-data.gouv-parquet-2024-geographie2025-produit-le2025-06-04.parquet"

# Mapping from long indicateur names to short keys
# The exact names must be confirmed from the actual data
INDICATEUR_MAP = {
    "Coups et blessures volontaires": "coups",
    "Violences sexuelles": "viol_sex",
    "Vols avec violences": "vols_av",
    "Vols sans violence contre des personnes": "vols_sv",
    "Cambriolages de logement": "cambr",
    "Vols de véhicules": "vols_veh",
    "Vols dans les véhicules": "vols_ds_veh",
    "Vols d'accessoires sur véhicules": "vols_acc_veh",
    "Destructions et dégradations volontaires": "destr",
    "Trafic de stupéfiants": "stup",
    "Usage de stupéfiants": "usage_stup",
    "Escroqueries": "escroc",
    "Homicides": "homic",
    "Tentatives d'homicide": "tent_homic",
    "Violences intrafamiliales": "viol_intraf",
    "Violences physiques hors cadre familial": "viol_phys",
}

# Short key -> French label for UI display
INDICATEUR_LABELS = {v: k for k, v in INDICATEUR_MAP.items()}

OUTPUT = os.path.join(os.path.dirname(__file__), "delinquance.json")


def download_parquet():
    """Download parquet and return DataFrame."""
    print("Downloading communal delinquance parquet...")
    resp = requests.get(PARQUET_URL, timeout=120)
    resp.raise_for_status()
    buf = io.BytesIO(resp.content)
    df = pd.read_parquet(buf)
    print(f"  {len(df)} rows, columns: {list(df.columns)}")
    return df


def process(df):
    """Aggregate by commune, latest year, build output dict."""
    # Print unique indicateurs to verify mapping
    indicateurs = df["indicateur"].unique()
    print(f"  {len(indicateurs)} unique indicateurs:")
    for ind in sorted(indicateurs):
        mapped = INDICATEUR_MAP.get(ind, "??? UNMAPPED")
        print(f"    {ind} -> {mapped}")

    # Find the commune code column (could be CODGEO_2025, codgeo, Code.commune, etc.)
    code_col = None
    for candidate in ["CODGEO_2025", "codgeo_2025", "CODGEO", "codgeo", "Code.commune"]:
        if candidate in df.columns:
            code_col = candidate
            break
    if code_col is None:
        print(f"ERROR: No commune code column found. Columns: {list(df.columns)}")
        sys.exit(1)
    print(f"  Using commune code column: {code_col}")

    # Filter to latest year available
    latest_year = df["annee"].max()
    print(f"  Latest year: {latest_year}")
    df_latest = df[df["annee"] == latest_year].copy()

    # Keep only indicateurs we have in our mapping
    df_latest = df_latest[df_latest["indicateur"].isin(INDICATEUR_MAP.keys())]

    # Build per-commune aggregation
    result = {}
    for code, group in df_latest.groupby(code_col):
        code_str = str(code).zfill(5)
        cats = {}
        total = 0
        pop = None
        for _, row in group.iterrows():
            short_key = INDICATEUR_MAP.get(row["indicateur"])
            if short_key:
                nombre = int(row["nombre"]) if pd.notna(row["nombre"]) else 0
                cats[short_key] = nombre
                total += nombre
            if pop is None and pd.notna(row.get("insee_pop")):
                pop = int(row["insee_pop"])

        if total == 0:
            continue

        entry = {"total": total, "cats": cats}
        if pop and pop > 0:
            entry["pop"] = pop
            entry["r"] = round(total / pop * 10000, 1)
        entry["year"] = str(latest_year)
        result[code_str] = entry

    return result


def main():
    df = download_parquet()
    result = process(df)
    print(f"Writing {len(result)} communes to {OUTPUT}")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"Done. {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
```

**Step 2: Run the script and verify output**

Run: `cd /home/hadrien/carte-politique && python3 process_delinquance.py`
Expected: Downloads parquet, prints column info and indicateur mapping, writes `delinquance.json`
Verify: `python3 -c "import json; d=json.load(open('delinquance.json')); print(len(d), 'communes'); k=list(d.keys())[0]; print(k, d[k])"`

**Step 3: Fix any unmapped indicateurs**

If the script prints "??? UNMAPPED" for any indicateur, add the missing mapping to `INDICATEUR_MAP`. The exact names in the communal file may differ slightly from the regional file (e.g., with accents, "hors AFD" suffixes).

**Step 4: Commit**

```bash
git add process_delinquance.py delinquance.json
git commit -m "feat: add process_delinquance.py — crime stats by commune from data.gouv.fr"
```

---

### Task 2: Create `process_enrichment.py`

**Files:**
- Create: `process_enrichment.py`
- Output: `enrichment.json`

This script merges 3 data sources into one file:
1. **QPV** (CSV list, 1584 rows, has `insee_com` column)
2. **Comptes individuels communes 2022** (CSV from DGFiP, 34,955 rows)
3. **Revenus 2013** (XLSX from Filosofi/INSEE)

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Generate enrichment.json: QPV count, DGF, budget data, revenus per commune."""

import io
import json
import os
import sys

import pandas as pd
import requests

OUTPUT = os.path.join(os.path.dirname(__file__), "enrichment.json")

# --- Data sources ---

# QPV 2024 CSV list (has insee_com column with commune code)
QPV_CSV_URL = "https://static.data.gouv.fr/resources/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20260116-110350/listeqp2024-cog2024.csv"

# Comptes individuels des communes 2022 (DGFiP) — JSON export
COMPTES_JSON_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-2022/exports/json"
# Alternative CSV (same data):
COMPTES_CSV_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-2022/exports/csv?use_labels=true"

# Revenus Filosofi 2013 (XLSX)
REVENUS_XLSX_URL = "https://static.data.gouv.fr/resources/revenus-des-francais-a-la-commune/20171102-114238/Niveau_de_vie_2013_a_la_commune-Global_Map_Solution.xlsx"


def download_csv(url, **kwargs):
    print(f"  Downloading {url[:80]}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text), **kwargs)


def download_json(url):
    print(f"  Downloading JSON {url[:80]}...")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    return resp.json()


def download_xlsx(url):
    print(f"  Downloading XLSX {url[:80]}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")


def process_qpv():
    """Count QPV per commune from CSV list."""
    print("Processing QPV...")
    df = download_csv(QPV_CSV_URL, sep=";", dtype={"insee_com": str, "insee_dep": str})
    # Pad commune code: insee_dep (2-3 digits) + insee_com (without dep prefix, or full code)
    # The CSV has insee_com as just the commune number (not zero-padded to 5)
    # We need to reconstruct the full 5-digit INSEE code
    qpv_count = {}
    for _, row in df.iterrows():
        dep = str(row.get("insee_dep", "")).strip()
        com = str(row.get("insee_com", "")).strip()
        if not com:
            continue
        # insee_com might be the full code or just commune part
        # From the data: insee_dep=1, insee_com=1053 -> code=01053
        code = com.zfill(5)
        qpv_count[code] = qpv_count.get(code, 0) + 1
    print(f"  {len(qpv_count)} communes with QPV ({sum(qpv_count.values())} total QPV)")
    return qpv_count


def process_comptes():
    """Extract key budget indicators from comptes individuels 2022."""
    print("Processing comptes individuels communes 2022...")
    # Use CSV export (smaller than JSON for this case)
    try:
        data = download_json(COMPTES_JSON_URL)
    except Exception as e:
        print(f"  JSON download failed ({e}), trying CSV...")
        df = download_csv(COMPTES_CSV_URL, sep=";")
        data = df.to_dict(orient="records")

    budget = {}
    for row in data:
        # Build INSEE code from dep + icom
        dep = str(row.get("dep", "")).strip()
        icom = str(row.get("icom", "")).strip()
        if not dep or not icom:
            continue
        # dep is 3-char (e.g. "050", "065", "02A"), icom is 3-char
        # INSEE code = dep (2 digits, strip leading 0 if 3-digit and numeric) + icom (3 digits)
        if len(dep) == 3 and dep[0] == "0":
            code = dep[1:] + icom
        else:
            code = dep + icom
        code = code.zfill(5)

        pop = row.get("pop1")
        if not pop or int(pop) == 0:
            continue

        pop = int(pop)
        entry = {}

        # DGF par habitant (fdgf = DGF / pop * 1000 in the dataset, i.e. EUR per hab)
        dgf_hab = row.get("fdgf")
        if dgf_hab is not None:
            entry["dgf_hab"] = round(float(dgf_hab), 1)

        # DGF total (dgf = in thousands of EUR, i.e. kEUR)
        dgf = row.get("dgf")
        if dgf is not None:
            entry["dgf"] = round(float(dgf), 1)

        # Dette par habitant
        dette_hab = row.get("fdette")
        if dette_hab is not None:
            entry["dette_hab"] = round(float(dette_hab), 1)

        # CAF nette par habitant
        cafn_hab = row.get("fcafn")
        if cafn_hab is not None:
            entry["cafn_hab"] = round(float(cafn_hab), 1)

        # Charges de personnel par habitant
        perso_hab = row.get("fperso")
        if perso_hab is not None:
            entry["perso_hab"] = round(float(perso_hab), 1)

        # Produits de fonctionnement par habitant
        prod_hab = row.get("fprod")
        if prod_hab is not None:
            entry["prod_hab"] = round(float(prod_hab), 1)

        # Equipement par habitant
        equip_hab = row.get("fequip")
        if equip_hab is not None:
            entry["equip_hab"] = round(float(equip_hab), 1)

        if entry:
            entry["pop"] = pop
            budget[code] = entry

    print(f"  {len(budget)} communes with budget data")
    return budget


def process_revenus():
    """Extract revenus from Filosofi 2013 XLSX."""
    print("Processing revenus 2013...")
    try:
        df = download_xlsx(REVENUS_XLSX_URL)
    except Exception as e:
        print(f"  WARNING: Could not download revenus XLSX: {e}")
        return {}

    print(f"  Columns: {list(df.columns)}")
    # Find the commune code column and relevant revenue columns
    # Expected columns vary; adapt based on actual file
    code_col = None
    for candidate in ["CODGEO", "Code commune", "code_commune", "INSEE_COM", "code"]:
        if candidate in df.columns:
            code_col = candidate
            break

    if code_col is None:
        # Try first column if it looks like codes
        first_col = df.columns[0]
        sample = str(df[first_col].iloc[0])
        if sample.isdigit() and len(sample) == 5:
            code_col = first_col
        else:
            print(f"  WARNING: No commune code column found, skipping revenus")
            return {}

    revenus = {}
    for _, row in df.iterrows():
        code = str(row[code_col]).zfill(5)
        entry = {}

        # Look for median income column
        for col in df.columns:
            col_lower = col.lower()
            if "median" in col_lower or "médian" in col_lower:
                val = row[col]
                if pd.notna(val):
                    try:
                        entry["rev_med"] = round(float(val), 0)
                    except (ValueError, TypeError):
                        pass
                break

        # Look for poverty rate column
        for col in df.columns:
            col_lower = col.lower()
            if "pauvre" in col_lower or "poverty" in col_lower:
                val = row[col]
                if pd.notna(val):
                    try:
                        entry["tx_pauv"] = round(float(val), 1)
                    except (ValueError, TypeError):
                        pass
                break

        if entry:
            revenus[code] = entry

    print(f"  {len(revenus)} communes with revenue data")
    return revenus


def main():
    qpv_count = process_qpv()
    budget = process_comptes()
    revenus = process_revenus()

    # Merge all into one dict keyed by INSEE code
    all_codes = set(qpv_count.keys()) | set(budget.keys()) | set(revenus.keys())
    result = {}
    for code in sorted(all_codes):
        entry = {}
        if code in qpv_count:
            entry["qpv"] = qpv_count[code]
        if code in budget:
            entry.update(budget[code])
        if code in revenus:
            entry.update(revenus[code])
        if entry:
            result[code] = entry

    print(f"\nWriting {len(result)} communes to {OUTPUT}")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"Done. {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
```

**Step 2: Run and verify**

Run: `cd /home/hadrien/carte-politique && python3 process_enrichment.py`
Verify: `python3 -c "import json; d=json.load(open('enrichment.json')); print(len(d), 'communes'); k='75056'; print(k, d.get(k, 'NOT FOUND'))"`

**Step 3: Debug and fix column detection**

The revenus XLSX and comptes JSON may have slightly different column names than expected. Run the script, check the printed column names, and fix the detection logic.

Key things to verify:
- QPV: `insee_com` is the full 5-digit code (e.g. "01053") or just a number (1053)?
- Comptes: dep="050" + icom="082" -> need to build "50082" correctly
- Revenus: identify the correct column names from `df.columns` output

**Step 4: Commit**

```bash
git add process_enrichment.py enrichment.json
git commit -m "feat: add process_enrichment.py — QPV, budget, revenus per commune"
```

---

## Phase 2: Frontend — Data Loading & State

### Task 3: Load new JSON files and add securite mode state

**Files:**
- Modify: `index.html`

**Step 1: Add new global variables** (near line 290)

Add after existing global state variables:
```javascript
var delinq = {};          // delinquance data keyed by INSEE code
var enrich = {};          // enrichment data (QPV, budget, revenus)
var secuFilter = null;    // active delinquance category filter (null = total)
var secuFilters = {
  ratioMin: 0,
  dataOnly: false
};
```

**Step 2: Update Promise.all fetch** (near line 238)

Change the data loading to include new files:
```javascript
var results = await Promise.all([
  fetchJSON('maires.json'),
  fetchJSON('surveillance.json'),
  fetchJSON('prospection.json'),
  fetchJSON('communes-topo.json'),
  fetchJSON('delinquance.json'),
  fetchJSON('enrichment.json')
]);
maires = results[0]; surv = results[1]; prosp = results[2];
var topoData = results[3];
delinq = results[4]; enrich = results[5];
```

**Step 3: Add mode constant and color** (near MODE_COLORS)

```javascript
// In MODE_COLORS object, add:
securite: '#c0392b'
```

**Step 4: Add securite button in HTML** (in #mode-tabs)

Add a 4th button:
```html
<button class="mode-btn" data-mode="securite">Securite</button>
```

**Step 5: Update switchMode() to handle securite** (near line 895)

In the `switchMode(mode)` function, add the securite case to the switch/if chain that calls the appropriate render function.

**Step 6: Verify page loads without errors**

Open index.html in browser, check console for fetch errors. All 6 JSON files should load.

**Step 7: Commit**

```bash
git add index.html
git commit -m "feat: load delinquance + enrichment JSON, add securite mode stub"
```

---

## Phase 3: Frontend — Enriched Detail Panel

### Task 4: Rewrite detail panel to show all data

**Files:**
- Modify: `index.html` — the `showDetail(code)` or equivalent function (around lines 594-856)

This is the largest frontend task. The detail panel currently shows different content per mode. We need to make it show ALL available data regardless of mode.

**Step 1: Add delinquance section to detail panel**

After the existing surveillance section, add a new section that shows delinquance data:

```javascript
// --- Delinquance section ---
var dl = delinq[code];
if (dl) {
  html += '<div class="detail-section">';
  html += '<div class="detail-section-title">Delinquance enregistree</div>';
  // Ratio total
  html += '<div style="font-size:22px;font-weight:700;color:#c0392b">';
  html += dl.r ? (dl.r + ' /10k hab') : (dl.total + ' faits');
  html += '</div>';
  // Year badge
  html += '<span class="freshness-badge" style="background:#27ae60">' + dl.year + '</span>';
  // Category breakdown bars
  if (dl.cats) {
    var catEntries = Object.entries(dl.cats).sort(function(a,b){ return b[1]-a[1]; });
    var maxCat = catEntries[0] ? catEntries[0][1] : 1;
    html += '<div style="margin-top:8px">';
    catEntries.forEach(function(pair) {
      var key = pair[0], val = pair[1];
      var label = DELINQ_LABELS[key] || key;
      var pct = Math.round(val / maxCat * 100);
      var ratio = dl.pop ? (val / dl.pop * 10000).toFixed(1) : '?';
      html += '<div style="display:flex;align-items:center;gap:6px;margin:3px 0;font-size:11px">';
      html += '<span style="width:140px;text-align:right;color:#aaa;flex-shrink:0">' + label + '</span>';
      html += '<div style="flex:1;height:10px;background:#333;border-radius:3px;overflow:hidden">';
      html += '<div style="width:' + pct + '%;height:100%;background:#c0392b;border-radius:3px"></div></div>';
      html += '<span style="width:45px;text-align:right;color:#eee">' + val.toLocaleString('fr-FR') + '</span>';
      html += '<span style="width:40px;text-align:right;color:#888;font-size:10px">' + ratio + '</span>';
      html += '</div>';
    });
    html += '</div>';
  }
  html += '</div>';
}
```

**Step 2: Add QPV badge in surveillance section**

In the existing surveillance section, add QPV info:
```javascript
var en = enrich[code];
if (en && en.qpv) {
  html += '<div class="detail-badge" style="background:#8e44ad;color:#fff">';
  html += 'QPV : ' + en.qpv + ' quartier' + (en.qpv > 1 ? 's' : '');
  html += '</div>';
}
```

**Step 3: Add socio-economic section**

After surveillance, add budget/revenue section:
```javascript
var en = enrich[code];
if (en && (en.dgf_hab || en.rev_med)) {
  html += '<div class="detail-section">';
  html += '<div class="detail-section-title">Contexte socio-economique</div>';
  if (en.rev_med) {
    html += '<div class="detail-row"><span class="detail-label">Revenu median</span>';
    html += '<span class="detail-value">' + Math.round(en.rev_med).toLocaleString('fr-FR') + ' EUR/UC</span></div>';
  }
  if (en.tx_pauv) {
    html += '<div class="detail-row"><span class="detail-label">Taux pauvrete</span>';
    html += '<span class="detail-value">' + en.tx_pauv + ' %</span></div>';
  }
  if (en.dgf_hab) {
    html += '<div class="detail-row"><span class="detail-label">DGF / habitant</span>';
    html += '<span class="detail-value">' + en.dgf_hab.toLocaleString('fr-FR') + ' EUR</span></div>';
  }
  if (en.dette_hab) {
    html += '<div class="detail-row"><span class="detail-label">Dette / habitant</span>';
    html += '<span class="detail-value">' + en.dette_hab.toLocaleString('fr-FR') + ' EUR</span></div>';
  }
  if (en.cafn_hab) {
    html += '<div class="detail-row"><span class="detail-label">CAF nette / hab</span>';
    html += '<span class="detail-value">' + en.cafn_hab.toLocaleString('fr-FR') + ' EUR</span></div>';
  }
  if (en.equip_hab) {
    html += '<div class="detail-row"><span class="detail-label">Equipement / hab</span>';
    html += '<span class="detail-value">' + en.equip_hab.toLocaleString('fr-FR') + ' EUR</span></div>';
  }
  html += '<div style="color:#666;font-size:10px;margin-top:4px">Source: DGFiP 2022 / Filosofi 2013</div>';
  html += '</div>';
}
```

**Step 4: Add DELINQ_LABELS constant** (near other constants)

```javascript
var DELINQ_LABELS = {
  coups: 'Coups & blessures',
  viol_sex: 'Violences sexuelles',
  vols_av: 'Vols avec violence',
  vols_sv: 'Vols sans violence',
  cambr: 'Cambriolages',
  vols_veh: 'Vols de vehicules',
  vols_ds_veh: 'Vols dans vehicules',
  vols_acc_veh: 'Vols accessoires veh.',
  destr: 'Destructions/degrad.',
  stup: 'Trafic stupefiants',
  usage_stup: 'Usage stupefiants',
  escroc: 'Escroqueries',
  homic: 'Homicides',
  tent_homic: 'Tent. homicide',
  viol_intraf: 'Violences intrafam.',
  viol_phys: 'Violences physiques'
};
```

**Step 5: Verify detail panel in browser**

Click on a large commune (Paris, Lyon, Marseille) and verify all sections appear with data. Click on a small commune and verify empty sections are hidden.

**Step 6: Commit**

```bash
git add index.html
git commit -m "feat: enriched detail panel — delinquance, QPV, budget, revenus"
```

---

## Phase 4: Frontend — New Securite Mode

### Task 5: Implement `getStyleSecurite()` and securite color scale

**Files:**
- Modify: `index.html`

**Step 1: Add color scale** (near SURV_COLORS)

```javascript
var SECU_COLORS = [
  { min: 0,   color: '#1a1a2e' },  // very low — dark
  { min: 20,  color: '#4a1942' },
  { min: 50,  color: '#7b2d5f' },
  { min: 100, color: '#b5446e' },
  { min: 200, color: '#e8665c' },
  { min: 400, color: '#f5a623' }   // very high — orange
];
```

**Step 2: Write `getStyleSecurite(feature)`**

```javascript
function getStyleSecurite(feature) {
  var code = feature.properties.codgeo || feature.properties.code;
  var d = delinq[code];
  if (!d || !d.r) {
    if (secuFilters.dataOnly) return { fillOpacity: 0, opacity: 0, weight: 0 };
    return { fillColor: '#111', fillOpacity: 0.15, weight: 0.3, color: '#333', opacity: 0.3 };
  }
  // Compute ratio based on active category filter
  var ratio;
  if (secuFilter && d.cats && d.cats[secuFilter]) {
    ratio = d.pop ? (d.cats[secuFilter] / d.pop * 10000) : 0;
  } else {
    ratio = d.r;
  }
  if (ratio < secuFilters.ratioMin) {
    return { fillColor: '#111', fillOpacity: 0.15, weight: 0.3, color: '#333', opacity: 0.3 };
  }
  var color = SECU_COLORS[0].color;
  for (var i = SECU_COLORS.length - 1; i >= 0; i--) {
    if (ratio >= SECU_COLORS[i].min) { color = SECU_COLORS[i].color; break; }
  }
  return { fillColor: color, fillOpacity: 0.85, weight: 0.5, color: '#444', opacity: 0.6 };
}
```

**Step 3: Wire into switchMode**

Add the securite case to call `geoLayer.setStyle(getStyleSecurite)` when switching to securite mode.

**Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add getStyleSecurite() with color scale for crime mode"
```

---

### Task 6: Implement securite sidebar (renderCmdSecurite)

**Files:**
- Modify: `index.html`

**Step 1: Write `renderCmdSecurite()`**

Follow the same pattern as `renderCmdSurveillance()`:
- **FILTRES section**: category pills (like famille pills) + ratio min slider + dataOnly checkbox
- **STATS section**: table showing crime ratio by political family
- **LEGENDE section**: color scale

The category pills should include "Tous" + one pill per delinquance category, styled like the famille pills in politique mode.

**Step 2: Write `renderSecuStats()`**

Same pattern as `renderSurvStats()` — iterate over political families, compute mean delinquance ratio per family, display in a table.

**Step 3: Update hover tooltip for securite mode**

In the `showInfo()` function, add the securite case:
```javascript
if (currentMode === 'securite') {
  var d = delinq[code];
  if (d && d.r) {
    var label = secuFilter ? (DELINQ_LABELS[secuFilter] || secuFilter) : 'Total';
    var ratio = secuFilter && d.cats && d.cats[secuFilter] && d.pop
      ? (d.cats[secuFilter] / d.pop * 10000).toFixed(1)
      : d.r;
    info = label + ' : ' + ratio + ' /10k';
  } else { info = 'Pas de donnees'; }
}
```

**Step 4: Update bottom bar for securite mode**

In `updateBottomBar()`, add securite case:
```javascript
if (currentMode === 'securite') {
  var count = 0, sum = 0;
  Object.keys(delinq).forEach(function(c) {
    if (delinq[c].r) { count++; sum += delinq[c].r; }
  });
  var avg = count ? (sum / count).toFixed(1) : 0;
  var catLabel = secuFilter ? DELINQ_LABELS[secuFilter] : 'Tous delits';
  stats.textContent = count + ' communes avec donnees | Ratio moyen : ' + avg + ' /10k | ' + catLabel;
}
```

**Step 5: Verify in browser**

Switch to securite mode, verify:
- Heatmap colors appear for communes with data
- Category pills filter the map
- Hover shows correct ratio
- Bottom bar updates

**Step 6: Commit**

```bash
git add index.html
git commit -m "feat: implement securite mode sidebar, filters, stats, bottom bar"
```

---

## Phase 5: Frontend — Prospection Enrichment

### Task 7: Add QPV filter and budget_capacity signal to prospection

**Files:**
- Modify: `index.html`

**Step 1: Add QPV filter checkbox**

In `renderCmdProspection()`, add a new checkbox filter:
```javascript
// After existing filter checkboxes
html += '<label class="filter-row"><input type="checkbox" id="filt-qpv"> Commune avec QPV</label>';
```

Wire it up in `prospFilters`:
```javascript
prospFilters.qpvOnly = false;
```

**Step 2: Add QPV filter logic in `passesProspFilters()`**

```javascript
if (prospFilters.qpvOnly && (!enrich[code] || !enrich[code].qpv)) return false;
```

**Step 3: Add budget_capacity signal to SIGNALS array**

```javascript
{
  key: 'budget_capacity',
  label: 'Capacite budgetaire',
  desc: 'DGF par habitant (DGFiP 2022)',
  weight: 0,
  year: '2022'
}
```

**Step 4: Add budget_capacity calculation in scoring function**

```javascript
// In the signal computation section:
if (sig.key === 'budget_capacity') {
  var en = enrich[code];
  if (en && en.dgf_hab) {
    raw = Math.min(en.dgf_hab / 500, 1);
  }
}
```

**Step 5: Verify scoring still works**

Open prospection mode, verify:
- QPV filter checkbox appears and filters correctly
- Budget capacity slider appears at 0% default weight
- Moving it to >0 changes some scores
- Existing scores are unchanged when budget_capacity weight = 0

**Step 6: Commit**

```bash
git add index.html
git commit -m "feat: add QPV filter and budget_capacity signal to prospection"
```

---

## Phase 6: Methodology & Polish

### Task 8: Update methodology drawer

**Files:**
- Modify: `index.html`

**Step 1: Add new data sources to methodology**

In `renderMethodo()`, add to the sources table:
- Delinquance enregistree | Ministere de l'Interieur | 2024 | Communes
- QPV | ANCT | 2024 | 1584 quartiers
- Comptes communes | DGFiP | 2022 | ~35,000 communes
- Revenus | Filosofi/INSEE | 2013 | ~36,000 communes

**Step 2: Add securite mode description**

Add a paragraph describing the securite mode: source, categories, how to interpret ratios.

**Step 3: Add known biases**

- Delinquance: seuil de population implicite (communes tres petites souvent absentes)
- Revenus: donnees de 2013 (anciennes mais seules disponibles par commune sur data.gouv)
- Comptes communes: donnees 2022 (plus recent disponible)

**Step 4: Commit**

```bash
git add index.html
git commit -m "docs: update methodology with new data sources and securite mode"
```

---

### Task 9: Final polish and QA

**Step 1: Test all 4 modes**

- Politique: filters, pills, detail panel
- Surveillance: slider, stats table, detail panel
- Securite: category pills, slider, stats, detail panel
- Prospection: QPV filter, budget slider, prospect list, detail panel

**Step 2: Test detail panel shows all sections**

Click on Paris (75056), Lyon (69123), Marseille (13055) — should show all sections.
Click on a small commune — some sections should be hidden.

**Step 3: Test mode switching**

Switch between all 4 modes rapidly. Verify:
- No state leak (activeFilter, secuFilter reset on switch)
- Colors change correctly
- Sidebar updates
- Bottom bar updates

**Step 4: Test search**

Search for a commune, click it, verify detail panel shows all enriched data.

**Step 5: Performance check**

Verify page load time is acceptable (<5s on decent connection). Check that mode switching is instant.

**Step 6: Final commit**

```bash
git add -A
git commit -m "fix: QA polish for data enrichment integration"
```

---

## Summary

| Task | Description | Est. complexity |
|------|-------------|----------------|
| 1 | process_delinquance.py | Medium |
| 2 | process_enrichment.py | Medium |
| 3 | Frontend data loading + securite stub | Small |
| 4 | Enriched detail panel | Large |
| 5 | getStyleSecurite + colors | Small |
| 6 | Securite sidebar + filters + stats | Large |
| 7 | Prospection QPV filter + budget signal | Medium |
| 8 | Methodology update | Small |
| 9 | QA and polish | Medium |

**Total: 9 tasks, ~6 commits**

## Data source URLs reference

| Data | Resource ID | URL |
|------|------------|-----|
| Delinquance (parquet) | 98fd2271-4d76-4015-a80c-bcec329f6ad0 | `https://static.data.gouv.fr/.../donnee-comm-data.gouv-parquet-2024-geographie2025-produit-le2025-06-04.parquet` |
| QPV CSV list | 4c6bb7f3-97b6-4834-8a3a-f5f8b3e6735b | `https://static.data.gouv.fr/.../listeqp2024-cog2024.csv` |
| Comptes communes 2022 JSON | a74678f9-4f89-4beb-9024-bc4b2329248b | `https://data.economie.gouv.fr/.../exports/json` |
| Revenus 2013 XLSX | d3ce0107-416f-42cf-a335-d71f89b00b21 | `https://static.data.gouv.fr/.../Niveau_de_vie_2013_a_la_commune-Global_Map_Solution.xlsx` |
| PM 2024 ODS | 081e94fe-b257-4ae7-bc31-bf1f2eb6c968 | `https://static.data.gouv.fr/.../enquete-stats-pm-2024.ods` |
