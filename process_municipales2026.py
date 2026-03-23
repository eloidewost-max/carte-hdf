#!/usr/bin/env python3
"""Convert resultats_municipales_2026.csv to municipales2026.json (compact, INSEE-keyed).

Reads the merged T1+T2 CSV and produces a JSON with final results for each commune.
Falls back to T1-only CSV if the merged file doesn't exist.
"""

import csv, json, os, sys

BLOC_COLORS = {
    "Extrême gauche": "#B71C1C",
    "Gauche": "#E2001A",
    "Centre": "#FFB300",
    "Droite": "#0056A6",
    "Extrême droite": "#0D1B4A",
    "Divers": "#9E9E9E",
    "Sans étiquette": "#666666",
}

def main():
    # Prefer merged CSV, fall back to T1-only
    csv_path = "resultats_municipales_2026.csv"
    if not os.path.exists(csv_path):
        csv_path = "resultats_municipales_2026_t1.csv"
        print(f"  (fallback to {csv_path})")

    out = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        has_t2 = "tour_decision" in reader.fieldnames

        for row in reader:
            code = row["code_insee"]
            if not code:
                continue

            def num(key):
                v = row.get(key, "")
                if v == "" or v == "nan":
                    return None
                try:
                    return round(float(v), 1)
                except ValueError:
                    return None

            # Tour decision: use final column if available, else derive from statut_t1
            if has_t2:
                td = row.get("tour_decision", "T1")
            else:
                st_raw = row.get("statut_t1", "")
                td = "T1" if st_raw == "ELU_T1" else ("T2" if st_raw == "SECOND_TOUR" else "")

            nm_raw = row.get("nouveau_maire", "")
            nm = 1 if nm_raw == "OUI" else (0 if nm_raw == "NON" else -1)

            cb_raw = row.get("changement_bord", "")
            cb = 1 if cb_raw == "OUI" else (0 if cb_raw == "NON" else -1)

            b20 = row.get("bloc_2020", "Sans étiquette") or "Sans étiquette"

            # Use final bloc/nuance if available, else T1
            if has_t2:
                bf = row.get("bloc_final", "Sans étiquette") or "Sans étiquette"
                nf = row.get("nuance_finale", "") or ""
                vf = row.get("vainqueur_final", "") or ""
                lf = row.get("liste_finale", "") or ""
                scf = num("score_final_pct")
            else:
                bf = row.get("bloc_2026", "Sans étiquette") or "Sans étiquette"
                nf = row.get("nuance_2026", "") or ""
                vf = row.get("vainqueur_t1", "") or ""
                lf = row.get("liste_vainqueur", "") or ""
                scf = num("score_t1_pct")

            entry = {
                "ms": row.get("maire_sortant", "") or "",
                "n20": row.get("nuance_2020", "") or "",
                "b20": b20,
                # T1 results (always present)
                "vt1": row.get("vainqueur_t1", "") or "",
                "lt1": row.get("liste_vainqueur", "") or "",
                "n26": row.get("nuance_2026", "") or "",
                "b26": row.get("bloc_2026", "Sans étiquette") or "Sans étiquette",
                "sc1": num("score_t1_pct"),
                "pa1": num("participation_pct"),
                "s2t1": row.get("second_t1", "") or "",
                "sc2t1": num("score_second_pct"),
                # T2 results (only for T2 communes)
                "vt2": row.get("vainqueur_t2", "") or "" if has_t2 else "",
                "lt2": row.get("liste_vainqueur_t2", "") or "" if has_t2 else "",
                "nt2": row.get("nuance_t2", "") or "" if has_t2 else "",
                "bt2": row.get("bloc_t2", "") or "" if has_t2 else "",
                "sc2": num("score_t2_pct") if has_t2 else None,
                "pa2": num("participation_t2_pct") if has_t2 else None,
                "s2t2": row.get("second_t2", "") or "" if has_t2 else "",
                "sc2t2": num("score_second_t2_pct") if has_t2 else None,
                # Final results
                "td": td,
                "vf": vf,
                "lf": lf,
                "nf": nf,
                "bf": bf,
                "scf": scf,
                # Analysis
                "nm": nm,
                "cb": cb,
                "sb": row.get("sens_bascule", "") or "",
                "cl20": BLOC_COLORS.get(b20, "#666666"),
                "clf": BLOC_COLORS.get(bf, "#666666"),
            }

            # Strip empty/null values to save space
            entry = {k: v for k, v in entry.items() if v is not None and v != ""}
            # Always keep td, nm, cb even if falsy
            for key, val in [("td", td), ("nm", nm), ("cb", cb)]:
                if key not in entry:
                    entry[key] = val
            entry["cl20"] = BLOC_COLORS.get(b20, "#666666")
            entry["clf"] = BLOC_COLORS.get(bf, "#666666")

            out[code] = entry

    with open("municipales2026.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))) / 1024
    print(f"municipales2026.json: {len(out)} communes, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
