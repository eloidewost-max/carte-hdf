#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
if not SRC.exists():
    print("ERREUR : fichier introuvable", SRC); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakgend"))
print("Backup cree :", SRC.with_suffix(".html.bakgend"))

html = SRC.read_text(encoding="utf-8")
original = html
ok = True

def must_replace(old, new, label):
    global html, ok
    if old not in html:
        print("  [X] ANCRE ABSENTE :", label); ok = False; return
    html = html.replace(old, new, 1)
    print("  [OK]", label)

# 1. Ajouter les 5 villes a HDF_DATA, juste apres "HDF_DATA = {"
# Format conforme aux entrees existantes. gend:true = chef-lieu gendarmerie.
villes = (
    '"80021":{"n":"Amiens","lat":49.8942,"lng":2.2958,"pop":134057,"pm":0,"asvp":0,"acc":0,"vv":false,"stat":false,"qpv":0,"rev":0,"pauv":0,"dgf":0,"f":"Non classé","lb":"Non classé","cl":"#CCCCCC","maire":"","fibre":1,"4g":1,"5g":1,"gend":true},'
    '"02408":{"n":"Laon","lat":49.5641,"lng":3.6237,"pop":24876,"pm":0,"asvp":0,"acc":0,"vv":false,"stat":false,"qpv":0,"rev":0,"pauv":0,"dgf":0,"f":"Non classé","lb":"Non classé","cl":"#CCCCCC","maire":"","fibre":1,"4g":1,"5g":1,"gend":true},'
    '"60057":{"n":"Beauvais","lat":49.4294,"lng":2.0810,"pop":56768,"pm":0,"asvp":0,"acc":0,"vv":false,"stat":false,"qpv":0,"rev":0,"pauv":0,"dgf":0,"f":"Non classé","lb":"Non classé","cl":"#CCCCCC","maire":"","fibre":1,"4g":1,"5g":1,"gend":true},'
    '"62041":{"n":"Arras","lat":50.2910,"lng":2.7775,"pop":41019,"pm":0,"asvp":0,"acc":0,"vv":false,"stat":false,"qpv":0,"rev":0,"pauv":0,"dgf":0,"f":"Non classé","lb":"Non classé","cl":"#CCCCCC","maire":"","fibre":1,"4g":1,"5g":1,"gend":true},'
    '"59009":{"n":"Villeneuve-d\'Ascq","lat":50.6217,"lng":3.1306,"pop":62308,"pm":0,"asvp":0,"acc":0,"vv":false,"stat":false,"qpv":0,"rev":0,"pauv":0,"dgf":0,"f":"Non classé","lb":"Non classé","cl":"#CCCCCC","maire":"","fibre":1,"4g":1,"5g":1,"gend":true},'
)
must_replace(
    'var HDF_DATA = {"59001":',
    'var HDF_DATA = {' + villes + '"59001":',
    "Ajout des 5 villes a HDF_DATA")

# 2. Layer + fonction refreshGendarmerieLabels, juste apres la creation de visiteLabelLayer
must_replace(
    "  var statusLabelLayer = L.layerGroup().addTo(map);\n"
    "  var visiteLabelLayer = L.layerGroup().addTo(map);",
    "  var statusLabelLayer = L.layerGroup().addTo(map);\n"
    "  var visiteLabelLayer = L.layerGroup().addTo(map);\n"
    "  var gendLabelLayer = L.layerGroup().addTo(map);\n"
    "  function refreshGendarmerieLabels() {\n"
    "    gendLabelLayer.clearLayers();\n"
    "    for (var code in hdf) {\n"
    "      var d = hdf[code];\n"
    "      if (!d || !d.gend || !d.lat || !d.lng) continue;\n"
    "      var icon = L.divIcon({\n"
    "        className: '',\n"
    "        html: '<div style=\"text-align:center;pointer-events:none;white-space:nowrap;\">'\n"
    "            + '<div style=\"font-size:22px;line-height:1;\">\\ud83d\\ude94</div>'\n"
    "            + '<span style=\"font-size:10px;font-weight:800;color:#1e3a8a;'\n"
    "            + 'text-shadow:0 1px 2px rgba(255,255,255,0.95),0 0 6px rgba(255,255,255,0.9);\">'\n"
    "            + d.n + '</span>'\n"
    "            + '</div>',\n"
    "        iconSize: [120, 36],\n"
    "        iconAnchor: [60, 18]\n"
    "      });\n"
    "      L.marker([d.lat, d.lng], { icon: icon, interactive: false, keyboard: false })\n"
    "        .addTo(gendLabelLayer);\n"
    "    }\n"
    "  }\n"
    "  refreshGendarmerieLabels();",
    "Layer + fonction refreshGendarmerieLabels")

# Checks
for needle, label in [
    ('"80021":{"n":"Amiens"', "Amiens dans HDF_DATA"),
    ('"59009":{"n":"Villeneuve-d', "Villeneuve-d'Ascq dans HDF_DATA"),
    ("refreshGendarmerieLabels", "Fonction labels gendarmerie"),
    ("gendLabelLayer", "Layer gendarmerie"),
]:
    print(("  [OK] " if needle in html else "  [X] MANQUANT : ") + label)
    if needle not in html: ok = False

if not ok:
    print("\\n[!] Patch incomplet. Fichier NON ecrase. (backup .bakgend dispo)"); sys.exit(1)
if html == original:
    print("\\n[!] Aucune modification."); sys.exit(1)

SRC.write_text(html, encoding="utf-8")
print("\\n[OK] Patch gendarmerie applique ->", SRC)
print("   Taille :", "{:,}".format(len(html)), "caracteres")
