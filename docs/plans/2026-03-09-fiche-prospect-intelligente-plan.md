# Fiche Prospect Intelligente — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add peer-group comparisons, auto-generated sales narratives, and deep linking to the detail panel so sales reps can prepare meetings with data-driven arguments.

**Architecture:** New Python script `process_insights.py` pre-computes peer groups and benchmarks for each commune. Frontend loads `insights.json` alongside existing data, renders a new "Argumentaire" section in `openDetail()`, and encodes mode+commune in the URL via `pushState`.

**Tech Stack:** Python 3 (numpy-free, pure stdlib + json/math), vanilla JS in index.html

---

### Task 1: Create `process_insights.py` — peer group computation

**Files:**
- Create: `process_insights.py`

**Step 1: Write the script skeleton with data loading**

```python
#!/usr/bin/env python3
"""
Compute peer groups, benchmarks, and narrative flags for each commune.
Produces insights.json indexed by INSEE code.

Inputs: maires.json, surveillance.json, prospection.json, delinquance.json, enrichment.json
Output: insights.json
"""
import json
import math
import os
import sys


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    base = os.path.dirname(__file__) or "."
    print("Loading data files...", file=sys.stderr)
    maires = load_json(os.path.join(base, "maires.json"))
    surv = load_json(os.path.join(base, "surveillance.json"))
    prosp = load_json(os.path.join(base, "prospection.json"))
    delinq = load_json(os.path.join(base, "delinquance.json"))
    enrich = load_json(os.path.join(base, "enrichment.json"))

    # Build unified commune index
    all_codes = set(maires) | set(surv) | set(prosp) | set(delinq) | set(enrich)
    print(f"  {len(all_codes)} total commune codes", file=sys.stderr)

    # Step 1: Build feature vectors for peer matching
    vectors = {}  # code -> {log_pop, rev_med_z, tx_pauv_z, famille}
    pops = {}
    for code in all_codes:
        pop = 0
        if code in prosp and prosp[code].get("pop"):
            pop = prosp[code]["pop"]
        elif code in surv and surv[code].get("pop"):
            pop = surv[code]["pop"]
        elif code in delinq and delinq[code].get("pop"):
            pop = delinq[code]["pop"]
        if pop <= 0:
            continue
        pops[code] = pop

        en = enrich.get(code, {})
        rev = en.get("rev_med")
        pauv = en.get("tx_pauv")
        fam = maires[code]["f"] if code in maires and "f" in maires[code] else None

        # Need at least population + one socio indicator
        if rev is None and pauv is None:
            continue

        vectors[code] = {
            "log_pop": math.log(pop),
            "rev_med": rev,
            "tx_pauv": pauv,
            "famille": fam,
        }

    print(f"  {len(vectors)} communes with feature vectors", file=sys.stderr)

    # Compute z-scores for normalization
    rev_vals = [v["rev_med"] for v in vectors.values() if v["rev_med"] is not None]
    pauv_vals = [v["tx_pauv"] for v in vectors.values() if v["tx_pauv"] is not None]
    logpop_vals = [v["log_pop"] for v in vectors.values()]

    def mean_std(vals):
        n = len(vals)
        if n == 0:
            return 0, 1
        m = sum(vals) / n
        variance = sum((x - m) ** 2 for x in vals) / n
        return m, max(math.sqrt(variance), 0.001)

    lp_mean, lp_std = mean_std(logpop_vals)
    rev_mean, rev_std = mean_std(rev_vals)
    pauv_mean, pauv_std = mean_std(pauv_vals)

    # Normalize vectors
    for v in vectors.values():
        v["lp_z"] = (v["log_pop"] - lp_mean) / lp_std
        v["rev_z"] = (v["rev_med"] - rev_mean) / rev_std if v["rev_med"] is not None else 0.0
        v["pauv_z"] = (v["tx_pauv"] - pauv_mean) / pauv_std if v["tx_pauv"] is not None else 0.0

    # Step 2: Find 20 nearest peers for each commune
    WEIGHTS = {"lp_z": 0.4, "rev_z": 0.25, "pauv_z": 0.25}
    FAMILY_BONUS = -0.3  # negative = closer if same family
    N_PEERS = 20

    def distance(a, b):
        d = 0.0
        for dim, w in WEIGHTS.items():
            d += w * (a[dim] - b[dim]) ** 2
        # Family bonus
        if a["famille"] and b["famille"] and a["famille"] == b["famille"]:
            d += FAMILY_BONUS
        return max(d, 0.0)

    codes_list = list(vectors.keys())
    print(f"  Computing peer groups for {len(codes_list)} communes...", file=sys.stderr)

    peers = {}  # code -> [list of peer codes]
    for i, code in enumerate(codes_list):
        if (i + 1) % 5000 == 0:
            print(f"    {i + 1}/{len(codes_list)}...", file=sys.stderr)
        va = vectors[code]
        dists = []
        for other in codes_list:
            if other == code:
                continue
            d = distance(va, vectors[other])
            dists.append((d, other))
        dists.sort(key=lambda x: x[0])
        peers[code] = [c for _, c in dists[:N_PEERS]]

    # Step 3: Compute benchmarks and flags
    print("  Computing benchmarks and flags...", file=sys.stderr)
    result = {}

    for code in codes_list:
        peer_codes = peers[code]
        if not peer_codes:
            continue

        rec = {}
        # Top 5 peer names
        top5 = peer_codes[:5]
        rec["peers"] = top5
        rec["peer_names"] = []
        for pc in top5:
            name = ""
            if pc in maires:
                name = maires[pc].get("n", pc)
            elif pc in prosp:
                name = pc
            rec["peer_names"].append(name or pc)

        # --- Benchmarks ---
        bench = {}

        # Crime ratio
        my_crime = delinq.get(code, {}).get("r")
        peer_crimes = sorted([delinq[pc]["r"] for pc in peer_codes if pc in delinq and "r" in delinq[pc]])
        if my_crime is not None and len(peer_crimes) >= 3:
            med = peer_crimes[len(peer_crimes) // 2]
            pct = sum(1 for v in peer_crimes if v < my_crime) / len(peer_crimes) * 100
            bench["crime_r"] = {"val": round(my_crime, 1), "med": round(med, 1), "pct": round(pct)}

        # PM ratio
        my_surv = surv.get(code, {})
        my_pop = pops.get(code, 0)
        my_pm_r = None
        if my_pop > 0 and code in surv:
            my_pm_r = ((my_surv.get("pm", 0) + my_surv.get("asvp", 0)) / my_pop) * 10000
        peer_pm_r = []
        for pc in peer_codes:
            ps = surv.get(pc, {})
            pp = pops.get(pc, 0)
            if pp > 0 and pc in surv:
                peer_pm_r.append(((ps.get("pm", 0) + ps.get("asvp", 0)) / pp) * 10000)
        peer_pm_r.sort()
        if my_pm_r is not None and len(peer_pm_r) >= 3:
            med = peer_pm_r[len(peer_pm_r) // 2]
            pct = sum(1 for v in peer_pm_r if v < my_pm_r) / len(peer_pm_r) * 100
            bench["pm_r"] = {"val": round(my_pm_r, 1), "med": round(med, 1), "pct": round(pct)}

        # Accidents ratio
        my_acc = prosp.get(code, {}).get("accidents")
        if my_acc is not None and my_pop > 0:
            my_acc_r = my_acc / my_pop * 10000
            peer_acc_r = []
            for pc in peer_codes:
                pa = prosp.get(pc, {}).get("accidents")
                pp = pops.get(pc, 0)
                if pa is not None and pp > 0:
                    peer_acc_r.append(pa / pp * 10000)
            peer_acc_r.sort()
            if len(peer_acc_r) >= 3:
                med = peer_acc_r[len(peer_acc_r) // 2]
                pct = sum(1 for v in peer_acc_r if v < my_acc_r) / len(peer_acc_r) * 100
                bench["accidents_r"] = {"val": round(my_acc_r, 1), "med": round(med, 1), "pct": round(pct)}

        # Income
        my_rev = enrich.get(code, {}).get("rev_med")
        peer_revs = sorted([enrich[pc]["rev_med"] for pc in peer_codes if pc in enrich and "rev_med" in enrich[pc]])
        if my_rev is not None and len(peer_revs) >= 3:
            med = peer_revs[len(peer_revs) // 2]
            pct = sum(1 for v in peer_revs if v < my_rev) / len(peer_revs) * 100
            bench["rev_med"] = {"val": round(my_rev), "med": round(med), "pct": round(pct)}

        # Poverty
        my_pauv = enrich.get(code, {}).get("tx_pauv")
        peer_pauvs = sorted([enrich[pc]["tx_pauv"] for pc in peer_codes if pc in enrich and "tx_pauv" in enrich[pc]])
        if my_pauv is not None and len(peer_pauvs) >= 3:
            med = peer_pauvs[len(peer_pauvs) // 2]
            pct = sum(1 for v in peer_pauvs if v < my_pauv) / len(peer_pauvs) * 100
            bench["tx_pauv"] = {"val": round(my_pauv, 1), "med": round(med, 1), "pct": round(pct)}

        rec["bench"] = bench

        # --- Narrative flags ---
        flags = {}

        # Crime above 75th percentile of peers
        if "crime_r" in bench:
            flags["crime_above_peers"] = bench["crime_r"]["pct"] > 75

        # No PM but peers have PM
        has_pm = code in surv and (surv[code].get("pm", 0) + surv[code].get("asvp", 0)) > 0
        peers_with_pm = sum(1 for pc in peer_codes if pc in surv and (surv[pc].get("pm", 0) + surv[pc].get("asvp", 0)) > 0)
        peers_pm_pct = round(peers_with_pm / len(peer_codes) * 100) if peer_codes else 0
        flags["no_pm_peers_have"] = (not has_pm) and peers_pm_pct > 50
        flags["peers_pm_pct"] = peers_pm_pct

        # No VV but peers have VV
        has_vv = prosp.get(code, {}).get("videoverb", False)
        peers_with_vv = sum(1 for pc in peer_codes if prosp.get(pc, {}).get("videoverb", False))
        peers_vv_pct = round(peers_with_vv / len(peer_codes) * 100) if peer_codes else 0
        flags["no_vv_peers_have"] = (not has_vv) and peers_vv_pct > 30
        flags["peers_vv_pct"] = peers_vv_pct

        # PM growing
        pm_trend = prosp.get(code, {}).get("pm_trend", [])
        flags["pm_growing"] = len(pm_trend) >= 2 and pm_trend[-1] > pm_trend[0]

        # High accident rate (above median of peers)
        if "accidents_r" in bench:
            flags["high_accident_rate"] = bench["accidents_r"]["pct"] > 50

        # Budget capacity (DGF above median of peers)
        my_dgf = enrich.get(code, {}).get("dgf_hab")
        peer_dgfs = sorted([enrich[pc]["dgf_hab"] for pc in peer_codes if pc in enrich and "dgf_hab" in enrich[pc]])
        if my_dgf is not None and len(peer_dgfs) >= 3:
            dgf_med = peer_dgfs[len(peer_dgfs) // 2]
            flags["budget_capacity"] = my_dgf > dgf_med

        # High poverty
        if "tx_pauv" in bench:
            flags["high_poverty"] = bench["tx_pauv"]["pct"] > 60

        # Stat payant peers
        peers_with_sp = sum(1 for pc in peer_codes if prosp.get(pc, {}).get("stat_payant", False))
        flags["peers_stat_payant_pct"] = round(peers_with_sp / len(peer_codes) * 100) if peer_codes else 0

        rec["flags"] = flags
        result[code] = rec

    # Write output
    output_path = os.path.join(base, "insights.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nOutput: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"  {len(result)} communes with insights", file=sys.stderr)

    # Sample
    if "11069" in result:
        print(f"\n  Sample (Carcassonne 11069):", file=sys.stderr)
        print(json.dumps(result["11069"], indent=2, ensure_ascii=False), file=sys.stderr)
    elif "75056" in result:
        print(f"\n  Sample (Paris 75056):", file=sys.stderr)
        print(json.dumps(result["75056"], indent=2, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
```

