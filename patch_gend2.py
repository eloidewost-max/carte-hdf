#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakgend2"))
print("Backup cree :", SRC.with_suffix(".html.bakgend2"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Dans getStyle : contour bleu epais pour les villes gendarmerie SANS statut.
#    On intercepte tout en haut de getStyle.
must_replace(
    "  function getStyle(feature) {\n"
    "    if (currentMode === 'icp')          return getStyleICP(feature);",
    "  var STYLE_GEND = { fillColor: '#3b82f6', fillOpacity: 0.25, weight: 3, color: '#1e3a8a', opacity: 0.95, dashArray: null };\n"
    "  function getStyle(feature) {\n"
    "    // Villes chef-lieu gendarmerie sans statut : contour bleu bien visible\n"
    "    var _c = feature.properties.codgeo;\n"
    "    if (hdf[_c] && hdf[_c].gend && !communeStatuts[_c] && currentMode === 'prospection') return STYLE_GEND;\n"
    "    if (currentMode === 'icp')          return getStyleICP(feature);",
    "Contour bleu pour villes gendarmerie")

# 2. Repositionner le logo 🚔 AU-DESSUS du nom (deja le cas dans le HTML genere ?)
#    Le marqueur actuel a le 🚔 puis le nom en dessous, mais iconAnchor centre les deux.
#    On agrandit la hauteur et on remonte l'ancrage pour que le 🚔 soit au-dessus du polygone.
must_replace(
    "        iconSize: [120, 36],\n"
    "        iconAnchor: [60, 18]\n"
    "      });\n"
    "      L.marker([d.lat, d.lng], { icon: icon, interactive: false, keyboard: false })\n"
    "        .addTo(gendLabelLayer);",
    "        iconSize: [140, 44],\n"
    "        iconAnchor: [70, 44]\n"
    "      });\n"
    "      L.marker([d.lat, d.lng], { icon: icon, interactive: false, keyboard: false })\n"
    "        .addTo(gendLabelLayer);",
    "Repositionnement logo gendarmerie au-dessus")

# Checks
for needle, label in [
    ("STYLE_GEND", "Style contour bleu defini"),
    ("hdf[_c].gend && !communeStatuts[_c]", "Regle villes gendarmerie dans getStyle"),
    ("iconAnchor: [70, 44]", "Logo repositionne"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakgend2 dispo)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch gendarmerie 2 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
