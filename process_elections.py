#!/usr/bin/env python3
"""
Process the 2022 French presidential election results (1st round)
to extract the winning candidate per commune and output a compact JSON.
"""

import csv
import json
import sys

# Political color mapping for each candidate
CANDIDATE_COLORS = {
    "ARTHAUD":        {"color": "#8B0000", "parti": "LO",          "bord": "Extrême gauche"},
    "POUTOU":         {"color": "#A80000", "parti": "NPA",         "bord": "Extrême gauche"},
    "ROUSSEL":        {"color": "#DD0000", "parti": "PCF",         "bord": "Gauche"},
    "MÉLENCHON":      {"color": "#CC2443", "parti": "LFI",         "bord": "Gauche"},
    "MELENCHON":      {"color": "#CC2443", "parti": "LFI",         "bord": "Gauche"},
    "HIDALGO":        {"color": "#FF8080", "parti": "PS",          "bord": "Centre gauche"},
    "JADOT":          {"color": "#00C060", "parti": "EELV",        "bord": "Écologie"},
    "MACRON":         {"color": "#FFD600", "parti": "LREM",        "bord": "Centre"},
    "LASSALLE":       {"color": "#E8A317", "parti": "Résistons!",  "bord": "Centre"},
    "PÉCRESSE":       {"color": "#0066CC", "parti": "LR",          "bord": "Droite"},
    "PECRESSE":       {"color": "#0066CC", "parti": "LR",          "bord": "Droite"},
    "DUPONT-AIGNAN":  {"color": "#5B6C8E", "parti": "DLF",         "bord": "Droite"},
    "ZEMMOUR":        {"color": "#1B2A4A", "parti": "Reconquête!", "bord": "Extrême droite"},
    "LE PEN":         {"color": "#0D378A", "parti": "RN",          "bord": "Extrême droite"},
}

def main():
    csv_path = "/home/hadrien/carte-politique/presidentielle-2022-t1-communes.csv"
    output_path = "/home/hadrien/carte-politique/winners.json"

    # Accumulate votes per commune per candidate
    # Key: (dep_code, commune_code) → {candidate_name: votes}
    communes = {}

    print("Reading CSV...", file=sys.stderr)
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dep = row["dep_code"].strip()
            com = row["commune_code"].strip()
            # Build the 5-digit INSEE code
            insee = dep + com
            cand = row["cand_nom"].strip()
            voix = int(row["cand_nb_voix"])

            if insee not in communes:
                communes[insee] = {
                    "nom": row["commune_name"].strip(),
                    "candidats": {}
                }

            communes[insee]["candidats"][cand] = voix

    print(f"Found {len(communes)} communes", file=sys.stderr)

    # For each commune, find the winner and compute results
    results = {}
    unknown_candidates = set()
    for insee, data in communes.items():
        candidats = data["candidats"]
        total_voix = sum(candidats.values())
        winner = max(candidats, key=candidats.get)
        winner_voix = candidats[winner]
        pct = round(winner_voix / total_voix * 100, 1) if total_voix > 0 else 0

        # Look up color info
        info = CANDIDATE_COLORS.get(winner)
        if info is None:
            unknown_candidates.add(winner)
            info = {"color": "#999999", "parti": "?", "bord": "?"}

        results[insee] = {
            "n": data["nom"],          # commune name
            "c": winner,               # candidate surname
            "p": info["parti"],        # party
            "b": info["bord"],         # political orientation
            "v": pct,                  # % of expressed votes
            "cl": info["color"],       # color
        }

    if unknown_candidates:
        print(f"Unknown candidates: {unknown_candidates}", file=sys.stderr)

    # Write compact JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = len(json.dumps(results, ensure_ascii=False, separators=(",", ":"))) / (1024 * 1024)
    print(f"Output: {output_path} ({size_mb:.1f} MB)", file=sys.stderr)

    # Print summary stats
    from collections import Counter
    winner_counts = Counter(r["c"] for r in results.values())
    print("\nCommunes won by candidate:", file=sys.stderr)
    for cand, count in winner_counts.most_common():
        info = CANDIDATE_COLORS.get(cand, {"parti": "?", "bord": "?"})
        print(f"  {cand} ({info['parti']}): {count} communes", file=sys.stderr)

if __name__ == "__main__":
    main()
