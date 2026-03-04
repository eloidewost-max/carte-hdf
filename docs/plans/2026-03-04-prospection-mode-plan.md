# Prospection Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Prospection" mode to the carte politique app with enriched open data (budgets sécurité, police trends, stationnement payant, vidéoverbalisation) and interactive scoring sliders, plus a global UX/UI polish.

**Architecture:** New Python script `process_prospection.py` downloads and merges 4 open data sources into `prospection.json`. Frontend adds a third mode to `index.html` with client-side scoring, weight sliders, and a refreshed UI across all modes.

**Tech Stack:** Python 3 (pandas, openpyxl, odf, urllib), Leaflet.js, vanilla JS/CSS (single-file SPA)

---

### Task 1: Create `process_prospection.py` — Budget sécurité

**Files:**
- Create: `process_prospection.py`

**Step 1: Create script skeleton with budget sécurité download**

Create `process_prospection.py` with:
- `download_file(url, suffix)` — download URL to temp file
- `parse_balances_comptables(csv_path)` — parse DGFiP balances comptables CSV for function 1 (Sécurité) spending
- Use balances comptables 2024 from data.gouv.fr (ZIP containing CSV, delimiter ";")
- M57 nomenclature: FONCTION field starting with "1" = Sécurité
- Sum OBNETDEB (net debit = actual spending) per commune
- Build INSEE code from NDEPT + NCOM columns (zero-pad to 5 chars)
- Reuse `normalize`, `safe_int`, `pandas_isna`, `build_insee_lookup` helpers from `process_surveillance.py`

Balances comptables URL: `https://www.data.gouv.fr/fr/datasets/r/7bfb4924-4654-4e97-a8e3-a62b5a15920f`

**Step 2: Run the script to test budget download and parsing**

```bash
python3 process_prospection.py
```

Expected: Downloads ZIP, extracts CSV, prints count of communes with sécurité spending. May need to adjust column names based on actual CSV headers — add a header debug print if first run fails.

**Step 3: Verify budget data and commit**

```bash
python3 -c "import json; d=json.load(open('prospection.json')); print(len(d), 'communes'); has_b=sum(1 for v in d.values() if 'budget_secu' in v); print(f'  budget: {has_b}')"
git add process_prospection.py
git commit -m "feat: add process_prospection.py with budget sécurité data"
```

---

### Task 2: Add police municipale multi-year trend to `process_prospection.py`

**Files:**
- Modify: `process_prospection.py`

The Min. Intérieur publishes yearly ODS/XLSX files for police municipale effectifs (2012-2024). The existing `process_surveillance.py` already parses one year. We need to download multiple years and compute a trend.

**Step 1: Add multi-year police municipale download**

The dataset page is `https://www.data.gouv.fr/fr/datasets/police-municipale-effectifs-par-commune/`. Each year has a separate resource file. Find the resource IDs for recent years by inspecting the dataset page.

Add a `PM_URLS` dict mapping year to download URL. Start with at least 2 years (e.g., 2020 and 2024) for a growth signal.

**Step 2: Reuse the ODS parser from `process_surveillance.py`**

Copy/adapt `parse_police_municipale` logic: read ODS with pandas, skip header rows (first ~10 rows), extract dept (col 0), name (col 3), pm (col 6), asvp (col 7). Use `build_insee_lookup` from maires.json for matching.

Create `parse_pm_year(ods_path, lookup)` returning `{insee: total_agents}`.

**Step 3: Build trend arrays and merge into result**

For each commune, store `pm_trend` (array of counts) and `pm_trend_years` (array of years).

**Step 4: Run, verify, commit**

```bash
python3 process_prospection.py
git add process_prospection.py
git commit -m "feat: add multi-year police municipale trends to prospection data"
```

---

### Task 3: Add stationnement payant + vidéoverbalisation scraping to `process_prospection.py`

**Files:**
- Modify: `process_prospection.py`

**Step 1: Add GART stationnement payant parsing**

