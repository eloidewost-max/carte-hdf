# Surveillance Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add video surveillance and municipal police data as a fused visual layer on the existing political commune map, with a legend showing data freshness.

**Architecture:** A Python script downloads two data.gouv.fr datasets (police municipale effectifs 2024 ODS + villes sous vidéosurveillance 2012 CSV), matches them to INSEE codes via commune name normalization against `maires.json`, and produces `surveillance.json`. The existing `index.html` is updated to load this data and encode it via border thickness (police effectifs) and border color (vidéoprotection), with an enriched info panel and a new legend section.

**Tech Stack:** Python 3 (pandas, odfpy for ODS parsing), Leaflet.js (existing), vanilla JS

---

### Task 1: Create `process_surveillance.py` — download and parse datasets

**Files:**
- Create: `process_surveillance.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
Download and process surveillance datasets from data.gouv.fr.
Produces surveillance.json indexed by INSEE code.
"""
import csv
import json
import io
import sys
import unicodedata
import urllib.request
import tempfile
import os

# URLs
POLICE_MUN_URL = "https://www.data.gouv.fr/api/1/datasets/r/081e94fe-b257-4ae7-bc31-bf1f2eb6c968"
VIDEOSURV_URL = "https://www.data.gouv.fr/api/1/datasets/r/b56c1eda-6b75-468a-b33f-147d37224c9e"


def normalize(name):
    """Normalize commune name for fuzzy matching."""
    # Remove accents
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Uppercase, strip parenthetical notes, normalize separators
    name = name.upper().strip()
    # Remove parenthetical suffixes like "(Fait partie de...)"
    if "(" in name:
        name = name[:name.index("(")].strip()
    # Normalize hyphens and spaces
    name = name.replace("-", " ").replace("'", " ").replace("  ", " ")
    # Remove SAINT/SAINTE abbreviation differences
    name = name.replace("ST ", "SAINT ").replace("STE ", "SAINTE ")
    return name.strip()


def build_insee_lookup(maires_path):
    """Build (dept_num, normalized_name) → INSEE code lookup from maires.json."""
    with open(maires_path, encoding="utf-8") as f:
        maires = json.load(f)

    lookup = {}
    for code, info in maires.items():
        name = info["n"]
        # Extract dept from INSEE code: 2-digit, or 3-digit for DOM (97x) and Corse (2A/2B)
        if code.startswith("97"):
            dept = code[:3]
        elif code.startswith("2A") or code.startswith("2B"):
            dept = code[:2]
        else:
            dept = code[:2]

        # Try to get numeric dept
        dept_num = dept.lstrip("0") if dept.isdigit() else dept

        lookup[(dept_num, normalize(name))] = code
    return lookup


def parse_police_municipale(ods_path, lookup):
    """Parse police municipale ODS file. Returns dict {insee: {pm, asvp}}."""
    import pandas as pd

    df = pd.read_excel(ods_path, engine="odf", header=None)
    result = {}
    matched = 0
    unmatched = []

    for i in range(10, len(df)):
        row = df.iloc[i]
        dept_raw = row.iloc[0]
        name_raw = row.iloc[3]

        # Skip department header rows and total rows
        if not isinstance(dept_raw, (int, float)):
            continue
        if pandas_isna(name_raw):
            continue

        dept = str(int(dept_raw))
        name = str(name_raw).strip()
        pm = safe_int(row.iloc[6])
        asvp = safe_int(row.iloc[7])

        key = (dept, normalize(name))
        insee = lookup.get(key)

        if insee:
            result[insee] = {"pm": pm, "asvp": asvp}
            matched += 1
        else:
            unmatched.append(f"  {dept} / {name}")

    print(f"Police municipale: {matched} matched, {len(unmatched)} unmatched", file=sys.stderr)
    if unmatched[:10]:
        print("First unmatched:", file=sys.stderr)
        for u in unmatched[:10]:
            print(u, file=sys.stderr)

    return result


def parse_videosurveillance(csv_text, lookup):
    """Parse vidéosurveillance CSV. Returns set of INSEE codes."""
    reader = csv.DictReader(io.StringIO(csv_text))
    result = set()
    matched = 0
    unmatched = 0

    for row in reader:
        dept = row["Numero departement"].strip()
        name = row["Ville"].strip()

        key = (dept, normalize(name))
        insee = lookup.get(key)
        if insee:
            result.add(insee)
            matched += 1
        else:
            unmatched += 1

    print(f"Vidéosurveillance: {matched} matched, {unmatched} unmatched", file=sys.stderr)
    return result


def safe_int(val):
    try:
        import math
        if isinstance(val, float) and math.isnan(val):
            return 0
        return int(val)
    except (ValueError, TypeError):
        return 0


def pandas_isna(val):
    try:
        import math
        if isinstance(val, float) and math.isnan(val):
            return True
    except (TypeError, ValueError):
        pass
    return val is None or (isinstance(val, str) and val.strip() == "")


def main():
    maires_path = os.path.join(os.path.dirname(__file__), "maires.json")
    output_path = os.path.join(os.path.dirname(__file__), "surveillance.json")

    # 1. Build INSEE lookup
    print("Building INSEE lookup from maires.json...", file=sys.stderr)
    lookup = build_insee_lookup(maires_path)
    print(f"  {len(lookup)} communes indexed", file=sys.stderr)

    # 2. Download and parse police municipale
    print("Downloading police municipale 2024 ODS...", file=sys.stderr)
    tmp = tempfile.NamedTemporaryFile(suffix=".ods", delete=False)
    urllib.request.urlretrieve(POLICE_MUN_URL, tmp.name)
    police_data = parse_police_municipale(tmp.name, lookup)
    os.unlink(tmp.name)

    # 3. Download and parse vidéosurveillance
    print("Downloading vidéosurveillance CSV...", file=sys.stderr)
    with urllib.request.urlopen(VIDEOSURV_URL) as resp:
        csv_text = resp.read().decode("utf-8")
    vs_codes = parse_videosurveillance(csv_text, lookup)

    # 4. Merge into single JSON
    result = {}
    all_codes = set(police_data.keys()) | vs_codes

    for code in all_codes:
        entry = {}
        if code in police_data:
            entry["pm"] = police_data[code]["pm"]
            entry["asvp"] = police_data[code]["asvp"]
        if code in vs_codes:
            entry["vs"] = 1
        result[code] = entry

    # 5. Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nOutput: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"  {len(police_data)} communes with police municipale data", file=sys.stderr)
    print(f"  {len(vs_codes)} communes with vidéosurveillance", file=sys.stderr)
    print(f"  {len(result)} communes total in output", file=sys.stderr)


if __name__ == "__main__":
    main()
```