**Step 2: Run the script and verify output**

Run: `python3 process_insights.py`
Expected: Creates `insights.json`, prints stats to stderr, sample for Carcassonne or Paris.

**Step 3: Verify output structure**

Run: `python3 -c "import json; d=json.load(open('insights.json')); print(len(d), 'communes'); print(json.dumps(d.get('11069', d.get('75056', {})), indent=2))"`
Expected: ~15-25k communes with insights, sample showing peers/bench/flags structure.

**Step 4: Commit**

```bash
git add process_insights.py insights.json
git commit -m "feat: add process_insights.py — peer groups, benchmarks, and narrative flags"
```

---

### Task 2: Load `insights.json` in the frontend

**Files:**
- Modify: `index.html:251-270` (data loading section)

**Step 1: Add insights.json to the parallel fetch**

In `index.html`, in the `Promise.all` block (~line 251), add `insights.json` as the 7th fetch. Then assign the result to a `var insights` variable.

Before (line 251-270):
```javascript
    results = await Promise.all([
      fetchJSON('maires.json'),
      fetchJSON('surveillance.json'),
      fetchJSON('prospection.json'),
      fetchJSON('communes-topo.json'),
      fetchJSON('delinquance.json'),
      fetchJSON('enrichment.json')
    ]);
  } catch (err) {
    document.getElementById('load-text').textContent = 'Erreur de chargement';
    status.textContent = err.message;
    status.style.color = '#e74c3c';
    return;
  }
  var maires = results[0];
  var surv = results[1];
  var prosp = results[2];
  var topoData = results[3];
  var delinq = results[4];
  var enrich = results[5];
```