Download GART/Cerema 2019 survey CSV from data.gouv.fr. Parse it to extract commune codes with paid parking. Dataset: `https://www.data.gouv.fr/fr/datasets/enquete-sur-la-reforme-du-stationnement-payant-sur-voirie/`

**Step 2: Scrape video-verbalisation.fr**

Fetch `https://video-verbalisation.fr/villes.php`, parse HTML to extract commune names. Match to INSEE codes using the `build_insee_lookup` + `normalize` approach. Set User-Agent header for the request.

**Step 3: Merge vidéoprotection + population from surveillance.json**

Pull `vs` (vidéoprotection flag, year 2012) and `pop` (population) from existing `surveillance.json` into `prospection.json`.

**Step 4: Add `_year` freshness fields to all data points**

Every field gets a companion `_year` field: `budget_secu_year: 2024`, `stat_payant_year: 2018`, `videoverb_year: 2024`, `vs_year: 2012`, `pop_year: 2021`.

**Step 5: Run full pipeline, verify, commit**

```bash
python3 process_prospection.py
python3 -c "
import json
d = json.load(open('prospection.json'))
print(f'{len(d)} communes')
for key in ['budget_secu', 'pm_trend', 'stat_payant', 'videoverb', 'vs', 'pop']:
    count = sum(1 for v in d.values() if key in v)
    print(f'  {key}: {count}')
"
git add process_prospection.py prospection.json
git commit -m "feat: complete prospection pipeline with stationnement and vidéoverbalisation data"
```

---

### Task 4: UX/UI polish — CSS overhaul

**Files:**
- Modify: `index.html` (CSS section, lines 8-125)

This task modernizes the UI across all modes. All changes are in the `<style>` block.

**Step 1: Update mode toggle to pill-style segmented control**

Replace `#mode-toggle` and `.mode-btn` CSS (lines 73-85):
- Pill shape with `border-radius: 25px`
- Glassmorphism background: `backdrop-filter: blur(12px)`, semi-transparent bg
- Light text on dark background (the toggle sits over the dark map)
- Active state: colored bottom border per mode (blue=politique, orange=surveillance, green=prospection)
- Remove the `.mode-btn:first-child { border-right }` hack (line 84)

**Step 2: Update panels to glassmorphism cards**

For `#legend`, `#info`, `#title-bar`, `#stats-panel`, `#surv-filters`, replace:
- `background: rgba(255,255,255,0.95)` with `rgba(255,255,255,0.92)` + `backdrop-filter: blur(12px)`
- `border-radius: 8px` with `10px`
- `box-shadow: 0 2px 8px` with `0 4px 16px rgba(0,0,0,0.2)`
- Add `border: 1px solid rgba(255,255,255,0.3)`

**Step 3: Improve typography hierarchy**

- Title: 18px, weight 700, letter-spacing -0.3px
- Subtitle: 11px, color #888
- Legend title: 13px, weight 700
- Legend labels: 11px, color #444
- Legend counts: 10px, color #999
- Add `.data-year` class: `font-size: 10px; color: #aaa; font-style: italic; margin-left: 4px;`

**Step 4: Upgrade filter buttons**

- `border-radius: 20px`, `border: 1.5px solid rgba(0,0,0,0.15)`
- Font-size 11px, lighter default state
- Active: `background: #333; color: white; box-shadow`

**Step 5: Add CSS transitions**

```css
#legend, #info, #stats-panel, #filter-bar, #surv-filters {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
```

**Step 6: Add responsive breakpoints**

```css
@media (max-width: 768px) {
  #stats-panel { top: auto; bottom: 0; right: 0; left: 0; width: 100%; max-height: 40vh; border-radius: 10px 10px 0 0; }
  #info { top: auto; bottom: 0; right: 0; left: 0; width: 100%; min-width: unset; border-radius: 10px 10px 0 0; }
  #filter-bar { max-width: 95vw; }
  #surv-filters { flex-direction: column; align-items: flex-start; }
  #mode-toggle { left: 5px; }
  #legend { max-width: 200px; font-size: 11px; }
}
```

**Step 7: Verify visually in browser, commit**