**Step 2: Run the script**

Run: `/tmp/datagouv-venv/bin/python3 process_surveillance.py`
Expected: `surveillance.json` created with ~4500 communes (police mun) + ~1900 (vidéosurveillance) entries. Some unmatched names are expected due to spelling differences.

**Step 3: Verify output**

Run: `python3 -c "import json; d=json.load(open('surveillance.json')); print(len(d), 'communes'); print(list(d.items())[:5])"`
Expected: valid JSON dict with `pm`, `asvp`, and/or `vs` fields.

**Step 4: Commit**

```bash
git add process_surveillance.py surveillance.json
git commit -m "feat: add surveillance data processing script and generated JSON"
```

---

### Task 2: Update `index.html` — load surveillance data and encode visually

**Files:**
- Modify: `index.html`

**Step 1: Add surveillance.json fetch after maires.json fetch (line ~123)**

After `var maires = await mairesResp.json();` add:

```javascript
status.textContent = 'Telechargement des donnees surveillance...';
var survResp = await fetch('surveillance.json');
var surv = await survResp.json();
```

**Step 2: Update `getStyle()` to use surveillance data (line ~206)**

Replace the style function to compute border width from `pm + asvp` and border color from `vs`:

```javascript
function getStyle(feature) {
    var code = feature.properties.codgeo;
    var m = maires[code];
    if (!m) return { fillColor: '#444', fillOpacity: 0.15, weight: 0.2, color: '#222', opacity: 0.5 };

    var isNC = m.f === 'Non classé';
    var isFiltered = activeFilter && m.f !== activeFilter;

    if (isFiltered) {
      return { fillColor: '#333', fillOpacity: 0.15, weight: 0.2, color: '#111', opacity: 0.3 };
    }

    // Surveillance encoding
    var s = surv[code];
    var borderWeight = 0.3;
    var borderColor = '#111';
    var borderOpacity = 0.4;

    if (s) {
      var effectif = (s.pm || 0) + (s.asvp || 0);
      // Scale: 0→0.5, 1-5→1, 6-20→1.5, 21-50→2, 51-200→3, 200+→4
      if (effectif > 200) borderWeight = 4;
      else if (effectif > 50) borderWeight = 3;
      else if (effectif > 20) borderWeight = 2;
      else if (effectif > 5) borderWeight = 1.5;
      else if (effectif > 0) borderWeight = 1;
      else borderWeight = 0.5;

      borderColor = s.vs ? '#ffffff' : '#888';
      borderOpacity = s.vs ? 0.9 : 0.6;
    }

    return {
      fillColor: m.cl,
      fillOpacity: isNC ? 0.3 : 0.8,
      weight: borderWeight,
      color: borderColor,
      opacity: borderOpacity
    };
}
```

