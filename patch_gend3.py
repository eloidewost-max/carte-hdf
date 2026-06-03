#!/usr/bin/env python3
import sys, shutil, json, re
from pathlib import Path

SRC = Path.home() / "Desktop/carte-politique-main/hdf-map.html"
FEAT = Path.home() / "Desktop/carte-politique-main/gend_features.json"

if not SRC.exists():
    print("ERREUR : hdf-map.html introuvable"); sys.exit(1)
if not FEAT.exists():
    print("ERREUR : gend_features.json introuvable (relance l'extraction)"); sys.exit(1)

shutil.copy(SRC, SRC.with_suffix(".html.bakgend3"))
print("Backup cree :", SRC.with_suffix(".html.bakgend3"))

html = SRC.read_text(encoding="utf-8")
feats = json.loads(FEAT.read_text(encoding="utf-8"))
print("Features a injecter :", [f['properties']['codgeo'] for f in feats])

# Localiser COMMUNES_GEO = { ... "features": [  <-- on insere juste apres le [
m = re.search(r'COMMUNES_GEO\s*=\s*', html)
if not m:
    print("  [X] COMMUNES_GEO introuvable"); sys.exit(1)

# Trouver la position de "features":[ a l'interieur de COMMUNES_GEO
# (premiere occurrence apres le signe =)
feat_marker = html.find('"features":[', m.end())
if feat_marker == -1:
    feat_marker = html.find('"features": [', m.end())
    insert_at = feat_marker + len('"features": [')
else:
    insert_at = feat_marker + len('"features":[')

if feat_marker == -1:
    print("  [X] '\"features\":[' introuvable dans COMMUNES_GEO"); sys.exit(1)

# Verifier qu'on est bien dans COMMUNES_GEO et pas HDF_BG_GEO
bg_pos = html.find('HDF_BG_GEO')
if bg_pos != -1 and feat_marker > bg_pos:
    print("  [X] On vise HDF_BG_GEO par erreur, pas COMMUNES_GEO"); sys.exit(1)

# Construire la chaine des 5 features (chacune suivie d'une virgule)
inject = ''.join(json.dumps(f, ensure_ascii=False, separators=(',',':')) + ',' for f in feats)

new_html = html[:insert_at] + inject + html[insert_at:]

# Verifications
ok = True
m2 = re.search(r'COMMUNES_GEO\s*=', new_html)
end = new_html.find('HDF_BG_GEO')
geo_part = new_html[m2.end():end]
for code in ['80021','02408','60057','62041','59009']:
    present = ('"'+code+'"') in geo_part
    print(("  [OK] " if present else "  [X] ") + code + " dans COMMUNES_GEO")
    if not present: ok = False

if not ok:
    print("\\n[!] Injection incomplete. Fichier NON ecrase."); sys.exit(1)

SRC.write_text(new_html, encoding="utf-8")
print("\\n[OK] 5 villes injectees dans COMMUNES_GEO (couche cliquable) ->", SRC)
print("   Taille :", "{:,}".format(len(new_html)), "caracteres")
