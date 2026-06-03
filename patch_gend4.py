#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakgend4"))
print("Backup cree :", SRC.with_suffix(".html.bakgend4"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    if html.count(old) > 1:
        print("  [!] ANCRE MULTIPLE (" + str(html.count(old)) + "x) :", label, "- on prend la 1ere")
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. CITY_LABELS : garder Lille seul
must_replace(
    "  var CITY_LABELS = [\n"
    "    { name: 'Lille',    lat: 50.6292, lng: 3.0573 },\n"
    "    { name: 'Arras',    lat: 50.2928, lng: 2.7809 },\n"
    "    { name: 'Amiens',   lat: 49.8942, lng: 2.2958 },\n"
    "    { name: 'Beauvais', lat: 49.4295, lng: 2.0807 },\n"
    "    { name: 'Laon',     lat: 49.5636, lng: 3.6242 }\n"
    "  ];",
    "  var CITY_LABELS = [\n"
    "    { name: 'Lille',    lat: 50.6292, lng: 3.0573 }\n"
    "  ];",
    "CITY_LABELS reduit a Lille seul")

# 2. STYLE_GEND : noir, sans bordure
must_replace(
    "  var STYLE_GEND = { fillColor: '#3b82f6', fillOpacity: 0.25, weight: 3, color: '#1e3a8a', opacity: 0.95, dashArray: null };",
    "  var STYLE_GEND = { fillColor: '#1a1a1a', fillOpacity: 0.88, weight: 0, color: '#1a1a1a', opacity: 0, dashArray: null };",
    "STYLE_GEND noir sans bordure")

# 3. Label gendarmerie : retirer 🚔, nom en blanc, recentrer
must_replace(
    "      var icon = L.divIcon({\n"
    "        className: '',\n"
    "        html: '<div style=\"text-align:center;pointer-events:none;white-space:nowrap;\">'\n"
    "            + '<div style=\"font-size:22px;line-height:1;\">\\ud83d\\ude94</div>'\n"
    "            + '<span style=\"font-size:10px;font-weight:800;color:#1e3a8a;'\n"
    "            + 'text-shadow:0 1px 2px rgba(255,255,255,0.95),0 0 6px rgba(255,255,255,0.9);\">'\n"
    "            + d.n + '</span>'\n"
    "            + '</div>',\n"
    "        iconSize: [140, 44],\n"
    "        iconAnchor: [70, 44]\n"
    "      });",
    "      var icon = L.divIcon({\n"
    "        className: '',\n"
    "        html: '<div style=\"text-align:center;pointer-events:none;white-space:nowrap;\">'\n"
    "            + '<span style=\"font-size:12px;font-weight:800;color:#ffffff;'\n"
    "            + 'text-shadow:0 1px 2px rgba(0,0,0,0.9),0 0 4px rgba(0,0,0,0.8);\">'\n"
    "            + d.n + '</span>'\n"
    "            + '</div>',\n"
    "        iconSize: [140, 20],\n"
    "        iconAnchor: [70, 10]\n"
    "      });",
    "Label gendarmerie : nom blanc, sans emoji, centre")

# Checks
for needle, label, want in [
    ("{ name: 'Arras',    lat: 50.2928", "Arras retire de CITY_LABELS", False),
    ("{ name: 'Lille',    lat: 50.6292", "Lille conserve", True),
    ("fillColor: '#1a1a1a', fillOpacity: 0.88", "Style noir applique", True),
    ("\\ud83d\\ude94", "Emoji voiture supprime", False),
    ("color:#ffffff;", "Nom gendarmerie en blanc", True),
]:
    present = needle in html
    good = (present == want)
    print(("  [OK] " if good else "  [X] ") + label)
    if not good: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakgend4)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch gend4 applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
