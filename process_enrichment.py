#!/usr/bin/env python3
"""
Download and process enrichment datasets for commune-level financial and social data.
Produces enrichment.json indexed by INSEE code.

Data sources:
- QPV (Quartiers Prioritaires de la Politique de la Ville) 2024 (data.gouv.fr, CSV)
- Comptes individuels des communes 2022 (DGFiP, JSON)
- Revenus Filosofi 2021 (INSEE via data.gouv.fr, CSV zip)
"""
import json
import math
import os
import sys
import tempfile
import urllib.request

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

QPV_URL = "https://static.data.gouv.fr/resources/quartiers-prioritaires-de-la-politique-de-la-ville-qpv/20260116-110350/listeqp2024-cog2024.csv"

COMPTES_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-2022/exports/json"

REVENUS_URL = "https://api.insee.fr/melodi/file/DS_FILOSOFI_CC/DS_FILOSOFI_CC_2021_CSV_FR"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_float(val):
    """Convert value to float, return None on failure or NaN."""
    try:
        if val is None:
            return None
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def safe_int(val):
    """Convert value to int, return None on failure."""
    try:
        if val is None:
            return None
        if isinstance(val, float) and math.isnan(val):
            return None
        return int(val)
    except (ValueError, TypeError):
        return None


def build_insee_from_dep_icom(dep, icom):
    """Build 5-digit INSEE code from DGFiP dep (3-char) and icom (3-char).

    For numeric departments: strip leading zero from dep then concat with icom.
      "050" + "082" -> "50" + "082" -> "50082"
      "001" + "053" -> "1" + "053" -> "01053" (zero-padded to 5)
    For Corsica: keep dep as-is.
      "02A" + "082" -> "2A" + "082" -> "2A082"
    """
    dep = str(dep).strip()
    icom = str(icom).strip()

    # Strip leading zero from numeric 3-digit departments
    if len(dep) == 3 and dep.isdigit():
        dep = dep.lstrip("0") or "0"

    code = dep + icom
    # Zero-pad to 5 digits for numeric codes
    if code.isdigit():
        code = code.zfill(5)

    return code


# ---------------------------------------------------------------------------
# Source 1: QPV
# ---------------------------------------------------------------------------

