#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakdiag"))
print("Backup cree :", SRC.with_suffix(".html.bakdiag"))

html = SRC.read_text(encoding="utf-8")

old = ('    var fromLatLng = getCentroid(fromCode);\n'
       '    var toLatLng   = getCentroid(toCode);\n'
       '    if (!fromLatLng || !toLatLng) { alert("Impossible de localiser une commune."); return; }')
new = ('    var fromLatLng = getCentroid(fromCode);\n'
       '    var toLatLng   = getCentroid(toCode);\n'
       '    console.log("[TRAJET]", fromCode, (hdf[fromCode]||{}).n, JSON.stringify(fromLatLng), "=>", toCode, (hdf[toCode]||{}).n, JSON.stringify(toLatLng));\n'
       '    if (!fromLatLng || !toLatLng) { alert("Impossible de localiser une commune."); return; }')

if old not in html:
    print("[X] ancre introuvable"); sys.exit(1)
html = html.replace(old, new, 1)
SRC.write_text(html, encoding="utf-8")
print("[OK] Diagnostic ajoute dans calcRoute")
print("    -> Recharge la carte, ouvre la console (Cmd+Option+I),")
print("       fais un trajet AVEC Blaincourt-Les-Precy, copie les lignes [TRAJET]")
