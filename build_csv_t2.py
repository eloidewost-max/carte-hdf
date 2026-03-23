#!/usr/bin/env python3
"""
Download Figaro/MdI municipal election T2 2026 data and merge with T1 CSV.

Source: GCS bucket figdata-mun2026-public (Ministère de l'Intérieur via Le Figaro pipeline)
Input:  resultats_municipales_2026_t1.csv  (existing T1 results)
Output: resultats_municipales_2026.csv     (T1 + T2 columns, final analysis)
"""

import os, sys, io, time, unicodedata, concurrent.futures, urllib.request
import pandas as pd

BASE = "https://storage.googleapis.com/figdata-mun2026-public/MUN2026"

DEPTS = [
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15",
    "16","17","18","19","2A","2B","21","22","23","24","25","26","27","28","29",
    "30","31","32","33","34","35","36","37","38","39","40","41","42","43","44",
    "45","46","47","48","49","50","51","52","53","54","55","56","57","58","59",
    "60","61","62","63","64","65","66","67","68","69","70","71","72","73","74",
    "75","76","77","78","79","80","81","82","83","84","85","86","87","88","89",
    "90","91","92","93","94","95","971","972","973","974","976",
]

BLOC_MAP = {
    "LEXG": "Extrême gauche", "LFI": "Extrême gauche",
    "LCOM": "Gauche", "LSOC": "Gauche", "LVEC": "Gauche",
    "LUG": "Gauche", "LDVG": "Gauche", "LECO": "Gauche",
    "LREN": "Centre", "LMDM": "Centre", "LHOR": "Centre",
    "LUDI": "Centre", "LDVC": "Centre", "LPR": "Centre",
    "LUCD": "Droite", "LLR": "Droite", "LDVD": "Droite", "LDSR": "Droite",
    "LRN": "Extrême droite", "LUDR": "Extrême droite",
    "LREC": "Extrême droite", "LEXD": "Extrême droite",
    "LDIV": "Divers", "LREG": "Divers", "LANM": "Divers",
    "EXG": "Extrême gauche", "FI": "Extrême gauche",
    "COM": "Gauche", "SOC": "Gauche", "VEC": "Gauche",
    "UG": "Gauche", "DVG": "Gauche", "ECO": "Gauche",
    "REN": "Centre", "MDM": "Centre", "HOR": "Centre",
    "UDI": "Centre", "DVC": "Centre", "PR": "Centre",
    "UCD": "Droite", "LR": "Droite", "DVD": "Droite", "DSV": "Droite",
    "RN": "Extrême droite", "UDR": "Extrême droite",
    "REC": "Extrême droite", "EXD": "Extrême droite",
    "DIV": "Divers", "REG": "Divers", "ANM": "Divers",
    "NC": "Sans étiquette",
    "LUXD": "Extrême droite", "LUC": "Centre",
    "LUD": "Droite", "LDSV": "Droite",
}

CACHE_DIR = "/tmp/mun2026_cache_t2"


def download(url):
    cache_path = os.path.join(CACHE_DIR, url.replace(BASE + "/", "").replace("/", "_"))
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(cache_path) or CACHE_DIR, exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(data)
        return data
    except Exception as e:
        return None


def read_parquet_from_url(url):
    data = download(url)
    if data is None:
        return None
    return pd.read_parquet(io.BytesIO(data))


def download_dept_t2(dept):
    winner = read_parquet_from_url(f"{BASE}/{dept}/resultatsT2/winner.parquet")
    index = read_parquet_from_url(f"{BASE}/{dept}/resultatsT2/index.parquet")
    tete = read_parquet_from_url(f"{BASE}/{dept}/resultatsT2/tete.parquet")
    return {"dept": dept, "winner": winner, "index": index, "tete": tete}


def normalize_name(name):
    if not isinstance(name, str):
        return ""
    return unicodedata.normalize("NFD", name.upper()).encode("ascii", "ignore").decode().strip()


def fmt_name(prenom, nom):
    p = str(prenom).strip() if pd.notna(prenom) else ""
    n = str(nom).strip() if pd.notna(nom) else ""
    if not p and not n:
        return ""
    p = p.title() if p == p.upper() or p == p.lower() else p
    n = n.title() if n == n.upper() or n == n.lower() else n
    return f"{p} {n}".strip()