Open `index.html`, check both politique and surveillance modes look correct with new styles.

```bash
git add index.html
git commit -m "style: modernize UI with glassmorphism, pill toggles, and responsive layout"
```

---

### Task 5: Add Prospection mode — data loading + mode switching

**Files:**
- Modify: `index.html` (HTML + JS sections)

**Step 1: Add third mode button in HTML**

Update the `#mode-toggle` div (~line 140) to add a third button:

```html
<button class="mode-btn" data-mode="prospection">Prospection</button>
```

**Step 2: Add prospection-specific info panel fields**

Inside `#info` div, after `#info-surv-row` (~line 204), add a new `#info-prosp-row` div with fields for: Score, Budget sécu, Évolution PM, Stat. payant, Vidéoverb.

**Step 3: Load prospection.json alongside other data**

After loading surveillance.json (~line 238), add:

```javascript
status.textContent = 'Telechargement des donnees prospection...';
var prospResp = await fetch('prospection.json');
var prosp = await prospResp.json();
```

**Step 4: Update `switchMode` function to handle 'prospection'**

- Show/hide `#stats-panel` for both surveillance and prospection modes
- Update subtitle text for prospection: `'Potentiel videoverbalisation par commune'`
- Add `document.body.classList.toggle('prosp-mode', mode === 'prospection')`
- Call `renderProspStats()` when entering prospection mode

**Step 5: Verify mode switching works (no scoring yet), commit**

```bash
git add index.html
git commit -m "feat: add prospection mode skeleton with data loading and mode switch"
```

---

### Task 6: Implement client-side scoring engine + weight sliders

**Files:**
- Modify: `index.html` (JS section)

**Step 1: Define scoring signals and default weights**

Create `PROSP_SIGNALS` array with 7 signals:
- `stat_payant` (weight 25, binary)
- `no_videoverb` (weight 25, binary inverted)
- `pm_count` (weight 15, normalized PM per capita, cap at 50/10k)
- `pm_growth` (weight 10, % change over trend, capped 0-1)
- `budget_secu` (weight 15, normalized per capita, cap at 200 EUR/hab)
- `has_vs` (weight 5, binary)
- `pop_sweet` (weight 5, Gaussian around 5k-100k, center 30k)

Create `prospWeights` object initialized from defaults.

**Step 2: Implement `computeProspScore(code)` function**

Takes an INSEE code, reads from `prosp[code]` and `surv[code]`, computes each signal as 0-1, returns weighted sum * 100 (0-100 score). Returns `null` if no data at all.

**Step 3: Build weight sliders dynamically**

Create `buildProspSliders()` that populates `#stats-panel` when in prospection mode:
- Title "Poids des signaux"
- One row per signal: label + data year in grey + range input (0-100) + current value display
- Each slider's `input` event updates `prospWeights`, calls `geoLayer.setStyle(getStyle)` and `renderProspStats()`

Call `buildProspSliders()` from within `renderProspStats()` (unified right panel).

**Step 4: Verify sliders render and scoring computes, commit**

```bash
git add index.html
git commit -m "feat: implement prospection scoring engine with interactive weight sliders"
```

---

### Task 7: Implement prospection map styling + legend + info panel

**Files:**
- Modify: `index.html` (JS section)

**Step 1: Define prospection color gradient**

Create `PROSP_COLORS` array:
- 0: `#2c3e50` (dark blue-grey, very low)
- 20: `#3498db` (blue, low)
- 40: `#f39c12` (orange, medium)
- 60: `#e67e22` (dark orange, high)
- 80: `#e74c3c` (red, very high)

Create `getProspColor(score)` — same pattern as `getSurvColor`.

**Step 2: Add `getStyleProspection` function**

Style based on `computeProspScore(code)`. Null score = dark grey at low opacity. Otherwise use `getProspColor(score)` at 0.8 opacity.

**Step 3: Update style dispatcher**

Add `if (currentMode === 'prospection') return getStyleProspection(feature);` to `getStyle()`.

**Step 4: Update `renderLegend` for prospection mode**

