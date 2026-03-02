#!/usr/bin/env python3
"""
Génère maires.json à partir du fichier nuances-communes.csv
et du RNE maires (elus-maires-mai.csv) pour les noms des maires.
"""

import csv
import json

# --- Mapping nuance → label lisible ---
NUANCE_LABELS = {
    "NC": "Non classé",
    "LNC": "Non classé",
    "LDVD": "Divers droite",
    "LLR": "Les Républicains",
    "LUD": "Union de la droite",
    "LDVG": "Divers gauche",
    "LSOC": "Socialiste",
    "LUG": "Union de la gauche",
    "LCOM": "Communiste",
    "LECO": "Écologiste",
    "LVEC": "Europe Écologie - Les Verts",
    "LDVC": "Divers centre",
    "LREM": "Renaissance (ex-LREM)",
    "LMDM": "MoDem",
    "LUC": "Union du centre",
    "LDIV": "Divers",
    "LUDI": "Union des indépendants",
    "LREG": "Régionaliste",
    "LRN": "Rassemblement National",
    "LEXD": "Extrême droite",
    "LRDG": "Parti radical de gauche",
}

# --- Couleurs par famille politique ---
FAMILLE_COLORS = {
    "Non classé": "#CCCCCC",
    "Droite": "#0056A6",
    "Gauche": "#E2001A",
    "Centre": "#FFB300",
    "Courants politiques divers": "#9E9E9E",
    "Extrême droite": "#0D1B4A",
}

# Famille par défaut pour les nuances connues (fallback si famille_nuance est vide)
NUANCE_TO_FAMILLE = {
    "NC": "Non classé", "LNC": "Non classé",
    "LDVD": "Droite", "LLR": "Droite", "LUD": "Droite",
    "LDVG": "Gauche", "LSOC": "Gauche", "LUG": "Gauche",
    "LCOM": "Gauche", "LECO": "Gauche", "LVEC": "Gauche", "LRDG": "Gauche",
    "LDVC": "Centre", "LREM": "Centre", "LMDM": "Centre", "LUC": "Centre",
    "LDIV": "Courants politiques divers", "LUDI": "Courants politiques divers",
    "LREG": "Courants politiques divers",
    "LRN": "Extrême droite", "LEXD": "Extrême droite",
}


def load_maires_names(path):
    """Charge le RNE maires pour récupérer prénom + nom par code commune."""
    maires = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = row["Code de la commune"].strip()
            dept = row["Code du département"].strip()
            # Construire le code INSEE complet (dept + commune)
            if len(dept) < 2:
                dept = dept.zfill(2)
            code_insee = dept + code[len(dept):]  # Le code commune inclut déjà le département
            prenom = row["Prénom de l'élu"].strip()
            nom = row["Nom de l'élu"].strip()
            # Formatter: Prénom Nom (capitalisation propre)
            prenom_fmt = prenom.capitalize() if prenom == prenom.upper() else prenom
            nom_fmt = nom.capitalize() if nom == nom.upper() else nom
            maires[code] = f"{prenom_fmt} {nom_fmt}"
    return maires


def main():
    # 1. Charger les noms des maires depuis le RNE
    print("Chargement des noms de maires (RNE)...")
    maires_noms = load_maires_names("/tmp/elus-maires.csv")
    print(f"  → {len(maires_noms)} maires chargés")

    # 2. Traiter les nuances politiques
    print("Traitement des nuances politiques...")
    result = {}
    stats = {"total": 0, "matched_maire": 0}

    with open("/tmp/nuances-communes.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["cog_commune"].strip()
            nom = row["nom_commune"].strip()
            nuance_raw = row["nuance_politique"].strip()
            famille_raw = row["famille_nuance"].strip()

            if not code:
                continue

            # Gérer les doubles nuances → garder la première
            nuance = nuance_raw.split(",")[0] if nuance_raw else "NC"

            # Déterminer la famille
            if famille_raw:
                famille = famille_raw
            elif nuance in NUANCE_TO_FAMILLE:
                famille = NUANCE_TO_FAMILLE[nuance]
            else:
                famille = "Non classé"

            # Couleur
            couleur = FAMILLE_COLORS.get(famille, "#CCCCCC")

            # Label lisible
            label = NUANCE_LABELS.get(nuance, nuance)

            entry = {
                "n": nom,
                "nu": nuance,
                "f": famille,
                "cl": couleur,
                "lb": label,
            }

            # Ajouter le nom du maire si disponible
            if code in maires_noms:
                entry["m"] = maires_noms[code]
                stats["matched_maire"] += 1

            result[code] = entry
            stats["total"] += 1

    # 3. Écrire le JSON
    output_path = "/home/hadrien/carte-politique/maires.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n  → {stats['total']} communes écrites dans maires.json")
    print(f"  → {stats['matched_maire']} communes avec nom du maire")
    size_mb = len(open(output_path).read()) / 1024 / 1024
    print(f"  → Taille: {size_mb:.1f} Mo")

    # Stats par famille
    from collections import Counter
    fam_counts = Counter(v["f"] for v in result.values())
    print("\nRépartition par famille :")
    for fam, count in fam_counts.most_common():
        print(f"  {fam:30s} {count:6d}")


if __name__ == "__main__":
    main()