def get_bloc(nuance):
    if pd.isna(nuance) or nuance == "" or nuance is None:
        return "Sans étiquette"
    return BLOC_MAP.get(str(nuance).strip(), "Sans étiquette")


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    # ── 1. Load existing T1 CSV ──────────────────────────────────────────────
    t1_path = "resultats_municipales_2026_t1.csv"
    print(f"Loading {t1_path}...")
    df = pd.read_csv(t1_path, encoding="utf-8-sig", dtype={"code_insee": str, "code_departement": str})
    print(f"  {len(df)} communes loaded")

    t2_communes = df[df["statut_t1"] == "SECOND_TOUR"]
    print(f"  {len(t2_communes)} communes en second tour")

    # ── 2. Download T2 data ──────────────────────────────────────────────────
    print(f"Downloading T2 results for {len(DEPTS)} departments (parallel)...")
    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(download_dept_t2, d): d for d in DEPTS}
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            dept = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                print(f"  ERROR dept {dept}: {e}", file=sys.stderr)
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(DEPTS)} done...")
    print(f"  Downloaded in {time.time()-t0:.1f}s")

    # ── 3. Assemble T2 data ──────────────────────────────────────────────────
    all_winner, all_index, all_tete = [], [], []
    for r in results:
        if r["winner"] is not None:
            all_winner.append(r["winner"])
        if r["index"] is not None:
            all_index.append(r["index"])
        if r["tete"] is not None:
            all_tete.append(r["tete"])

    if not all_winner:
        print("ERROR: No T2 winner data found!", file=sys.stderr)
        sys.exit(1)

    winner = pd.concat(all_winner, ignore_index=True)
    index = pd.concat(all_index, ignore_index=True)
    tete = pd.concat(all_tete, ignore_index=True)
    print(f"  T2 winners: {len(winner)}, index: {len(index)}, têtes: {len(tete)}")

    # ── 4. Build T2 winner table ─────────────────────────────────────────────
    win = winner[winner["IsLeadingList"] == True].copy()
    win = win[["CodCirElec", "NomPsn", "PrenomPsn", "NomCompListe",
               "CodNuaListe", "RapportExprimes", "NbSieges", "Elu"]].copy()
    win = win.drop_duplicates(subset="CodCirElec", keep="first")
    win["vainqueur_t2"] = win.apply(lambda r: fmt_name(r["PrenomPsn"], r["NomPsn"]), axis=1)
    win["bloc_t2"] = win["CodNuaListe"].apply(get_bloc)
    win = win.rename(columns={
        "CodCirElec": "code_insee",
        "NomCompListe": "liste_vainqueur_t2",
        "CodNuaListe": "nuance_t2",
        "RapportExprimes": "score_t2_pct",
        "NbSieges": "sieges_t2",
        "Elu": "elu_t2",
    })
    win = win[["code_insee", "vainqueur_t2", "liste_vainqueur_t2", "nuance_t2",
               "bloc_t2", "score_t2_pct", "sieges_t2"]].copy()

    # ── 5. Build T2 second-place table ───────────────────────────────────────
    tete_sorted = tete.sort_values(["CodCirElec", "RapportExprimes"], ascending=[True, False])
    second = (
        tete_sorted.groupby("CodCirElec")
        .nth(1)
        .reset_index()[["CodCirElec", "RapportExprimes", "NomPsn", "PrenomPsn"]]
    )
    second["second_t2"] = second.apply(lambda r: fmt_name(r["PrenomPsn"], r["NomPsn"]), axis=1)
    second = second.rename(columns={
        "CodCirElec": "code_insee",
        "RapportExprimes": "score_second_t2_pct",
    })
    second = second[["code_insee", "second_t2", "score_second_t2_pct"]].copy()

    # ── 6. Build T2 participation table ──────────────────────────────────────
    idx = index[["CodCirElec", "VotantsRapportInscrits"]].copy()
    idx = idx.rename(columns={
        "CodCirElec": "code_insee",
        "VotantsRapportInscrits": "participation_t2_pct",
    })

    # ── 7. Merge T2 into T1 ─────────────────────────────────────────────────
    print("Merging T2 into T1...")
    df = df.merge(win, on="code_insee", how="left")
    df = df.merge(second, on="code_insee", how="left")
    df = df.merge(idx, on="code_insee", how="left")

    # ── 8. Compute final columns ─────────────────────────────────────────────
    has_t2 = df["vainqueur_t2"].notna() & (df["vainqueur_t2"] != "")

    df["tour_decision"] = "T1"
    df.loc[has_t2, "tour_decision"] = "T2"

    # Final winner = T2 if available, else T1
    df["vainqueur_final"] = df["vainqueur_t1"]
    df.loc[has_t2, "vainqueur_final"] = df.loc[has_t2, "vainqueur_t2"]

    df["liste_finale"] = df["liste_vainqueur"]
    df.loc[has_t2, "liste_finale"] = df.loc[has_t2, "liste_vainqueur_t2"]

    df["nuance_finale"] = df["nuance_2026"]
    df.loc[has_t2, "nuance_finale"] = df.loc[has_t2, "nuance_t2"]

    df["bloc_final"] = df["bloc_2026"]
    df.loc[has_t2, "bloc_final"] = df.loc[has_t2, "bloc_t2"]

    df["score_final_pct"] = df["score_t1_pct"]
    df.loc[has_t2, "score_final_pct"] = df.loc[has_t2, "score_t2_pct"]

    # Recompute analysis on final results
    def check_nouveau_maire(row):
        if row["statut_t1"] == "SANS_CANDIDATURE":
            return ""
        sortant = normalize_name(str(row.get("maire_sortant", "")))
        vainqueur = normalize_name(str(row.get("vainqueur_final", "")))
        if not sortant or not vainqueur:
            return "INCONNU"
        return "NON" if sortant == vainqueur else "OUI"

    def check_changement_bord(row):
        if row["statut_t1"] == "SANS_CANDIDATURE":
            return ""
        b20 = row["bloc_2020"]
        bf = row["bloc_final"]
        if b20 == "Sans étiquette" or bf == "Sans étiquette":
            return "INCONNU"
        return "NON" if b20 == bf else "OUI"

    df["nouveau_maire"] = df.apply(check_nouveau_maire, axis=1)
    df["changement_bord"] = df.apply(check_changement_bord, axis=1)
    df["sens_bascule"] = df.apply(
        lambda r: f"{r['bloc_2020']} → {r['bloc_final']}" if r["changement_bord"] == "OUI" else "", axis=1
    )
    df["sortant_reconduit"] = df.apply(
        lambda r: "" if r["statut_t1"] == "SANS_CANDIDATURE"
        else ("OUI" if r["nouveau_maire"] == "NON" else ("NON" if r["nouveau_maire"] == "OUI" else "INCONNU")),
        axis=1,
    )
    df["marge_victoire_pts"] = (df["score_final_pct"] - df.apply(
        lambda r: r["score_second_t2_pct"] if pd.notna(r.get("score_second_t2_pct")) and r["tour_decision"] == "T2"
        else r["score_second_pct"], axis=1
    )).round(1)

    # ── 9. Select & order final columns ──────────────────────────────────────
    output = df[[
        # Identité commune
        "code_insee", "commune", "code_departement", "departement", "code_region", "region", "population",
        # Sortant
        "maire_sortant", "nuance_2020", "nuance_2020_lib", "bloc_2020",
        # Résultat T1
        "vainqueur_t1", "liste_vainqueur", "nuance_2026", "nuance_2026_lib", "bloc_2026",
        "score_t1_pct", "sieges_obtenus", "statut_t1", "participation_pct",
        "second_t1", "liste_second", "nuance_2e", "score_second_pct",
        # Résultat T2
        "vainqueur_t2", "liste_vainqueur_t2", "nuance_t2", "bloc_t2",
        "score_t2_pct", "sieges_t2", "participation_t2_pct",
        "second_t2", "score_second_t2_pct",
        # Résultat final
        "tour_decision", "vainqueur_final", "liste_finale", "nuance_finale", "bloc_final",
        "score_final_pct", "marge_victoire_pts",
        # Analyse
        "nouveau_maire", "changement_bord", "sens_bascule", "sortant_reconduit",
    ]].copy()

    output = output.sort_values("population", ascending=False)

    for col in ["score_t1_pct", "participation_pct", "score_second_pct",
                "score_t2_pct", "participation_t2_pct", "score_second_t2_pct",
                "score_final_pct", "marge_victoire_pts"]:
        if col in output.columns:
            output[col] = output[col].round(1)

    # ── 10. Write CSV ────────────────────────────────────────────────────────
    outpath = "resultats_municipales_2026.csv"
    output.to_csv(outpath, index=False, encoding="utf-8-sig")
    print(f"\n✓ {outpath}: {len(output)} communes, {len(output.columns)} columns")

    # Stats
    elus_t1 = (output["tour_decision"] == "T1").sum()
    elus_t2 = (output["tour_decision"] == "T2").sum()
    nouveaux = (output["nouveau_maire"] == "OUI").sum()
    bascules = (output["changement_bord"] == "OUI").sum()
    print(f"  Élus au T1: {elus_t1}")
    print(f"  Élus au T2: {elus_t2}")
    print(f"  Nouveaux maires (définitif): {nouveaux}")
    print(f"  Changements de bord (définitif): {bascules}")

    bascule_df = output[output["changement_bord"] == "OUI"]
    if len(bascule_df) > 0:
        print(f"\n  Top 10 bascules (par population):")
        for _, r in bascule_df.nlargest(10, "population").iterrows():
            print(f"    {r['commune']} ({r['population']:.0f} hab) : {r['sens_bascule']}")


if __name__ == "__main__":
    main()
