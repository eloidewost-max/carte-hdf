#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path("/Users/eloi/Desktop/Artefact Vizzia/carte-politique-main/hdf-map.html")
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakbackuprdv"))
print("Backup cree :", SRC.with_suffix(".html.bakbackuprdv"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

# Ajouter rdv: communeRdv dans l'objet exporte
old = (
    "    var data = {\n"
    "      date: new Date().toISOString(),\n"
    "      statuts: communeStatuts,\n"
    "      visites: communeVisites\n"
    "    };"
)
new = (
    "    var data = {\n"
    "      date: new Date().toISOString(),\n"
    "      statuts: communeStatuts,\n"
    "      visites: communeVisites,\n"
    "      rdv: communeRdv\n"
    "    };"
)
if old not in html:
    print("  [X] ANCRE ABSENTE : objet data export"); ok = False
else:
    html = html.replace(old, new, 1)
    print("  [OK] rdv ajoute a la sauvegarde")

# Check
if "rdv: communeRdv" in html:
    print("  [OK] Verification : rdv: communeRdv present")
else:
    print("  [X] rdv absent apres patch"); ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakbackuprdv)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch backup rdv applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