def parse_qpv():
    """Download and parse QPV CSV.

    Returns dict {insee_code: count_of_qpv}.
    """
    print("Downloading QPV data...", file=sys.stderr)
    try:
        with urllib.request.urlopen(QPV_URL, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARNING: Could not download QPV data: {e}", file=sys.stderr)
        return {}

    import csv
    reader = csv.DictReader(text.splitlines(), delimiter=";")

    counts = {}
    rows_read = 0
    for row in reader:
        rows_read += 1
        raw_code = row.get("insee_com", "").strip()
        if not raw_code:
            continue
        # Zero-pad to 5 digits (some are just numbers like "1053")
        if raw_code.isdigit():
            raw_code = raw_code.zfill(5)
        counts[raw_code] = counts.get(raw_code, 0) + 1

    print(f"  QPV: {rows_read} rows read, {len(counts)} communes with QPV data", file=sys.stderr)
    total_qpv = sum(counts.values())
    print(f"  QPV: {total_qpv} total QPV entries", file=sys.stderr)
    return counts


# ---------------------------------------------------------------------------
# Source 2: Comptes individuels des communes (DGFiP)
# ---------------------------------------------------------------------------

def parse_comptes():
    """Download and parse DGFiP commune accounts JSON.

    Returns dict {insee_code: {dgf_hab, dgf, dette_hab, cafn_hab, perso_hab,
                                prod_hab, equip_hab, pop}}.
    """
    print("Downloading DGFiP comptes individuels 2022 (may take a few minutes)...", file=sys.stderr)
    try:
        req = urllib.request.Request(COMPTES_URL)
        req.add_header("User-Agent", "Mozilla/5.0 (carte-politique research bot)")
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARNING: Could not download DGFiP data: {e}", file=sys.stderr)
        return {}

    print("  Parsing JSON...", file=sys.stderr)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  WARNING: Invalid JSON from DGFiP: {e}", file=sys.stderr)
        return {}

    result = {}
    parsed = 0
    skipped = 0

    for entry in data:
        dep = entry.get("dep", "")
        icom = entry.get("icom", "")
        if not dep or not icom:
            skipped += 1
            continue

        code = build_insee_from_dep_icom(dep, icom)
        rec = {}

        # DGF per inhabitant
        v = safe_float(entry.get("fdgf"))
        if v is not None:
            rec["dgf_hab"] = round(v, 1)

        # Dette per inhabitant
        v = safe_float(entry.get("fdette"))
        if v is not None:
            rec["dette_hab"] = round(v, 1)

        # CAF nette per inhabitant
        v = safe_float(entry.get("fcafn"))
        if v is not None:
            rec["cafn_hab"] = round(v, 1)

        # Personnel charges per inhabitant
        v = safe_float(entry.get("fperso"))
        if v is not None:
            rec["perso_hab"] = round(v, 1)

        if rec:
            result[code] = rec
            parsed += 1

    print(f"  Comptes: {parsed} communes parsed, {skipped} skipped", file=sys.stderr)
    return result


# ---------------------------------------------------------------------------
# Source 3: Revenus Filosofi 2021 (INSEE)
# ---------------------------------------------------------------------------

def parse_revenus():
    """Download and parse Filosofi 2021 CSV (zip) from INSEE.

    The file is a zip containing a long-format CSV with one row per
    (commune, measure).  We extract:
      - MED_SL  → rev_med  (niveau de vie médian, EUR/an)
      - PR_MD60 → tx_pauv  (taux de pauvreté à 60 %, %)

    Returns dict {insee_code: {rev_med, tx_pauv}}.
    """
    import csv
    import io
    import zipfile

    print("Downloading Revenus Filosofi 2021 CSV (INSEE)...", file=sys.stderr)
    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()

        req = urllib.request.Request(REVENUS_URL)
        req.add_header("User-Agent", "Mozilla/5.0 (carte-politique research bot)")
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(tmp_path, "wb") as out:
                out.write(resp.read())

        z = zipfile.ZipFile(tmp_path)
        # Find the data CSV inside the zip (exclude metadata file)
        data_name = None
        for name in z.namelist():
            lower = name.lower()
            if lower.endswith(".csv") and "metadata" not in lower:
                if "_data" in lower or lower.endswith("_data.csv"):
                    data_name = name
                    break
        if data_name is None:
            # Fallback: take the largest CSV (skip metadata)
            csv_files = [n for n in z.namelist()
                         if n.endswith(".csv") and "metadata" not in n.lower()]
            if csv_files:
                data_name = max(csv_files, key=lambda n: z.getinfo(n).file_size)
        if data_name is None:
            # Last resort: take the largest CSV overall
            csv_files = [n for n in z.namelist() if n.endswith(".csv")]
            if csv_files:
                data_name = max(csv_files, key=lambda n: z.getinfo(n).file_size)
        if data_name is None:
            print("  WARNING: No CSV data file found in zip", file=sys.stderr)
            return {}

        print(f"  Reading {data_name}...", file=sys.stderr)

        result = {}
        rows_read = 0

        with z.open(data_name) as f:
            reader = csv.DictReader(
                io.TextIOWrapper(f, encoding="utf-8"), delimiter=";"
            )
            for row in reader:
                rows_read += 1

                # Only keep commune-level rows
                if row.get("GEO_OBJECT") != "COM":
                    continue

                measure = row.get("FILOSOFI_MEASURE", "")
                if measure not in ("MED_SL", "PR_MD60"):
                    continue

                code = row.get("GEO", "").strip()
                if not code:
                    continue
                if code.isdigit():
                    code = code.zfill(5)

                val_str = row.get("OBS_VALUE", "").strip()
                if not val_str:
                    continue
                v = safe_float(val_str)
                if v is None:
                    continue

                if code not in result:
                    result[code] = {}

                if measure == "MED_SL":
                    result[code]["rev_med"] = round(v)
                elif measure == "PR_MD60":
                    result[code]["tx_pauv"] = round(v, 1)

        rev_count = sum(1 for r in result.values() if "rev_med" in r)
        pauv_count = sum(1 for r in result.values() if "tx_pauv" in r)
        print(f"  Revenus: {rows_read} rows read, {len(result)} communes with data", file=sys.stderr)
        print(f"    rev_med: {rev_count} communes, tx_pauv: {pauv_count} communes", file=sys.stderr)
        return result

    except Exception as e:
        print(f"  WARNING: Could not process revenus data: {e}", file=sys.stderr)
        return {}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    base_dir = os.path.dirname(__file__) or "."
    output_path = os.path.join(base_dir, "enrichment.json")

    # --- Source 1: QPV ---
    qpv_counts = parse_qpv()

    # --- Source 2: DGFiP comptes ---
    comptes = parse_comptes()

    # --- Source 3: Revenus Filosofi 2021 ---
    revenus = parse_revenus()

    # --- Merge all sources ---
    print("\nMerging data sources...", file=sys.stderr)
    all_codes = set()
    all_codes |= set(qpv_counts.keys())
    all_codes |= set(comptes.keys())
    all_codes |= set(revenus.keys())

    result = {}
    for code in sorted(all_codes):
        entry = {}

        # QPV count
        if code in qpv_counts:
            entry["qpv"] = qpv_counts[code]

        # DGFiP financial data
        if code in comptes:
            entry.update(comptes[code])

        # Revenus data
        if code in revenus:
            entry.update(revenus[code])

        if entry:
            result[code] = entry

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nOutput: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"  {len(result)} communes total", file=sys.stderr)
    for key in ["qpv", "dgf_hab", "dette_hab", "cafn_hab", "perso_hab",
                "rev_med", "tx_pauv"]:
        count = sum(1 for v in result.values() if key in v)
        print(f"  {key}: {count} communes", file=sys.stderr)

    # Sample: Paris
    if "75056" in result:
        print(f"\n  Sample (Paris 75056): {json.dumps(result['75056'], indent=2)}", file=sys.stderr)


if __name__ == "__main__":
    main()