After:
```javascript
    results = await Promise.all([
      fetchJSON('maires.json'),
      fetchJSON('surveillance.json'),
      fetchJSON('prospection.json'),
      fetchJSON('communes-topo.json'),
      fetchJSON('delinquance.json'),
      fetchJSON('enrichment.json'),
      fetchJSON('insights.json')
    ]);
  } catch (err) {
    document.getElementById('load-text').textContent = 'Erreur de chargement';
    status.textContent = err.message;
    status.style.color = '#e74c3c';
    return;
  }
  var maires = results[0];
  var surv = results[1];
  var prosp = results[2];
  var topoData = results[3];
  var delinq = results[4];
  var enrich = results[5];
  var insights = results[6];
```

**Step 2: Verify the page still loads**

Open `index.html` in a browser. All 4 modes should still work. Check DevTools Network tab: `insights.json` should appear as a loaded resource.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: load insights.json in frontend data pipeline"
```

---

### Task 3: Add CSS styles for the argumentaire section

**Files:**
- Modify: `index.html` (CSS section, after existing `.detail-*` styles)

**Step 1: Find existing detail panel CSS**

Search for `.detail-missing` in the CSS section — add new styles after it.

**Step 2: Add argumentaire CSS**

Add these CSS rules after the `.detail-missing` styles:

```css
/* --- Argumentaire section --- */
.argumentaire-narrative { font-size: 12px; line-height: 1.6; color: #b0b3ba; margin-bottom: 12px; padding: 10px; background: rgba(78,205,196,0.06); border-radius: 6px; border-left: 3px solid #4ecdc4; }
.argumentaire-narrative strong { color: #e2e4e9; }
.bench-table { width: 100%; font-size: 11px; border-collapse: collapse; margin: 8px 0; }
.bench-table th { text-align: left; color: #555; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.bench-table td { padding: 4px 6px; color: #b0b3ba; }
.bench-table .bench-val { color: #e2e4e9; font-weight: 600; }
.bench-bar-bg { height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; flex: 1; overflow: hidden; }
.bench-bar-fill { height: 100%; border-radius: 2px; }
.bench-bar-green { background: #27ae60; }
.bench-bar-orange { background: #f39c12; }
.bench-bar-red { background: #e74c3c; }
.bench-pct { min-width: 50px; text-align: right; font-size: 10px; font-weight: 600; }
.bench-pct-high { color: #e74c3c; }
.bench-pct-mid { color: #f39c12; }
.bench-pct-low { color: #27ae60; }
.peer-links { font-size: 11px; color: #8b8f98; margin-top: 8px; }
.peer-link { color: #4ecdc4; cursor: pointer; text-decoration: none; }
.peer-link:hover { text-decoration: underline; }
```

**Step 3: Commit**

```bash
git add index.html
git commit -m "style: add CSS for argumentaire section in detail panel"
```

---

### Task 4: Build the argumentaire narrative generator

**Files:**
- Modify: `index.html` (JS section, before `openDetail` function ~line 694)

**Step 1: Add the narrative builder function**

Insert this function before `openDetail()`. The function builds the narrative using safe DOM methods (textContent and createElement) — no innerHTML. It returns a DocumentFragment.

```javascript
  // --- Argumentaire narrative builder ---
  function buildNarrative(code) {
    var ins = insights[code];
    if (!ins || !ins.flags) return null;
    var f = ins.flags;
    var b = ins.bench || {};
    var m = maires[code];
    var p = prosp[code];
    var pop = p ? p.pop : (surv[code] ? surv[code].pop : 0);
    var name = m ? m.n : code;

    var phrases = [];
    // Crime
    if (f.crime_above_peers && b.crime_r) {
      phrases.push({
        bold: null,
        text: 'La delinquance enregistree est superieure a ' + b.crime_r.pct + '% des communes comparables (' + b.crime_r.val + ' vs ' + b.crime_r.med + ' /10k).'
      });
    }
    // No PM but peers have
    if (f.no_pm_peers_have) {
      phrases.push({
        bold: null,
        text: f.peers_pm_pct + '% des communes similaires disposent d\'une police municipale, mais pas ' + name + '.'
      });
    }
    // No VV but peers have
    if (f.no_vv_peers_have) {
      phrases.push({
        bold: null,
        text: f.peers_vv_pct + '% des communes comparables sont deja equipees en videoverbalisation.'
      });
    }
    // PM growing
    if (f.pm_growing) {
      phrases.push({
        bold: null,
        text: 'Les effectifs de police municipale sont en croissance, signe d\'une dynamique d\'investissement en securite.'
      });
    }
    // High accidents
    if (f.high_accident_rate && b.accidents_r) {
      phrases.push({
        bold: null,
        text: 'Le taux d\'accidents corporels (' + b.accidents_r.val.toFixed(1) + ' /10k) est au-dessus de la mediane des pairs (' + b.accidents_r.med.toFixed(1) + ').'
      });
    }
    // Budget capacity
    if (f.budget_capacity) {
      var dgf = (enrich[code] || {}).dgf_hab;
      if (dgf !== undefined) {
        phrases.push({
          bold: null,
          text: 'La capacite budgetaire (DGF ' + dgf.toFixed(0) + ' \u20ac/hab) permet d\'envisager un investissement.'
        });
      }
    }
    // High poverty (counterpoint)
    if (f.high_poverty && b.tx_pauv) {
      phrases.push({
        bold: null,
        text: 'Attention : taux de pauvrete eleve (' + b.tx_pauv.val + '%), a prendre en compte dans l\'approche commerciale.'
      });
    }

    if (phrases.length === 0) return null;

    // Build DOM fragment
    var frag = document.createDocumentFragment();
    // Opening bold: commune name + pop
    var opener = document.createElement('strong');
    opener.textContent = name + ' (' + (pop ? pop.toLocaleString('fr') : '?') + ' hab.) \u2014 ';
    frag.appendChild(opener);
    phrases.forEach(function(ph, i) {
      if (i > 0) frag.appendChild(document.createTextNode(' '));
      frag.appendChild(document.createTextNode(ph.text));
    });
    return frag;
  }
```

**Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add buildNarrative() — auto-generated sales argumentaire via safe DOM"
```

---

### Task 5: Render argumentaire section in the detail panel

**Files:**
- Modify: `index.html:828-829` (inside `openDetail()`, after score section, before surveillance section)

**Step 1: Insert argumentaire rendering after the score section**

After the line `content.appendChild(scoreSec);` (approx line 828) and the closing `}` of the `if (p)` block, but before the `// Surveillance section` comment, insert:

```javascript
    // --- Argumentaire section ---
    var ins = insights[code];
    if (ins) {
      var argSec = document.createElement('div');
      argSec.className = 'detail-section';

      var argTitle = document.createElement('div');
      argTitle.className = 'cmd-section-title';
      argTitle.textContent = 'ARGUMENTAIRE';
      argSec.appendChild(argTitle);

      // Narrative
      var narrative = buildNarrative(code);
      if (narrative) {
        var narDiv = document.createElement('div');
        narDiv.className = 'argumentaire-narrative';
        narDiv.appendChild(narrative);
        argSec.appendChild(narDiv);
      }

      // Benchmark table
      var bench = ins.bench;
      if (bench && Object.keys(bench).length > 0) {
        var table = document.createElement('table');
        table.className = 'bench-table';

        var thead = document.createElement('thead');
        var headRow = document.createElement('tr');
        ['Indicateur', 'Commune', 'Pairs (med.)', 'Rang'].forEach(function(h) {
          var th = document.createElement('th');
          th.textContent = h;
          headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        var benchLabels = {
          crime_r: 'Criminalite /10k',
          pm_r: 'Police mun. /10k',
          accidents_r: 'Accidents /10k',
          rev_med: 'Revenu median',
          tx_pauv: 'Taux pauvrete'
        };
        var benchOrder = ['crime_r', 'pm_r', 'accidents_r', 'rev_med', 'tx_pauv'];
        benchOrder.forEach(function(key) {
          if (!bench[key]) return;
          var bv = bench[key];
          var tr = document.createElement('tr');

          var tdLabel = document.createElement('td');
          tdLabel.textContent = benchLabels[key] || key;
          tr.appendChild(tdLabel);

          var tdVal = document.createElement('td');
          tdVal.className = 'bench-val';
          tdVal.textContent = (key === 'rev_med') ? bv.val.toLocaleString('fr') + ' \u20ac' :
                              (key === 'tx_pauv') ? bv.val + ' %' : bv.val;
          tr.appendChild(tdVal);

          var tdMed = document.createElement('td');
          tdMed.textContent = (key === 'rev_med') ? bv.med.toLocaleString('fr') + ' \u20ac' :
                              (key === 'tx_pauv') ? bv.med + ' %' : bv.med;
          tr.appendChild(tdMed);

          var tdPct = document.createElement('td');
          tdPct.className = 'bench-pct';
          tdPct.textContent = bv.pct + 'e pct';
          if (key === 'rev_med') {
            // For income, high is good
            tdPct.className += bv.pct > 60 ? ' bench-pct-low' : (bv.pct > 30 ? ' bench-pct-mid' : ' bench-pct-high');
          } else {
            // For crime/accidents/poverty, high is bad
            tdPct.className += bv.pct > 75 ? ' bench-pct-high' : (bv.pct > 50 ? ' bench-pct-mid' : ' bench-pct-low');
          }
          tr.appendChild(tdPct);

          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        argSec.appendChild(table);
      }

      // Peer links
      if (ins.peers && ins.peer_names) {
        var peerDiv = document.createElement('div');
        peerDiv.className = 'peer-links';
        peerDiv.appendChild(document.createTextNode('Communes comparables : '));
        ins.peers.forEach(function(pc, i) {
          if (i > 0) peerDiv.appendChild(document.createTextNode(', '));
          var link = document.createElement('span');
          link.className = 'peer-link';
          link.textContent = ins.peer_names[i] || pc;
          link.addEventListener('click', function() {
            var layer = layerByCode[pc];
            if (layer) {
              map.fitBounds(layer.getBounds());
              openDetail(pc);
            }
          });
          peerDiv.appendChild(link);
        });
        argSec.appendChild(peerDiv);
      }

      content.appendChild(argSec);
    }
```

**Step 2: Verify in browser**

Open `index.html`, click on a commune (e.g., Carcassonne). The detail panel should now show:
1. Header (name, pop, political badge)
2. Score section (if prospection data)
3. **NEW: Argumentaire section** with narrative + benchmark table + peer links
4. Surveillance section
5. Signals section
6. Delinquance section
7. Socio-economic section

**Step 3: Test peer links**

Click on a peer commune name in the argumentaire. It should zoom to that commune and open its detail panel.

**Step 4: Commit**

```bash
git add index.html
git commit -m "feat: render argumentaire section in detail panel with narrative, benchmarks, and peer links"
```

---

### Task 6: Deep linking — encode state in URL

**Files:**
- Modify: `index.html` (JS section — add URL parsing at startup, update on mode switch and detail open)

**Step 1: Add URL state management functions**

After the state variable declarations (~line 310) and before the style functions, add:

```javascript
  // --- URL state management ---
  function updateURL() {
    var params = new URLSearchParams();
    if (currentMode !== 'prospection') params.set('mode', currentMode);
    if (activeFilter) params.set('filter', activeFilter);
    var qs = params.toString();
    var url = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
    history.replaceState(null, '', url);
  }

  function updateURLWithCommune(code) {
    var params = new URLSearchParams(window.location.search);
    if (currentMode !== 'prospection') params.set('mode', currentMode);
    else params.delete('mode');
    if (code) params.set('commune', code);
    else params.delete('commune');
    var qs = params.toString();
    var url = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
    history.pushState(null, '', url);
  }

  function readURLState() {
    var params = new URLSearchParams(window.location.search);
    return {
      mode: params.get('mode') || 'prospection',
      commune: params.get('commune') || null,
      filter: params.get('filter') || null
    };
  }
```

**Step 2: Call updateURL on mode switch**

In the `switchMode()` function, add `updateURL();` at the end (after the mode indicator update).

**Step 3: Call updateURLWithCommune on detail open**

In `openDetail()`, add `updateURLWithCommune(code);` at the very beginning of the function (after `var panel = ...`).

**Step 4: Clear commune from URL on detail close**

In the detail panel close handler (~line 1154), add:
```javascript
    var params = new URLSearchParams(window.location.search);
    params.delete('commune');
    var qs = params.toString();
    history.replaceState(null, '', window.location.pathname + (qs ? '?' + qs : ''));
```

**Step 5: Restore state from URL on load**

After the loading screen is hidden and the map is built (after `geoLayer.addTo(map)` and search index setup), add:

```javascript
  // Restore state from URL
  var urlState = readURLState();
  if (urlState.mode && urlState.mode !== currentMode) {
    switchMode(urlState.mode);
  }
  if (urlState.filter) {
    activeFilter = urlState.filter;
    geoLayer.setStyle(getStyle);
  }
  if (urlState.commune) {
    var layer = layerByCode[urlState.commune];
    if (layer) {
      map.fitBounds(layer.getBounds());
      openDetail(urlState.commune);
    }
  }
```

**Step 6: Test deep linking**

1. Open `index.html`, click on a commune. URL should update to `?commune=XXXXX`
2. Copy URL, open in new tab. Commune detail should open automatically.
3. Switch mode. URL should update to `?mode=securite` (or similar).
4. Close detail panel. `commune` param should be removed from URL.

**Step 7: Commit**

```bash
git add index.html
git commit -m "feat: deep linking — encode mode, commune, and filter in URL"
```

---

### Task 7: Update CLAUDE.md and METHODOLOGIE.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `METHODOLOGIE.md`

**Step 1: Update CLAUDE.md**

Add `insights.json` to the data files section and document the new `process_insights.py` script.

In the **Data Pipeline** section, add:
```
process_insights.py     -> insights.json      (peer groups, benchmarks, narrative flags, ~2-3 MB)
```

In the **Key Data Files** section, add:
```
- `insights.json` -- keyed by INSEE code, fields: `peers` (top 5 peer codes), `peer_names` (display names), `bench` (benchmarks: crime_r, pm_r, accidents_r, rev_med, tx_pauv with val/med/pct), `flags` (narrative booleans: crime_above_peers, no_pm_peers_have, no_vv_peers_have, pm_growing, high_accident_rate, budget_capacity, high_poverty, plus peers_pm_pct, peers_vv_pct, peers_stat_payant_pct)
```

In the **Core Flow** section, mention that the detail panel now includes an argumentaire section with peer-group narrative, benchmark table, and clickable peer links.

Add a note about deep linking: `?mode=X&commune=XXXXX&filter=Y` URL parameters.

**Step 2: Update METHODOLOGIE.md**

Add a new section documenting the peer group methodology:
- Distance metric (weighted euclidean on log(pop), rev_med z-score, tx_pauv z-score, family bonus)
- Peer group size (20 communes)
- Benchmark computation (percentile among peers)
- Narrative flags and their thresholds

**Step 3: Commit**

```bash
git add CLAUDE.md METHODOLOGIE.md
git commit -m "docs: document insights pipeline, argumentaire, and deep linking"
```

---

## Summary

| Task | Description | Estimated complexity |
|------|-------------|---------------------|
| 1 | `process_insights.py` -- full Python pipeline | Large (main compute) |
| 2 | Load `insights.json` in frontend | Small (2 lines) |
| 3 | CSS for argumentaire section | Small |
| 4 | `buildNarrative()` JS function | Medium |
| 5 | Render argumentaire in detail panel | Medium |
| 6 | Deep linking with `pushState` | Medium |
| 7 | Documentation updates | Small |

**Total: 7 tasks, 7 commits.**