Add a `mode === 'prospection'` branch: show gradient swatches from PROSP_COLORS with labels like "< 20 (faible)", "80+ (tres fort)". Add note: "Score composite — gris = pas de donnees".

**Step 5: Update `showInfo` for prospection data**

When `currentMode === 'prospection'`, show `#info-prosp-row` with: score, budget sécu (with year), PM trend % (with year range), stationnement payant (with year), vidéoverbalisation (with year). Use DOM methods (createElement/textContent) instead of innerHTML for all content. Add `.data-year` spans for freshness.

**Step 6: Verify map coloring, legend, and info panel in browser, commit**

```bash
git add index.html
git commit -m "feat: add prospection map styling, legend, and info panel with data freshness"
```

---

### Task 8: Add prospection stats + filters into right panel

**Files:**
- Modify: `index.html` (JS section)

**Step 1: Build `renderProspStats` as unified right panel**

This function populates `#stats-panel` with:
1. Title "Prospection"
2. Weight sliders (from `buildProspSliders`)
3. Filter section: checkboxes (stat payant only, sans vidéoverbalisation, avec vidéoprotection) + population range sliders
4. Stats table: per-famille breakdown (count, avg score)
5. Summary line: total scored + count with stationnement sans vidéoverbalisation
6. Sources footnote with all data years

All built with DOM methods (createElement, textContent, appendChild).

**Step 2: Add `passesProspFilters(code)` function**

Checks filter state (checkboxes + pop range) against commune data. Returns boolean.

**Step 3: Wire filters into `getStyleProspection`**

Communes failing filters get dimmed style (grey, low opacity).

**Step 4: Update `switchMode` to call `renderProspStats` and update panel title**

**Step 5: Verify filters and stats in browser, commit**

```bash
git add index.html
git commit -m "feat: add prospection filters and stats in unified right panel"
```

---

### Task 9: Add prospection CSS + final mode integration

**Files:**
- Modify: `index.html` (CSS section)

**Step 1: Add prospection-mode-specific CSS**

```css
.prosp-mode #info { top: auto; bottom: 30px; }
```

**Step 2: Ensure `#stats-panel` works for both surveillance and prospection**

Both modes share the right panel. The content is rebuilt by `renderStats()` or `renderProspStats()` depending on mode. No CSS conflict needed — same panel, different content.

**Step 3: Verify both modes side by side, commit**

```bash
git add index.html
git commit -m "style: add prospection mode CSS and finalize mode integration"
```

---

### Task 10: Final integration testing + polish

**Files:**
- Modify: `index.html` (if fixes needed)

**Step 1: Test all three modes**

Open `index.html` in browser. Verify:
- Politique mode: colors, filters, legend, info panel all work
- Surveillance mode: heatmap, filters, stats sidebar, info panel all work
- Prospection mode: scoring, sliders, filters, stats, info panel all work
- Mode switching is smooth with transitions
- Glassmorphism cards look correct on dark map
- Responsive: check at 768px width

**Step 2: Fix any visual issues found during testing**

Common issues to watch for:
- Panel overlap on small screens
- Slider values not updating map in real time
- Info panel showing wrong fields for wrong mode
- Legend not updating on mode switch

**Step 3: Ensure all data freshness years are displayed**

Verify every data point in the info panel shows its year in grey italic.

**Step 4: Final commit**

```bash
git add index.html
git commit -m "feat: complete prospection mode with scoring, sliders, and polished UI"
```

---

## Task Dependency Summary

```
Task 1 (budget sécurité) → Task 2 (PM trends) → Task 3 (stationnement + vidéoverb + final pipeline)
Task 4 (CSS polish) — independent, can run in parallel with Tasks 1-3
Task 5 (mode switch skeleton) — depends on Task 3 (needs prospection.json) + Task 4 (needs updated CSS)
Tasks 6-9 — sequential, each depends on the previous
Task 10 (final testing) — depends on all previous tasks
```

Parallelizable: Tasks 1-3 (pipeline) and Task 4 (CSS) can be done simultaneously.