**Step 3: Update info panel to show surveillance data (line ~229)**

Add surveillance rows to the HTML info panel and update `showInfo()`:

In the HTML `#info` div, add after the famille row:
```html
<div class="detail" id="info-surv-row" style="display:none; margin-top:6px; padding-top:6px; border-top:1px solid #eee;">
  <div><strong>Police mun. :</strong> <span id="info-pm"></span></div>
  <div><strong>ASVP :</strong> <span id="info-asvp"></span></div>
  <div><strong>Vidéoprot. :</strong> <span id="info-vs"></span></div>
</div>
```

In `showInfo()`, add after `infoPanel.style.display = 'block';`:
```javascript
var s = surv[code];
var survRow = document.getElementById('info-surv-row');
if (s) {
  survRow.style.display = 'block';
  document.getElementById('info-pm').textContent = (s.pm || 0) + ' agents';
  document.getElementById('info-asvp').textContent = (s.asvp || 0) + ' agents';
  document.getElementById('info-vs').textContent = s.vs ? 'Oui (2012)' : 'Non répertoriée';
} else {
  survRow.style.display = 'none';
}
```

**Step 4: Add surveillance legend section**

In the HTML `#legend` div, after `<div id="legend-items"></div>`, add:

```html
<div id="legend-surv" style="margin-top:12px; padding-top:10px; border-top:1px solid #ddd;">
  <h3 style="font-size:13px; margin-bottom:8px;">Surveillance</h3>

  <div style="display:flex; align-items:center; margin:6px 0;">
    <svg width="80" height="16" style="margin-right:8px;">
      <line x1="2" y1="8" x2="18" y2="8" stroke="#888" stroke-width="0.5"/>
      <line x1="22" y1="8" x2="38" y2="8" stroke="#888" stroke-width="1.5"/>
      <line x1="42" y1="8" x2="58" y2="8" stroke="#888" stroke-width="3"/>
      <line x1="62" y1="8" x2="78" y2="8" stroke="#888" stroke-width="4"/>
    </svg>
    <span class="legend-label">Effectif police mun.</span>
  </div>

  <div style="display:flex; align-items:center; margin:6px 0;">
    <div style="width:16px; height:16px; border:3px solid white; border-radius:3px; background:#666; margin-right:8px; box-shadow:0 0 2px rgba(0,0,0,0.5);"></div>
    <span class="legend-label">Videoprotection</span>
  </div>

  <div style="margin-top:8px; font-size:10px; color:#999; line-height:1.4;">
    Police mun. : donnees 2024<br>
    Videoprotection : donnees 2012
  </div>
</div>
```

**Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add surveillance data layer with legend and data freshness"
```

---

### Task 3: Improve matching and verify end-to-end

**Files:**
- Modify: `process_surveillance.py` (if needed)

**Step 1: Run the full pipeline and check match rates**

Run: `/tmp/datagouv-venv/bin/python3 process_surveillance.py`
Expected: >80% match rate for both datasets.

**Step 2: Open the map in browser and verify**

Run: `python3 -m http.server 8000 -d /home/hadrien/carte-politique &`
Check: communes with police municipale have visible thicker borders; communes with vidéoprotection have white borders; hover shows surveillance info; legend displays correctly with freshness dates.

**Step 3: Final commit if adjustments needed**

```bash
git add -A
git commit -m "fix: improve commune name matching for surveillance data"
```
